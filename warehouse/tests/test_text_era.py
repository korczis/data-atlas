"""Unit tests for the plain-text parser's structural rules.

Needs neither the corpus nor a database: the fixtures below are the shapes that
actually occur, reduced to the smallest form that still exercises the rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata.parsers.text_era import (
    _is_back_matter,
    _match_marker,
    _parse_section,
)

failures: list[str] = []
checks = 0


def check(label: str, actual, expected) -> None:
    global checks
    checks += 1
    if actual != expected:
        failures.append(f"{label}\n      expected {expected!r}\n      got      {actual!r}")


# ── the five marker conventions across the text era ──────────────────────────

for line, entity, section in [
    ("@Czech Republic:Geography",      "Czech Republic", "Geography"),
    (":Afghanistan Geography",         "Afghanistan",    "Geography"),
    ("*Afghanistan, Geography",        "Afghanistan",    "Geography"),
    ("@Afghanistan, Geography",        "Afghanistan",    "Geography"),
    ("Czech Republic    Introduction", "Czech Republic", "Introduction"),
]:
    m = _match_marker(line)
    check(f"marker {line!r} entity", m.group("entity").strip() if m else None, entity)
    check(f"marker {line!r} section", m.group("section").strip() if m else None, section)

check("prose is not a marker", _match_marker("Terrain: mostly mountainous"), None)
check("bare country name is not a marker", _match_marker("Czech Republic"), None)

# ── back matter ──────────────────────────────────────────────────────────────
# Regression: the 2001 edition continues after its last country with
# "@Administrative divisions", a cross-country appendix. Without a boundary the
# final country's last section swallowed 141,099 lines and Czech content was
# attributed to Zimbabwe.

check("rule of equals is back matter", _is_back_matter("=" * 70), True)
check("short equals run is not", _is_back_matter("==="), False)
check("appendix heading is back matter", _is_back_matter("@Administrative divisions"), True)
check("a real marker is not back matter", _is_back_matter("@Czech Republic:Geography"), False)

# Five entities in this corpus have a comma inside their own name. The
# comma-separated marker form used by 1993 and 1994 matched none of their marker
# lines, which lost every field of all five: in 1993 they were re-attributed to
# whichever country preceded them alphabetically, and in 1994 the "@" prefix
# made the back-matter guard delete them outright, with zero failures reported.
for line, entity, section in (
        ("*Korea, North, Geography", "Korea, North", "Geography"),
        ("@Korea, South, People", "Korea, South", "People"),
        ("@Man, Isle of, Government", "Man, Isle of", "Government"),
        ("*Micronesia, Federated States of, Geography",
         "Micronesia, Federated States of", "Geography"),
        ("@Pacific Islands, Trust Territory of the (Palau), Economy",
         "Pacific Islands, Trust Territory of the (Palau)", "Economy"),
        ("@Pacific Islands (Palau), Trust Territory of the, Economy",
         "Pacific Islands (Palau), Trust Territory of the", "Economy")):
    m = _match_marker(line)
    check(f"{entity!r} marker matches", m is not None, True)
    if m:
        check(f"{entity!r} entity", m.group("entity"), entity)
        check(f"{entity!r} section", m.group("section"), section)
    # The 1994 failure mode: an unmatched "@" marker reads as an appendix
    # boundary and truncates everything after it.
    check(f"{entity!r} is not back matter",
          _is_back_matter("@" + line.lstrip("*@")), False)

# 1992 ends its last country with eight asterisks, not ten. Two characters
# short of the old threshold put that separator into Zimbabwe as a field value.
check("eight asterisks are a rule", _is_back_matter("*" * 8), True)
check("six dashes are a rule", _is_back_matter("-" * 6), True)
check("three equals are not", _is_back_matter("==="), False)
check("a comma-form marker is not back matter", _is_back_matter("@Afghanistan, Geography"), False)
check("ordinary prose is not back matter", _is_back_matter("Location: Central Europe"), False)

# ── field and subfield structure ─────────────────────────────────────────────
# Case carries the structure: a Capitalised label is a field, a lower-case one at
# the same indent is its subfield. Keying on indentation instead produced one
# field containing every subfield run together.

body = [
    " Location: Central Europe, southeast of Germany",
    "",
    " Area:",
    " total area: 78,703 sq km",
    " land area: 78,645 sq km",
    "",
    " Land boundaries: total 1,880 km, Austria 362 km,",
    " Poland 658 km",
]
fields, fails = _parse_section(body, "Geography", "test.txt", "Czech Republic")
by = {(f.field_name, f.subfield_name): f.raw_text for f in fields}

check("simple field", by.get(("Location", "")), "Central Europe, southeast of Germany")
check("subfield total area", by.get(("Area", "total area")), "78,703 sq km")
check("subfield land area", by.get(("Area", "land area")), "78,645 sq km")
check("area has no bare value", ("Area", "") in by, False)
check("wrapped value is rejoined",
      by.get(("Land boundaries", "")),
      "total 1,880 km, Austria 362 km, Poland 658 km")
check("no unattached lines", len(fails), 0)

# A line before any field label is unattached, and is reported rather than dropped.
fields, fails = _parse_section(["orphan text with no label"], "Geography", "t", "X")
check("orphan produces no field", len(fields), 0)
check("orphan is reported", len(fails), 1)
check("orphan keeps its text", fails[0]["raw_input"], "orphan text with no label")

if failures:
    print(f"test_text_era: {len(failures)} of {checks} checks FAILED", file=sys.stderr)
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    raise SystemExit(1)
print(f"test_text_era: {checks} checks passed")
