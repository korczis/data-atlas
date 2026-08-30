"""Era parsers: bytes in, uninterpreted records out.

Every parser in this package produces the same shape — `RawEntry` holding
`RawField` values — regardless of whether it read plain text, one of three
generations of HTML, or JSON. That shape is deliberately dumb: a section name, a
field name, an optional subfield name, an ordinal, and the text exactly as
published. No units, no numbers, no entity resolution.

The separation matters. Parsing "what did this file say" and deciding "what does
that mean" are different problems with different failure modes, and a parser that
does both cannot be tested against a fixture without also asserting a mapping.
Interpretation happens later, from staging, driven by source.field_mapping. §72.

Selecting a parser is a property of the artifact, not of the year: 2001 has both
a text artifact and an HTML one.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawField:
    """One field of one entry, exactly as published."""

    section_name: str
    field_name: str
    raw_text: str
    subfield_name: str = ""
    ordinal: int = 0
    raw_markup: str | None = None


@dataclass
class RawEntry:
    """One country or territory entry, before any interpretation."""

    source_key: str
    source_name: str
    member_path: str
    ordinal: int = 0
    fields: list[RawField] = field(default_factory=list)


@dataclass
class ParseOutcome:
    """What a parser produced, and what defeated it.

    `failures` is never discarded by callers: it becomes rows in
    meta.rejected_record. A parser that returns entries and drops its failures
    has made the corpus look cleaner than it is. §21.
    """

    entries: list[RawEntry] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    members_seen: int = 0
    members_parsed: int = 0
    # Markers or containers that yielded no fields. Counted rather than ignored:
    # in the text era these are the instructional example block, and a sudden
    # rise would mean real sections had stopped parsing.
    empty_sections: int = 0
    # Archive members deliberately not treated as content (site apparatus).
    # Counted so the decision is visible in the run record.
    skipped_members: int = 0


class MemberTooLarge(Exception):
    """An archive member decompressed past the ceiling it was allowed."""

    def __init__(self, name: str, ceiling: int):
        super().__init__(f"{name} decompresses past the {ceiling} byte ceiling")
        self.name = name
        self.ceiling = ceiling


def read_member(z, name: str, ceiling: int) -> bytes:
    """Read one archive member, bounded by bytes actually decompressed.

    `ZipInfo.file_size` is the archive's own claim about a member, written by
    whoever built the archive. Bounding a read with it is trusting the
    attacker's arithmetic: a member declaring a kilobyte can inflate to tens of
    megabytes before zipfile truncates what it hands back, and the memory is
    spent either way. Reading one byte past the ceiling and refusing is the only
    check that costs what it says it costs. The declared size is still worth
    testing first — it rejects the honest oversized member without decompressing
    anything — but it is a shortcut, not the guarantee.
    """
    with z.open(name) as fh:
        data = fh.read(ceiling + 1)
    if len(data) > ceiling:
        raise MemberTooLarge(name, ceiling)
    return data


PARSER_FAMILIES = ("text_gutenberg", "text_cia_wayback", "html_cia_zip",
                   "json_factbook_cache")


def get_parser(family: str):
    """Return the parse function for a parser family."""
    if family in ("text_gutenberg", "text_cia_wayback"):
        from .text_era import parse_artifact
        return parse_artifact
    if family == "html_cia_zip":
        from .html_era import parse_artifact
        return parse_artifact
    if family == "json_factbook_cache":
        from .json_era import parse_artifact
        return parse_artifact
    raise ValueError(f"unknown parser family {family!r}; known: {PARSER_FAMILIES}")
