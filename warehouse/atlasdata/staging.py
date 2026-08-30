"""Artifacts -> source registry -> staging tables, losslessly.

Two responsibilities, in order:

1. **Register** what the manifest describes — publisher, dataset, release,
   artifact, retrievals — so that provenance rows exist before any value does.
   Idempotent by natural key: re-running updates rather than duplicating.

2. **Stage** the parsed records. Every field of every entry lands in
   `staging_cwf.*` and in `source.field_value`, whether or not a canonical
   mapping exists for it. This is Layer A and B of §105: no interpretation, no
   losses, and the raw text preserved so a better parser can be run later.

Idempotence is enforced by database constraints rather than by the application
checking first (§73): re-staging an artifact deletes its previous staging rows
inside the same transaction and rewrites them, so a partial earlier run cannot
leave orphans and a repeat run cannot duplicate.

On write strategy: this stages row by row, not via COPY. The corpus is a few
hundred thousand field values and one edition stages in about twenty seconds,
which is comfortably inside the budget for a step that runs once per artifact.
COPY would be materially faster and is the right answer if this grows an order
of magnitude -- but it cannot use ON CONFLICT, so adopting it means moving
conflict handling into staging tables and merge statements. That complexity is
not yet earned, and measuring before restructuring is the rule here (§148).
The counts that would justify the change are in `atlas-data report storage`.
"""
from __future__ import annotations

import argparse
import hashlib
import json

from . import PARSER_VERSION, config
from .db import DatabaseUnavailable, connect, scalar
from .logging import emit, log
from .manifest import Artifact, Manifest
from .parsers import get_parser


def _config_fingerprint(artifact: Artifact) -> str:
    """Digest of the inputs that shape a run. Never contains secrets. §20."""
    payload = json.dumps({
        "artifact": artifact.artifact_id,
        "sha256": artifact.sha256,
        "parser_family": artifact.parser_family,
        "parser_version": PARSER_VERSION,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


# ── registry ─────────────────────────────────────────────────────────────────

def register_manifest(conn, manifest: Manifest) -> dict[str, int]:
    """Ensure the manifest's provenance rows exist. Returns artifact_id by code."""
    d = manifest.dataset

    publisher_id = scalar(conn, """
        INSERT INTO source.publisher (code, name, country_code)
        VALUES (%s, %s, %s)
        ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
        RETURNING publisher_id""",
        (d.publisher["code"], d.publisher["name"], d.publisher.get("country")))

    lic = d.license
    license_id = scalar(conn, """
        INSERT INTO source.license (code, name, url, is_open, requires_attribution, statement)
        VALUES (%s, %s, NULL, %s, %s, %s)
        ON CONFLICT (code) DO UPDATE SET statement = EXCLUDED.statement
        RETURNING license_id""",
        (lic["basis"], lic["basis"].replace("_", " ").title(), True, False,
         lic["statement"] + " " + lic.get("third_party_note", "")))

    years = manifest.years
    dataset_id = scalar(conn, """
        INSERT INTO source.dataset
               (publisher_id, code, title, description, license_id, status,
                first_release_year, last_release_year, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (code) DO UPDATE
            SET title = EXCLUDED.title, status = EXCLUDED.status,
                first_release_year = EXCLUDED.first_release_year,
                last_release_year = EXCLUDED.last_release_year,
                notes = EXCLUDED.notes
        RETURNING dataset_id""",
        (publisher_id, d.code, d.title, "", license_id, d.status,
         min(years), max(years), d.discontinued_note))

    artifact_ids: dict[str, int] = {}
    for a in manifest.artifacts:
        release_code = f"{d.code}-{a.edition_year}"
        release_id = scalar(conn, """
            INSERT INTO source.release
                   (dataset_id, code, label, edition_year, published_precision)
            VALUES (%s, %s, %s, %s, 'year')
            ON CONFLICT (dataset_id, code) DO UPDATE SET label = EXCLUDED.label
            RETURNING release_id""",
            (dataset_id, release_code, a.edition_label, a.edition_year))

        on_disk = a.path().exists()
        status = "retrieved" if on_disk else "declared"
        if a.role == "superseded":
            status = "superseded"

        artifact_id = scalar(conn, """
            INSERT INTO source.artifact
                   (release_id, code, filename, media_type, compression, size_bytes,
                    sha256, checksum_origin, parser_family, role, status,
                    license_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE
                SET status = EXCLUDED.status, role = EXCLUDED.role,
                    notes = EXCLUDED.notes
            RETURNING artifact_id""",
            (release_id, a.artifact_id, a.filename, a.media_type, a.compression,
             a.size_bytes, a.sha256, a.checksum_origin, a.parser_family, a.role,
             status, license_id, a.notes))
        artifact_ids[a.artifact_id] = artifact_id

        # Retrievals are replaced wholesale: they describe the manifest's current
        # view of where bytes can be had, and a stale URL is worse than none.
        with conn.cursor() as cur:
            cur.execute("DELETE FROM source.retrieval WHERE artifact_id = %s", (artifact_id,))
            for r in a.retrievals:
                cur.execute("""
                    INSERT INTO source.retrieval
                           (artifact_id, url, vcs_repo, vcs_commit, role, priority,
                            byte_stable, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (artifact_id, r.url,
                     (r.vcs or {}).get("repo"), (r.vcs or {}).get("commit"),
                     r.role, r.priority, r.byte_stable, r.note))

    conn.commit()
    return artifact_ids


# ── staging ──────────────────────────────────────────────────────────────────

def stage_artifact(conn, manifest: Manifest, artifact: Artifact,
                   artifact_db_id: int, *, limit_entities: int | None = None) -> dict:
    """Parse one artifact and write it into staging and the source registry."""
    path = artifact.path()
    if not path.exists():
        raise FileNotFoundError(
            f"{artifact.artifact_id}: not on disk at {path}. "
            f"Run `atlas-data source fetch --artifact {artifact.artifact_id}` first.")

    dataset_id = scalar(conn, "SELECT dataset_id FROM source.dataset WHERE code = %s",
                        (manifest.dataset.code,))
    release_id = scalar(conn, "SELECT release_id FROM source.artifact WHERE artifact_id = %s",
                        (artifact_db_id,))

    run_id = scalar(conn, """
        INSERT INTO meta.ingestion_run
               (dataset_id, release_id, artifact_id, stage, status, parser_version,
                code_revision, config_fingerprint)
        VALUES (%s, %s, %s, 'stage', 'running', %s, %s, %s)
        RETURNING ingestion_run_id""",
        (dataset_id, release_id, artifact_db_id, PARSER_VERSION,
         config.git_revision(), _config_fingerprint(artifact)))
    conn.commit()

    try:
        parse = get_parser(artifact.parser_family)
        outcome = parse(path, limit_entities=limit_entities)

        with conn.cursor() as cur:
            # Re-staging replaces: the previous rows for this artifact go, and
            # the new ones arrive, in one transaction. Nothing observes a state
            # where half of an edition is present.
            #
            # Canonical rows derived from this artifact must go first. They
            # reference source.field_value with ON DELETE RESTRICT, which is
            # deliberate -- an observation may never be silently detached from
            # the evidence it cites -- so re-staging without clearing them fails
            # loudly rather than orphaning provenance. That is the constraint
            # working, not an obstacle to route around: re-reading the bytes
            # invalidates everything derived from them, and `ingest load`
            # regenerates it. Scoped to this artifact's own field values, so a
            # sibling artifact of the same release (2001 has both a text and an
            # HTML artifact) keeps its observations.
            scope = """
                SELECT fv.field_value_id
                  FROM source.field_value fv
                  JOIN source.record sr ON sr.record_id = fv.record_id
                 WHERE sr.artifact_id = %s"""

            cur.execute(f"""
                DELETE FROM obs.composition_member
                 WHERE composition_id IN (
                       SELECT composition_id FROM obs.composition
                        WHERE field_value_id IN ({scope}))""", (artifact_db_id,))
            cur.execute(f"DELETE FROM obs.composition WHERE field_value_id IN ({scope})",
                        (artifact_db_id,))
            cur.execute(f"DELETE FROM obs.bilateral_observation "
                        f"WHERE field_value_id IN ({scope})", (artifact_db_id,))
            # obs.source_rank also cites source.field_value with RESTRICT. It is
            # empty today because rank ingestion is not implemented, so omitting
            # it costs nothing now -- and would make the first re-stage after
            # ranking is wired up fail on the field_value delete. Cheaper to
            # include while the omission is still visible.
            cur.execute(f"DELETE FROM obs.source_rank WHERE field_value_id IN ({scope})",
                        (artifact_db_id,))
            cur.execute(f"DELETE FROM geo.entity_point WHERE field_value_id IN ({scope})",
                        (artifact_db_id,))
            for sub in ("integer", "numeric", "boolean", "categorical", "text"):
                cur.execute(f"""
                    DELETE FROM obs.{sub}_observation
                     WHERE observation_id IN (
                           SELECT observation_id FROM obs.observation
                            WHERE field_value_id IN ({scope}))""", (artifact_db_id,))
            cur.execute(f"DELETE FROM obs.observation WHERE field_value_id IN ({scope})",
                        (artifact_db_id,))
            # Two kinds of quarantine row point at this artifact, and both must
            # go or a re-stage double-counts. Load-time rejections carry a
            # field_value_id; parse-time ones (an unreadable page, a file whose
            # sub-format has no parser) carry only the artifact. Deleting just
            # the first kind left the second accumulating on every run, which
            # inflated the reported quarantine total several-fold.
            cur.execute(f"DELETE FROM meta.rejected_record WHERE field_value_id IN ({scope})",
                        (artifact_db_id,))
            cur.execute("DELETE FROM meta.rejected_record WHERE artifact_id = %s",
                        (artifact_db_id,))
            # Narrative content references source.record, also with RESTRICT.
            # Sections and fields cascade from the document, so removing the
            # documents is enough. Missing this is the same mistake as missing
            # the observation tables: every table that cites the evidence has to
            # be cleared before the evidence can be replaced.
            cur.execute("""
                DELETE FROM content.document
                 WHERE record_id IN (SELECT record_id FROM source.record
                                      WHERE artifact_id = %s)""", (artifact_db_id,))

            cur.execute("DELETE FROM staging_cwf.entry WHERE artifact_id = %s",
                        (artifact_db_id,))
            cur.execute("""
                DELETE FROM source.field_value
                 WHERE record_id IN (SELECT record_id FROM source.record
                                      WHERE artifact_id = %s)""", (artifact_db_id,))
            cur.execute("DELETE FROM source.record WHERE artifact_id = %s",
                        (artifact_db_id,))

            staged_fields = 0
            for entry in outcome.entries:
                entry_id = _one(cur, """
                    INSERT INTO staging_cwf.entry
                           (artifact_id, ingestion_run_id, edition_year, member_path,
                            source_key, source_name, ordinal, parser_family)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING entry_id""",
                    (artifact_db_id, run_id, artifact.edition_year, entry.member_path,
                     entry.source_key, entry.source_name, entry.ordinal,
                     artifact.parser_family))

                record_id = _one(cur, """
                    INSERT INTO source.record
                           (artifact_id, member_path, source_key, source_label, ordinal)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING record_id""",
                    (artifact_db_id, entry.member_path, entry.source_key,
                     entry.source_name, entry.ordinal))

                for f in entry.fields:
                    cur.execute("""
                        INSERT INTO staging_cwf.entry_field
                               (entry_id, section_name, field_name, subfield_name,
                                ordinal, raw_text, raw_markup)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (entry_id, section_name, field_name,
                                     subfield_name, ordinal) DO NOTHING""",
                        (entry_id, f.section_name, f.field_name, f.subfield_name,
                         f.ordinal, f.raw_text, f.raw_markup))

                    fd_id = _one(cur, """
                        INSERT INTO source.field_definition
                               (dataset_id, section_name, field_name, first_seen_year,
                                last_seen_year, edition_count, record_count, example_value)
                        VALUES (%s, %s, %s, %s, %s, 0, 0, %s)
                        ON CONFLICT (dataset_id, section_name, field_name) DO UPDATE
                            SET first_seen_year =
                                    least(source.field_definition.first_seen_year,
                                          EXCLUDED.first_seen_year),
                                last_seen_year =
                                    greatest(source.field_definition.last_seen_year,
                                             EXCLUDED.last_seen_year)
                        RETURNING field_definition_id""",
                        (dataset_id, f.section_name,
                         _qualified(f.field_name, f.subfield_name),
                         artifact.edition_year, artifact.edition_year,
                         f.raw_text[:400]))

                    cur.execute("""
                        INSERT INTO source.field_value
                               (record_id, field_definition_id, ordinal, raw_text, raw_markup)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (record_id, field_definition_id, ordinal) DO NOTHING""",
                        (record_id, fd_id, f.ordinal, f.raw_text, f.raw_markup))
                    # Count rows actually inserted, not insert attempts. ON
                    # CONFLICT DO NOTHING silently skips a duplicate
                    # (record, field, ordinal) -- which happens when one entry
                    # repeats a field under a subfield the parser flattened --
                    # and counting attempts made the run report more field
                    # values than the table holds. The reconciliation check
                    # caught it on the 2015 and 2017 editions.
                    staged_fields += cur.rowcount

            # Failures become quarantine rows. A parser that returns entries and
            # drops its failures makes the corpus look cleaner than it is. §21.
            for fail in outcome.failures:
                cur.execute("""
                    INSERT INTO meta.rejected_record
                           (ingestion_run_id, artifact_id, source_pointer, error_code,
                            reason, raw_input, parser_version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (run_id, artifact_db_id, fail["source_pointer"], fail["error_code"],
                     fail["reason"], fail["raw_input"], PARSER_VERSION))

            cur.execute("""
                UPDATE meta.ingestion_run
                   SET status = 'succeeded', finished_at = now(),
                       rows_read = %s, rows_staged = %s, rows_rejected = %s,
                       warning_count = %s,
                       message = %s
                 WHERE ingestion_run_id = %s""",
                (outcome.members_seen, staged_fields, len(outcome.failures),
                 outcome.empty_sections,
                 f"{outcome.members_parsed} entries, {staged_fields} fields, "
                 f"{outcome.empty_sections} empty containers",
                 run_id))
        conn.commit()

        return {
            "artifact": artifact.artifact_id,
            "entries": outcome.members_parsed,
            "fields": staged_fields,
            "rejected": len(outcome.failures),
            "empty_sections": outcome.empty_sections,
            "run_id": run_id,
        }

    except Exception as exc:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE meta.ingestion_run
                   SET status = 'failed', finished_at = now(), error_count = 1,
                       message = %s
                 WHERE ingestion_run_id = %s""",
                (f"{type(exc).__name__}: {exc}"[:2000], run_id))
        conn.commit()
        raise


def _one(cur, sql: str, params: tuple):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def _qualified(field_name: str, subfield_name: str) -> str:
    """Field identity includes its subfield.

    "Area / total" and "Area / land" are different measurements, and merging
    them under "Area" would make the field dictionary claim a single field where
    the source has three.
    """
    return f"{field_name} / {subfield_name}" if subfield_name else field_name


def refresh_field_statistics(conn, dataset_code: str) -> int:
    """Recompute per-field edition and record counts, set-based.

    Kept out of the staging loop deliberately: maintaining running counts per
    row would be thousands of updates, while this is one pass at the end. §154.
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH stats AS (
                SELECT fv.field_definition_id,
                       count(*)                        AS record_count,
                       count(DISTINCT r.edition_year)  AS edition_count
                  FROM source.field_value fv
                  JOIN source.record sr ON sr.record_id = fv.record_id
                  JOIN source.artifact a ON a.artifact_id = sr.artifact_id
                  JOIN source.release r ON r.release_id = a.release_id
                 GROUP BY fv.field_definition_id)
            UPDATE source.field_definition fd
               SET record_count = s.record_count,
                   edition_count = s.edition_count
              FROM stats s
             WHERE s.field_definition_id = fd.field_definition_id""")
        updated = cur.rowcount
    conn.commit()
    return updated


# ── CLI ──────────────────────────────────────────────────────────────────────

# Arbitrary but fixed: the key identifies "the staging pipeline on this
# database" and must never collide with another advisory lock in the same
# cluster. Recorded here rather than inline so a second lock added later is
# forced to pick a different number deliberately.
_STAGE_LOCK = 0x0A71A5DA7A01

def cmd_stage(args: argparse.Namespace) -> int:
    from .cli import _selected

    try:
        manifest, selected = _selected(args)
    except SystemExit as exc:
        log("error", str(exc))
        return 2

    selected = [a for a in selected if a.ingestable]
    if not selected:
        log("error", "selection matched no ingestable artifacts "
                     "(superseded artifacts are fetched and verified, never parsed)")
        return 1

    missing = [a for a in selected if not a.path().exists()]
    if missing:
        for a in missing:
            log("error", f"{a.artifact_id}: not on disk — fetch it first")
        return 1

    try:
        with connect() as conn:
            # Only one staging run at a time, enforced by the database rather
            # than by hoping. Staging deletes an artifact's previous rows before
            # rewriting them, so two overlapping runs delete each other's work
            # and leave editions silently empty -- which is exactly what happened
            # during development, and the counts looked plausible enough that
            # only a per-artifact query revealed it. A session-level advisory
            # lock is the cheapest correct guard: it is released automatically
            # if the process dies, so a crash cannot leave the pipeline wedged.
            if not scalar(conn, "SELECT pg_try_advisory_lock(%s)", (_STAGE_LOCK,)):
                log("error",
                    "another staging run holds the lock on this database.\n"
                    "    Staging rewrites an artifact's rows, so concurrent runs "
                    "corrupt each other. Wait for it to finish, or check for a "
                    "stale process:\n"
                    "        SELECT * FROM meta.ingestion_run WHERE status = 'running';")
                return 1

            artifact_ids = register_manifest(conn, manifest)
            log("info", f"registry synced: {len(artifact_ids)} artifacts")

            total = {"entries": 0, "fields": 0, "rejected": 0, "failed": 0}
            for a in sorted(selected, key=lambda x: (x.edition_year, x.artifact_id)):
                try:
                    r = stage_artifact(conn, manifest, a, artifact_ids[a.artifact_id],
                                       limit_entities=args.limit_entities)
                except Exception as exc:
                    log("error", f"{a.artifact_id}: {type(exc).__name__}: {exc}")
                    total["failed"] += 1
                    continue
                total["entries"] += r["entries"]
                total["fields"] += r["fields"]
                total["rejected"] += r["rejected"]
                log("info", f"staged {a.artifact_id}",
                    entries=r["entries"], fields=r["fields"], rejected=r["rejected"])
                emit(r)

            updated = refresh_field_statistics(conn, manifest.dataset.code)
            log("info", f"field statistics refreshed for {updated} field definitions")
            log("info", f"staged {total['entries']} entries, {total['fields']} fields, "
                        f"{total['rejected']} rejected, {total['failed']} artifacts failed")
            return 1 if total["failed"] else 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1
