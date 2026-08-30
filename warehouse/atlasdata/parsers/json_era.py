"""JSON era, 2021-2025: the factbook.json cache.

Structure, confirmed by reading the files rather than the project's README:

    { name, code, published, updated, region, media,
      categories: [ { id, title, fields: [ { name, content, subfields?, ... } ] } ] }

**The upstream `value`, `suffix`, `estimated` and `info_date` keys are not CIA
data.** They are the archiving project's own parse of `content`, and treating
them as source values would silently present a third party's interpretation as
the publisher's statement. This parser therefore reads `content` — the CIA text —
and records the upstream's parse separately, where it is useful as a cross-check
against our own. §189, §190, §191.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from . import MemberTooLarge, ParseOutcome, RawEntry, RawField, read_member
from .values import normalise_space

# Keys the archiving project adds. Listed explicitly so that if the upstream
# format gains a key, it shows up as unrecognised rather than being absorbed
# silently as though it were source data.
UPSTREAM_DERIVED_KEYS = frozenset({"value", "suffix", "prefix", "estimated",
                                   "info_date", "field_id", "comparative"})

# Region directories in the archive. Not a taxonomy this platform adopts — it is
# the source's own filing system, kept only to build the member path.
SKIP_MEMBERS = ("LICENSE.md", "README.md", ".gitignore")

# Ceilings shared with the HTML parser. A country file is tens to hundreds
# of kilobytes; anything far past that is not a country file.
MAX_MEMBER_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 20_000


def _strip_markup(text: str) -> str:
    """Turn the embedded presentational HTML into plain text.

    `content` carries `<strong>` labels and `<br>` separators. The subfield
    structure is read from `subfields`, so here the markup only has to become
    readable text; the original stays in raw_markup.
    """
    import html
    import re

    out = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    out = re.sub(r"<[^>]+>", "", out)
    return normalise_space(html.unescape(out))


def parse_artifact(path: Path, *, limit_entities: int | None = None) -> ParseOutcome:
    outcome = ParseOutcome()

    with zipfile.ZipFile(path) as z:
        members = []
        for info in z.infolist():
            if not info.filename.endswith(".json") or info.filename.endswith(SKIP_MEMBERS):
                continue
            # The same guards html_era.py applies. They were missing here, which
            # left the JSON path reading any member straight into memory with no
            # ceiling — a decompression bomb in an archive whose digest happened
            # to match would simply be swallowed.
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
                    "reason": f"{info.file_size} bytes exceeds the "
                              f"{MAX_MEMBER_BYTES} ceiling for one country file",
                    "raw_input": "",
                })
                continue
            members.append(info.filename)
        members.sort()

        if len(members) > MAX_MEMBERS:
            outcome.failures.append({
                "source_pointer": str(path.name),
                "error_code": "too_many_members",
                "reason": f"{len(members)} members exceeds the {MAX_MEMBERS} ceiling",
                "raw_input": "",
            })
            return outcome

        for ordinal, member in enumerate(members):
            if limit_entities is not None and outcome.members_parsed >= limit_entities:
                break
            outcome.members_seen += 1
            try:
                doc = json.loads(read_member(z, member, MAX_MEMBER_BYTES)
                                 .decode("utf-8"))
            except MemberTooLarge as exc:
                outcome.failures.append({
                    "source_pointer": member,
                    "error_code": "member_too_large",
                    "reason": str(exc),
                    "raw_input": "",
                })
                continue
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                outcome.failures.append({
                    "source_pointer": member,
                    "error_code": "json_undecodable",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "raw_input": "",
                })
                continue

            code = (doc.get("code") or Path(member).stem).strip()
            name = normalise_space(doc.get("name") or "")
            if not name:
                outcome.failures.append({
                    "source_pointer": member,
                    "error_code": "entry_without_name",
                    "reason": "no `name` key; cannot be resolved to an entity",
                    "raw_input": json.dumps(doc)[:500],
                })
                continue

            entry = RawEntry(source_key=code.lower(), source_name=name,
                             member_path=member, ordinal=ordinal)

            # Document-level publication metadata is a field like any other, so
            # that the release's own timestamps stay attached to the record they
            # came from rather than being inferred later.
            for key in ("published", "updated", "region"):
                if doc.get(key):
                    entry.fields.append(RawField(
                        section_name="_document", field_name=key,
                        raw_text=normalise_space(str(doc[key]))))

            for cat in doc.get("categories") or []:
                section = normalise_space(cat.get("title") or cat.get("id") or "")
                for f_ord, fld in enumerate(cat.get("fields") or []):
                    fname = normalise_space(fld.get("name") or "")
                    if not fname:
                        continue
                    content = fld.get("content") or ""
                    subfields = fld.get("subfields") or []

                    if subfields:
                        for s_ord, sub in enumerate(subfields):
                            sname = normalise_space(sub.get("name") or sub.get("title") or "")
                            stext = _strip_markup(sub.get("content") or "")
                            if not stext:
                                continue
                            entry.fields.append(RawField(
                                section_name=section, field_name=fname,
                                subfield_name=sname, raw_text=stext,
                                ordinal=s_ord,
                                raw_markup=sub.get("content")))
                    else:
                        text = _strip_markup(content)
                        if not text:
                            continue
                        entry.fields.append(RawField(
                            section_name=section, field_name=fname,
                            raw_text=text, ordinal=f_ord, raw_markup=content))

                    # A field note qualifies the whole field and is kept as its
                    # own subfield rather than being concatenated into the value.
                    if fld.get("field_note"):
                        entry.fields.append(RawField(
                            section_name=section, field_name=fname,
                            subfield_name="_note",
                            raw_text=_strip_markup(fld["field_note"]),
                            ordinal=900))

            if not entry.fields:
                outcome.failures.append({
                    "source_pointer": member,
                    "error_code": "entry_without_fields",
                    "reason": "parsed but produced no fields",
                    "raw_input": json.dumps(doc)[:500],
                })
                continue

            outcome.entries.append(entry)
            outcome.members_parsed += 1

    return outcome
