"""Acquisition: get bytes, prove they are the right bytes, never overwrite.

Design rules, each of which exists because the opposite fails quietly:

  * **Content-addressed.** A finished artifact lives at `<sha256>/<filename>`.
    A remote file that changes therefore lands somewhere new instead of
    destroying the copy that the database's provenance already points at.
  * **Verify before commit.** Bytes are written to `.partial`, hashed, and only
    renamed into place if the digest matches. A truncated download is never
    visible under its final name, so "the file exists" and "the file is correct"
    are the same statement.
  * **Idempotent.** An artifact already present with the right digest is not
    re-fetched. Re-running `fetch --all` over a complete corpus does no network
    I/O at all.
  * **Refuse rather than guess.** A digest mismatch is an error with both hashes
    printed. It is never repaired by overwriting, and never downgraded to a
    warning, because the one thing worse than a failed download is a corpus that
    reports success while holding the wrong bytes.

Politeness is not optional: one connection at a time, an identifying
User-Agent, explicit timeouts, bounded retries with exponential backoff, and
Range resumption where the server offers it. Nothing here follows redirects to
a non-HTTPS scheme, executes anything it downloads, or attempts to defeat any
access control.
"""
from __future__ import annotations

import hashlib
import ipaddress
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from . import config
from .logging import log
from .manifest import Artifact

CHUNK = 1024 * 256
DEFAULT_TIMEOUT = 60.0
MAX_ATTEMPTS = 4
BACKOFF_BASE = 2.0
MAX_REDIRECTS = 8
# How far a server may overshoot its declared size before the read is
# abandoned. Small: the digest must match exactly anyway, so any overshoot
# is already a failure — this only bounds how much disk it can waste first.
OVERSHOOT_SLACK = 1024 * 1024


class FetchError(RuntimeError):
    pass


class DigestMismatch(FetchError):
    def __init__(self, artifact: Artifact, actual: str, size: int):
        self.artifact, self.actual, self.size = artifact, actual, size
        super().__init__(
            f"{artifact.artifact_id}: digest mismatch\n"
            f"    expected sha256 {artifact.sha256} ({artifact.size_bytes:,} bytes)\n"
            f"    got      sha256 {actual} ({size:,} bytes)\n"
            f"    The bytes on disk were NOT accepted. If the remote file has "
            f"legitimately changed, add a new artifact record with the new "
            f"digest — never edit the old one (ADR-0003).")


@dataclass
class FetchResult:
    artifact: Artifact
    path: Path
    status: str            # "present" | "downloaded" | "skipped"
    bytes_downloaded: int
    retrieval_url: str | None
    http_etag: str | None = None
    http_last_modified: str | None = None
    retrieved_at: str | None = None


def sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _public_address(host: str) -> None:
    """Refuse a host that resolves to an address inside the local network.

    Redirect-following is load-bearing here — Wayback redirects between captures
    — which means a trusted mirror can send the fetcher anywhere. Without this,
    one redirect reaches `169.254.169.254` and the cloud metadata service
    answers, over HTTPS, from a host the manifest never named.

    Every resolved address must be public: a name resolving to one public and
    one loopback address is refused, not partially trusted. This does not close
    DNS rebinding — the name is resolved here and again by urllib, and a record
    with a one-second TTL can differ between the two. Closing that needs the
    connection pinned to the address that was checked, which urllib does not
    expose. The check is worth having anyway: it stops the redirect and the
    misconfigured-manifest cases, which are the reachable ones.
    """
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise FetchError(f"cannot resolve {host!r}: {exc}") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise FetchError(
                f"refusing {host!r}: resolves to non-public address {ip}")


def _https_only(url: str) -> None:
    if not url.startswith("https://"):
        raise FetchError(f"refusing non-HTTPS URL: {url!r}")
    host = urllib.parse.urlsplit(url).hostname
    if not host:
        raise FetchError(f"refusing URL with no host: {url!r}")
    _public_address(host)


def _open(url: str, *, offset: int = 0, timeout: float) -> urllib.request.addinfourl:
    """Open a URL, following redirects manually so every hop stays HTTPS.

    urllib would follow a cross-scheme redirect to plain HTTP without comment.
    Wayback in particular redirects between captures, so redirects are normal
    here and must be handled, not disabled.
    """
    seen = 0
    current = url
    while True:
        _https_only(current)
        req = urllib.request.Request(current, method="GET")
        req.add_header("User-Agent", config.user_agent())
        req.add_header("Accept", "*/*")
        if offset:
            req.add_header("Range", f"bytes={offset}-")
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            return opener.open(req, timeout=timeout)
        except _Redirect as r:
            seen += 1
            if seen > MAX_REDIRECTS:
                raise FetchError(f"too many redirects from {url!r}") from None
            current = r.location


class _Redirect(Exception):
    def __init__(self, location: str):
        self.location = location


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise _Redirect(urllib.parse.urljoin(req.full_url, newurl))



def fetch_artifact(artifact: Artifact, *, raw_dir: Path | None = None,
                   timeout: float = DEFAULT_TIMEOUT,
                   dry_run: bool = False) -> FetchResult:
    """Ensure `artifact`'s bytes are on disk under their digest."""
    final = artifact.path(raw_dir)

    if final.exists():
        # Trust the location, but confirm the size cheaply. A full re-hash of
        # 3 GB on every status call would make verification something people
        # skip; `verify` does the real check.
        if final.stat().st_size == artifact.size_bytes:
            return FetchResult(artifact, final, "present", 0, None)
        log("warn", f"{artifact.artifact_id}: wrong size on disk, re-fetching",
            expected=artifact.size_bytes, found=final.stat().st_size)

    retrieval = next((r for r in sorted(artifact.retrievals, key=lambda x: x.priority)
                      if r.url and r.byte_stable), None)
    if retrieval is None:
        raise FetchError(
            f"{artifact.artifact_id}: no byte-stable URL to fetch from. Its origin "
            f"is a git commit or a mutable page; see the manifest notes.")

    if dry_run:
        return FetchResult(artifact, final, "skipped", 0, retrieval.url)

    final.parent.mkdir(parents=True, exist_ok=True)
    partial = final.with_suffix(final.suffix + ".partial")

    downloaded, etag, last_modified = _download(retrieval.url, partial, artifact, timeout)

    actual, size = sha256_file(partial)
    if actual != artifact.sha256 or size != artifact.size_bytes:
        # Keep the evidence next to the expected location rather than deleting
        # it; a mismatch is something to investigate, not to tidy away.
        bad = final.parent / (artifact.filename + f".rejected-{actual[:12]}")
        partial.replace(bad)
        raise DigestMismatch(artifact, actual, size)

    os.replace(partial, final)          # atomic within the filesystem
    return FetchResult(artifact, final, "downloaded", downloaded, retrieval.url,
                       etag, last_modified, datetime.now(UTC).isoformat())


def _download(url: str, partial: Path, artifact: Artifact,
              timeout: float) -> tuple[int, str | None, str | None]:
    """Fetch to `partial`, resuming and retrying with exponential backoff."""
    etag = last_modified = None
    total_written = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        try:
            resp = _open(url, offset=offset, timeout=timeout)
        except (urllib.error.URLError, OSError, FetchError) as exc:
            if attempt == MAX_ATTEMPTS:
                raise FetchError(f"{artifact.artifact_id}: {url} failed after "
                                 f"{MAX_ATTEMPTS} attempts: {exc}") from exc
            delay = BACKOFF_BASE ** attempt
            log("warn", f"{artifact.artifact_id}: {type(exc).__name__}, retry in {delay:.0f}s",
                attempt=attempt)
            time.sleep(delay)
            continue

        with resp:
            status = getattr(resp, "status", 200)
            etag = resp.headers.get("ETag") or etag
            last_modified = resp.headers.get("Last-Modified") or last_modified

            # 206 means the server honoured Range and we append; anything else
            # means it sent the whole file and a resumed offset would corrupt.
            append = status == 206 and offset > 0
            mode = "ab" if append else "wb"
            if not append:
                total_written = 0

            # Bound the write against the declared size. The size was only
            # checked after the response was fully drained, so a server sending
            # more bytes than it declared -- misconfigured, compromised, or
            # simply wrong -- would fill the disk before the mismatch was
            # noticed. The pre-flight free-space check cannot help: it is
            # computed from the *expected* size. Slack allows the server to
            # overshoot slightly before we stop reading and report it.
            ceiling = artifact.size_bytes + OVERSHOOT_SLACK
            with partial.open(mode) as fh:
                written_here = offset if append else 0
                while chunk := resp.read(CHUNK):
                    written_here += len(chunk)
                    if written_here > ceiling:
                        raise FetchError(
                            f"{artifact.artifact_id}: {url} sent more than the "
                            f"declared {artifact.size_bytes:,} bytes "
                            f"(stopped at {written_here:,}); refusing to keep "
                            f"writing. The bytes are not what the manifest "
                            f"describes.")
                    fh.write(chunk)
                    total_written += len(chunk)

        got = partial.stat().st_size
        if got == artifact.size_bytes:
            return total_written, etag, last_modified

        if attempt == MAX_ATTEMPTS:
            raise FetchError(
                f"{artifact.artifact_id}: short read from {url} — "
                f"{got:,} of {artifact.size_bytes:,} bytes after {MAX_ATTEMPTS} attempts")
        log("warn", f"{artifact.artifact_id}: short read, resuming",
            have=got, want=artifact.size_bytes)
        time.sleep(BACKOFF_BASE ** attempt)

    raise FetchError(f"{artifact.artifact_id}: unreachable")   # pragma: no cover


def verify_artifact(artifact: Artifact, *, raw_dir: Path | None = None) -> tuple[bool, str]:
    """Re-hash what is on disk. This is the check that actually means something."""
    path = artifact.path(raw_dir)
    if not path.exists():
        return False, "absent"
    actual, size = sha256_file(path)
    if actual != artifact.sha256:
        return False, f"digest mismatch (got {actual[:16]}…)"
    if size != artifact.size_bytes:
        return False, f"size mismatch (got {size:,})"
    return True, "ok"
