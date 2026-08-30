"""The manifest: what artifacts exist, and what identifies their bytes.

Three things that look like one thing, and are not:

  * a **logical artifact** — "the 1990 Factbook as plain text";
  * its **bytes** — identified by SHA-256, and by nothing else;
  * its **retrievals** — the URLs that have, at some moment, returned those bytes.

Conflating them is the standard way an archive quietly rots. A URL is not an
identity: Project Gutenberg rewrites its own boilerplate, so the file at
`pg14.txt` today hashes differently from the same edition captured in 2026,
while the CIA text inside is unchanged. A digest is not proof of origin either
— it fixes bytes from the moment we first saw them, which is a different and
weaker claim than "this is what the CIA published". Both claims are recorded
separately, and `docs/database/RAW-DATA.md` says which is which.

The manifest is curated, committed data, in the same sense as
`data/sources/*.json`: a human decides what belongs in it, and a checker
verifies that what it describes is internally consistent.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import config

SHA256_HEX_LENGTH = 64


@dataclass(frozen=True)
class Retrieval:
    """One place bytes have been obtained from, and how much it can be trusted.

    `byte_stable` is the operational question: will fetching this URL again
    reproduce the recorded digest? For an immutable release asset, yes. For a
    live Gutenberg file or a `git archive` of a commit, no — those reproduce
    *content*, not bytes, and pinning a hash against them would turn a normal
    upstream edit into a verification failure.
    """

    priority: int
    role: str                      # "mirror" | "origin"
    url: str | None = None
    vcs: dict | None = None
    byte_stable: bool = False
    note: str = ""


def _bad_filename(filename: str) -> bool:
    """True when a filename could leave the directory it is joined to."""
    return filename != Path(filename).name or filename in ("", ".", "..")


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    edition_year: int
    edition_label: str
    filename: str
    media_type: str
    compression: str
    size_bytes: int
    sha256: str
    checksum_origin: str
    parser_family: str
    role: str                      # "primary" | "repair" | "superseded"
    retrievals: tuple[Retrieval, ...]
    notes: str = ""

    @property
    def ingestable(self) -> bool:
        """Superseded artifacts are kept so the failure stays auditable.

        The 2001 HTML zip is the case this exists for: the preservation project
        recorded it as corrupt and fell back to the Gutenberg text. Deleting it
        from the manifest would erase the evidence that 2001 is a special case;
        ingesting it would import garbage. It is fetched, hashed and never
        parsed.
        """
        return self.role in ("primary", "repair")

    def __post_init__(self) -> None:
        # The guard belongs on the type, not on one call site. _validate() runs
        # inside load(); anything constructing an Artifact directly — a test
        # helper, a future CLI subcommand — would otherwise skip it and hand a
        # traversing filename straight to path(), which is exactly the hole the
        # validator was added to close.
        if _bad_filename(self.filename):
            raise ValueError(
                f"{self.artifact_id}: filename {self.filename!r} is not a plain "
                f"basename — it must contain no path separator and no '..'")

    def path(self, raw_dir: Path | None = None) -> Path:
        """Content-addressed location: `<sha256>/<original-filename>`.

        The digest is the directory, so two artifacts with identical bytes and
        different names cannot collide, re-downloading a changed remote file
        cannot overwrite the old one, and a corrupted partial write cannot be
        mistaken for a good copy. ADR-0003.
        """
        return (raw_dir or config.RAW) / self.sha256 / self.filename

    def best_retrieval(self) -> Retrieval:
        return min(self.retrievals, key=lambda r: r.priority)


@dataclass(frozen=True)
class Dataset:
    code: str
    title: str
    publisher: dict
    license: dict
    status: str = "active"
    discontinued_note: str = ""
    upstream_manifest: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Manifest:
    dataset: Dataset
    artifacts: tuple[Artifact, ...]

    def by_id(self, artifact_id: str) -> Artifact:
        for a in self.artifacts:
            if a.artifact_id == artifact_id:
                return a
        raise KeyError(f"no artifact {artifact_id!r} in manifest {self.dataset.code!r}")

    def select(self, *, years: set[int] | None = None,
               families: set[str] | None = None,
               artifact_ids: set[str] | None = None,
               ingestable_only: bool = False) -> list[Artifact]:
        out = []
        for a in self.artifacts:
            if years is not None and a.edition_year not in years:
                continue
            if families is not None and a.parser_family not in families:
                continue
            if artifact_ids is not None and a.artifact_id not in artifact_ids:
                continue
            if ingestable_only and not a.ingestable:
                continue
            out.append(a)
        return out

    @property
    def years(self) -> list[int]:
        return sorted({a.edition_year for a in self.artifacts})


class ManifestError(ValueError):
    """A manifest that cannot be trusted. Never downgraded to a warning."""


def load(dataset_code: str, manifests_dir: Path | None = None) -> Manifest:
    path = (manifests_dir or config.MANIFESTS) / f"{dataset_code.replace('_', '-')}.json"
    if not path.exists():
        raise ManifestError(f"no manifest at {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))

    if doc.get("schema_version") != 1:
        raise ManifestError(f"{path}: unsupported schema_version {doc.get('schema_version')!r}")

    d = doc["dataset"]
    dataset = Dataset(
        code=d["code"], title=d["title"], publisher=d["publisher"],
        license=d["license"], status=d.get("status", "active"),
        discontinued_note=d.get("discontinued_note", ""),
        upstream_manifest=d.get("upstream_manifest", {}),
    )

    artifacts: list[Artifact] = []
    # A traversing filename would raise out of Artifact.__post_init__ on the
    # first offender. Collected here instead, so the manifest report names every
    # problem at once rather than one per re-run; the constructor stays the
    # backstop for anything built outside load().
    bad_names = [f"{a['artifact_id']}: filename {a['filename']!r} is not a plain "
                 f"basename — it must contain no path separator and no '..'"
                 for ed in doc["editions"] for a in ed["artifacts"]
                 if _bad_filename(a["filename"])]
    if bad_names:
        raise ManifestError(f"{path}: " + "; ".join(bad_names))

    for ed in doc["editions"]:
        for a in ed["artifacts"]:
            artifacts.append(Artifact(
                artifact_id=a["artifact_id"],
                edition_year=ed["edition_year"],
                edition_label=ed["edition_label"],
                filename=a["filename"],
                media_type=a["media_type"],
                compression=a["compression"],
                size_bytes=a["size_bytes"],
                sha256=a["sha256"].lower(),
                checksum_origin=a["checksum_origin"],
                parser_family=a["parser_family"],
                role=a["role"],
                retrievals=tuple(
                    Retrieval(priority=r["priority"], role=r["role"], url=r.get("url"),
                              vcs=r.get("vcs"), byte_stable=bool(r.get("byte_stable")),
                              note=r.get("note", ""))
                    for r in a["retrievals"]),
                notes=a.get("notes", ""),
            ))

    manifest = Manifest(dataset=dataset, artifacts=tuple(artifacts))
    _validate(manifest, path)
    return manifest


def _validate(m: Manifest, path: Path) -> None:
    """Internal consistency. A manifest is a promise; this is the audit of it."""
    problems: list[str] = []

    seen_ids: set[str] = set()
    for a in m.artifacts:
        if a.artifact_id in seen_ids:
            problems.append(f"duplicate artifact_id {a.artifact_id!r}")
        seen_ids.add(a.artifact_id)

        if len(a.sha256) != SHA256_HEX_LENGTH or not all(
                c in "0123456789abcdef" for c in a.sha256):
            problems.append(f"{a.artifact_id}: sha256 is not 64 hex characters")
        if a.size_bytes <= 0:
            problems.append(f"{a.artifact_id}: non-positive size_bytes")

        # The filename is the one manifest field that maps directly onto a
        # filesystem write: Artifact.path() builds `raw/<sha256>/<filename>`.
        # pathlib discards everything to the left of an absolute component, so
        # a filename of "/etc/cron.d/x" resolves to exactly that path and the
        # fetcher would create the directory and write verified bytes into it.
        # A "../.." filename escapes the same way once the OS resolves it.
        #
        # Manifests are curated and reviewed, so this is defence in depth rather
        # than a live hole — but the validator's whole job is to check that a
        # manifest is safe to act on, and it was silently skipping the only
        # field that can leave the raw directory.
        #
        # Artifact.__post_init__ enforces the same rule, so an unchecked
        # Artifact cannot exist at all. This copy stays because it names the
        # offending artifact_id and reports alongside every other manifest
        # problem, rather than aborting on the first one.
        if not a.retrievals:
            problems.append(f"{a.artifact_id}: no retrieval source — unfetchable")
        if not any(r.byte_stable for r in a.retrievals):
            problems.append(
                f"{a.artifact_id}: no byte-stable retrieval, so the recorded "
                f"sha256 can never be reproduced by fetching")
        for r in a.retrievals:
            if r.url is None and r.vcs is None:
                problems.append(f"{a.artifact_id}: retrieval with neither url nor vcs")
            if r.url and not r.url.startswith("https://"):
                problems.append(f"{a.artifact_id}: non-HTTPS retrieval {r.url!r}")

    # Two artifacts claiming different bytes under one digest is a contradiction;
    # the same digest reached by several URLs is normal and expected (§164).
    by_digest: dict[str, set[int]] = {}
    for a in m.artifacts:
        by_digest.setdefault(a.sha256, set()).add(a.size_bytes)
    for digest, sizes in by_digest.items():
        if len(sizes) > 1:
            problems.append(f"digest {digest[:12]}… claimed with conflicting sizes {sorted(sizes)}")

    if problems:
        raise ManifestError(f"{path}:\n" + "\n".join(f"  - {p}" for p in problems))
