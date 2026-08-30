"""Schema documentation generated from the live catalogue.

A hand-written ER diagram is wrong within a week. Everything here is read from
`information_schema` and `pg_catalog`, so the documentation describes the
database that exists rather than the one someone remembers designing. §84.

Two outputs:

  * `docs/database/SCHEMA-REFERENCE.md` — every schema, table, column, type,
    nullability, constraint, index and comment.
  * `docs/database/ERD.md` — Mermaid diagrams, one per bounded context, because
    a single diagram of a hundred-plus tables is decoration rather than
    documentation. §177.
"""
from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime

from . import config
from .db import DatabaseUnavailable, connect, dicts
from .logging import emit, log

MANAGED = ("meta", "source", "ref", "core", "obs", "geo", "content",
           "derived", "publication", "mart", "search", "api", "staging_cwf")

# Bounded contexts for the ERDs. One diagram per question a reader might have,
# rather than one diagram nobody can read.
CONTEXTS = [
    ("Source and provenance",
     "Where evidence comes from: publisher to dataset to release to the bytes, "
     "and the raw records and fields inside them.",
     ["source.publisher", "source.dataset", "source.release", "source.artifact",
      "source.retrieval", "source.record", "source.field_definition",
      "source.field_value", "source.field_mapping", "source.license"]),
    ("Canonical entity identity",
     "Places and their names, codes and relations over time. The model that has "
     "to survive states appearing, merging and being renamed.",
     ["core.entity", "core.entity_type", "core.entity_name", "core.name_kind",
      "core.entity_identifier", "core.identifier_scheme", "core.entity_relation",
      "core.entity_relation_type", "core.entity_resolution"]),
    ("Observations",
     "Typed claims and the disjoint subtype hierarchy that keeps them typed.",
     ["obs.observation", "obs.integer_observation", "obs.numeric_observation",
      "obs.boolean_observation", "obs.categorical_observation",
      "obs.text_observation", "obs.composition", "obs.composition_member",
      "obs.bilateral_observation", "obs.source_rank", "ref.metric", "ref.unit"]),
    ("Dimensional mart",
     "The analytics projection, generated from the canonical model.",
     ["mart.dim_entity", "mart.dim_metric", "mart.dim_release", "mart.dim_period",
      "mart.fact_observation", "mart.fact_composition", "mart.fact_bilateral"]),
]


def _fetch(conn) -> dict:
    tables = dicts(conn, """
        SELECT c.oid, n.nspname AS schema, c.relname AS name,
               CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view'
                              WHEN 'm' THEN 'materialized view' END AS kind,
               obj_description(c.oid) AS comment,
               c.reltuples::bigint AS est_rows
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind IN ('r','v','m') AND n.nspname = ANY(%s)
         ORDER BY n.nspname, c.relname""", (list(MANAGED),))

    columns = dicts(conn, """
        SELECT n.nspname AS schema, c.relname AS table_name, a.attname AS column_name,
               format_type(a.atttypid, a.atttypmod) AS data_type,
               a.attnotnull AS not_null, a.attnum AS position,
               pg_get_expr(d.adbin, d.adrelid) AS default_expr,
               col_description(c.oid, a.attnum) AS comment,
               a.attgenerated <> '' AS is_generated
          FROM pg_attribute a
          JOIN pg_class c ON c.oid = a.attrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
          LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
         WHERE a.attnum > 0 AND NOT a.attisdropped
           AND c.relkind IN ('r','v','m') AND n.nspname = ANY(%s)
         ORDER BY n.nspname, c.relname, a.attnum""", (list(MANAGED),))

    constraints = dicts(conn, """
        SELECT n.nspname AS schema, c.relname AS table_name,
               con.conname AS name,
               CASE con.contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY'
                                WHEN 'u' THEN 'UNIQUE' WHEN 'c' THEN 'CHECK'
                                WHEN 'x' THEN 'EXCLUDE' END AS kind,
               pg_get_constraintdef(con.oid) AS definition,
               obj_description(con.oid, 'pg_constraint') AS comment
          FROM pg_constraint con
          JOIN pg_class c ON c.oid = con.conrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = ANY(%s)
         ORDER BY n.nspname, c.relname, con.contype, con.conname""", (list(MANAGED),))

    indexes = dicts(conn, """
        SELECT schemaname AS schema, tablename AS table_name,
               indexname AS name, indexdef AS definition
          FROM pg_indexes WHERE schemaname = ANY(%s)
         ORDER BY schemaname, tablename, indexname""", (list(MANAGED),))

    fks = dicts(conn, """
        SELECT n.nspname || '.' || c.relname AS child,
               n2.nspname || '.' || c2.relname AS parent,
               con.conname AS name
          FROM pg_constraint con
          JOIN pg_class c  ON c.oid  = con.conrelid
          JOIN pg_namespace n  ON n.oid  = c.relnamespace
          JOIN pg_class c2 ON c2.oid = con.confrelid
          JOIN pg_namespace n2 ON n2.oid = c2.relnamespace
         WHERE con.contype = 'f' AND n.nspname = ANY(%s)""", (list(MANAGED),))

    schemas = dicts(conn, """
        SELECT n.nspname AS name, obj_description(n.oid, 'pg_namespace') AS comment
          FROM pg_namespace n WHERE n.nspname = ANY(%s) ORDER BY n.nspname""",
        (list(MANAGED),))

    domains = dicts(conn, """
        SELECT n.nspname AS schema, t.typname AS name,
               format_type(t.typbasetype, t.typtypmod) AS base_type,
               obj_description(t.oid, 'pg_type') AS comment,
               (SELECT string_agg(pg_get_constraintdef(c.oid), '; ')
                  FROM pg_constraint c WHERE c.contypid = t.oid) AS checks
          FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
         WHERE t.typtype = 'd' AND n.nspname = ANY(%s)
         ORDER BY n.nspname, t.typname""", (list(MANAGED),))

    enums = dicts(conn, """
        SELECT n.nspname AS schema, t.typname AS name,
               string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS values,
               obj_description(t.oid, 'pg_type') AS comment
          FROM pg_type t
          JOIN pg_namespace n ON n.oid = t.typnamespace
          JOIN pg_enum e ON e.enumtypid = t.oid
         WHERE n.nspname = ANY(%s)
         GROUP BY n.nspname, t.typname, t.oid ORDER BY n.nspname, t.typname""",
        (list(MANAGED),))

    return {"tables": tables, "columns": columns, "constraints": constraints,
            "indexes": indexes, "fks": fks, "schemas": schemas,
            "domains": domains, "enums": enums}


def _reference_markdown(data: dict) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        "<!-- Generated by `atlas-data docs generate` from the live database catalogue.",
        "     Do not edit by hand: regenerate it. -->",
        "",
        "# Schema reference",
        "",
        f"Read out of `pg_catalog` on {now}. Every comment below is a `COMMENT ON` "
        "stored in the database itself, so the documentation and the schema cannot "
        "drift apart.",
        "",
        "## Schemas",
        "",
        "| Schema | Purpose |",
        "|---|---|",
    ]
    for s in data["schemas"]:
        out.append(f"| `{s['name']}` | {(s['comment'] or '').replace('|', '\\|')} |")

    if data["enums"]:
        out += ["", "## Enumerated types", "",
                "Closed internal states. Anything describing the world is a reference "
                "table instead — see ADR-0004.", "",
                "| Type | Values | Meaning |", "|---|---|---|"]
        for e in data["enums"]:
            out.append(f"| `{e['schema']}.{e['name']}` | `{e['values']}` | "
                       f"{(e['comment'] or '').replace('|', '\\|')} |")

    if data["domains"]:
        out += ["", "## Domains", "", "| Domain | Base type | Constraint | Meaning |",
                "|---|---|---|---|"]
        for d in data["domains"]:
            out.append(f"| `{d['schema']}.{d['name']}` | `{d['base_type']}` | "
                       f"`{d['checks'] or ''}` | "
                       f"{(d['comment'] or '').replace('|', '\\|')} |")

    cols_by = {}
    for c in data["columns"]:
        cols_by.setdefault((c["schema"], c["table_name"]), []).append(c)
    cons_by = {}
    for c in data["constraints"]:
        cons_by.setdefault((c["schema"], c["table_name"]), []).append(c)
    idx_by = {}
    for i in data["indexes"]:
        idx_by.setdefault((i["schema"], i["table_name"]), []).append(i)

    current_schema = None
    for t in data["tables"]:
        if t["schema"] != current_schema:
            current_schema = t["schema"]
            out += ["", f"## Schema `{current_schema}`", ""]
        key = (t["schema"], t["name"])
        out += ["", f"### `{t['schema']}.{t['name']}`", "",
                f"*{t['kind']}*", ""]
        if t["comment"]:
            out += [t["comment"], ""]
        out += ["| Column | Type | Null | Default | Meaning |", "|---|---|---|---|---|"]
        for c in cols_by.get(key, []):
            default = c["default_expr"] or ""
            if c["is_generated"]:
                default = "generated"
            out.append(
                f"| `{c['column_name']}` | `{c['data_type']}` | "
                f"{'no' if c['not_null'] else 'yes'} | "
                f"`{default}`" .replace("``", "") +
                f" | {(c['comment'] or '').replace('|', '\\|')} |")

        cons = cons_by.get(key, [])
        if cons:
            out += ["", "**Constraints**", ""]
            for c in cons:
                line = f"- `{c['name']}` — {c['kind']}: `{c['definition']}`"
                if c["comment"]:
                    line += f"\n  - {c['comment']}"
                out.append(line)

        idxs = [i for i in idx_by.get(key, [])
                if not any(c["name"] == i["name"] for c in cons)]
        if idxs:
            out += ["", "**Indexes**", ""]
            for i in idxs:
                out.append(f"- `{i['name']}`: `{i['definition']}`")

    return "\n".join(out) + "\n"


def _erd_markdown(data: dict) -> str:
    cols_by = {}
    for c in data["columns"]:
        cols_by.setdefault(f"{c['schema']}.{c['table_name']}", []).append(c)

    pk_cols = {}
    for c in data["constraints"]:
        if c["kind"] == "PRIMARY KEY":
            inner = c["definition"][c["definition"].find("(") + 1:c["definition"].rfind(")")]
            pk_cols[f"{c['schema']}.{c['table_name']}"] = {
                x.strip().strip('"') for x in inner.split(",")}

    out = [
        "<!-- Generated by `atlas-data docs generate`. Do not edit by hand. -->",
        "",
        "# Entity-relationship diagrams",
        "",
        "One diagram per bounded context. A single diagram of every table would be "
        "decoration rather than documentation, so the model is split by the question "
        "each part answers. Relationships are real foreign keys read from the "
        "catalogue, not drawn by hand.",
        "",
    ]

    for title, blurb, members in CONTEXTS:
        present = [m for m in members if m in cols_by]
        if not present:
            continue
        out += [f"## {title}", "", blurb, "", "```mermaid", "erDiagram"]
        for full in present:
            name = full.split(".", 1)[1]
            out.append(f"    {name} {{")
            for c in cols_by[full][:14]:
                # Mermaid attribute types must be bare words: a dot or a bracket
                # ends the attribute and breaks the whole diagram silently, so a
                # domain like `ref.entity_code` renders as nothing at all.
                t = re.sub(r"\W+", "_", c["data_type"].split("(")[0].strip()).strip("_")
                marker = " PK" if c["column_name"] in pk_cols.get(full, set()) else ""
                out.append(f"        {t} {c['column_name']}{marker}")
            if len(cols_by[full]) > 14:
                out.append(f"        _ and_{len(cols_by[full]) - 14}_more")
            out.append("    }")
        for fk in data["fks"]:
            if fk["child"] in present and fk["parent"] in present:
                child = fk["child"].split(".", 1)[1]
                parent = fk["parent"].split(".", 1)[1]
                if child != parent:
                    out.append(f'    {parent} ||--o{{ {child} : ""')
        out += ["```", ""]

    return "\n".join(out) + "\n"


def cmd_generate(args: argparse.Namespace) -> int:
    try:
        with connect() as conn:
            data = _fetch(conn)
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1

    target = config.ROOT / "docs" / "database"
    target.mkdir(parents=True, exist_ok=True)

    ref = target / "SCHEMA-REFERENCE.md"
    ref.write_text(_reference_markdown(data), encoding="utf-8")
    erd = target / "ERD.md"
    erd.write_text(_erd_markdown(data), encoding="utf-8")

    counts = {
        "schemas": len(data["schemas"]),
        "tables": sum(1 for t in data["tables"] if t["kind"] == "table"),
        "views": sum(1 for t in data["tables"] if t["kind"] == "view"),
        "materialized_views": sum(1 for t in data["tables"]
                                  if t["kind"] == "materialized view"),
        "columns": len(data["columns"]),
        "constraints": len(data["constraints"]),
        "indexes": len(data["indexes"]),
        "domains": len(data["domains"]),
        "enums": len(data["enums"]),
    }
    log("info", f"wrote {ref.relative_to(config.ROOT)} and {erd.relative_to(config.ROOT)}")
    log("info", " · ".join(f"{v} {k}" for k, v in counts.items()))
    emit(counts)

    undocumented = [f"{t['schema']}.{t['name']}" for t in data["tables"]
                    if not t["comment"]]
    if undocumented:
        log("warn", f"{len(undocumented)} relations have no COMMENT: "
                    f"{', '.join(undocumented[:8])}"
                    + (" …" if len(undocumented) > 8 else ""))
    return 0
