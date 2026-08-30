"""Plain-text era, 1990-1999 and 2001.

Structure, established by reading the files:

    @Czech Republic:Geography

     Location: Central Europe, southeast of Germany

     Area:
     total area: 78,703 sq km
     land area: 78,645 sq km

     Land boundaries: total 1,880 km, Austria 362 km, Germany 646 km,
     Poland 658 km, Slovakia 214 km

A `@Entity:Section` marker opens each section. Fields are `Name: value` at a
single space of indent. A bare `Name:` introduces indented subfields. Values wrap
across lines and are rejoined.

Two things this parser must not do. It must not treat the alphabetical
table-of-contents listing near the top of the file as data — those lines are bare
country names with no `@` marker. And it must not repair the source: the 1995
edition contains "l,600 square kilometers", with a letter where a digit belongs,
and that reaches the value parser exactly as written so it can be refused there.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import ParseOutcome, RawEntry, RawField
from .values import normalise_space

# The "text era" is not one format. Measured across the eleven text artifacts,
# three distinct marker conventions carry the country/section boundary, and two
# further editions (1996, 1999) use bare section headings with no country marker
# at all and are not handled here -- they are reported as unsupported rather
# than parsed into silence. docs/database/SOURCE-AUDIT-CIA-WORLD-FACTBOOK.md
# records the measurement.
#
#   1992        :Afghanistan Geography      colon prefix, space separator
#   1993        *Afghanistan, Geography     star prefix, comma separator
#   1994        @Afghanistan, Geography     at prefix, comma separator
#   1995,97,98  @Czech Republic:Geography   at prefix, colon separator
#   2001        Czech Republic    Geography country and section, run of spaces
#
# 1990 and 1991 mark the section only ("- Geography", "_*_Geography") and carry
# the country heading separately; 1996 and 1999 use bare section headings. Those
# four are not handled and are reported as unsupported.
#
# The section vocabulary is closed and short, which is what makes the last two
# forms safely distinguishable from ordinary prose.
SECTIONS = (r"Geography|People(?: and Society)?|Government|Economy|Communications|"
            r"Transportation|Defense Forces|Military(?: and Security)?|"
            r"Transnational Issues|Introduction")

MARKER_PATTERNS = (
    re.compile(r"^@(?P<entity>[^:@]+?):(?P<section>.+?)\s*$"),
    re.compile(rf"^:(?P<entity>[^:]+?)\s+(?P<section>{SECTIONS})\s*$"),
    # The entity group must admit its own commas. "Korea, North" and
    # "Micronesia, Federated States of" are how these files write those names,
    # so `[^,]+?` matched none of their marker lines at all. In 1993 the
    # unmatched line fell through as a continuation and every field of five
    # countries was silently attributed to whichever entity preceded them
    # alphabetically; in 1994 the same line starts with "@", so the back-matter
    # guard treated it as an appendix boundary and deleted those countries
    # outright — with members_seen == members_parsed and zero failures, because
    # an entity that never matches a marker is never counted as seen.
    #
    # Lazy matching against the closed SECTIONS vocabulary, anchored at the end
    # of the line, splits on the last comma that leaves a valid section behind.
    re.compile(rf"^[*@](?P<entity>.+?),\s*(?P<section>{SECTIONS})\s*$"),
    re.compile(rf"^(?P<entity>[A-Z][^\s].{{0,48}}?)\s{{3,}}(?P<section>{SECTIONS})\s*$"),
)


def _match_marker(line: str):
    for pattern in MARKER_PATTERNS:
        m = pattern.match(line)
        if m:
            return m
    return None

# "Field name: value" or a bare "Field name:" introducing subfields. The colon
# must arrive within a plausible label length, so that a sentence containing a
# colon is not mistaken for a field.
#
# Case carries the structure in this era, and it is the only thing that does:
# a top-level field is Capitalised ("Area:", "Land boundaries:") while its
# subfields are lower-case ("total area:", "land area:") at the *same* indent.
# An earlier version keyed on indentation and produced one field containing
# every subfield run together, because there is no extra indentation to key on.
FIELD_RE = re.compile(r"^(?P<name>[A-Z][^:]{0,60}?):\s*(?P<value>.*)$")
SUBFIELD_RE = re.compile(r"^(?P<name>[a-z][^:]{0,45}?):\s*(?P<value>.*)$")

# Back matter. After the last country these files continue with cross-country
# appendices -- "@Administrative divisions" in 2001, listing every country again
# under its own "Afghanistan:" heading. Those headings parse as ordinary fields,
# so without a boundary the final country's last section swallows them: in 2001
# that is 141,099 lines, more than half the file, and every appendix entry ends
# up attributed to Zimbabwe. It inflated that edition to 83,120 field values
# against roughly 36,000 for comparable editions, and put Czech content under
# Zimbabwe -- found by reading a full-text search result, not by any count.
#
# Two delimiters, both the files' own: a rule of equals signs, and an "@" line
# that is not one of the country/section markers.
# A horizontal rule. The editions do not agree on the character: 2001 uses "=",
# 1995 uses "_". Accepting only "=" is why the 2001 fix did not generalise.
# 1992 closes its last country with a run of eight asterisks, two short of
# the old ten-character threshold, so that line leaked into Zimbabwe as a
# bogus second "Defense expenditures" value. Six is still far longer than
# any run of these characters that carries meaning inside a field.
RULE_RE = re.compile(r"^\s*[=_*-]{6,}\s*$")

# An appendix heading. 1992-1994 introduce their back matter with no rule at all
# -- just "Appendix A: Abbreviations" on its own line, which parses as an
# ordinary field and is swallowed into the last country. That is how Appendix F
# and G ended up attributed to Zimbabwe, at 17-27x its real field count.
# Case-insensitive: 1992 titles its glossary "Notes, Definitions, and
# Abbreviations" in title case while other editions shout it, and matching only
# the upper-case form left 1992's entire glossary attributed to Zimbabwe.
APPENDIX_RE = re.compile(
    r"^\s*appendix\s+[a-z0-9]\b|"
    r"^\s*(?:table of contents|notes,\s*definitions|selected international"
    r"|country listing|cross-reference|abbreviations for)\b",
    re.I)


def _is_back_matter(line: str) -> bool:
    """True when a line begins material that is no longer country content.

    Three signals, all of them the files' own: a horizontal rule, an appendix or
    front-matter heading, and an "@"-prefixed line that is not a country marker.
    """
    if RULE_RE.match(line) or APPENDIX_RE.match(line):
        return True
    return line.startswith("@") and _match_marker(line) is None


# Project Gutenberg wraps every text in its own boilerplate. It is not CIA
# content and must not become fields; the markers are stable across the corpus.
GUTENBERG_START = re.compile(r"\*\*\*\s*START OF TH(?:E|IS) PROJECT GUTENBERG", re.I)
GUTENBERG_END = re.compile(r"\*\*\*\s*END OF TH(?:E|IS) PROJECT GUTENBERG", re.I)


def _decode(path: Path) -> str:
    """These files are not all UTF-8; the older ones are Latin-1.

    Decoding is attempted strictly in order and never with errors='ignore',
    because silently dropping a byte corrupts a name without saying so.
    """
    data = path.read_bytes()
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    # latin-1 cannot fail, so this is unreachable; kept so the intent is explicit.
    return data.decode("latin-1", errors="replace")   # pragma: no cover


def _trim_boilerplate(text: str) -> str:
    start = GUTENBERG_START.search(text)
    if start:
        nl = text.find("\n", start.end())
        text = text[nl + 1:] if nl >= 0 else text[start.end():]
    end = GUTENBERG_END.search(text)
    if end:
        text = text[: end.start()]
    return text


def parse_artifact(path: Path, *, limit_entities: int | None = None) -> ParseOutcome:
    outcome = ParseOutcome()
    text = _trim_boilerplate(_decode(path))
    lines = text.splitlines()

    # Pass 1: locate section markers. Everything between two markers belongs to
    # the first of them.
    marks: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines):
        m = _match_marker(line)
        if m:
            marks.append((i, normalise_space(m.group("entity")),
                          normalise_space(m.group("section"))))

    if not marks:
        outcome.failures.append({
            "source_pointer": path.name,
            "error_code": "no_section_markers",
            "reason": ("none of the three known country/section marker forms "
                       "appear in this artifact; it is most likely a "
                       "bare-section-heading edition (1996, 1999), which this "
                       "parser does not yet support"),
            "raw_input": "\n".join(lines[:20])[:500],
        })
        return outcome

    entries: dict[str, RawEntry] = {}
    order: list[str] = []
    # Front matter is, by definition, before the body. Once a section parses
    # cleanly we are past it.
    seen_clean_section = False

    for idx, (line_no, entity, section) in enumerate(marks):
        end = marks[idx + 1][0] if idx + 1 < len(marks) else len(lines)
        # Stop at back matter as well as at the next marker. Only the final
        # section is normally affected, but bounding every section costs nothing
        # and means an appendix appearing mid-file cannot leak either.
        for j in range(line_no + 1, end):
            if _is_back_matter(lines[j]):
                end = j
                break
        body = lines[line_no + 1:end]

        fields, failures = _parse_section(body, section, path.name, entity)

        # These files open with an instructional block that *demonstrates* the
        # marker syntax -- "search for @country: @Afganistan, for example" --
        # followed by six empty markers and a seventh that runs on into the
        # publication notes, the table of contents and the alphabetical country
        # list. Those markers look exactly like content markers, and the last of
        # them would otherwise contribute a phantom "Afganistan" entity whose
        # fields are things like "Telephone" and "Attn." scraped out of an
        # address block.
        #
        # Two signals separate front matter from content, both measured rather
        # than assumed. A content section yields fields at all; and a content
        # section is *cleanly* parsed -- across this corpus a real section leaves
        # no unattached lines, while the front-matter block leaves 292 of them
        # against 66 spurious fields. Requiring fields to outnumber unattached
        # lines rejects the block without hard-coding the misspelling that
        # happens to identify it in this one edition.
        #
        # Both rejections are counted, never silently dropped, so a genuine
        # section this parser stopped reading would show up as a jump in
        # empty_sections rather than as quietly missing data.
        # Two different rejections, and conflating them lost real data.
        #
        # A section with no fields is never content -- drop it.
        #
        # A section where unattached lines outnumber fields is front matter, but
        # ONLY while we are still in the preamble. Applied everywhere, this rule
        # discarded genuine mid-file sections: 1993 lost twelve, including whole
        # "Flag description" fields, because a page-break artifact left a few
        # orphaned continuation lines in the same chunk as real content. Once a
        # cleanly-parsed section has been seen, the file is in its body and a
        # noisy section is kept -- its fields are real, and its unattached lines
        # are reported as failures rather than taking the fields down with them.
        if not fields:
            outcome.empty_sections += 1
            continue
        if not seen_clean_section and len(failures) > len(fields):
            outcome.empty_sections += 1
            continue
        if not failures:
            seen_clean_section = True

        key = entity.lower()
        if key not in entries:
            if limit_entities is not None and len(order) >= limit_entities:
                continue
            entries[key] = RawEntry(source_key=key, source_name=entity,
                                    member_path=path.name, ordinal=len(order))
            order.append(key)
            outcome.members_seen += 1
        entry = entries[key]

        entry.fields.extend(fields)
        outcome.failures.extend(failures)

    for key in order:
        entry = entries[key]
        if entry.fields:
            outcome.entries.append(entry)
            outcome.members_parsed += 1
        else:
            outcome.failures.append({
                "source_pointer": f"{path.name}#{entry.source_name}",
                "error_code": "entry_without_fields",
                "reason": "section markers present but no field lines parsed",
                "raw_input": "",
            })

    return outcome


# A section name standing alone on a line. Several editions mark only *some*
# sections with a country marker and leave the rest as bare headings inside the
# previous marker's body: 1997 has no ":Economy" marker at all, so every
# country's GDP and exports were filed under "Government", and 1998 has no
# ":Communications" marker, filing telephones under "Economy". The heading is
# right there in the text; it just was not being read.
BARE_SECTION_RE = re.compile(rf"^\s*({SECTIONS})\s*$")


def _parse_section(body: list[str], section: str, member: str,
                   entity: str) -> tuple[list[RawField], list[dict]]:
    """Read one section body into fields, joining wrapped value lines.

    `section` is the section the marker named; a bare section heading inside the
    body overrides it from that point on.
    """
    fields: list[RawField] = []
    failures: list[dict] = []

    open_field: str | None = None     # the Capitalised field currently in scope
    pending: list[str] = []           # accumulating value lines
    pending_field: str | None = None
    pending_sub: str = ""
    ordinal = 0
    current_section = section

    def emit(name: str, sub: str, value: str) -> None:
        nonlocal ordinal
        fields.append(RawField(section_name=current_section, field_name=name,
                               subfield_name=sub, raw_text=value, ordinal=ordinal))
        ordinal += 1

    def flush() -> None:
        nonlocal pending, pending_field, pending_sub, ordinal
        if pending_field is not None:
            value = normalise_space(" ".join(pending))
            if value:
                emit(pending_field, pending_sub, value)
        pending = []
        pending_field = None
        pending_sub = ""

    for raw_line in body:
        stripped = raw_line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("@"):
            continue

        bare = BARE_SECTION_RE.match(stripped)
        if bare:
            # A heading, not a field. Close whatever is open and re-label.
            flush()
            open_field = None
            current_section = normalise_space(bare.group(1))
            continue

        field_m = FIELD_RE.match(stripped)
        sub_m = None if field_m else SUBFIELD_RE.match(stripped)

        if field_m:
            name = normalise_space(field_m.group("name"))
            value = field_m.group("value").strip()
            flush()
            open_field = name
            if value:
                pending_field, pending_sub, pending = name, "", [value]
            continue

        if sub_m and open_field is not None:
            name = normalise_space(sub_m.group("name"))
            value = sub_m.group("value").strip()
            flush()
            pending_field, pending_sub = open_field, name
            pending = [value] if value else []
            continue

        # Anything else continues the value above. A line with nothing open is
        # unattached: recorded rather than dropped, because a parser that
        # discards lines in silence cannot be audited. §21.
        if pending_field is not None:
            pending.append(stripped)
        elif open_field is not None:
            pending_field, pending_sub, pending = open_field, "", [stripped]
        else:
            failures.append({
                "source_pointer": f"{member}#{entity}:{section}",
                "error_code": "unattached_text",
                "reason": "line precedes any field label in its section",
                "raw_input": stripped[:300],
            })

    flush()
    return fields, failures
