"""Data-quality checks, recorded as queryable findings rather than printed.

Every check writes rows to `meta.quality_issue` against a `meta.quality_run`.
That matters more than it sounds: a release gate can read a table, and cannot
read a log. It also means "the suite found nothing" and "the suite did not run"
are distinguishable, which is the failure mode this repository has already been
bitten by five times on the catalogue side.

Checks are declared in `meta.quality_check` (migration 0007) and implemented
here. A check declared and not implemented is itself reported, so the catalogue
of checks cannot quietly overstate what is verified.
"""
from __future__ import annotations

import argparse

from .db import DatabaseUnavailable, connect, dicts, scalar
from .logging import emit, log

# Tolerance for composition shares. Wide on purpose: rounding, unlisted
# residuals and overlapping categories all occur in real sources, and a tight
# bound would fire constantly on correct data and then be ignored. §78.
COMPOSITION_TOLERANCE = 25.0

# How many example rows a check records per run. The cap keeps one bad edition
# from writing a million issue rows -- but the *count* reported must be the true
# count, not the capped one. Reporting 500 when 4,051 exist is a check that
# understates the problem it was written to surface.
ISSUE_SAMPLE_LIMIT = 500


def _issue(cur, run_id: int, check_code: str, severity: str, subject: str,
           detail: str, entity_id=None, release_id=None, observation_id=None) -> None:
    cur.execute("""
        INSERT INTO meta.quality_issue
               (quality_run_id, quality_check_id, severity, subject, detail,
                entity_id, release_id, observation_id)
        VALUES (%s, (SELECT quality_check_id FROM meta.quality_check WHERE code = %s),
                %s, %s, %s, %s, %s, %s)""",
        (run_id, check_code, severity, subject[:500], detail[:2000],
         entity_id, release_id, observation_id))


def run_checks(conn, dataset_code: str) -> dict:
    dataset_id = scalar(conn, "SELECT dataset_id FROM source.dataset WHERE code = %s",
                        (dataset_code,))
    run_id = scalar(conn, """
        INSERT INTO meta.quality_run (dataset_id, status) VALUES (%s, 'running')
        RETURNING quality_run_id""", (dataset_id,))
    conn.commit()

    implemented = {
        "observation_without_provenance": _check_provenance,
        "unresolved_entity": _check_unresolved,
        "composition_share_sum": _check_composition_sums,
        "reference_period_after_publication": _check_period_after_publication,
        "value_outside_expected_range": _check_expected_range,
        "duplicate_observation": _check_duplicates,
        "parser_coverage": _check_parser_coverage,
        "record_count_reconciliation": _check_reconciliation,
        "artifact_digest_mismatch": _check_digests,
        "value_contradicts_unit": _check_unit_contradiction,
    }

    declared = {r["code"] for r in dicts(conn, "SELECT code FROM meta.quality_check")}
    missing = declared - set(implemented)

    found = 0
    with conn.cursor() as cur:
        for fn in implemented.values():
            found += fn(cur, run_id, dataset_id)
        # A declared-but-unimplemented check is a finding about this system, not
        # about the data. Reported so the check catalogue cannot overstate
        # what is actually verified.
        for code in sorted(missing):
            _issue(cur, run_id, "parser_coverage", "info", f"check:{code}",
                   f"quality check {code!r} is declared in meta.quality_check but no "
                   f"implementation is wired up in atlasdata/quality.py")
            found += 1

        cur.execute("""
            UPDATE meta.quality_run
               SET status='succeeded', finished_at=now(), checks_run=%s, issues_found=%s
             WHERE quality_run_id=%s""",
            (len(implemented), found, run_id))
    conn.commit()
    return {"run_id": run_id, "checks_run": len(implemented), "issues": found,
            "unimplemented": sorted(missing)}


def _note_truncation(cur, run_id: int, check_code: str, total: int, recorded: int) -> None:
    """Say so when the recorded examples are a sample of a larger population.

    Without this, a check that found 4,051 problems and recorded 500 of them
    reported "500" -- an eightfold understatement of its own finding, with
    nothing anywhere to indicate the number had been capped.
    """
    if total > recorded:
        _issue(cur, run_id, check_code, "info", f"check:{check_code}",
               f"{total} occurrences found; the first {recorded} are recorded as "
               f"examples. The count reported for this check is the true total, "
               f"not the number of example rows.")


def _check_provenance(cur, run_id, dataset_id) -> int:
    cur.execute("""
        SELECT o.observation_id, e.slug, m.code
          FROM obs.observation o
          JOIN core.entity e ON e.entity_id = o.entity_id
          JOIN ref.metric m ON m.metric_id = o.metric_id
         WHERE o.field_value_id IS NULL AND btrim(o.notes) = ''
         LIMIT 500""")
    rows = cur.fetchall()
    for obs_id, slug, metric in rows:
        _issue(cur, run_id, "observation_without_provenance", "error",
               f"{slug}/{metric}",
               "observation has neither a source field value nor an explanation of "
               "how it was derived", observation_id=obs_id)
    return len(rows)


def _check_unresolved(cur, run_id, dataset_id) -> int:
    cur.execute("""
        SELECT source_key, source_label, first_seen_year, last_seen_year
          FROM core.entity_resolution
         WHERE dataset_id = %s AND entity_id IS NULL
         ORDER BY source_key LIMIT 1000""", (dataset_id,))
    rows = cur.fetchall()
    for key, label, first, last in rows:
        _issue(cur, run_id, "unresolved_entity", "warning", f"{key} ({label})",
               f"source entry appears in editions {first}-{last} and resolves to no "
               f"canonical entity; its records and raw values are staged and "
               f"loadable once resolved")
    return len(rows)


def _check_composition_sums(cur, run_id, dataset_id) -> int:
    cur.execute("""
        SELECT c.composition_id, e.slug, m.code,
               EXTRACT(YEAR FROM lower(c.reference_period))::int AS yr,
               sum(cm.share_percent) AS total
          FROM obs.composition c
          JOIN obs.composition_member cm ON cm.composition_id = c.composition_id
          JOIN core.entity e ON e.entity_id = c.entity_id
          JOIN ref.metric m ON m.metric_id = c.metric_id
         GROUP BY c.composition_id, e.slug, m.code, yr
        HAVING sum(cm.share_percent) IS NOT NULL
           AND abs(sum(cm.share_percent) - 100) > %s
         LIMIT %s""", (COMPOSITION_TOLERANCE, ISSUE_SAMPLE_LIMIT))
    rows = cur.fetchall()
    cur.execute("""
        SELECT count(*) FROM (
            SELECT 1 FROM obs.composition c
              JOIN obs.composition_member cm ON cm.composition_id = c.composition_id
             GROUP BY c.composition_id
            HAVING sum(cm.share_percent) IS NOT NULL
               AND abs(sum(cm.share_percent) - 100) > %s) x""",
        (COMPOSITION_TOLERANCE,))
    # Named distinctly from the per-row share sum below. Calling both `total`
    # let the loop variable shadow the count, so the check returned the last
    # composition's share sum instead of how many compositions were out of
    # tolerance -- which is how a findings count came out as 2140.3.
    out_of_tolerance = cur.fetchone()[0]
    for _comp_id, slug, metric, yr, share_sum in rows:
        _issue(cur, run_id, "composition_share_sum", "warning",
               f"{slug}/{metric}/{yr}",
               f"named shares sum to {share_sum}, more than {COMPOSITION_TOLERANCE} "
               f"from 100. Often legitimate (unlisted residual, overlapping "
               f"categories); occasionally a parse error")
    _note_truncation(cur, run_id, "composition_share_sum", out_of_tolerance, len(rows))
    return out_of_tolerance


def _check_period_after_publication(cur, run_id, dataset_id) -> int:
    cur.execute("""
        SELECT o.observation_id, e.slug, m.code,
               EXTRACT(YEAR FROM lower(o.reference_period))::int AS ref_year,
               rel.edition_year
          FROM obs.observation o
          JOIN core.entity e ON e.entity_id = o.entity_id
          JOIN ref.metric m ON m.metric_id = o.metric_id
          JOIN source.release rel ON rel.release_id = o.release_id
         WHERE EXTRACT(YEAR FROM lower(o.reference_period)) > rel.edition_year + 1
         LIMIT 500""")
    rows = cur.fetchall()
    for obs_id, slug, metric, ref_year, edition in rows:
        _issue(cur, run_id, "reference_period_after_publication", "warning",
               f"{slug}/{metric}",
               f"reference year {ref_year} is later than edition {edition}; usually a "
               f"note misread as a date, occasionally a genuine projection",
               observation_id=obs_id)
    return len(rows)


def _check_expected_range(cur, run_id, dataset_id) -> int:
    cur.execute("""
        SELECT o.observation_id, e.slug, m.code, m.expected_min, m.expected_max,
               COALESCE(io.value::numeric, no.value) AS v
          FROM obs.observation o
          JOIN ref.metric m ON m.metric_id = o.metric_id
          JOIN core.entity e ON e.entity_id = o.entity_id
          LEFT JOIN obs.integer_observation io ON io.observation_id = o.observation_id
          LEFT JOIN obs.numeric_observation no ON no.observation_id = o.observation_id
         WHERE COALESCE(io.value::numeric, no.value) IS NOT NULL
           AND ((m.expected_min IS NOT NULL
                 AND COALESCE(io.value::numeric, no.value) < m.expected_min)
             OR (m.expected_max IS NOT NULL
                 AND COALESCE(io.value::numeric, no.value) > m.expected_max))
         LIMIT 500""")
    rows = cur.fetchall()
    for obs_id, slug, metric, lo, hi, v in rows:
        _issue(cur, run_id, "value_outside_expected_range", "warning",
               f"{slug}/{metric}",
               f"value {v} lies outside the plausible range [{lo}, {hi}]; commonly a "
               f"unit or magnitude parsing error", observation_id=obs_id)
    return len(rows)


def _check_unit_contradiction(cur, run_id, dataset_id) -> int:
    """Values that cannot mean what their unit claims.

    Range checks do not find these. A public debt of 2006 percent of GDP is
    outside no bound the metric declares, and the row has correct provenance to
    a real field value -- the extractor took the year out of a sentence about
    when a debt was repaid. The tell is the contradiction: a percentage is not
    denominated in a currency, and a percentage that is exactly a year inside
    this corpus's own publication range is almost never a measurement.
    """
    cur.execute("""
        SELECT o.observation_id, e.slug, m.code, no.value, o.currency_id,
               CASE WHEN o.currency_id IS NOT NULL THEN 'carries a currency'
                    ELSE 'is exactly a publication year' END AS why
          FROM obs.observation o
          JOIN ref.metric m ON m.metric_id = o.metric_id
          JOIN ref.unit u ON u.unit_id = o.unit_id
          JOIN core.entity e ON e.entity_id = o.entity_id
          JOIN obs.numeric_observation no ON no.observation_id = o.observation_id
         WHERE u.code = 'percent'
           AND (o.currency_id IS NOT NULL
                OR (no.value BETWEEN 1990 AND 2025
                    AND no.value = round(no.value)))
         ORDER BY o.observation_id
         LIMIT %s""", (ISSUE_SAMPLE_LIMIT,))
    rows = cur.fetchall()
    for obs_id, slug, metric, value, _cur_id, why in rows:
        _issue(cur, run_id, "value_contradicts_unit", "warning",
               f"{slug}/{metric}",
               f"value {value} is recorded as a percentage but {why}; this is the "
               f"signature of a number taken from explanatory prose rather than "
               f"from a published figure", observation_id=obs_id)

    cur.execute("""
        SELECT count(*)
          FROM obs.observation o
          JOIN ref.unit u ON u.unit_id = o.unit_id
          JOIN obs.numeric_observation no ON no.observation_id = o.observation_id
         WHERE u.code = 'percent'
           AND (o.currency_id IS NOT NULL
                OR (no.value BETWEEN 1990 AND 2025
                    AND no.value = round(no.value)))""")
    total = cur.fetchone()[0]
    _note_truncation(cur, run_id, "value_contradicts_unit", total, len(rows))
    return total


def _check_duplicates(cur, run_id, dataset_id) -> int:
    # True total first, then a capped sample. The two are different numbers and
    # the caller is told the first.
    cur.execute("""
        SELECT count(*) FROM (
            SELECT 1 FROM obs.observation o
             GROUP BY o.entity_id, o.metric_id, o.reference_period, o.release_id
            HAVING count(*) > 1) d""")
    total = cur.fetchone()[0]
    cur.execute("""
        SELECT e.slug, m.code, o.reference_period, o.release_id, count(*) AS n
          FROM obs.observation o
          JOIN core.entity e ON e.entity_id = o.entity_id
          JOIN ref.metric m ON m.metric_id = o.metric_id
         GROUP BY e.slug, m.code, o.reference_period, o.release_id
        HAVING count(*) > 1
         LIMIT %s""", (ISSUE_SAMPLE_LIMIT,))
    rows = cur.fetchall()
    for slug, metric, _period, release_id, n in rows:
        _issue(cur, run_id, "duplicate_observation", "warning",
               f"{slug}/{metric}",
               f"{n} observations for the same metric, entity, period and release. "
               f"Legitimate when the source repeats a field under different "
               f"subfields; a duplicate otherwise", release_id=release_id)
    _note_truncation(cur, run_id, "duplicate_observation", total, len(rows))
    return total


def _check_parser_coverage(cur, run_id, dataset_id) -> int:
    """How much of the source has a canonical mapping. Expected to be low early."""
    cur.execute("""
        SELECT count(*) FILTER (WHERE fm.field_mapping_id IS NULL) AS unmapped,
               count(*)                                            AS total
          FROM source.field_definition fd
          LEFT JOIN source.field_mapping fm
                 ON fm.dataset_id = fd.dataset_id
                AND fm.field_pattern = fd.field_name
                AND fm.status = 'accepted'
         WHERE fd.dataset_id = %s""", (dataset_id,))
    unmapped, total = cur.fetchone()
    if total:
        _issue(cur, run_id, "parser_coverage", "info", f"dataset:{dataset_id}",
               f"{unmapped} of {total} distinct source fields have no accepted "
               f"canonical mapping ({100.0 * unmapped / total:.1f}%). Their raw values "
               f"are fully preserved and become loadable as mappings are added; this "
               f"number is the honest measure of normalisation coverage, not a defect")
    return 1 if total else 0


def _check_reconciliation(cur, run_id, dataset_id) -> int:
    """Do the counts a run reported add up against what is in the tables?"""
    cur.execute("""
        SELECT a.code, ir.rows_staged,
               (SELECT count(*) FROM source.field_value fv
                  JOIN source.record sr ON sr.record_id = fv.record_id
                 WHERE sr.artifact_id = a.artifact_id) AS actual
          FROM meta.ingestion_run ir
          JOIN source.artifact a ON a.artifact_id = ir.artifact_id
         WHERE ir.stage = 'stage' AND ir.status = 'succeeded'
           AND ir.ingestion_run_id IN (
                SELECT max(ingestion_run_id) FROM meta.ingestion_run
                 WHERE stage = 'stage' GROUP BY artifact_id)""")
    rows = cur.fetchall()
    bad = 0
    for code, reported, actual in rows:
        if reported != actual:
            _issue(cur, run_id, "record_count_reconciliation", "error", code,
                   f"the staging run reported {reported} field values but "
                   f"{actual} are present for this artifact")
            bad += 1
    return bad


def _check_digests(cur, run_id, dataset_id) -> int:
    """Artifacts whose bytes are missing, the wrong size, or the wrong digest.

    The previous version did none of those things. It skipped any artifact whose
    file was absent -- the exact case its own name and docstring describe -- and
    for files that were present it compared only the size, never the digest, so
    a same-size corruption passed a check called `artifact_digest_mismatch`.

    Digests are verified only when `--deep` is requested, because re-hashing
    2.8 GB on every quality run would make the suite something people skip. The
    cheap structural checks (present, right size) always run, and the report
    says which mode it used rather than implying more than it did.
    """
    from . import manifest as manifest_mod
    from .fetch import sha256_file

    # The dataset under check, not a hardcoded one. This read
    # `manifest_mod.load("cia_world_factbook")` regardless of --dataset, so a
    # second source's quality run would have reported on the Factbook's
    # artifacts and called it a pass — a false success, and exactly the kind of
    # single-source assumption the canonical layer is supposed to be free of.
    cur.execute("SELECT code FROM source.dataset WHERE dataset_id = %s", (dataset_id,))
    row = cur.fetchone()
    if not row:
        _issue(cur, run_id, "artifact_digest_mismatch", "error", "dataset",
               f"no source.dataset row with dataset_id {dataset_id}")
        return 1
    dataset_code = row[0]

    try:
        m = manifest_mod.load(dataset_code)
    except Exception as exc:                              # pragma: no cover
        _issue(cur, run_id, "artifact_digest_mismatch", "error", "manifest",
               f"manifest for dataset {dataset_code!r} could not be loaded: {exc}")
        return 1

    found = 0
    deep = bool(globals().get("_DEEP_DIGESTS"))
    for a in m.artifacts:
        path = a.path()
        if not path.exists():
            # Only a problem for something the registry says we retrieved.
            cur.execute("""SELECT status::text FROM source.artifact WHERE code = %s""",
                        (a.artifact_id,))
            row = cur.fetchone()
            if row and row[0] in ("retrieved", "verified"):
                _issue(cur, run_id, "artifact_digest_mismatch", "error", a.artifact_id,
                       f"recorded as {row[0]} but no file exists at {path}")
                found += 1
            continue
        if path.stat().st_size != a.size_bytes:
            _issue(cur, run_id, "artifact_digest_mismatch", "error", a.artifact_id,
                   f"on-disk size {path.stat().st_size} does not match the "
                   f"manifest's {a.size_bytes}")
            found += 1
            continue
        if deep:
            actual, _size = sha256_file(path)
            if actual != a.sha256:
                _issue(cur, run_id, "artifact_digest_mismatch", "error", a.artifact_id,
                       f"digest {actual} does not match the manifest's {a.sha256}")
                found += 1
    if not deep:
        _issue(cur, run_id, "artifact_digest_mismatch", "info", "mode",
               "size and presence checked; digests NOT re-hashed. Run "
               "`atlas-data quality run --deep` or `just wh-verify --all` to "
               "compare digests.")
        found += 1
    return found


def cmd_quality(args: argparse.Namespace) -> int:
    globals()["_DEEP_DIGESTS"] = bool(getattr(args, "deep", False))
    try:
        with connect() as conn:
            result = run_checks(conn, args.dataset)
            log("info", f"quality run {result['run_id']}: {result['checks_run']} checks, "
                        f"{result['issues']} findings")
            if result["unimplemented"]:
                log("warn", f"declared but not implemented: "
                            f"{', '.join(result['unimplemented'])}")
            for r in dicts(conn, """
                SELECT qc.code, qi.severity, count(*) AS n
                  FROM meta.quality_issue qi
                  JOIN meta.quality_check qc ON qc.quality_check_id = qi.quality_check_id
                 WHERE qi.quality_run_id = %s
                 GROUP BY qc.code, qi.severity ORDER BY qi.severity DESC, n DESC""",
                (result["run_id"],)):
                log("info", f"  {r['severity']:<8} {r['code']:<36} {r['n']}")
            emit(result)

            errors = scalar(conn, """
                SELECT count(*) FROM meta.quality_issue qi
                  JOIN meta.quality_check qc ON qc.quality_check_id = qi.quality_check_id
                 WHERE qi.quality_run_id = %s AND qi.severity = 'error'
                   AND qc.is_release_gate""", (result["run_id"],))
            if errors:
                log("error", f"{errors} release-gate errors — see api.data_quality_summary")
                return 1
            return 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1
