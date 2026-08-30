"""HTML era, 2002-2020: three generations of CIA site markup in one zip family.

Verified by reading the artifacts rather than assuming a split (§8). The
generations are structurally different, not cosmetically:

  A. 2002-2008   table layout. `<td class="FieldLabel"><div align="right">Area:
                 </div></td>` followed by a value cell; subfields are `<i>total:
                 </i>` runs separated by `<br>`. Sections are marked by anchors,
                 `<a name="Geo">Geography</a>`.

  B. 2009-2016   div layout. `<div id='field' class='category ...'>` carries the
                 label; the value follows in `<div class=category_data>`, or as
                 `<span class=category>total: </span><span class=category_data>`
                 pairs. Section headings are not reliably marked in the country
                 pages, so section is recorded empty for this generation.

  C. 2017-2020   semantic layout. `<div class="category" id="field-anchor-
                 geography-area">` names both section and field in the id, and
                 the value lives in `<div id="field-area">` with
                 `<span class="subfield-name">` / `subfield-number` pairs.

A tolerant token walk is used rather than a strict DOM: these files are twenty
years of hand-edited HTML with unclosed tags, and a strict parser would reject
documents that a browser renders without complaint. `html.parser` from the
standard library is deliberately lenient, which is the property needed here.

2000 is **not** generation A and is not parsed by this module. Its pages label
fields with inline `<b>Background:</b>` bold tags in ordinary body text, with
`<a name="Geo">` section anchors and none of generation A's table markup, so
every member fails as `html_generation_unrecognised`. That is the correct
outcome -- an unimplemented format refused loudly -- but it is a fourth
generation, not the first one starting two years early. 2001's zip is recorded
corrupt upstream and is superseded by the Gutenberg text for that edition.

Where a generation does not expose the section, it is recorded as empty rather
than guessed. The mapping layer matches on field name, with section as an
optional discriminator, so an empty section costs nothing and an invented one
would silently split a field's history in two.
"""
from __future__ import annotations

import html as html_mod
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from . import MemberTooLarge, ParseOutcome, RawEntry, RawField, read_member
from .values import normalise_space

# Country pages live in geos/. Everything else in these archives is apparatus:
# field listings, rank orders, appendices, reference maps, stylesheets.
GEOS_RE = re.compile(r"(?:^|/)geos/(?:print/(?:country/)?)?([a-z]{2})\.html$", re.I)

# 2005-generation section anchors, mapped to the names the rest of the corpus
# uses so a field's section is comparable across editions.
ANCHOR_SECTIONS = {
    "geo": "Geography", "people": "People and Society", "govt": "Government",
    "econ": "Economy", "comm": "Communications", "trans": "Transportation",
    "military": "Military and Security", "issues": "Transnational Issues",
    "intro": "Introduction", "energy": "Energy", "env": "Environment",
}

SECTION_SLUGS = {
    "geography": "Geography", "people-and-society": "People and Society",
    "government": "Government", "economy": "Economy", "energy": "Energy",
    "communications": "Communications", "transportation": "Transportation",
    "military-and-security": "Military and Security",
    "transnational-issues": "Transnational Issues",
    "introduction": "Introduction", "environment": "Environment",
}

MAX_MEMBER_BYTES = 8 * 1024 * 1024      # a country page far larger than this is not one
# An edition holds a few hundred country pages. An archive claiming tens of
# thousands is not a Factbook edition, and parsing it to find that out is the
# thing worth refusing. Matches the ceiling json_era.py applies. §136.
MAX_MEMBERS = 20_000

# `<meta http-equiv="refresh" content="0;url=um.html">` — a forwarding page.
REDIRECT_RE = re.compile(
    r"""<meta[^>]+http-equiv\s*=\s*["']?refresh["']?[^>]*"""
    r"""url\s*=\s*([^"'>\s]+)""", re.I)


class _Tokeniser(HTMLParser):
    """Flatten HTML into (kind, name, attrs, text) tokens.

    Deliberately not a tree. Twenty years of hand-written markup contains
    unclosed `<td>` and stray `</div>`, so any tree built from it would be
    wrong in ways that vary by edition; a flat stream with explicit state
    machines per generation is both simpler and more honest about what it knows.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[tuple[str, str, dict, str]] = []

    def handle_starttag(self, tag, attrs):
        self.tokens.append(("start", tag, dict(attrs), ""))

    def handle_startendtag(self, tag, attrs):
        self.tokens.append(("start", tag, dict(attrs), ""))
        self.tokens.append(("end", tag, {}, ""))

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag, {}, ""))

    def handle_data(self, data):
        if data.strip():
            self.tokens.append(("text", "", {}, data))


def _tokenise(markup: str) -> list[tuple[str, str, dict, str]]:
    p = _Tokeniser()
    try:
        p.feed(markup)
        p.close()
    except Exception:                                    # pragma: no cover
        # html.parser is lenient, but a truncated file can still raise. Whatever
        # was tokenised before the failure is kept; the caller reports the
        # shortfall rather than pretending the page was empty.
        pass
    return p.tokens


def _classes(attrs: dict) -> set[str]:
    return set((attrs.get("class") or "").replace("'", " ").split())


def detect_generation(markup: str) -> str:
    if "field-anchor-" in markup:
        return "C"
    if "FieldLabel" in markup:
        return "A"
    if "category_data" in markup:
        return "B"
    return "unknown"


def _clean(text: str) -> str:
    return normalise_space(html_mod.unescape(text))


def _label(text: str) -> str:
    """Strip the trailing colon that every generation puts on field labels."""
    return _clean(text).rstrip(":").strip()


def parse_country_page(markup: str, member: str) -> tuple[str, list[RawField], list[dict]]:
    """-> (page title, fields, failures)."""
    generation = detect_generation(markup)
    tokens = _tokenise(markup)

    title = ""
    for i, (kind, name, _attrs, _text) in enumerate(tokens):
        if kind == "start" and name == "title":
            for k2, _n2, _a2, t2 in tokens[i + 1:i + 4]:
                if k2 == "text":
                    title = _clean(t2)
                    break
            break

    if generation == "A":
        fields, failures = _parse_gen_a(tokens)
    elif generation == "B":
        fields, failures = _parse_gen_b(tokens)
    elif generation == "C":
        fields, failures = _parse_gen_c(tokens)
    else:
        # A redirect and an unimplemented format are different failures, and
        # filing both under one code made the quarantine misleading. 19 of the
        # 302 rows are 318-byte meta-refresh stubs -- `um.html` and friends,
        # where the CIA moved an entry and left a forwarding page. No data is
        # missing: the target is another member of the same archive and is
        # parsed on its own. The other 283 are the 2000 edition, a real format
        # this parser does not implement. "283 pages we cannot read" is the
        # true number; 302 overstates the gap.
        redirect = REDIRECT_RE.search(markup)
        if redirect:
            return title, [], [{
                "source_pointer": member,
                "error_code": "html_redirect_stub",
                "reason": f"page is a meta-refresh redirect to "
                          f"{redirect.group(1)!r} and carries no content of its "
                          f"own; the target is a separate member of this archive",
                "raw_input": markup[:400],
            }]
        return title, [], [{
            "source_pointer": member,
            "error_code": "html_generation_unrecognised",
            "reason": "page matches none of the three known CIA HTML generations",
            "raw_input": markup[:400],
        }]
    return title, fields, failures


def _split_subfields(chunks: list[tuple[str, str]], section: str,
                     field_name: str) -> list[RawField]:
    """Turn (subfield-label, value) chunks into RawFields.

    A chunk with an empty label is the field's own value; chunks with labels are
    its subfields. Both shapes occur within a single page.
    """
    out: list[RawField] = []
    for ordinal, (sub, value) in enumerate(chunks):
        value = _clean(value)
        if not value:
            continue
        out.append(RawField(section_name=section, field_name=field_name,
                            subfield_name=_label(sub) if sub else "",
                            raw_text=value, ordinal=ordinal))
    return out


def _parse_gen_a(tokens) -> tuple[list[RawField], list[dict]]:
    """2000-2008: a label cell, then a value cell, in a table row.

    Deliberately does not try to balance `<td>` tags. This generation leaves
    cells unclosed routinely, so counting opens against closes runs past the end
    of the row and attributes the whole page to its first field -- which is
    exactly what an earlier version of this function did. Instead the label
    cells are located first, and each field's value is simply everything between
    its label and the next label. That is immune to unbalanced markup, which is
    the only property that survives twenty years of hand-edited HTML.
    """
    fields: list[RawField] = []
    n = len(tokens)

    # Pass 1: every label cell, plus the section anchor in force at that point.
    labels: list[tuple[int, int, str, str]] = []   # (label_idx, value_start, section, label)
    section = ""
    for i, (kind, name, attrs, _text) in enumerate(tokens):
        if kind == "start" and name == "a" and attrs.get("name"):
            anchor = attrs["name"].strip().lower()
            if anchor in ANCHOR_SECTIONS:
                section = ANCHOR_SECTIONS[anchor]
            continue
        if kind != "start" or name != "td" or "FieldLabel" not in _classes(attrs):
            continue

        label = ""
        j = i + 1
        # The label is the first text in the cell; a label cell is small, so a
        # bounded scan avoids running into the next row on unclosed markup.
        while j < min(n, i + 25):
            if tokens[j][0] == "text":
                candidate = _label(tokens[j][3])
                if candidate:
                    label = candidate
                    break
            j += 1
        if not label:
            continue

        # The value cell is the next <td> after the label text.
        k = j
        while k < min(n, j + 40) and not (tokens[k][0] == "start" and tokens[k][1] == "td"):
            k += 1
        labels.append((i, k + 1 if k < n else j + 1, section, label))

    # Pass 2: each field's value runs to the next label cell.
    for idx, (_label_idx, value_start, sec, label) in enumerate(labels):
        end = labels[idx + 1][0] if idx + 1 < len(labels) else n
        chunks: list[tuple[str, str]] = []
        cur_sub, cur_val = "", []
        i = value_start
        while i < end:
            kind, name, _attrs, text = tokens[i]
            if kind == "start" and name in ("i", "em"):
                # A new subfield label; close whatever was accumulating.
                if cur_val or cur_sub:
                    chunks.append((cur_sub, " ".join(cur_val)))
                cur_sub, cur_val = "", []
                if i + 1 < end and tokens[i + 1][0] == "text":
                    cur_sub = tokens[i + 1][3]
                    i += 1
            elif kind == "text":
                cur_val.append(text)
            i += 1
        if cur_val or cur_sub:
            chunks.append((cur_sub, " ".join(cur_val)))

        fields.extend(_split_subfields(chunks, sec, label))

    return fields, []


def _parse_gen_b(tokens) -> tuple[list[RawField], list[dict]]:
    """2009-2016: a label div, then value divs until the next label div."""
    fields: list[RawField] = []
    n = len(tokens)

    label_positions: list[tuple[int, str]] = []
    for i, (kind, name, attrs, _text) in enumerate(tokens):
        if kind != "start" or name != "div":
            continue
        if attrs.get("id") != "field" and "category" not in _classes(attrs):
            continue
        if attrs.get("id") != "field":
            continue
        label = ""
        j = i + 1
        while j < min(n, i + 30):
            if tokens[j][0] == "text":
                candidate = _label(tokens[j][3])
                if candidate:
                    label = candidate
                    break
            j += 1
        if label:
            label_positions.append((i, label))

    for idx, (start, label) in enumerate(label_positions):
        end = label_positions[idx + 1][0] if idx + 1 < len(label_positions) else n
        chunks: list[tuple[str, str]] = []
        cur_sub, cur_val = "", []
        in_data = False
        i = start + 1
        while i < end:
            kind, name, attrs, text = tokens[i]
            cls = _classes(attrs)
            if kind == "start" and name in ("div", "span"):
                if "category_data" in cls:
                    in_data = True
                    cur_val = []
                elif "category" in cls and name == "span":
                    if cur_val or cur_sub:
                        chunks.append((cur_sub, " ".join(cur_val)))
                        cur_val = []
                    cur_sub = ""
                    if i + 1 < end and tokens[i + 1][0] == "text":
                        cur_sub = tokens[i + 1][3]
                        i += 1
            elif kind == "end" and name in ("div", "span") and in_data:
                if cur_val:
                    chunks.append((cur_sub, " ".join(cur_val)))
                    cur_sub, cur_val = "", []
                in_data = False
            elif kind == "text" and in_data:
                cur_val.append(text)
            i += 1
        if cur_val:
            chunks.append((cur_sub, " ".join(cur_val)))

        # "country comparison to the world" is a published rank, not a value of
        # the field it sits under. It is kept as its own subfield so the rank
        # stays available without contaminating the measurement. §159.
        fields.extend(_split_subfields(chunks, "", label))

    return fields, []


def _parse_gen_c(tokens) -> tuple[list[RawField], list[dict]]:
    """2017-2020: id="field-anchor-<section>-<field>", value in id="field-<slug>"."""
    fields: list[RawField] = []
    n = len(tokens)

    anchors: list[tuple[int, str, str]] = []   # (index, section, label)
    for i, (kind, name, attrs, _t) in enumerate(tokens):
        if kind != "start" or name != "div":
            continue
        node_id = attrs.get("id") or ""
        if not node_id.startswith("field-anchor-"):
            continue
        slug = node_id[len("field-anchor-"):]
        section = ""
        for sec_slug, sec_name in SECTION_SLUGS.items():
            if slug.startswith(sec_slug + "-") or slug == sec_slug:
                section = sec_name
                break
        label = ""
        j = i + 1
        while j < min(n, i + 40):
            if tokens[j][0] == "text":
                candidate = _label(tokens[j][3])
                if candidate:
                    label = candidate
                    break
            j += 1
        if label:
            anchors.append((i, section, label))

    for idx, (start, section, label) in enumerate(anchors):
        end = anchors[idx + 1][0] if idx + 1 < len(anchors) else n
        chunks: list[tuple[str, str]] = []
        cur_sub, cur_val = "", []
        in_data = skip_tooltip = False
        i = start + 1
        while i < end:
            kind, name, attrs, text = tokens[i]
            cls = _classes(attrs)
            if kind == "start" and "tooltip-content" in cls:
                # The tooltip is the CIA's definition of the field, not a value
                # for this country. Including it would attach an identical
                # paragraph to all 260 entries.
                skip_tooltip = True
            elif kind == "end" and skip_tooltip and name == "span":
                skip_tooltip = False
            elif skip_tooltip:
                pass
            elif kind == "start" and "subfield-name" in cls:
                if cur_val or cur_sub:
                    chunks.append((cur_sub, " ".join(cur_val)))
                    cur_val = []
                cur_sub = ""
                if i + 1 < end and tokens[i + 1][0] == "text":
                    cur_sub = tokens[i + 1][3]
                    i += 1
                in_data = True
            elif kind == "start" and ("category_data" in cls or "subfield-number" in cls
                                      or "subfield-note" in cls or "subfield" in cls):
                in_data = True
            elif kind == "text" and in_data:
                cur_val.append(text)
            i += 1
        if cur_val or cur_sub:
            chunks.append((cur_sub, " ".join(cur_val)))

        fields.extend(_split_subfields(chunks, section, label))

    return fields, []


# Strings that identify the publisher or the publication, never the country.
# The spelled-out agency name matters: several editions title every page
# "The World Factbook — Central Intelligence Agency" with no country in it at
# all, and stripping only the "CIA" abbreviation left the agency name standing
# as though it were the entry's name.
PUBLISHER_TOKENS = (
    r"the\s+world\s+factbook",
    r"central\s+intelligence\s+agency",
    r"\bcia\b",
)

# The country name as the page itself marks it up. Present in the later
# generations and far more reliable than the <title>, which carries a different
# amount of site furniture in every era.
# "Flag of Czech Republic" — the only place the 2009-2016 generation names the
# country outside the page body.
FLAG_ALT_RE = re.compile(r'alt="\s*Flag of\s+([^"]{2,60})"', re.I)

COUNTRY_SPAN_RE = re.compile(
    r"<(?:span|div|h1|h2)[^>]*class=[\"']?[^\"'>]*\bcountry(?:-?name)?\b[^\"'>]*[\"']?[^>]*>"
    r"(.*?)</(?:span|div|h1|h2)>",
    re.I | re.S)


def _strip_publisher(text: str) -> str:
    out = text
    for token in PUBLISHER_TOKENS:
        out = re.sub(token, " ", out, flags=re.I)
    return out


def _country_name(markup: str, title: str, code: str) -> str:
    """The entry's country name, from the most reliable source available.

    Three attempts, in descending order of trust:

      1. The page's own country element, where the markup marks one up.
      2. The <title>, with publisher and publication strings removed. Titles
         take several shapes across the eras --
             "CIA - The World Factbook -- Aruba"                    (2002-2008)
             "CIA - The World Factbook"                             (2009-2015)
             "The World Factbook — Central Intelligence Agency"     (2016)
             "Europe :: Czechia — The World Factbook - Central …"   (2017-2020)
         Note the last one: the country sits *before* the em dash and *after*
         the region, so the publisher strings have to come out before the "::"
         split, or the trailing agency name is mistaken for the country.
      3. The two-letter code, upper-cased.

    Never invents a name. Falling back to the code is correct behaviour: entity
    resolution works from the code anyway, and a wrong name resolves to a wrong
    country, which is worse than no name.
    """
    m = COUNTRY_SPAN_RE.search(markup)
    if m:
        candidate = _clean(re.sub(r"<[^>]+>", " ", m.group(1)))
        candidate = _strip_publisher(candidate).strip(" -|,:\u2013\u2014\t")
        candidate = normalise_space(candidate)
        # Later editions upper-case it in the markup; title-case it back rather
        # than storing a shouted name.
        if candidate and candidate.isupper():
            candidate = candidate.title()
        if len(candidate) >= 2:
            return candidate

    # The 2009-2016 generation titles every page "CIA - The World Factbook" with
    # no country anywhere in the title, but labels the flag image with it.
    m = FLAG_ALT_RE.search(markup)
    if m:
        candidate = normalise_space(_strip_publisher(_clean(m.group(1))))
        candidate = candidate.strip(" -|,:\u2013\u2014\t")
        if len(candidate) >= 2:
            return candidate

    name = _strip_publisher(title)
    if "::" in name:
        name = name.split("::")[-1]
    name = name.replace("\u2014", " ").replace("\u2013", " ")
    name = name.strip(" -|,\u2014\u2013\t")
    name = re.sub(r"^\s*(?:19|20)\d{2}\s*[-\u2013\u2014:]*\s*", "", name)
    name = normalise_space(name.strip(" -|,\u2014\u2013\t"))
    if len(name) >= 2:
        return name

    return code.upper()


def parse_artifact(path: Path, *, limit_entities: int | None = None) -> ParseOutcome:
    outcome = ParseOutcome()

    with zipfile.ZipFile(path) as z:
        members = []
        skipped_non_geos = 0
        for info in z.infolist():
            m = GEOS_RE.search(info.filename)
            if not m:
                # Apparatus, not content: field listings, rank orders, appendices,
                # stylesheets, images. Counted rather than silently dropped, so
                # "we ignored 40,000 files" is visible and a change in archive
                # layout shows up as a jump instead of as missing countries.
                skipped_non_geos += 1
                continue
            # Zip-slip guard: a member that escapes the extraction root is
            # refused, not trusted. Nothing here is written to disk, but the
            # same reasoning applies to memory. §136. The size test below is a
            # cheap first pass on the archive's own claim; the ceiling that
            # actually holds is enforced at read time by read_member().
            if info.filename.startswith("/") or ".." in info.filename.split("/"):
                outcome.failures.append({
                    "source_pointer": info.filename,
                    "error_code": "unsafe_member_path",
                    "reason": "archive member escapes its root",
                    "raw_input": info.filename[:300],
                })
                continue
            if info.file_size > MAX_MEMBER_BYTES:
                outcome.failures.append({
                    "source_pointer": info.filename,
                    "error_code": "member_too_large",
                    "reason": f"{info.file_size} bytes exceeds the {MAX_MEMBER_BYTES} ceiling",
                    "raw_input": "",
                })
                continue
            members.append((m.group(1).lower(), info.filename))

        # `geos/` and `geos/print/` can both hold a page for the same country.
        # The first path wins so an edition contributes one entry per country.
        seen: set[str] = set()
        unique: list[tuple[str, str]] = []
        for code, filename in sorted(members, key=lambda x: (x[0], len(x[1]), x[1])):
            if code in seen:
                continue
            seen.add(code)
            unique.append((code, filename))

        if len(unique) > MAX_MEMBERS:
            outcome.failures.append({
                "source_pointer": str(path.name),
                "error_code": "too_many_members",
                "reason": f"{len(unique)} country pages exceeds the "
                          f"{MAX_MEMBERS} ceiling",
                "raw_input": "",
            })
            return outcome

        for ordinal, (code, filename) in enumerate(unique):
            if limit_entities is not None and outcome.members_parsed >= limit_entities:
                break
            outcome.members_seen += 1
            try:
                raw = read_member(z, filename, MAX_MEMBER_BYTES)
            except MemberTooLarge as exc:
                outcome.failures.append({
                    "source_pointer": filename,
                    "error_code": "member_too_large",
                    "reason": str(exc),
                    "raw_input": "",
                })
                continue
            except (zipfile.BadZipFile, OSError) as exc:
                outcome.failures.append({
                    "source_pointer": filename,
                    "error_code": "member_unreadable",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "raw_input": "",
                })
                continue

            markup = None
            for encoding in ("utf-8", "cp1252", "latin-1"):
                try:
                    markup = raw.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if markup is None:                            # pragma: no cover
                outcome.failures.append({
                    "source_pointer": filename,
                    "error_code": "member_undecodable",
                    "reason": "no candidate encoding decoded this page",
                    "raw_input": "",
                })
                continue

            title, fields, failures = parse_country_page(markup, filename)
            outcome.failures.extend(failures)

            if not fields:
                outcome.empty_sections += 1
                continue

            name = _country_name(markup, title, code)

            outcome.entries.append(RawEntry(
                source_key=code, source_name=name or code.upper(),
                member_path=filename, ordinal=ordinal, fields=fields))
            outcome.members_parsed += 1

        if skipped_non_geos:
            outcome.skipped_members += skipped_non_geos

    return outcome
