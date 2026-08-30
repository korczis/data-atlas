"""Unit tests for the value parser.

Every case here is a string that appears in the corpus, or a deliberate
near-miss chosen to prove the parser refuses rather than guesses.

Run with `just data-test`, which needs neither a database nor the network.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata.parsers.values import (
    parse_partners,
    parse_shares,
    parse_value,
)

failures: list[str] = []
checks = 0


def check(label: str, actual, expected) -> None:
    global checks
    checks += 1
    if actual != expected:
        failures.append(f"{label}\n      expected {expected!r}\n      got      {actual!r}")


# ── numbers that must parse ──────────────────────────────────────────────────

v = parse_value("$2.14 trillion (2023 est.)")
check("trillion value", v.value, Decimal("2140000000000"))
check("trillion currency", v.currency, "USD")
check("trillion year", v.reference_year, 2023)
check("trillion estimate", v.is_estimate, True)
check("trillion status", v.status, "parsed_with_qualifier")
check("trillion raw preserved", v.raw, "$2.14 trillion (2023 est.)")

v = parse_value("12.3% (2024 est.)")
check("percent value", v.value, Decimal("12.3"))
check("percent flag", v.is_percent, True)
check("percent year", v.reference_year, 2024)

v = parse_value("1,234 km")
check("thousands value", v.value, Decimal("1234"))
check("thousands unit", v.unit_hint, "km")
check("thousands status", v.status, "parsed_exact")

v = parse_value("78,703 sq km")
check("area value", v.value, Decimal("78703"))
check("area unit", v.unit_hint, "sq km")

v = parse_value("1.2 billion kWh")
check("billion kwh value", v.value, Decimal("1200000000"))
check("billion kwh unit", v.unit_hint, "kwh")

v = parse_value("0.5 million")
check("scaled decimal", v.value, Decimal("500000"))

v = parse_value("10,838,703 (2025 est.)")
check("population value", v.value, Decimal("10838703"))
check("population year", v.reference_year, 2025)

# ── absences, each distinct ──────────────────────────────────────────────────

v = parse_value("NA")
check("NA has no value", v.value, None)
check("NA reason", v.missing_reason, "not_reported")

v = parse_value("NA%")
check("NA% has no value", v.value, None)
check("NA% reason", v.missing_reason, "not_reported")

v = parse_value("negligible")
check("negligible has no value", v.value, None)
check("negligible reason", v.missing_reason, "negligible")

v = parse_value("none")
check("none reason", v.missing_reason, "not_applicable")

v = parse_value("")
check("empty reason", v.missing_reason, "not_reported")

# A currency marker on an absence. The Factbook writes "$NA" wherever it would
# have written a dollar amount and had none; read as a parse failure it turns
# 4,143 stated absences in this corpus into quarantine rows, which is the
# system claiming its own defect where the source was simply silent.
for token in ("$NA", "US$NA", "\u20acNA", "$NA (31 December 2008)",
              "$NA, NA% of GDP"):
    v = parse_value(token)
    check(f"{token!r} is an absence", v.missing_reason, "not_reported")
    check(f"{token!r} has no value", v.value, None)
    check(f"{token!r} is not a failure", v.failure_code, None)

# Stripping the marker must not blind the parser to real amounts.
v = parse_value("$1,600")
check("$1,600 still parses", v.value, Decimal("1600"))
check("$1,600 keeps its currency", v.currency, "USD")

# NEGL is the Factbook's own abbreviation for negligible, and appears bare and
# with a percent sign. It is an absence with a reason, not an unreadable string.
for token in ("NEGL", "NEGL%"):
    v = parse_value(token)
    check(f"{token!r} reason", v.missing_reason, "negligible")
    check(f"{token!r} has no value", v.value, None)

# A published range is not a negative number. "15-20%" read with a bare sign
# becomes -20: wrong magnitude and wrong sign, and indistinguishable afterwards
# from a real contraction. The first bound is taken and the row marked partial,
# because more was published than one column can hold.
for token, expected in (("15-20% (1991 est.)", Decimal("15")),
                        ("250-300% (1992 est.)", Decimal("250")),
                        ("20-40% (1997 est.)", Decimal("20")),
                        ("around 9-10% (2005 est.)", Decimal("9"))):
    v = parse_value(token)
    check(f"{token!r} takes the first bound", v.value, expected)
    check(f"{token!r} is not negative", v.value > 0, True)
    check(f"{token!r} is flagged partial", v.status, "parsed_partial")

# The same change must not blind the parser to a real negative.
for token, expected in (("-2.5% (2010 est.)", Decimal("-2.5")),
                        ("-62.1% (2011 est.)", Decimal("-62.1")),
                        ("-9% (2003 est.)", Decimal("-9"))):
    v = parse_value(token)
    check(f"{token!r} stays negative", v.value, expected)

# The critical property: an absence is never a zero.
for token in ("NA", "negligible", "none", "unknown", ""):
    check(f"{token!r} never becomes 0", parse_value(token).value, None)

# ── inequalities are bounds, not measurements ────────────────────────────────

v = parse_value("less than 1%")
check("less-than value", v.value, Decimal("1"))
check("less-than inequality", v.inequality, "less_than")
check("less-than not exact", v.status, "parsed_partial")

# ── refusals: the parser must not repair a source typo ───────────────────────

v = parse_value("l,600")
check("letter-l typo not parsed", v.value, None)
check("letter-l typo status", v.status, "unparsed")
check("letter-l typo code", v.failure_code, "no_number_found")
check("letter-l typo keeps raw", v.raw, "l,600")

v = parse_value("mostly mountainous terrain")
check("prose has no value", v.value, None)
check("prose status", v.status, "unparsed")
check("prose reason is not a missing token", v.missing_reason, None)

# ── compound fields are flagged, not silently truncated ──────────────────────

# The parenthetical here is a note about an otherwise exact value, so the
# status is 'parsed_with_qualifier'. A genuinely compound value -- two numbers
# in the value itself -- is what yields 'parsed_partial', tested below.
v = parse_value("15.7% (male 871,303/female 826,896)")
check("noted value", v.value, Decimal("15.7"))
check("noted status", v.status, "parsed_with_qualifier")
check("noted keeps note", "male 871,303/female 826,896" in v.note, True)

v = parse_value("2,046 to 2,100 km")
check("range value", v.value, Decimal("2046"))
check("range status", v.status, "parsed_partial")

# ── rate denominators are not values ─────────────────────────────────────────
# Regression: "NA births/1,000 population" once parsed as a birth rate of 1000.
# The only number in the string belongs to the unit, and the value is absent.
# Caught in the loaded database by the value_outside_expected_range check.

v = parse_value("NA births/1,000 population (1992)")
check("NA rate has no value", v.value, None)
check("NA rate reason", v.missing_reason, "not_reported")
check("NA rate keeps year", v.reference_year, 1992)

v = parse_value("12.5 births/1,000 population (2021 est.)")
check("rate value", v.value, Decimal("12.5"))
check("rate year", v.reference_year, 2021)

v = parse_value("8.7 deaths/1,000 population")
check("rate without note", v.value, Decimal("8.7"))

v = parse_value("0 births/1,000 population")
check("zero rate is zero, not absent", v.value, Decimal("0"))
check("zero rate is not missing", v.missing_reason, None)

v = parse_value("NA sq km")
check("NA with unit has no value", v.value, None)
check("NA with unit reason", v.missing_reason, "not_reported")

# ── multi-year lists: the value and its year must come from the same item ────
# Regression: later editions publish several years in one field. Taking the
# first number with the LAST year paired a 2017 figure with 2015.

v = parse_value("$41.65 billion (2017 est.) $39.72 billion (2016 est.) $38.92 billion (2015 est.)")
check("multi-year value", v.value, Decimal("41650000000"))
check("multi-year takes its own year", v.reference_year, 2017)
check("multi-year flagged partial", v.status, "parsed_partial")

v = parse_value("4% (2017 est.) 4.7% (2016 est.) 1% (2015 est.)")
check("multi-year percent value", v.value, Decimal("4"))
check("multi-year percent year", v.reference_year, 2017)

# A single pair is exact, not partial.
v = parse_value("$2.14 trillion (2023 est.)")
check("single pair value", v.value, Decimal("2140000000000"))
check("single pair year", v.reference_year, 2023)

# ── an explanatory note is not a value ───────────────────────────────────────
# Regression: "data are in 2010 US dollars" contains exactly one number — the
# year — and was parsed as a GDP of 2010. ~2,463 observations were affected.

v = parse_value("data are in 2010 US dollars")
check("basis note has no value", v.value, None)
check("basis note status", v.status, "unparsed")
check("basis note code", v.failure_code, "explanatory_note_not_a_value")

v = parse_value("note: data are estimates for 2019")
check("note prefix has no value", v.value, None)

# ── a percent inside a note does not make the value a percentage ─────────────

v = parse_value("$2.14 trillion (12% higher than 2022)")
check("note percent does not set is_percent", v.is_percent, False)
check("note percent keeps currency", v.currency, "USD")
check("real percent still detected", parse_value("12.3% (2024 est.)").is_percent, True)

# ── a quantity is not a partner ──────────────────────────────────────────────
# Regression: "0 km" is a landlocked country stating it has no neighbours. It
# was recorded as a neighbour named "0 km" — 2,312 such rows.

check("bare quantity is not a partner", parse_partners("0 km"), [])
check("quantity with note is not a partner", parse_partners("0 km (landlocked)"), [])
check("real partners still parsed",
      [p.label for p in parse_partners("Austria 402 km; Germany 704 km")],
      ["Austria", "Germany"])
check("leading total is not a partner",
      [p.label for p in parse_partners("total 1,880 km, Austria 362 km")],
      ["Austria"])

# ── compositions ─────────────────────────────────────────────────────────────

members, header = parse_shares(
    "Czech (official) 88.4%, Slovak 1.5%, other 2.6%, unspecified 7.2% (2021 est.)")
check("share count", len(members), 4)
check("share first label", members[0].label, "Czech")
check("share first value", members[0].share_percent, Decimal("88.4"))
check("share last label", members[3].label, "unspecified")
check("share header year", header.reference_year, 2021)
check("share header estimate", header.is_estimate, True)
check("share sum", sum(m.share_percent for m in members), Decimal("99.7"))

# A composition summing to 99.7 is correct data. The parser must not adjust it.
check("shares not normalised to 100",
      sum(m.share_percent for m in members) == Decimal("100"), False)

# A footnote is not a composition member. Regression: Factbook composition
# fields carry explanatory notes that split on commas like any list, and 15% of
# ref.category was prose — permanently, because that table is shared and nothing
# is scoped to clean it.
members, _ = parse_shares(
    "note: an 1872 law prohibiting state authorities from collecting data on "
    "individuals' ethnicity or religious beliefs was reaffirmed in 2005")
check("footnote yields no members", len(members), 0)

members, _ = parse_shares("Dinka, Nuer, Bari, Zande, Shilluk")
check("short unpercented names still parse", [m.label for m in members],
      ["Dinka", "Nuer", "Bari", "Zande", "Shilluk"])

# A long label WITH a share is kept: an odd name plus a real percentage is far
# more likely to be a real category than a footnote.
members, _ = parse_shares(
    "Eastern Orthodox including Russian Orthodox and other Orthodox churches 71%, other 29%")
check("long label with a share is kept", len(members), 2)

members, header = parse_shares("NA")
check("NA composition empty", len(members), 0)
check("NA composition reason", header.missing_reason, "not_reported")

# ── partner lists ────────────────────────────────────────────────────────────

partners = parse_partners("Austria 402 km; Germany 704 km; Poland 699 km; Slovakia 241 km")
check("partner count semicolon", len(partners), 4)
check("partner first label", partners[0].label, "Austria")
check("partner first value", partners[0].value, Decimal("402"))
check("partner unit", partners[0].unit_hint, "km")

partners = parse_partners("Austria 362 km, Germany 646 km, Poland 658 km, Slovakia 214 km")
check("partner count comma", len(partners), 4)
check("partner comma label", partners[1].label, "Germany")
check("partner comma value", partners[1].value, Decimal("646"))

# The regression this guards: a thousands separator must not split a partner.
partners = parse_partners("Germany 1,646 km, France 451 km")
check("thousands not split", len(partners), 2)
check("thousands partner value", partners[0].value, Decimal("1646"))
check("thousands partner label", partners[0].label, "Germany")

# ── report ───────────────────────────────────────────────────────────────────

# ── a thousands separator is not a list separator ────────────────────────────
#
# "Norwegian, Sami 20,000" is two groups. Split on every comma it becomes three,
# the third being a category named "000" — 421 composition members in this
# corpus carry such a label, 348 of them exactly "000". The same splitter feeds
# bilateral partners, where it turned "Canada 8,893 km" into a partner named
# "Canada 8" and an unresolvable "893 km".
shares, _ = parse_shares("Norwegian, Sami 20,000")
check("headcount is not split", [m.label for m in shares],
      ["Norwegian", "Sami 20,000"])

shares, _ = parse_shares("Chinese 1,300,000, other 200")
check("only the real separator splits", [m.label for m in shares],
      ["Chinese 1,300,000", "other 200"])

shares, _ = parse_shares("Bulgarian 76.9%, Turkish 8%, Roma 4.4%")
check("ordinary shares still split", [m.label for m in shares],
      ["Bulgarian", "Turkish", "Roma"])
check("ordinary shares keep their percentages",
      [m.share_percent for m in shares],
      [Decimal("76.9"), Decimal("8"), Decimal("4.4")])

partners = parse_partners("Canada 8,893 km")
check("partner name is not split from its distance",
      [(p.label, p.value) for p in partners], [("Canada", Decimal("8893"))])

partners = parse_partners("Norway 1,619 km, Finland 614 km")
check("several partners still split",
      [(p.label, p.value) for p in partners],
      [("Norway", Decimal("1619")), ("Finland", Decimal("614"))])

if failures:
    print(f"test_values: {len(failures)} of {checks} checks FAILED", file=sys.stderr)
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    raise SystemExit(1)
print(f"test_values: {checks} checks passed")
