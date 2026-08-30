"""HTML-era parser: three site generations, from fixtures rather than the corpus.

These tests exist because their absence was demonstrated to be dangerous. With
no fixture anywhere for `html_era.py`, changing a single token in `_parse_gen_b`
-- `category_data` to `category-data` -- made the parser return zero fields and
zero failures for the whole 2009-2016 generation, and every one of the other
test files still passed. An entire era of the corpus could go dark silently.

The markup below is modelled on real pages read out of the archives (2005 for
generation A, 2012 for B, 2018 for C), reduced to the smallest shape that still
exercises the structure each parser keys on. It is deliberately not invented:
the attribute names, the icon links that must be ignored, and the title shapes
are the ones the CIA actually published.

Needs no database, no network and no downloaded corpus, so it runs in
`just check`.

    just wh-test
"""
from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata.parsers import html_era
from atlasdata.parsers.html_era import (
    _country_name,
    detect_generation,
    parse_country_page,
)

failures: list[str] = []
checks = 0


def check(label: str, got, want) -> None:
    global checks
    checks += 1
    if got != want:
        failures.append(f"{label}: got {got!r}, want {want!r}")


# ── generation A, 2002-2008 ──────────────────────────────────────────────────
#
# A table layout. The label sits in a FieldLabel cell; the value cell opens with
# two icon links -- a dictionary graphic and a field-listing graphic -- which are
# apparatus and must not become part of the value.
GEN_A = """<html><head><title>CIA - The World Factbook -- Aruba</title></head>
<body><table>
<tr><td width="20%" valign="top" class="FieldLabel"><div align="right">Background:</div></td>
    <td valign="top" width="80%">
      <a href="../docs/notesanddefs.html#2028"><img src="../graphics/dictionary.jpg" alt="Definition"></a>
      <a href="../fields/2028.html"><img src="../graphics/listing.jpg" alt="Field Listing"></a>
      Discovered and claimed for Spain in 1499.
    </td></tr>
<tr><td class="FieldLabel"><div align="right">Area:</div></td>
    <td><i>total:</i> 180 sq km<br><i>land:</i> 180 sq km</td></tr>
</table></body></html>"""

check("generation A is detected", detect_generation(GEN_A), "A")
title, fields, fails = parse_country_page(GEN_A, "geos/aa.html")
by_name = {(f.field_name, f.subfield_name): f.raw_text for f in fields}
check("A: background value", by_name.get(("Background", "")),
      "Discovered and claimed for Spain in 1499.")
check("A: icon alt text is not the value",
      any("Definition" in v or "Field Listing" in v for v in by_name.values()),
      False)
check("A: subfields are split", by_name.get(("Area", "total")), "180 sq km")
check("A: second subfield", by_name.get(("Area", "land")), "180 sq km")
check("A: no bare Area value", ("Area", "") in by_name, False)
check("A: no failures", fails, [])

# ── generation B, 2009-2016 ──────────────────────────────────────────────────
#
# The label is an anchor inside `id="field"`; the value follows in a
# `class="category_data"` div in a separate cell. This generation marks no
# section in its country pages, so section is recorded empty rather than guessed.
GEN_B = """<html><head><title>CIA - The World Factbook</title></head>
<body><table>
<tr><td><div style="padding-left:5px;" id="field">
      <a href="../docs/notesanddefs.html#2028" title="Definitions and Notes: Background">Background</a>:
    </div></td>
    <td align="right"><a href="../fields/2028.html#at"><img src="../graphics/field_listing_on.gif"
       alt="Field info displayed for all countries in alpha order."></a></td></tr>
<tr><td id="data" colspan="2"><div class="category_data">These uninhabited islands came
      under Australian authority in 1931.</div></td></tr>
</table></body></html>"""

check("generation B is detected", detect_generation(GEN_B), "B")
title, fields, fails = parse_country_page(GEN_B, "geos/at.html")
check("B: exactly one field parsed", len(fields), 1)
if fields:
    check("B: field name", fields[0].field_name, "Background")
    check("B: value", fields[0].raw_text,
          "These uninhabited islands came under Australian authority in 1931.")
    check("B: section is empty, not guessed", fields[0].section_name, "")
# The regression this file exists for: if the class token stops matching, this
# is the assertion that fails instead of the corpus silently emptying.
check("B: a page with fields never parses to nothing", len(fields) > 0, True)

# ── generation C, 2017-2020 ──────────────────────────────────────────────────
#
# The anchor id names both section and field; the value lives in id="field-<slug>".
GEN_C = """<html><head>
<title>Oceans :: Indian Ocean &mdash; The World Factbook - Central Intelligence Agency</title>
</head><body>
<div class="category" id="field-anchor-geography-area">
  <span class="btn-tooltip definition"><a href="../docs/notesanddefs.html#279">Area</a>:
    <span class="tooltip-content">This entry includes three subfields.</span></span>
  <div id="field-area">
    <span class="subfield-name">total:</span> <span class="subfield-number">83,871 sq km</span>
  </div>
</div></body></html>"""

check("generation C is detected", detect_generation(GEN_C), "C")
title, fields, fails = parse_country_page(GEN_C, "geos/xo.html")
by_name = {(f.section_name, f.field_name, f.subfield_name): f.raw_text for f in fields}
check("C: section comes from the anchor id",
      any(k[0] == "Geography" for k in by_name), True)
check("C: field name", any(k[1] == "Area" for k in by_name), True)
check("C: tooltip prose is not the value",
      any("This entry includes three subfields" in v for v in by_name.values()),
      False)

# ── unknown markup is refused, loudly ────────────────────────────────────────
#
# The 2000 edition labels fields with inline <b> tags and matches none of the
# three signatures. It must fail with a code, not parse to an empty success.
GEN_2000 = ("<html><head><title>CIA -- The World Factbook 2000 -- Aruba</title></head>"
            "<body><a name=\"Geo\">Geography</a><b>Background:</b> Some prose.</body></html>")
check("2000 markup matches no known generation",
      detect_generation(GEN_2000), "unknown")
title, fields, fails = parse_country_page(GEN_2000, "geos/aa.html")
check("unknown markup yields no fields", fields, [])
check("unknown markup is reported, not swallowed", len(fails), 1)
check("unknown markup error code", fails[0]["error_code"],
      "html_generation_unrecognised")

# A forwarding page is not an unreadable format: the target is another member of
# the same archive and is parsed on its own. Conflating the two overstated the
# unparsed count by 19 pages.
REDIRECT = ("<html><head><title>Redirect page</title>"
            "<meta http-equiv=\"refresh\" content=\"0;url=um.html\">"
            "</head><body></body></html>")
title, fields, fails = parse_country_page(REDIRECT, "geos/fq.html")
check("redirect stub is classified apart", fails[0]["error_code"],
      "html_redirect_stub")
check("redirect stub names its target", "um.html" in fails[0]["reason"], True)

# ── country naming ───────────────────────────────────────────────────────────
#
# A wrong name resolves to a wrong country, which is worse than no name, so the
# last resort is the code rather than a guess. These are the four real title
# shapes across the eras.
check("name from a 2002-2008 title",
      _country_name("", "CIA - The World Factbook -- Aruba", "aa"), "Aruba")
check("name from a 2017-2020 title, which puts the region first",
      _country_name("", "Europe :: Czechia — The World Factbook - "
                        "Central Intelligence Agency", "ez"), "Czechia")
check("name from a 2016 title with no country at all",
      _country_name("", "The World Factbook — Central Intelligence Agency",
                    "xx"), "XX")
check("name falls back to the code, never to the publisher",
      _country_name("", "CIA - The World Factbook", "fr"), "FR")
check("publisher is never accepted as a country name",
      _country_name("", "Central Intelligence Agency", "us"), "US")

# ── archive handling ─────────────────────────────────────────────────────────


def _zip(members: dict[str, str]) -> Path:
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in members.items():
            z.writestr(name, body)
    return Path(path)


p = _zip({"factbook/geos/aa.html": GEN_A,
          "factbook/graphics/flag.gif": "not html",
          "factbook/fields/2028.html": "<html>field listing</html>"})
out = html_era.parse_artifact(p)
check("only geos/ members become entries", len(out.entries), 1)
check("apparatus is counted, not quarantined", out.failures, [])
check("skipped members are counted", out.skipped_members > 0, True)
os.unlink(p)

# Zip-slip: a member path that escapes its root is refused even though it
# matches the geos pattern.
p = _zip({"factbook/geos/aa.html": GEN_A,
          "some/../geos/yy.html": GEN_A})
out = html_era.parse_artifact(p)
codes = {f["error_code"] for f in out.failures}
check("a traversing member is refused", "unsafe_member_path" in codes, True)
check("the legitimate member still parses", len(out.entries), 1)
os.unlink(p)

# A member whose declared size is a lie. zipfile stops at the declared length,
# so the ceiling has to count bytes actually decompressed.
big = "<html>" + "A" * (html_era.MAX_MEMBER_BYTES + 1024) + "</html>"
p = _zip({"factbook/geos/aa.html": big})
out = html_era.parse_artifact(p)
codes = {f["error_code"] for f in out.failures}
check("an oversized member is refused", "member_too_large" in codes, True)
check("no entry is produced from it", out.entries, [])
os.unlink(p)

if failures:
    print(f"test_html_era: {len(failures)} of {checks} checks FAILED", file=sys.stderr)
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    raise SystemExit(1)
print(f"test_html_era: {checks} checks passed")
