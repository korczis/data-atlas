"""Turning published strings into typed quantities, without ever guessing.

The governing rule is §22 and §76: a parser may not invent a number. Every
function here returns a result that either carries a value it can justify, or
says why it has none — and in both cases the original string survives untouched.
There is no path through this module that turns an unrecognised string into
zero, into NULL, or into a plausible-looking figure.

Shapes this corpus actually contains, all of which appear in the fixtures:

    $2.14 trillion (2023 est.)          scaled currency with an estimate marker
    12.3% (2024 est.)                   percentage with a reference year
    less than 1%                        an inequality, not a number
    NA / NA%                            the source's own "no data"
    negligible                          a stated near-zero that is not zero
    0.5 million                         a scaled decimal
    1.2 billion kWh                     a scaled quantity with a unit
    1,234 km                            thousands separators
    2.4% of GDP                         a ratio whose denominator is not the entity
    78,703 sq km                        area
    l,600                               a source typo: letter l for digit 1

The last one is the reason this module refuses rather than repairs. "l,600" is
almost certainly 1,600 — and a parser that acts on "almost certainly" has begun
inventing evidence. It goes to quarantine with its raw text, where a human can
decide. §21.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Multipliers written as words. The corpus never uses "milliard"; British and
# American "billion" do not both appear, so the American reading is safe here and
# is asserted rather than assumed.
SCALES: dict[str, Decimal] = {
    "hundred": Decimal(100),
    "thousand": Decimal(1_000),
    "million": Decimal(1_000_000),
    "billion": Decimal(1_000_000_000),
    "trillion": Decimal(1_000_000_000_000),
}

# Values the sources use to say "there is no number here". Each maps to a
# distinct missing_reason, because they do not mean the same thing: NA is "not
# available", negligible is "measured and almost zero", and none is "measured and
# actually zero". Collapsing them loses real information. §76.
MISSING_TOKENS: dict[str, str] = {
    "na": "not_reported",
    "n/a": "not_reported",
    "nan": "not_reported",
    "no data": "not_reported",
    "not available": "not_reported",
    "unknown": "unknown",
    "none": "not_applicable",
    "none reported": "not_reported",
    "nil": "not_applicable",
    "negligible": "negligible",
    "negl": "negligible",
    "uncertain": "unknown",
    "n.a.": "not_reported",
    "-": "not_reported",
    "": "not_reported",
}

QUALIFIER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\best\.?\b", "estimate"),
    (r"\bestimated\b", "estimate"),
    (r"\bapprox(?:\.|imately)?\b", "approximate"),
    (r"\babout\b", "approximate"),
    (r"\bprovisional\b", "provisional"),
    (r"\bpreliminary\b", "provisional"),
    (r"\bprojected?\b", "projection"),
    (r"\brevised\b", "revised"),
    (r"\bcensus\b", "census"),
)

INEQUALITIES: tuple[tuple[str, str], ...] = (
    (r"\bless than\b|\bunder\b|\bfewer than\b|<", "less_than"),
    (r"\bmore than\b|\bover\b|\bgreater than\b|\bat least\b|>", "greater_than"),
)

# The denominator of a rate expressed as "per N of something". In
# "12.5 births/1,000 population" the 1,000 is part of the unit, not the value —
# and in "NA births/1,000 population" it is the ONLY number present, so a parser
# that simply takes the first number reports a birth rate of 1000. That bug
# reached the database and was caught by the value_outside_expected_range
# quality check; this pattern removes the denominator before any number is read.
DENOMINATOR_RE = re.compile(
    r"(?:/|\bper\b)\s*\d[\d,]*\s*"
    r"(?:population|people|persons?|inhabitants|live\s+births|births|adults?)\b",
    re.I)

# A number: optional sign, digits with optional thousands separators, optional
# decimal part. Deliberately strict about what a digit is, so no letter may stand
# in for one.
#
# The second lookbehind is what rejects "l,600", a real typo in the 1995 edition
# where a letter l stands where a 1 belongs. Without it the leading "l," is
# treated as separate from "600" and the parser confidently returns six hundred
# -- a number that appears nowhere in the source. One character of lookbehind is
# not enough, because the character immediately before the digits is the comma.
NUMBER_RE = re.compile(
    r"(?<![\w.])(?<![A-Za-z],)(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)(?![\w])")

# "(2023 est.)", "(2024)", "(July 2021 est.)", "2021 est."
YEAR_RE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")

# A value immediately followed by the year it belongs to:
#   "$41.65 billion (2017 est.) $39.72 billion (2016 est.) ..."
#   "4% (2017 est.) 4.7% (2016 est.) ..."
# Later editions publish several years in one field. Taking the first number and
# the LAST year -- which is what a naive scan does -- pairs a 2017 figure with
# 2015, silently mislabelling the period of a value that is itself correct.
# The two lookbehinds keep a range out of the sign. "15-20% (1991 est.)" is a
# span from fifteen to twenty; read with a bare `-?` the hyphen becomes a minus
# and the field records *negative twenty* — a number of the wrong magnitude and
# the wrong sign, which no later check can distinguish from a real contraction.
# Refusing to match here drops the value through to the general first-number
# path, which takes 15 and marks the row partial because more tokens were seen.
# A genuine leading negative ("-2.5% (2010 est.)") still matches: nothing
# precedes its sign.
VALUE_YEAR_PAIR_RE = re.compile(
    r"(?P<value>(?<![\d.,])(?<!\d-)-?\$?\d[\d,]*(?:\.\d+)?\s*"
    r"(?:hundred|thousand|million|billion|trillion)?\s*%?)"
    r"\s*\(\s*(?:[A-Za-z]+\s+)?(?P<year>1[89]\d{2}|20\d{2})[^)]*\)",
    re.I)

# Text that explains the basis of a figure rather than being one. "data are in
# 2010 US dollars" contains exactly one number -- the year -- and a parser that
# takes the first number reports a GDP of 2010.
NOTE_PREFIX_RE = re.compile(
    r"^\s*(?:note\s*:|data\s+are\s+in\b|figures?\s+are\b|values?\s+are\b|"
    r"estimates?\s+are\b|all\s+figures\b|amounts?\s+are\b|"
    r"this\s+entry\b|the\s+data\b)",
    re.I)

CURRENCY_SYMBOLS = {"$": "USD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}

# "$NA" is the source saying it has no figure, exactly as "NA" is. The currency
# marker qualifies a number that was never published; it does not make the
# absence into a parse failure. Stripped only for the absence test below, so a
# real amount still has its symbol read by the currency detection further down.
CURRENCY_PREFIX_RE = re.compile(r"^\s*(?:US\$|[$\u20ac\u00a3\u00a5]|USD|EUR|GBP|JPY)\s*", re.I)


@dataclass
class ParsedValue:
    """What a parser could justify, and what it could not.

    `raw` is always the input, unmodified. A caller that stores only `value` has
    thrown away the evidence and is doing the thing this module exists to
    prevent.
    """

    raw: str
    value: Decimal | None = None
    unit_hint: str | None = None
    currency: str | None = None
    scale_word: str | None = None
    is_percent: bool = False
    reference_year: int | None = None
    is_estimate: bool = False
    qualifiers: tuple[str, ...] = ()
    inequality: str | None = None
    missing_reason: str | None = None
    note: str = ""
    # 'parsed_exact' | 'parsed_with_qualifier' | 'parsed_partial' | 'unparsed'
    status: str = "unparsed"
    failure_code: str | None = None

    @property
    def ok(self) -> bool:
        return self.value is not None

    @property
    def is_missing(self) -> bool:
        return self.value is None and self.missing_reason is not None


@dataclass
class ParsedShare:
    """One member of a composition: "Czech (official) 88.4%"."""

    raw: str
    label: str
    share_percent: Decimal | None = None
    qualifiers: tuple[str, ...] = ()
    note: str = ""
    ordinal: int = 0


@dataclass
class ParsedPartner:
    """One member of a partner list: "Germany 704 km" or "Germany 32%"."""

    raw: str
    label: str
    value: Decimal | None = None
    unit_hint: str | None = None
    is_percent: bool = False
    ordinal: int = 0


def normalise_space(text: str) -> str:
    """Collapse whitespace without touching anything else.

    Deliberately does not strip diacritics or normalise Unicode: the canonical
    store keeps text as published, and search normalisation is a separate,
    derived concern. §162.
    """
    return re.sub(r"\s+", " ", text).strip()


def _strip_notes(text: str) -> tuple[str, list[str]]:
    """Pull parenthetical asides out, returning the remainder and the asides."""
    notes: list[str] = []

    def take(m: re.Match) -> str:
        notes.append(m.group(1).strip())
        return " "

    # Non-greedy, innermost-first, repeated: handles "12% (male 5/female 7)".
    prev = None
    out = text
    while prev != out:
        prev = out
        out = re.sub(r"\(([^()]*)\)", take, out)
    return normalise_space(out), notes


def _detect_qualifiers(text: str) -> tuple[tuple[str, ...], bool]:
    found: list[str] = []
    low = text.lower()
    for pattern, name in QUALIFIER_PATTERNS:
        if re.search(pattern, low) and name not in found:
            found.append(name)
    return tuple(found), ("estimate" in found)


def _detect_inequality(text: str) -> str | None:
    low = text.lower()
    for pattern, name in INEQUALITIES:
        if re.search(pattern, low):
            return name
    return None


def _to_decimal(token: str) -> Decimal | None:
    try:
        return Decimal(token.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def parse_value(raw: str, *, expect_percent: bool = False) -> ParsedValue:
    """Parse one published quantity.

    Returns a ParsedValue whose `status` is never 'parsed_exact' unless a number
    was actually recognised in the input. An unrecognised string yields
    status='unparsed' with a failure_code, which the loader turns into a
    quarantine row rather than a NULL.
    """
    original = raw if isinstance(raw, str) else str(raw)
    text = normalise_space(original)
    result = ParsedValue(raw=original)

    if not text:
        result.missing_reason = "not_reported"
        result.failure_code = "empty"
        return result

    # "NA", "negligible", "none" — the source saying there is no number.
    bare = CURRENCY_PREFIX_RE.sub("", text).lower().rstrip("%").strip().rstrip(".")
    if bare in MISSING_TOKENS:
        result.missing_reason = MISSING_TOKENS[bare]
        result.note = "source stated absence"
        return result

    body, notes = _strip_notes(text)
    note_text = "; ".join(notes)

    # "NA births/1,000 population" is an absence, not a rate of 1000. The bare
    # token check above only catches a string that is *entirely* a missing
    # token, so a stated absence carrying its unit needs this second test on the
    # first word.
    first_word = re.split(r"[\s/]+", CURRENCY_PREFIX_RE.sub("", body),
                          maxsplit=1)[0].strip().lower().rstrip("%.,;:")
    if MISSING_TOKENS.get(first_word):
        result.missing_reason = MISSING_TOKENS[first_word]
        result.note = "source stated absence, with unit text"
        years_in_note = YEAR_RE.findall(note_text)
        if years_in_note:
            result.reference_year = int(years_in_note[-1])
        return result

    # Strip rate denominators so they cannot be mistaken for the value.
    body = DENOMINATOR_RE.sub(" ", body)

    # A reference year is far more often inside the parenthetical ("2023 est.")
    # than in the value itself, so the asides are searched first. This is what
    # keeps edition_year from being silently reused as the observation year. §16.
    years = YEAR_RE.findall(note_text) or YEAR_RE.findall(body)
    if years:
        result.reference_year = int(years[-1])

    quals, is_est = _detect_qualifiers(text)
    result.qualifiers, result.is_estimate = quals, is_est
    result.note = note_text
    result.inequality = _detect_inequality(body)

    # The percent sign must be in the value itself, not in a parenthetical note.
    # "$2.14 trillion (12% higher than 2022)" is a currency amount with a note
    # about a percentage; reading the note's % made it a percentage observation
    # and would have attached the wrong unit to a monetary value.
    if "%" in body or expect_percent:
        result.is_percent = True

    for sym, code in CURRENCY_SYMBOLS.items():
        if sym in text:
            result.currency = code
            break

    m = re.search(r"\b(hundred|thousand|million|billion|trillion)\b", body, re.I)
    if m:
        result.scale_word = m.group(1).lower()

    # Unit words after the number: "sq km", "km", "kWh", "bbl/day", "barrels".
    # The scale word is optional between the number and the unit: "1.2 billion
    # kWh" carries a unit just as "1,234 km" does, and requiring the unit to
    # follow a digit directly dropped it.
    unit_m = re.search(
        r"\d\s*(?:hundred|thousand|million|billion|trillion)?\s*"
        r"(sq\s*km|sq\s*mi|km/?h|kWh|kW|GWh|MW|cu\s*m|bbl/day|bbl|km|mi|nm|"
        r"metric\s+tons?|tonnes?|tons?|years?|people|persons?)\b",
        body, re.I)
    if unit_m:
        result.unit_hint = normalise_space(unit_m.group(1).lower())

    # A field that only explains the basis of a figure is not a figure.
    if NOTE_PREFIX_RE.match(text):
        result.failure_code = "explanatory_note_not_a_value"
        result.note = (note_text + "; " if note_text else "") + \
                      "text explains the basis of a figure rather than stating one"
        return result

    # Several "value (year)" pairs in one field: take the FIRST pair and use
    # *its* year, rather than the first number with the last year seen.
    pairs = list(VALUE_YEAR_PAIR_RE.finditer(text))
    if pairs:
        first = pairs[0]
        pair_value = _to_decimal(re.sub(r"[^\d.\-]", "", first.group("value")))
        if pair_value is not None:
            scale = re.search(r"\b(hundred|thousand|million|billion|trillion)\b",
                              first.group("value"), re.I)
            if scale:
                pair_value = pair_value * SCALES[scale.group(1).lower()]
                result.scale_word = scale.group(1).lower()
            result.value = pair_value
            result.reference_year = int(first.group("year"))
            result.is_percent = "%" in first.group("value")
            if len(pairs) > 1:
                # More periods are present than this row can hold. Flagged so the
                # loss is visible; a future loader can emit one row per pair.
                result.status = "parsed_partial"
                result.note = (result.note + "; " if result.note else "") + \
                              f"{len(pairs)} value/year pairs present, first taken"
            else:
                result.status = "parsed_with_qualifier" if (quals or notes) else "parsed_exact"
            return result

    numbers = NUMBER_RE.findall(body)
    if not numbers:
        # There is text here, and no number in it. That is not zero and not
        # NULL — it is a value this parser did not understand, and it is
        # reported as such.
        result.failure_code = "no_number_found"
        result.note = (note_text + "; " if note_text else "") + "no numeric token"
        return result

    value = _to_decimal(numbers[0])
    if value is None:                                   # pragma: no cover
        result.failure_code = "number_unparseable"
        return result

    if result.scale_word:
        value = value * SCALES[result.scale_word]

    result.value = value

    if len(numbers) > 1:
        # A compound field such as a range or "male X/female Y". The first number
        # is taken and the fact that more were present is recorded, so the row is
        # visible as incompletely understood rather than quietly truncated.
        result.status = "parsed_partial"
        result.note = (result.note + "; " if result.note else "") + \
                      f"{len(numbers)} numeric tokens present, first taken"
        return result

    if result.inequality:
        # "less than 1%" has a number in it but is a bound, not a measurement.
        result.status = "parsed_partial"
        return result

    result.status = "parsed_with_qualifier" if (quals or notes) else "parsed_exact"
    return result


# A category label is a name: a few words at most. These are the shapes that
# distinguish a footnote from a group name.
_PROSE_MARKERS = re.compile(
    r"\b(?:this entry|includes only|note that|according to|the proportion|"
    r"data (?:are|is)|percentages?\s+(?:add|do not)|approximately|"
    r"prohibit\w*|reaffirm\w*|continues? to)\b", re.I)
MAX_CATEGORY_WORDS = 8


def _is_prose(label: str) -> bool:
    """True when a candidate composition member reads as a sentence, not a name."""
    if _PROSE_MARKERS.search(label):
        return True
    words = label.split()
    if len(words) > MAX_CATEGORY_WORDS:
        return True
    # A trailing full stop, or an internal one that is not an abbreviation.
    return label.endswith(".") and len(words) > 2


def parse_shares(raw: str) -> tuple[list[ParsedShare], ParsedValue]:
    """Parse a composition: "Czech (official) 88.4%, Slovak 1.5%, other 2.6%".

    Returns the members and a ParsedValue carrying the header-level qualifiers
    (reference year, estimate marker) that apply to the list as a whole.
    """
    original = raw if isinstance(raw, str) else str(raw)
    text = normalise_space(original)
    header = ParsedValue(raw=original)

    if not text:
        header.missing_reason = "not_reported"
        return [], header

    bare = text.lower().rstrip(".")
    if bare in MISSING_TOKENS:
        header.missing_reason = MISSING_TOKENS[bare]
        return [], header

    # A trailing "(2021 est.)" qualifies the whole list, so it is lifted off
    # before splitting rather than becoming a phantom final member.
    trailing = re.search(r"\(([^()]*(?:est\.?|census|\d{4})[^()]*)\)\s*$", text, re.I)
    if trailing:
        years = YEAR_RE.findall(trailing.group(1))
        if years:
            header.reference_year = int(years[-1])
        header.is_estimate = bool(re.search(r"est\.?", trailing.group(1), re.I))
        text = text[: trailing.start()].strip()

    members: list[ParsedShare] = []
    # Split on commas and semicolons that are not inside parentheses, and not
    # inside a number. "Norwegian, Sami 20,000" is two groups, not three: the
    # comma in the headcount is a thousands separator, and splitting on it
    # invented a category literally named "000" — 421 such members across this
    # corpus, "000" alone accounting for 348 of them.
    parts, depth, buf = [], 0, []
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        thousands = (ch == "," and i > 0 and text[i - 1].isdigit()
                     and text[i + 1:i + 4].isdigit()
                     and not text[i + 4:i + 5].isdigit())
        if ch in ",;" and depth == 0 and not thousands:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))

    for i, part in enumerate(p.strip() for p in parts):
        if not part:
            continue
        pct = re.search(r"(-?\d+(?:\.\d+)?)\s*%", part)
        label_text = part[: pct.start()].strip() if pct else part
        label_text, notes = _strip_notes(label_text)
        label = normalise_space(label_text).strip(" -")
        if not label:
            continue
        # A composition member names a group; it is not a sentence. Factbook
        # composition fields carry explanatory footnotes ("an 1872 law
        # prohibiting state authorities from collecting data on individuals'
        # ethnicity...") which split on commas like any other list and became
        # "categories" -- 15% of ref.category was prose, and because that table
        # is shared and never release-scoped, nothing could ever clean it up.
        #
        # A member with no share AND prose shape is rejected rather than stored.
        # One that carries a percentage is kept whatever its length: an odd
        # label with a real share is far more likely to be a real category.
        if pct is None and _is_prose(label):
            continue

        members.append(ParsedShare(
            raw=part,
            label=label,
            share_percent=_to_decimal(pct.group(1)) if pct else None,
            qualifiers=_detect_qualifiers(part)[0],
            note="; ".join(notes),
            ordinal=i,
        ))

    header.status = "parsed_exact" if members else "unparsed"
    if not members:
        header.failure_code = "no_members_found"
    return members, header


# Units and bare numbers that can look like a partner name once a list has been
# split. A neighbour is named; a quantity is not.
_QUANTITY_ONLY_RE = re.compile(
    r"^[\d.,\s]*(?:km|mi|nm|m|sq\s*km|%|total|none|na)?[\d.,\s]*$", re.I)


def _is_quantity_only(label: str) -> bool:
    """True when a candidate partner label names no entity at all."""
    return bool(_QUANTITY_ONLY_RE.match(label.strip()))


def parse_partners(raw: str) -> list[ParsedPartner]:
    """Parse a partner list: "Austria 402 km; Germany 704 km" or "Germany 32%".

    This is what turns a string nobody can join on into rows with a real entity
    reference. §35.
    """
    text = normalise_space(raw if isinstance(raw, str) else str(raw))
    if not text or text.lower().rstrip(".") in MISSING_TOKENS:
        return []

    # Semicolons separate partners in later editions, commas in earlier ones.
    # A comma between digits is a thousands separator, not a boundary between
    # partners: splitting "Germany 1,646 km" on commas would invent a partner
    # called "646 km". Those commas are swapped for a placeholder from the
    # Unicode private-use area -- which cannot occur in this corpus, and unlike
    # NUL can survive a round trip through PostgreSQL text -- then restored
    # immediately after the split.
    SEP = "\ue000"
    protected = re.sub(r"(?<=\d),(?=\d{3}\b)", SEP, text)
    parts = protected.split(";") if ";" in protected else protected.split(",")

    out: list[ParsedPartner] = []
    for i, part in enumerate(p.replace(SEP, ",").strip() for p in parts):
        if not part:
            continue
        # "Austria 402 km" -> label "Austria", value 402, unit km
        m = re.match(
            r"^(.*?)[\s:]+(-?\d[\d,]*(?:\.\d+)?)\s*(%|sq\s*km|km|mi|nm|m)?\s*$",
            part, re.I)
        if not m:
            # A partner with no quantity ("Germany") is still a partner; the fact
            # that it was named is the information. But a "label" that is only a
            # number and a unit is not a partner at all -- "0 km" is a landlocked
            # country's statement that it has no land boundaries, and recording
            # it as a neighbour called "0 km" produced 2,312 such rows.
            label = normalise_space(_strip_notes(part)[0])
            if label and not _is_quantity_only(label):
                out.append(ParsedPartner(raw=part, label=label, ordinal=i))
            continue
        label = normalise_space(_strip_notes(m.group(1))[0]).strip(" -")
        if not label or _is_quantity_only(label):
            continue
        unit = normalise_space(m.group(3).lower()) if m.group(3) else None
        out.append(ParsedPartner(
            raw=part,
            label=label,
            value=_to_decimal(m.group(2)),
            unit_hint=None if unit == "%" else unit,
            is_percent=unit == "%",
            ordinal=i,
        ))
    return out
