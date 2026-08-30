"""Schema tests: prove the database refuses what the design says it refuses.

Every claim the schema documentation makes about integrity is asserted here by
trying to violate it. A constraint nobody has tested is a comment.

Runs against the configured database inside a transaction that is always rolled
back, so it neither needs nor leaves a fixture. It requires the migrations to
have been applied; it does not require any data to have been loaded.

    just wh-test-db
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata.db import DatabaseUnavailable, connect

failures: list[str] = []
checks = 0


def rejects(conn, label: str, sql: str, params: tuple = (), *,
            deferred: bool = False, constraint: str | None = None,
            message: str | None = None) -> None:
    """Assert that the database refuses `sql` — for the right reason.

    An earlier version accepted any exception whose class name contained
    "Violation" or "Error" as proof that the constraint fired. That is too
    generous in two ways, both demonstrated against this database:

      * a SQL *syntax* error raises psycopg.errors.SyntaxError, whose name ends
        in "Error", so a typo in a fixture counted as a pass while the
        constraint under test was never reached;
      * an unrelated NOT NULL violation on the same statement also counted, so a
        test labelled "percentage of 140" would still pass with the percentage
        domain deleted from the schema.

    The first is a hard failure of the harness. The second is not fixable by
    SQLSTATE alone -- an unrelated NOT NULL and the check under test are both
    class 23 -- so a refusal must also name the rule that produced it. Every
    fixture passes `constraint=` (the constraint whose violation it is
    demonstrating) or `message=` (a substring, for the deferred assertion
    triggers, which raise with no constraint name). A fixture that trips some
    other class-23 rule now fails instead of quietly passing, which is what the
    previous version of this docstring claimed and did not do.

    `deferred=True` forces DEFERRABLE INITIALLY DEFERRED constraints with
    SET CONSTRAINTS ALL IMMEDIATE — without it a deferred trigger would not fire
    in a test that never commits, and the check would silently not run.
    """
    global checks
    checks += 1

    # SQLSTATE classes that mean "the data was refused":
    #   23xxx integrity constraint violation (NOT NULL, FK, unique, check, exclusion)
    #   22xxx data exception (domain violation, numeric out of range, bad cast)
    #   P0001 raise_exception, used by the assertion triggers
    ACCEPTABLE = ("23", "22")
    # Anything here means the test itself is broken, not the schema.
    HARNESS_BUGS = {"42601": "SQL syntax error",
                    "42703": "undefined column",
                    "42P01": "undefined table",
                    "42883": "undefined function",
                    "42P02": "undefined parameter"}

    with conn.cursor() as cur:
        cur.execute("SAVEPOINT t")
        try:
            cur.execute(sql, params)
            if deferred:
                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cur.execute("RELEASE SAVEPOINT t")
        except Exception as exc:
            cur.execute("ROLLBACK TO SAVEPOINT t")
            state = getattr(exc, "sqlstate", None) or ""
            if state in HARNESS_BUGS:
                failures.append(
                    f"{label}: the FIXTURE is broken ({HARNESS_BUGS[state]}, "
                    f"SQLSTATE {state}) — the constraint under test was never "
                    f"reached, and an earlier harness would have called this a pass")
            elif state.startswith(ACCEPTABLE) or state == "P0001":
                got = getattr(getattr(exc, "diag", None), "constraint_name", None)
                if constraint is not None and got != constraint:
                    failures.append(
                        f"{label}: refused, but by {got!r} rather than the "
                        f"{constraint!r} this fixture exists to demonstrate — the "
                        f"rule under test may no longer be reachable")
                elif message is not None and message not in str(exc):
                    failures.append(
                        f"{label}: refused, but the message does not mention "
                        f"{message!r}: {str(exc).splitlines()[0]}")
                elif constraint is None and message is None:
                    failures.append(
                        f"{label}: passed no constraint= or message=, so this "
                        f"check cannot tell which rule refused it")
                return
            else:
                failures.append(f"{label}: refused with unexpected SQLSTATE "
                                f"{state or '(none)'}: {type(exc).__name__}: {exc}")
            return
        failures.append(f"{label}: the database ACCEPTED it, but must not")


def accepts(conn, label: str, sql: str, params: tuple = ()) -> None:
    global checks
    checks += 1
    with conn.cursor() as cur:
        cur.execute("SAVEPOINT t")
        try:
            cur.execute(sql, params)
            cur.execute("ROLLBACK TO SAVEPOINT t")
        except Exception as exc:
            cur.execute("ROLLBACK TO SAVEPOINT t")
            failures.append(f"{label}: the database REFUSED valid input: "
                            f"{type(exc).__name__}: {exc}")


def main() -> int:
    # The context manager is bound to a name deliberately: `connect().__enter__()`
    # leaves the generator unreferenced, Python collects it, its `finally` runs,
    # and the connection closes underneath the test.
    try:
        cm = connect()
        conn = cm.__enter__()
    except DatabaseUnavailable as exc:
        print(f"test_schema: NOT RUN — {exc}", file=sys.stderr)
        return 1

    with conn.cursor() as cur:
        cur.execute("BEGIN")

        # Fixtures, rolled back at the end.
        cur.execute("""
            INSERT INTO source.publisher (code, name) VALUES ('t_pub','T')
            RETURNING publisher_id""")
        pub = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO source.dataset (publisher_id, code, title)
            VALUES (%s,'t_ds','T') RETURNING dataset_id""", (pub,))
        ds = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO source.release (dataset_id, code, label, edition_year)
            VALUES (%s,'t_r','T 2020',2020) RETURNING release_id""", (ds,))
        rel = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO core.entity (entity_type_id, slug)
            SELECT entity_type_id,'t_entity' FROM core.entity_type
             WHERE code='sovereign_state' RETURNING entity_id""")
        ent = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO ref.metric (code,label,description,metric_domain_id,
                                    value_kind,preferred_unit_id)
            SELECT 't.pop','T','A test integer metric.', d.metric_domain_id,
                   'integer', u.unit_id
              FROM ref.metric_domain d, ref.unit u
             WHERE d.path='demo.population' AND u.code='person'
            RETURNING metric_id""")
        metric = cur.fetchone()[0]

    # ── typing: a metric's value kind is not negotiable ──────────────────────
    rejects(conn, "population stored as text",
        """INSERT INTO obs.observation
                  (entity_id, metric_id, value_kind, reference_period, release_id,
                   parser_version, parse_status, notes)
           VALUES (%s,%s,'text','[2020-01-01,2021-01-01)',%s,'t','parsed_exact','t')""",
        (ent, metric, rel),
        constraint="observation_metric_value_kind_fk")

    rejects(conn, "observation header with no typed value row",
        """INSERT INTO obs.observation
                  (entity_id, metric_id, value_kind, reference_period, release_id,
                   parser_version, parse_status, notes)
           VALUES (%s,%s,'integer','[2020-01-01,2021-01-01)',%s,'t','parsed_exact','t')""",
        (ent, metric, rel), deferred=True,
        message="typed value rows, expected exactly 1")

    # The mirror of the case above: header plus value, checked with the same
    # deferred constraint forced immediate, must be accepted.
    accepts(conn, "a well-formed integer observation",
        """WITH o AS (
             INSERT INTO obs.observation
                    (entity_id, metric_id, value_kind, reference_period, release_id,
                     parser_version, parse_status, notes)
             VALUES (%s,%s,'integer','[2020-01-01,2021-01-01)',%s,'t','parsed_exact','t')
             RETURNING observation_id)
           INSERT INTO obs.integer_observation (observation_id, value)
           SELECT observation_id, 1000 FROM o""",
        (ent, metric, rel))

    # ── missingness must state which kind it is ──────────────────────────────
    rejects(conn, "parsed value that also claims to be missing",
        """INSERT INTO obs.observation
                  (entity_id, metric_id, value_kind, reference_period, release_id,
                   parser_version, parse_status, missing_reason, notes)
           VALUES (%s,%s,'integer','[2020-01-01,2021-01-01)',%s,'t','parsed_exact',
                   'unknown','t')""",
        (ent, metric, rel),
        constraint="observation_missing_reason_iff_unparsed")

    rejects(conn, "unparsed observation with no missing_reason",
        """INSERT INTO obs.observation
                  (entity_id, metric_id, value_kind, reference_period, release_id,
                   parser_version, parse_status, notes)
           VALUES (%s,%s,'integer','[2020-01-01,2021-01-01)',%s,'t','unparsed','t')""",
        (ent, metric, rel),
        constraint="observation_missing_reason_iff_unparsed")

    # ── provenance is not optional ───────────────────────────────────────────
    rejects(conn, "observation with neither a source field nor an explanation",
        """INSERT INTO obs.observation
                  (entity_id, metric_id, value_kind, reference_period, release_id,
                   parser_version, parse_status)
           VALUES (%s,%s,'integer','[2020-01-01,2021-01-01)',%s,'t','parsed_exact')""",
        (ent, metric, rel),
        constraint="observation_has_provenance")

    # ── domains ──────────────────────────────────────────────────────────────
    rejects(conn, "percentage of 140",
        """INSERT INTO obs.composition_member
                  (composition_id, category_id, share_percent)
           SELECT 1, 1, 140::ref.percentage""",
        constraint="percentage_within_0_100")

    rejects(conn, "latitude beyond the pole",
        """SELECT 95::ref.latitude""",
        constraint="latitude_within_range")
    rejects(conn, "longitude beyond the antimeridian",
        """SELECT 181::ref.longitude""",
        constraint="longitude_within_range")
    rejects(conn, "sha256 that is not 64 hex characters",
        """SELECT 'nothex'::ref.sha256_hex""",
        constraint="sha256_hex_is_64_lowercase_hex")
    accepts(conn, "a valid sha256",
        """SELECT repeat('a',64)::ref.sha256_hex""")

    # ── temporal identity: the constraint the whole entity model rests on ────
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO core.entity (entity_type_id, slug)
            SELECT entity_type_id,'t_entity_2' FROM core.entity_type
             WHERE code='historical_state' RETURNING entity_id""")
        ent2 = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO core.entity_identifier
                   (entity_id, identifier_scheme_id, value, validity, status)
            SELECT %s, identifier_scheme_id, 'ZZ',
                   daterange('1974-01-01','1993-01-01','[)'), 'historical'
              FROM core.identifier_scheme WHERE code='iso3166_1_alpha2'""", (ent2,))

    accepts(conn, "the same code reassigned to another entity in a later period",
        """INSERT INTO core.entity_identifier
                  (entity_id, identifier_scheme_id, value, validity, status)
           SELECT %s, identifier_scheme_id, 'ZZ',
                  daterange('1993-01-01','2006-01-01','[)'), 'historical'
             FROM core.identifier_scheme WHERE code='iso3166_1_alpha2'""", (ent,))

    rejects(conn, "the same code denoting two entities at the same instant",
        """INSERT INTO core.entity_identifier
                  (entity_id, identifier_scheme_id, value, validity, status)
           SELECT %s, identifier_scheme_id, 'ZZ',
                  daterange('1980-01-01','1990-01-01','[)'), 'current'
             FROM core.identifier_scheme WHERE code='iso3166_1_alpha2'""", (ent,),
        constraint="entity_identifier_code_denotes_one_entity")

    # ── preferred names may not overlap in time ──────────────────────────────
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO core.entity_name
                   (entity_id, name_kind_id, name, language_tag, is_preferred, validity)
            SELECT %s, name_kind_id, 'First', 'en', true,
                   daterange('1990-01-01','2000-01-01','[)')
              FROM core.name_kind WHERE code='canonical'""", (ent,))

    rejects(conn, "two preferred names of one kind overlapping in time",
        """INSERT INTO core.entity_name
                  (entity_id, name_kind_id, name, language_tag, is_preferred, validity)
           SELECT %s, name_kind_id, 'Second', 'en', true,
                  daterange('1995-01-01','2005-01-01','[)')
             FROM core.name_kind WHERE code='canonical'""", (ent,),
        constraint="entity_name_one_preferred_at_a_time")

    accepts(conn, "a rename: preferred names in adjacent, non-overlapping periods",
        """INSERT INTO core.entity_name
                  (entity_id, name_kind_id, name, language_tag, is_preferred, validity)
           SELECT %s, name_kind_id, 'Second', 'en', true,
                  daterange('2000-01-01','2010-01-01','[)')
             FROM core.name_kind WHERE code='canonical'""", (ent,))

    # ── referential integrity and self-reference ─────────────────────────────
    rejects(conn, "an observation against a non-existent entity",
        """INSERT INTO obs.observation
                  (entity_id, metric_id, value_kind, reference_period, release_id,
                   parser_version, parse_status, notes)
           VALUES (-1,%s,'integer','[2020-01-01,2021-01-01)',%s,'t','parsed_exact','t')""",
        (metric, rel),
        constraint="observation_entity_id_fkey")

    rejects(conn, "an entity related to itself",
        """INSERT INTO core.entity_relation
                  (subject_entity_id, object_entity_id, entity_relation_type_id)
           SELECT %s, %s, entity_relation_type_id
             FROM core.entity_relation_type WHERE code='borders'""", (ent, ent),
        constraint="entity_relation_not_reflexive")

    rejects(conn, "duplicate release code within one dataset",
        """INSERT INTO source.release (dataset_id, code, label, edition_year)
           VALUES (%s,'t_r','duplicate',2021)""", (ds,),
        constraint="release_code_unique_per_dataset")

    rejects(conn, "an empty reference period",
        """INSERT INTO obs.observation
                  (entity_id, metric_id, value_kind, reference_period, release_id,
                   parser_version, parse_status, notes)
           VALUES (%s,%s,'integer','[2020-01-01,2020-01-01)',%s,'t','parsed_exact','t')""",
        (ent, metric, rel),
        constraint="observation_period_not_empty")

    # ── curation guards ──────────────────────────────────────────────────────
    rejects(conn, "a fuzzy entity match accepted without further evidence",
        """INSERT INTO core.entity_resolution
                  (dataset_id, source_key, entity_id, status, method)
           VALUES (%s,'t_key',%s,'accepted','fuzzy_candidate')""", (ds, ent),
        constraint="entity_resolution_fuzzy_is_never_self_accepted")

    rejects(conn, "an accepted entity resolution with no entity",
        """INSERT INTO core.entity_resolution
                  (dataset_id, source_key, entity_id, status, method)
           VALUES (%s,'t_key2',NULL,'accepted','curated')""", (ds,),
        constraint="entity_resolution_accepted_has_entity")

    rejects(conn, "a quantitative metric with no unit",
        """INSERT INTO ref.metric (code,label,description,metric_domain_id,value_kind)
           SELECT 't.nounit','T','A numeric metric with no unit.',
                  metric_domain_id,'numeric'
             FROM ref.metric_domain WHERE path='demo.population'""",
        constraint="metric_quantitative_has_unit")

    rejects(conn, "a curation decision with no rationale",
        """INSERT INTO meta.curation_decision
                  (subject_kind, subject_key, new_state, rationale, decided_by)
           VALUES ('other','k','{}'::jsonb,'   ','tester')""",
        constraint="curation_rationale_present")

    # ── the subtype invariant must hold against subtype DML too ──────────
    # Regression: the deferred trigger fired only on obs.observation, so
    # deleting a value row after commit left an orphaned header that nothing
    # re-examined. Reproduced live before migration 0018.
    with conn.cursor() as cur:
        cur.execute("""
            WITH o AS (
              INSERT INTO obs.observation
                     (entity_id, metric_id, value_kind, reference_period, release_id,
                      parser_version, parse_status, notes)
              VALUES (%s,%s,'integer','[2021-01-01,2022-01-01)',%s,'t','parsed_exact','orphan-test')
              RETURNING observation_id)
            INSERT INTO obs.integer_observation (observation_id, value)
            SELECT observation_id, 7 FROM o""", (ent, metric, rel))
        cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    rejects(conn, "deleting a value row, orphaning its header",
        """DELETE FROM obs.integer_observation
            WHERE observation_id IN (SELECT observation_id FROM obs.observation
                                      WHERE notes = 'orphan-test')""",
        deferred=True,
        message="typed value rows, expected exactly 1")

    # ── provenance is now enforced on the other fact tables too ──────────
    rejects(conn, "composition with neither a field value nor a note",
        """INSERT INTO obs.composition
                  (entity_id, metric_id, category_scheme_id, reference_period,
                   release_id, parser_version, parse_status)
           SELECT %s, %s, cs.category_scheme_id, '[2020-01-01,2021-01-01)', %s,
                  't', 'parsed_exact'
             FROM ref.category_scheme cs WHERE cs.code = 'language'""",
        (ent, metric, rel),
        constraint="composition_has_provenance")

    conn.rollback()
    cm.__exit__(None, None, None)

    if failures:
        print(f"test_schema: {len(failures)} of {checks} checks FAILED", file=sys.stderr)
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"test_schema: {checks} constraint checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
