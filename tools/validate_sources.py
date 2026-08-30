#!/usr/bin/env python3
"""Check the curated data in data/sources/*.json before anything is built from it.

`build_catalog.py` already enforces the schema — without valid data it has
nothing to write. This script adds the quality checks that do not stop a build
but damage the catalogue quietly: an empty description, a description reading
"official website of the authority", a verification date in the future, two
entries pointing at the same place on the same site.

It runs inside `just check`, so bad data fails in the same place as bad UI.
"""
from __future__ import annotations

import ast, collections, datetime, json, re, sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_catalog import load_sources, load_taxonomy, domain  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# `data: none` means "a portal or a document, no data". A description that says
# the source publishes open data therefore contradicts its own classification —
# one of the two is wrong, and only a human can say which. A warning, not an
# error: this reads prose, and prose is not evidence of what a site really
# serves. It is deliberately narrow — "otevřená data" only, not "datové sady",
# which also matches a file format that legitimately carries no data itself.
CLAIMS_OPEN_DATA = re.compile(r"otevřen\w*\s+data", re.I)

# A description answers "why would I open this". These shapes answer nothing.
EMPTY_PHRASES = re.compile(
    r"^(oficiální (web|stránk|portál)|webové stránky|domovská stránka|portál úřadu)\S*\s*\.?$",
    re.I)


def main() -> int:
    topic_meta, _, places, _ = load_taxonomy()
    sources = load_sources()
    today = datetime.date.today()

    errors, warnings = [], []
    seen_path = {}
    per_country_domain = collections.defaultdict(list)

    for s in sources:
        where = f"{s.get('country')}:{s.get('id')}"
        desc = (s.get("desc") or "").strip()
        if len(desc) < 40:
            errors.append(f"{where}: description is {len(desc)} characters — too short to "
                          f"answer 'why open this'")
        if EMPTY_PHRASES.match(desc):
            errors.append(f"{where}: description says nothing — {desc!r}")
        if desc.endswith(("..", "…")):
            warnings.append(f"{where}: description trails off in an ellipsis")

        try:
            v = datetime.date.fromisoformat(s.get("verified", ""))
            # One day of slack: adding sources after midnight CEST stamps a date
            # that is still tomorrow for a runner in UTC. A real defect — a date
            # weeks ahead — is still caught.
            if v > today + datetime.timedelta(days=1):
                errors.append(f"{where}: verification date {v} is in the future")
            elif (today - v).days > 730:
                warnings.append(f"{where}: last verified {v}")
        except ValueError:
            errors.append(f"{where}: 'verified' is not a YYYY-MM-DD date")

        u = urlsplit(s["url"])
        # The query string belongs in the key: some portals route through it
        # (minv.sk/?register-adries), and without it two different pages would
        # look like one place.
        key = ((u.hostname or "").lower().removeprefix("www.") + u.path.rstrip("/")
               + ("?" + u.query if u.query else ""))
        if key in seen_path:
            errors.append(f"{where}: same place as {seen_path[key]} — only the scheme or "
                          f"a trailing slash differs")
        seen_path[key] = where
        per_country_domain[(s["country"], domain(s["url"]))].append((s["id"], u.path.rstrip("/")))

        if s.get("data") == "none" and CLAIMS_OPEN_DATA.search(desc):
            warnings.append(f"{where}: data is 'none' but the description says the "
                            f"source publishes open data — one of the two is wrong")

        if s.get("data") == "sw" and s.get("topic") not in (
                "maplibs", "spatialdb", "routing", "formats", "geocoding", "osint", "learning"):
            warnings.append(f"{where}: 'sw' on data topic '{s.get('topic')}' — is it really a tool?")

    # One domain may legitimately carry several entries — a geoportal, a cadastre
    # service and a WFS catalogue are three different things on one site. What is
    # suspicious is holding the domain root *and* several of its subpages: that is
    # usually one landing page written out as entries that all lead to the same
    # place.
    for (country, dom), items in per_country_domain.items():
        deep = [i for i, path in items if path]
        if any(not path for _, path in items) and len(deep) >= 4:
            warnings.append(f"{country}: {dom} is in the catalogue as both the root and "
                            f"{len(deep)} subpages — one landing page written out as "
                            "entries? " + ", ".join(sorted(deep)[:5]))

    # Every tool is forbidden the personal browser export unless it is on the
    # list below. The polarity matters: a hard-coded list of *checked* tools
    # missed build_places.py, which `just build` runs, so a read of .cache/
    # added there would have passed. Deny by default, permit by name.
    #
    # Searched in code, not in comments: a docstring that names the file and
    # explains why nothing may touch it is fine.
    private = ("raw.json", "candidates.json")
    MAY_READ_EXPORT = {
        "extract.py": "writes the export",
        "scan.py": "filters the export into candidates",
        "build_longlist.py": "builds the raw long list from the candidates",
        "build_provenance.py": "recomputes provenance from the export",
        "validate_sources.py": "this file — it names the tokens it searches for",
    }
    for path in sorted((ROOT / "tools").glob("*.py")):
        name = path.name
        if name in MAY_READ_EXPORT:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {ast.get_docstring(n, clean=False) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if node.value in docstrings:
                continue
            for token in private:
                if token in node.value:
                    errors.append(
                        f"tools/{name}: reads {token} — the public build must run "
                        f"on a clean clone with no browser profile. Only "
                        f"{', '.join(sorted(MAY_READ_EXPORT))} may touch the export")

    # ── Graph of topic relations ──────────────────────────────────────────────
    # A relation is a relationship, not a link. A one-way one would be lost when
    # read from the other side: a reader on topic A sees B, on B does not see A,
    # and cannot tell a relation was meant to be there. Symmetry is enforced.
    topics_raw = json.loads((ROOT / "data" / "topics.json").read_text(encoding="utf-8"))
    rel = {t["id"]: set(t.get("related", ()))
           for g in topics_raw["groups"] for t in g["topics"]}
    for tid, targets in rel.items():
        if tid in targets:
            errors.append(f"topics {tid}: topic is related to itself")
        for other in targets:
            if other not in rel:
                errors.append(f"topics {tid}: relation to unknown topic {other!r}")
            elif tid not in rel[other]:
                errors.append(f"topics {tid} ↔ {other}: relation is only one-way")

    # ── Documented absences ───────────────────────────────────────────────────
    # The gap list is a claim about what was verified not to exist. Without this
    # gate it could keep a cell that someone has since filled with a source — and
    # the matrix would then hatch a place where a source exists.
    # Deleting data/gaps.json used to remove this whole block silently: the
    # summary printed "0 documented absences", the matrix simply stopped
    # hatching, and nothing turned red. A missing input is not a pass.
    gaps_file = ROOT / "data" / "gaps.json"
    if not gaps_file.exists():
        errors.append("data/gaps.json is missing — documented absences cannot be "
                      "checked. Restore it, or write `{\"gaps\": []}` to say the "
                      "list is deliberately empty")
    if gaps_file.exists():
        gaps = json.loads(gaps_file.read_text(encoding="utf-8"))
        national = {tid for tid, m in topic_meta.items() if m.get("scope") != "supra"}
        codes = set(places)          # places is {code: name}
        filled = {(s["country"], s["topic"]) for s in sources}
        seen_cell = set()
        for g in gaps["gaps"]:
            cell = (g.get("country"), g.get("topic"))
            where = f"gaps {cell[0]}:{cell[1]}"
            if cell[1] not in topic_meta:
                errors.append(f"{where}: topic is not in data/topics.json")
            elif cell[1] not in national:
                errors.append(f"{where}: topic is supranational — blank there is not an absence")
            if cell[0] not in codes:
                errors.append(f"{where}: country is not in data/countries.json")
            if cell in filled:
                errors.append(f"{where}: the cell has a source in the catalogue — the absence "
                              f"record is a lie")
            if cell in seen_cell:
                errors.append(f"{where}: cell is listed twice")
            seen_cell.add(cell)
            if len((g.get("reason") or "").strip()) < 20:
                errors.append(f"{where}: 'reason' does not say why no source exists")

    for e in errors:
        print(f"  ✗ {e}")
    for w in warnings:
        print(f"  ⚠ {w}")
    print(f"validate_sources: {len(sources)} sources · "
          f"{len(seen_cell) if gaps_file.exists() else 0} documented absences · "
          f"{len(errors)} errors · {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
