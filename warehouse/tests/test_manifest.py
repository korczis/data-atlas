"""Unit tests for the manifest validator and the migration planner.

Both are pure Python and need neither a database nor the network, and both guard
something the whole subsystem depends on: that a manifest describes artifacts
which can actually be fetched and verified, and that the SQL on disk still
matches the schema it claims to have produced.

Neither had a single test before an adversarial review pointed it out.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata import manifest as manifest_mod
from atlasdata import migrate

failures: list[str] = []
checks = 0


def check(label: str, actual, expected) -> None:
    global checks
    checks += 1
    if actual != expected:
        failures.append(f"{label}\n      expected {expected!r}\n      got      {actual!r}")


def _doc(**artifact_overrides) -> dict:
    """A minimal valid manifest, with one artifact that can be perturbed."""
    artifact = {
        "artifact_id": "a-1", "filename": "a.txt", "media_type": "text/plain",
        "compression": "none", "size_bytes": 10, "sha256": "a" * 64,
        "checksum_origin": "computed_on_retrieval", "parser_family": "text_gutenberg",
        "role": "primary",
        "retrievals": [{"priority": 1, "role": "mirror",
                        "url": "https://example.org/a.txt", "byte_stable": True}],
    }
    artifact.update(artifact_overrides)
    return {
        "schema_version": 1,
        "dataset": {"code": "d", "title": "D",
                    "publisher": {"code": "p", "name": "P"},
                    "license": {"basis": "us_government_work", "statement": "s"}},
        "editions": [{"edition_year": 2000, "edition_label": "D 2000",
                      "artifacts": [artifact]}],
    }


def _load(doc) -> tuple[bool, str]:
    """-> (accepted, message). Writes the doc to a temp dir and loads it."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "d.json").write_text(json.dumps(doc), encoding="utf-8")
        try:
            manifest_mod.load("d", manifests_dir=d)
            return True, ""
        except manifest_mod.ManifestError as exc:
            return False, str(exc)


# ── the valid case must load ─────────────────────────────────────────────────
ok, msg = _load(_doc())
check("a well-formed manifest loads", ok, True)

# ── each rejection condition ────────────────────────────────────────────────
ok, msg = _load(_doc(sha256="nothex"))
check("bad sha256 rejected", ok, False)
check("bad sha256 explained", "sha256" in msg, True)

ok, _ = _load(_doc(size_bytes=0))
check("zero size rejected", ok, False)

ok, _ = _load(_doc(retrievals=[]))
check("no retrievals rejected", ok, False)

ok, msg = _load(_doc(retrievals=[{"priority": 1, "role": "origin",
                                  "url": "https://example.org/a", "byte_stable": False}]))
check("no byte-stable retrieval rejected", ok, False)
check("byte-stable rejection explained", "byte-stable" in msg, True)

ok, _ = _load(_doc(retrievals=[{"priority": 1, "role": "mirror",
                                "url": "http://example.org/a", "byte_stable": True}]))
check("non-HTTPS retrieval rejected", ok, False)

ok, _ = _load(_doc(retrievals=[{"priority": 1, "role": "mirror", "byte_stable": True}]))
check("retrieval with no locator rejected", ok, False)

# duplicate artifact_id across two editions
dup = _doc()
dup["editions"].append({"edition_year": 2001, "edition_label": "D 2001",
                        "artifacts": [dict(dup["editions"][0]["artifacts"][0])]})
ok, msg = _load(dup)
check("duplicate artifact_id rejected", ok, False)
check("duplicate explained", "duplicate" in msg, True)

# same digest claimed with two different sizes
conflict = _doc()
second = dict(conflict["editions"][0]["artifacts"][0])
second["artifact_id"] = "a-2"
second["size_bytes"] = 99
conflict["editions"].append({"edition_year": 2001, "edition_label": "D 2001",
                             "artifacts": [second]})
ok, msg = _load(conflict)
check("conflicting sizes for one digest rejected", ok, False)

ok, _ = _load({**_doc(), "schema_version": 2})
check("unsupported schema_version rejected", ok, False)

# ── path traversal: the filename must be a plain basename ───────────────────
# A filename is the one manifest field that becomes a filesystem write, and
# pathlib silently discards the base directory when handed an absolute path.
for bad in ("/etc/cron.d/evil", "../../evil", "sub/dir.txt", "..", ""):
    ok, msg = _load(_doc(filename=bad))
    check(f"filename {bad!r} rejected", ok, False)

ok, _ = _load(_doc(filename="ordinary-name.txt"))
check("a plain basename is accepted", ok, True)

# ── the migration planner ───────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    (d / "0001_a.sql").write_text("SELECT 1;")
    (d / "0002_b.sql").write_text("SELECT 2;")
    found = migrate.discover(d)
    check("discover finds and orders migrations", [f.name for f in found],
          ["0001_a.sql", "0002_b.sql"])

    (d / "nonsense.sql").write_text("SELECT 3;")
    try:
        migrate.discover(d)
        check("malformed filename rejected", "accepted", "rejected")
    except migrate.MigrationError as exc:
        check("malformed filename rejected", "four-digit" in str(exc), True)
    (d / "nonsense.sql").unlink()

    (d / "0002_c.sql").write_text("SELECT 4;")
    try:
        migrate.discover(d)
        check("duplicate number rejected", "accepted", "rejected")
    except migrate.MigrationError as exc:
        check("duplicate number rejected", "duplicate" in str(exc), True)
    (d / "0002_c.sql").unlink()

    # checksum is stable and content-sensitive
    first = migrate.checksum(d / "0001_a.sql")
    check("checksum is deterministic", migrate.checksum(d / "0001_a.sql"), first)
    (d / "0001_a.sql").write_text("SELECT 1; -- edited")
    check("checksum changes when the file changes",
          migrate.checksum(d / "0001_a.sql") != first, True)

if failures:
    print(f"test_manifest: {len(failures)} of {checks} checks FAILED", file=sys.stderr)
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    raise SystemExit(1)
print(f"test_manifest: {checks} checks passed")
