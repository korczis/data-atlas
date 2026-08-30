"""Resolving a source's own key for a place onto a canonical entity.

Three kinds of evidence, in strict order of strength:

1. **An identifier match.** The source key is a GEC code; if that code is
   recorded for an entity in `core.entity_identifier` for a period overlapping
   the edition, the mapping is deterministic and is accepted.
2. **An exact name match.** The source's heading matches a recorded name for
   exactly one entity, within its validity period. Accepted, with the matched
   name kept as evidence.
3. **Nothing.** The record stays unresolved and enters the curation queue.

There is no fourth rule. Trigram similarity may be used to *propose* candidates
for a human to look at, and the schema forbids a fuzzy proposal from being
self-accepted (`entity_resolution_fuzzy_is_never_self_accepted`). "Congo" is the
case that settles the argument: in this corpus it can mean either of two
republics depending on the edition, and a parser that picks one is not resolving
an entity, it is fabricating a fact. §80, §81.

Resolution is recorded per (dataset, source_key) rather than per record, so one
decision applies to every edition and changing it is a single auditable edit.
"""
from __future__ import annotations

from .db import dicts, scalar


def resolve_dataset(conn, dataset_code: str, *, gec_scheme: str = "cwf_gec") -> dict:
    """Resolve every distinct source key in a dataset. Returns counts."""
    dataset_id = scalar(conn, "SELECT dataset_id FROM source.dataset WHERE code = %s",
                        (dataset_code,))
    if dataset_id is None:
        raise ValueError(f"no dataset {dataset_code!r}")

    stats = {"by_code": 0, "by_name": 0, "unresolved": 0, "ambiguous": 0}

    # Distinct source keys, with a representative label and the span of editions
    # they appear in. One row per key, not per record.
    # The representative label is the one used by the MOST editions, not the
    # alphabetically first. `min()` looks harmless and is not: where one era's
    # parser produced a bad label, "Central Intelligence Agency" sorts before
    # almost every country name and was chosen for every key that had it in
    # even one edition -- so the publisher's name became the name of 206
    # entities carrying two thirds of all observations.
    #
    # Ties break on the longer label, then alphabetically, so the result is
    # deterministic rather than dependent on scan order.
    keys = dicts(conn, """
        WITH labelled AS (
            SELECT sr.source_key, sr.source_label,
                   count(*) AS uses,
                   min(rel.edition_year) AS first_year,
                   max(rel.edition_year) AS last_year
              FROM source.record sr
              JOIN source.artifact a ON a.artifact_id = sr.artifact_id
              JOIN source.release rel ON rel.release_id = a.release_id
             WHERE rel.dataset_id = %s
             GROUP BY sr.source_key, sr.source_label),
        ranked AS (
            SELECT source_key, source_label, uses,
                   row_number() OVER (
                       PARTITION BY source_key
                       ORDER BY uses DESC, length(source_label) DESC, source_label) AS rn
              FROM labelled)
        SELECT r.source_key,
               r.source_label AS label,
               min(l.first_year) AS first_year,
               max(l.last_year)  AS last_year,
               sum(l.uses)       AS record_count
          FROM ranked r
          JOIN labelled l ON l.source_key = r.source_key
         WHERE r.rn = 1
         GROUP BY r.source_key, r.source_label
         ORDER BY r.source_key""", (dataset_id,))

    with conn.cursor() as cur:
        for k in keys:
            entity_id, method, evidence = _resolve_one(
                conn, k["source_key"], k["label"], k["first_year"], k["last_year"],
                gec_scheme)

            status = "accepted" if entity_id else "proposed"
            if method == "ambiguous":
                stats["ambiguous"] += 1
            elif method == "exact_code":
                stats["by_code"] += 1
            elif method == "exact_name":
                stats["by_name"] += 1
            else:
                stats["unresolved"] += 1

            cur.execute("""
                INSERT INTO core.entity_resolution
                       (dataset_id, source_key, source_label, entity_id, status,
                        method, evidence, decided_by, decided_at,
                        first_seen_year, last_seen_year)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), %s, %s)
                ON CONFLICT (dataset_id, source_key) DO UPDATE
                   SET entity_id = EXCLUDED.entity_id,
                       status = EXCLUDED.status,
                       method = EXCLUDED.method,
                       evidence = EXCLUDED.evidence,
                       source_label = EXCLUDED.source_label,
                       first_seen_year = EXCLUDED.first_seen_year,
                       last_seen_year = EXCLUDED.last_seen_year
                 -- A curated decision is never overwritten by an automatic one.
                 -- Re-running resolution must not undo a human's work. §110.
                 WHERE core.entity_resolution.method <> 'curated'""",
                (dataset_id, k["source_key"], k["label"], entity_id, status,
                 method if method != "ambiguous" else "unresolved", evidence,
                 "auto-resolver", k["first_year"], k["last_year"]))

        # Apply accepted resolutions to the records themselves, set-based. §154.
        cur.execute("""
            UPDATE source.record sr
               SET entity_id = er.entity_id,
                   resolution_status = 'accepted'
              FROM core.entity_resolution er
              JOIN source.artifact a2 ON true
             WHERE er.dataset_id = %s
               AND er.source_key = sr.source_key
               AND er.entity_id IS NOT NULL
               AND er.status = 'accepted'
               AND sr.artifact_id = a2.artifact_id
               AND a2.release_id IN (SELECT release_id FROM source.release
                                      WHERE dataset_id = %s)""",
            (dataset_id, dataset_id))
        stats["records_linked"] = cur.rowcount

    conn.commit()
    return stats


def _resolve_one(conn, source_key: str, label: str, first_year: int, last_year: int,
                 gec_scheme: str) -> tuple[int | None, str, str]:
    """-> (entity_id | None, method, evidence)."""
    # 1. Identifier match, bounded by the edition span. The overlap test is what
    #    stops a reassigned code resolving to the wrong holder: a code valid only
    #    until 1993 does not match a 2020 edition.
    rows = dicts(conn, """
        SELECT ei.entity_id, e.slug
          FROM core.entity_identifier ei
          JOIN core.entity e ON e.entity_id = ei.entity_id
          JOIN core.identifier_scheme s
            ON s.identifier_scheme_id = ei.identifier_scheme_id
         WHERE s.code = %s
           AND lower(ei.value) = lower(%s)
           AND ei.status <> 'erroneous'
           AND ei.validity && daterange(make_date(%s, 1, 1), make_date(%s, 12, 31), '[]')
         """, (gec_scheme, source_key, first_year, last_year))
    if len(rows) == 1:
        return (rows[0]["entity_id"], "exact_code",
                f"{gec_scheme}={source_key} valid over editions {first_year}-{last_year}")
    if len(rows) > 1:
        return (None, "ambiguous",
                f"{gec_scheme}={source_key} resolves to {len(rows)} entities over "
                f"{first_year}-{last_year}: {', '.join(r['slug'] for r in rows)}")

    # 2. Exact name match, also bounded by period.
    if label:
        rows = dicts(conn, """
            SELECT DISTINCT en.entity_id, e.slug, en.name
              FROM core.entity_name en
              JOIN core.entity e ON e.entity_id = en.entity_id
             WHERE lower(btrim(en.name)) = lower(btrim(%s))
               AND en.validity && daterange(make_date(%s, 1, 1), make_date(%s, 12, 31), '[]')
             """, (label, first_year, last_year))
        if len(rows) == 1:
            return (rows[0]["entity_id"], "exact_name",
                    f"name {rows[0]['name']!r} matched exactly")
        if len(rows) > 1:
            return (None, "ambiguous",
                    f"name {label!r} matches {len(rows)} entities: "
                    f"{', '.join(r['slug'] for r in rows)}")

    return (None, "unresolved",
            f"no identifier or exact name match for {source_key!r} ({label!r})")


def candidate_names(conn, label: str, limit: int = 5) -> list[dict]:
    """Trigram-ranked suggestions for a human reviewing an unresolved record.

    Suggestions only. Nothing in this module writes a resolution based on this
    function's output, and the database would reject it if it tried.
    """
    return dicts(conn, """
        SELECT e.slug, en.name, similarity(lower(en.name), lower(%s)) AS score
          FROM core.entity_name en
          JOIN core.entity e ON e.entity_id = en.entity_id
         WHERE similarity(lower(en.name), lower(%s)) > 0.3
         ORDER BY score DESC
         LIMIT %s""", (label, label, limit))


def bootstrap_entities(conn, dataset_code: str, *, gec_scheme: str = "cwf_gec") -> dict:
    """Create one canonical entity per unresolved source entry.

    What this asserts, precisely: *this source has a distinct entry with this
    identifier, and called it this*. That is a restatement of the source, not an
    inference about the world, which is what makes it safe to automate.

    What it deliberately does NOT assert:

      * a kind -- every bootstrapped entity is 'unclassified', because the
        Factbook does not reliably say whether an entry is a sovereign state, a
        dependency, an ocean or a disputed territory, and guessing would classify
        Antarctica as a country;
      * an existence period -- left unbounded rather than inferred from which
        editions happen to mention it, since a corpus starting in 1992 says
        nothing about when a country began;
      * identity across sources -- one entity per source key, so a later adapter
        that also has Czechia produces a separate entity until someone merges
        them. Merging is curation, and the merge is the interesting decision.

    The identifier is recorded as 'provisional' and the resolution evidence says
    it came from here, so nothing downstream can mistake a bootstrapped entity
    for a curated one. §82.
    """
    dataset_id = scalar(conn, "SELECT dataset_id FROM source.dataset WHERE code = %s",
                        (dataset_code,))
    unclassified = scalar(conn,
        "SELECT entity_type_id FROM core.entity_type WHERE code = 'unclassified'")
    scheme_id = scalar(conn,
        "SELECT identifier_scheme_id FROM core.identifier_scheme WHERE code = %s",
        (gec_scheme,))

    pending = dicts(conn, """
        SELECT er.source_key, er.source_label, er.first_seen_year, er.last_seen_year
          FROM core.entity_resolution er
         WHERE er.dataset_id = %s AND er.entity_id IS NULL
         ORDER BY er.source_key""", (dataset_id,))

    created = 0
    with conn.cursor() as cur:
        for row in pending:
            label = (row["source_label"] or "").strip()
            slug = _slugify(label or row["source_key"])
            if not slug:
                continue

            # Slugs are unique; a collision means two source entries share a
            # name. Disambiguate with the source key rather than silently
            # merging two entries into one entity.
            cur.execute("SELECT 1 FROM core.entity WHERE slug = %s", (slug,))
            if cur.fetchone():
                slug = f"{slug}-{row['source_key']}"

            cur.execute("""
                INSERT INTO core.entity (entity_type_id, slug, notes)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO NOTHING
                RETURNING entity_id""",
                (unclassified, slug,
                 f"Bootstrapped from {dataset_code} entry {row['source_key']!r} "
                 f"({label!r}), editions {row['first_seen_year']}-{row['last_seen_year']}. "
                 f"Kind, existence period and cross-source identity are all pending curation."))
            got = cur.fetchone()
            if not got:
                continue
            entity_id = got[0]
            created += 1

            if label:
                cur.execute("""
                    INSERT INTO core.entity_name
                           (entity_id, name_kind_id, name, language_tag, is_preferred)
                    VALUES (%s, (SELECT name_kind_id FROM core.name_kind WHERE code='canonical'),
                            %s, 'en', true)
                    ON CONFLICT DO NOTHING""", (entity_id, label[:300]))
                cur.execute("""
                    INSERT INTO core.entity_name
                           (entity_id, name_kind_id, name, language_tag, is_preferred)
                    VALUES (%s, (SELECT name_kind_id FROM core.name_kind WHERE code='source_form'),
                            %s, 'en', false)
                    ON CONFLICT DO NOTHING""", (entity_id, label[:300]))

            cur.execute("""
                INSERT INTO core.entity_identifier
                       (entity_id, identifier_scheme_id, value, status, notes)
                VALUES (%s, %s, %s, 'provisional', %s)
                ON CONFLICT DO NOTHING""",
                (entity_id, scheme_id, row["source_key"],
                 "Recorded by bootstrap from the source's own entry key; provisional "
                 "until a human confirms the entity it denotes."))

            cur.execute("""
                UPDATE core.entity_resolution
                   SET entity_id = %s, status = 'accepted', method = 'exact_code',
                       evidence = %s, decided_by = 'bootstrap', decided_at = now()
                 WHERE dataset_id = %s AND source_key = %s
                   AND method <> 'curated'""",
                (entity_id,
                 f"Entity created by bootstrap from {gec_scheme}={row['source_key']}; "
                 f"asserts a distinct source entry, not a classification.",
                 dataset_id, row["source_key"]))
    conn.commit()

    # Link the records, set-based.
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE source.record sr
               SET entity_id = er.entity_id, resolution_status = 'accepted'
              FROM core.entity_resolution er, source.artifact a, source.release rel
             WHERE er.dataset_id = %s
               AND er.source_key = sr.source_key
               AND er.entity_id IS NOT NULL
               AND sr.entity_id IS NULL
               AND a.artifact_id = sr.artifact_id
               AND rel.release_id = a.release_id
               AND rel.dataset_id = %s""", (dataset_id, dataset_id))
        linked = cur.rowcount
    conn.commit()
    return {"created": created, "records_linked": linked}


def _slugify(text: str) -> str:
    import re
    import unicodedata
    n = unicodedata.normalize("NFKD", text)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-zA-Z0-9]+", "-", n).strip("-").lower()
    return n[:80]


def repair_bootstrapped_names(conn, dataset_code: str) -> int:
    """Re-derive the name of bootstrapped entities from the current best label.

    A bootstrapped entity's name is not a curated fact — it is a copy of what
    the source called the entry, and it is only as good as the parser was on the
    day it ran. When a parser fix produces a better label, the entity should
    follow; otherwise a naming bug is frozen into the entity registry forever
    and the only remedy is a full rebuild.

    Scope is deliberately narrow. Only entities typed `unclassified` (i.e.
    created by bootstrap, never curated) are touched, and only their canonical
    name and slug. Identity, identifiers and every observation attached to them
    are untouched, so nothing that cites the entity is disturbed.
    """
    dataset_id = scalar(conn, "SELECT dataset_id FROM source.dataset WHERE code = %s",
                        (dataset_code,))
    rows = dicts(conn, """
        SELECT e.entity_id, e.slug, er.source_label, er.source_key,
               (SELECT n.name FROM core.entity_name n
                 WHERE n.entity_id = e.entity_id AND n.is_preferred
                 ORDER BY n.entity_name_id LIMIT 1) AS current_name
          FROM core.entity_resolution er
          JOIN core.entity e ON e.entity_id = er.entity_id
          JOIN core.entity_type t ON t.entity_type_id = e.entity_type_id
         WHERE er.dataset_id = %s AND t.code = 'unclassified'
           AND btrim(er.source_label) <> ''""", (dataset_id,))

    repaired = 0
    with conn.cursor() as cur:
        for r in rows:
            desired = r["source_label"].strip()[:300]
            if not desired or desired == r["current_name"]:
                continue
            cur.execute("""
                UPDATE core.entity_name SET name = %s
                 WHERE entity_id = %s AND is_preferred
                   AND name_kind_id = (SELECT name_kind_id FROM core.name_kind
                                        WHERE code = 'canonical')""",
                (desired, r["entity_id"]))
            new_slug = _slugify(desired) or r["slug"]
            cur.execute("SELECT 1 FROM core.entity WHERE slug = %s AND entity_id <> %s",
                        (new_slug, r["entity_id"]))
            if cur.fetchone():
                new_slug = f"{new_slug}-{r['source_key']}"
            if new_slug != r["slug"]:
                cur.execute("UPDATE core.entity SET slug = %s WHERE entity_id = %s",
                            (new_slug, r["entity_id"]))
            repaired += 1
    conn.commit()
    return repaired
