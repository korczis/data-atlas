"""JSON-era parser, 2021-2025: fixtures for the third parser family.

Like `test_html_era.py`, this exists because nothing exercised `json_era.py`.
The fixture below is the real shape of `cache.factbook.json` -- an entry file
carrying `categories -> fields -> subfields`, read out of the 2023 archive and
cut down.

The load-bearing assertion is the one about `value` and `suffix`. Those keys are
the archiving project's own parse of the CIA text, not the CIA's data. A parser
that read them would be republishing somebody else's arithmetic as the
publisher's statement, and the difference is invisible once it is in the
database. This parser reads `content` and derives its own numbers later.

Needs no database, no network and no downloaded corpus.

    just wh-test
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata.parsers import json_era

failures: list[str] = []
checks = 0


def check(label: str, got, want) -> None:
    global checks
    checks += 1
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


ENTRY = {
    "name": "Angola",
    "code": "ao",
    "region": "africa",
    "categories": [
        {"id": "introduction", "title": "Introduction",
         "fields": [{"name": "Background", "field_id": 325,
                     "content": "Bantu-speaking people settled in the area."}]},
        {"id": "geography", "title": "Geography",
         "fields": [{"name": "Area", "field_id": 279,
                     "content": "<strong>total: </strong>1,246,700 sq km"
                                "<br><br><strong>land: </strong>1,246,700 sq km",
                     "subfields": [
                         {"name": "total", "content": "1,246,700 sq km",
                          "value": "1246700", "suffix": "sq km"},
                         {"name": "land", "content": "1,246,700 sq km",
                          "value": "1246700", "suffix": "sq km"}]}]},
    ],
}


def _zip(members: dict[str, str]) -> Path:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in members.items():
            z.writestr(name, body)
    return Path(path)


p = _zip({"africa/ao.json": json.dumps(ENTRY),
          "README.md": "not an entry"})
out = json_era.parse_artifact(p)
os.unlink(p)

check("one entry is produced", len(out.entries), 1)
check("no failures on a well-formed archive", out.failures, [])

entry = out.entries[0] if out.entries else None
if entry:
    check("entry name", entry.source_name, "Angola")
    check("entry key is the code", entry.source_key, "ao")
    by = {(f.section_name, f.field_name, f.subfield_name): f.raw_text
          for f in entry.fields}
    check("section comes from the category title",
          by.get(("Introduction", "Background", "")),
          "Bantu-speaking people settled in the area.")
    check("subfields are split out",
          by.get(("Geography", "Area", "total")), "1,246,700 sq km")
    check("second subfield", by.get(("Geography", "Area", "land")),
          "1,246,700 sq km")
    check("markup is stripped from the text",
          any("<strong>" in v for v in by.values()), False)
    # The whole reason this family is priority 3 rather than 2.
    check("upstream's parsed value is never taken as the published text",
          any(v == "1246700" for v in by.values()), False)
    check("upstream's suffix is never taken as the published text",
          any(v == "sq km" for v in by.values()), False)

# An entry with no name cannot be resolved to a country; it is reported rather
# than attached to whatever came before it.
p = _zip({"africa/xx.json": json.dumps({"code": "xx", "categories": []})})
out = json_era.parse_artifact(p)
os.unlink(p)
check("a nameless entry produces no entry", out.entries, [])
check("a nameless entry is reported", len(out.failures), 1)
check("nameless entry code", out.failures[0]["error_code"], "entry_without_name")

# Undecodable JSON is quarantined with its pointer, never skipped.
p = _zip({"africa/ao.json": "{not json"})
out = json_era.parse_artifact(p)
os.unlink(p)
check("bad JSON yields no entries", out.entries, [])
check("bad JSON is reported", out.failures[0]["error_code"], "json_undecodable")

# Zip-slip and the decompression ceiling, as for the HTML family.
p = _zip({"africa/ao.json": json.dumps(ENTRY),
          "../escape.json": json.dumps(ENTRY)})
out = json_era.parse_artifact(p)
os.unlink(p)
codes = {f["error_code"] for f in out.failures}
check("a traversing member is refused", "unsafe_member_path" in codes, True)
check("the legitimate member still parses", len(out.entries), 1)

big = json.dumps({"name": "X", "code": "xx", "note": "A" * (
    json_era.MAX_MEMBER_BYTES + 1024), "categories": []})
p = _zip({"africa/xx.json": big})
out = json_era.parse_artifact(p)
os.unlink(p)
codes = {f["error_code"] for f in out.failures}
check("an oversized member is refused", "member_too_large" in codes, True)
check("no entry is produced from it", out.entries, [])

if failures:
    print(f"test_json_era: {len(failures)} of {checks} checks FAILED", file=sys.stderr)
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    raise SystemExit(1)
print(f"test_json_era: {checks} checks passed")
