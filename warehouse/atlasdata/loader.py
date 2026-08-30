"""Staging plus mappings -> typed canonical observations.

This is the step where interpretation finally happens, and where every rule the
rest of the system exists to enforce is applied at once:

  * a value is typed according to its metric, or it is not stored as a value;
  * a reference period comes from the source's own qualifier where there is one,
    and falls back to the edition year *marked as such*, never silently;
  * an absence records which kind of absence it is;
  * anything the parser cannot justify becomes a quarantine row with its raw
    text, not a NULL;
  * every observation points at the field value it came from.

Loading is idempotent per release: a release's observations are deleted and
rewritten inside one transaction, so a rerun cannot duplicate and a failure
cannot leave half an edition. §73, §74.
"""
from __future__ import annotations

import argparse

from . import PARSER_VERSION, config
from .db import DatabaseUnavailable, connect, dicts, scalar
from .logging import emit, log
from .parsers.coordinates import parse_coordinate
from .parsers.values import parse_partners, parse_shares, parse_value

_LOAD_LOCK = 0x0A71A5DA7A02


def _period(reference_year: int | None, edition_year: int) -> tuple[str, str]:
    """-> (daterange literal, precision).

    When the source stated a year, that is the reference period and the
    precision is 'year'. When it did not, the edition year is used and the
    precision is recorded as 'unknown' — so a consumer can always tell a period
    the publisher asserted from one this platform inferred. Collapsing the two
    is the single most common way a historical dataset becomes quietly wrong.
    """
    if reference_year:
        return (f"[{reference_year}-01-01,{reference_year + 1}-01-01)", "year")
    return (f"[{edition_year}-01-01,{edition_year + 1}-01-01)", "unknown")


def load_dataset(conn, dataset_code: str) -> dict:
    dataset_id = scalar(conn, "SELECT dataset_id FROM source.dataset WHERE code = %s",
                        (dataset_code,))
    if dataset_id is None:
        raise ValueError(f"no dataset {dataset_code!r}")

    # The curated mappings are seeded here rather than by a migration, because
    # the dataset row they hang off is written by staging — after every
    # migration has run. Seeding from a migration inserted nothing on any clean
    # database and said nothing about it; see migration 0020.
    seeded = scalar(conn, "SELECT source.seed_field_mappings()")
    conn.commit()
    if seeded:
        log("info", f"seeded {seeded} curated field mappings")

    mappings = dicts(conn, """
        SELECT fm.field_mapping_id, fm.field_pattern, fm.target_kind,
               fm.transform, fm.metric_id,
               fm.category_scheme_id, fm.default_unit_id,
               m.value_kind, m.code AS metric_code
          FROM source.field_mapping fm
          LEFT JOIN ref.metric m ON m.metric_id = fm.metric_id
         WHERE fm.dataset_id = %s AND fm.status = 'accepted'""", (dataset_id,))
    by_field = {m["field_pattern"]: m for m in mappings}
    # Without mappings this function still succeeds: it walks every field value,
    # matches none of them, writes the narrative half, and reports a load. That
    # is how a from-zero rebuild produced 1.8 million staged values and zero
    # observations while exiting 0. An empty mapping set is a broken
    # installation, not an empty dataset, and it says so here.
    if not by_field:
        raise ValueError(
            f"dataset {dataset_code!r} has no accepted field mappings, so nothing "
            f"could be typed. Loading would silently produce narrative content "
            f"and no observations. Check that migration 0020 applied and that "
            f"source.seed_field_mappings() returned rows.")

    unit_ids = {r["code"]: r["unit_id"] for r in dicts(conn, "SELECT code, unit_id FROM ref.unit")}
    currency_ids = {r["code"]: r["currency_id"]
                    for r in dicts(conn, "SELECT code, currency_id FROM ref.currency")}
    totals = {"observations": 0, "compositions": 0, "bilateral": 0,
              "coordinates": 0, "rejected": 0, "unmapped": 0, "narrative": 0,
              "releases": 0}

    releases = dicts(conn, """
        SELECT release_id, edition_year, code FROM source.release
         WHERE dataset_id = %s ORDER BY edition_year""", (dataset_id,))

    for rel in releases:
        n = _load_release(conn, dataset_id, rel, by_field, unit_ids, currency_ids)
        if n["observations"] or n["compositions"] or n["bilateral"]:
            totals["releases"] += 1
        for k in ("observations", "compositions", "bilateral", "coordinates",
                  "rejected", "unmapped", "narrative"):
            totals[k] += n[k]
        if n["observations"] or n["rejected"]:
            log("info", f"loaded {rel['code']}", obs=n["observations"],
                comp=n["compositions"], bilat=n["bilateral"], rejected=n["rejected"])
    return totals


def _load_release(conn, dataset_id: int, rel: dict, by_field: dict,
                  unit_ids: dict, currency_ids: dict) -> dict:
    edition_year = rel["edition_year"]
    release_id = rel["release_id"]
    counts = {"observations": 0, "compositions": 0, "bilateral": 0,
              "coordinates": 0, "rejected": 0, "unmapped": 0, "narrative": 0}

    # The load run must record which code and which mapping set produced its
    # values. Omitting these left every loaded observation citing a run whose
    # code_revision was empty -- the provenance chain looked complete and was
    # missing the one field that identifies the code.
    #
    # The fingerprint covers the accepted mappings in force, so a load performed
    # after a mapping change is distinguishable from one performed before it,
    # without storing the mappings themselves. It contains no secrets.
    mapping_fingerprint = scalar(conn, """
        SELECT md5(coalesce(string_agg(
                   fm.field_mapping_id::text || ':' || fm.version::text, ','
                   ORDER BY fm.field_mapping_id), ''))
          FROM source.field_mapping fm
         WHERE fm.dataset_id = %s AND fm.status = 'accepted'""", (dataset_id,))

    run_id = scalar(conn, """
        INSERT INTO meta.ingestion_run
               (dataset_id, release_id, stage, status, parser_version,
                code_revision, config_fingerprint)
        VALUES (%s, %s, 'load', 'running', %s, %s, %s)
        RETURNING ingestion_run_id""",
        (dataset_id, release_id, PARSER_VERSION, config.git_revision(),
         f"mappings:{mapping_fingerprint}"))
    conn.commit()

    rows = dicts(conn, """
        SELECT fv.field_value_id, fv.raw_text, fd.field_name,
               sr.entity_id, sr.source_key, sr.source_label
          FROM source.field_value fv
          JOIN source.field_definition fd
            ON fd.field_definition_id = fv.field_definition_id
          JOIN source.record sr ON sr.record_id = fv.record_id
          JOIN source.artifact a ON a.artifact_id = sr.artifact_id
         WHERE a.release_id = %s""", (release_id,))

    try:
        with conn.cursor() as cur:
            # Rewrite this release wholesale so a rerun cannot duplicate.
            # Order matters: children before parents, since these are RESTRICT
            # rather than CASCADE where provenance must not vanish silently.
            cur.execute("""
                DELETE FROM obs.composition_member
                 WHERE composition_id IN (SELECT composition_id FROM obs.composition
                                           WHERE release_id = %s)""", (release_id,))
            cur.execute("DELETE FROM obs.composition WHERE release_id = %s", (release_id,))
            cur.execute("DELETE FROM obs.bilateral_observation WHERE release_id = %s",
                        (release_id,))
            cur.execute("DELETE FROM geo.entity_point WHERE release_id = %s", (release_id,))
            cur.execute("DELETE FROM content.document WHERE release_id = %s", (release_id,))
            for sub in ("integer", "numeric", "boolean", "categorical", "text"):
                cur.execute(f"""
                    DELETE FROM obs.{sub}_observation
                     WHERE observation_id IN (SELECT observation_id FROM obs.observation
                                               WHERE release_id = %s)""", (release_id,))
            cur.execute("DELETE FROM obs.observation WHERE release_id = %s", (release_id,))
            # Load-time quarantine rows are keyed to a field value, not to an
            # artifact, so the artifact-scoped cleanup in staging never reaches
            # them. Without this, every repeat `ingest load` -- the normal thing
            # to do after accepting a new field mapping -- added another full set
            # of rejections on top of the previous one. Same bug class already
            # fixed on the stage side; this is the port.
            cur.execute("""
                DELETE FROM meta.rejected_record
                 WHERE field_value_id IN (
                       SELECT fv.field_value_id
                         FROM source.field_value fv
                         JOIN source.record sr ON sr.record_id = fv.record_id
                         JOIN source.artifact a ON a.artifact_id = sr.artifact_id
                        WHERE a.release_id = %s)""", (release_id,))

            for r in rows:
                mapping = by_field.get(r["field_name"])
                if mapping is None:
                    counts["unmapped"] += 1
                    continue
                if mapping["target_kind"] == "ignore":
                    continue
                if r["entity_id"] is None:
                    # An unresolved entity is not a parse failure; the record is
                    # already in the curation queue. Loading it against no entity
                    # would fabricate a subject.
                    continue

                kind = mapping["target_kind"]
                if kind == "observation":
                    counts["observations"] += _load_observation(
                        cur, r, mapping, release_id, edition_year, run_id,
                        unit_ids, currency_ids, counts)
                elif kind == "composition":
                    counts["compositions"] += _load_composition(
                        cur, r, mapping, release_id, edition_year, run_id, counts)
                elif kind == "bilateral":
                    counts["bilateral"] += _load_bilateral(
                        cur, r, mapping, release_id, edition_year, run_id, dataset_id,
                        counts)
                elif kind == "coordinate":
                    counts["coordinates"] += _load_coordinate(
                        cur, r, mapping, release_id, run_id, counts)

            counts["narrative"] = _load_content(cur, release_id)

            cur.execute("""
                UPDATE meta.ingestion_run
                   SET status='succeeded', finished_at=now(),
                       rows_read=%s, rows_loaded=%s, rows_rejected=%s,
                       message=%s
                 WHERE ingestion_run_id=%s""",
                (len(rows),
                 counts["observations"] + counts["compositions"] + counts["bilateral"],
                 counts["rejected"],
                 f"{counts['unmapped']} field values had no accepted mapping",
                 run_id))
        conn.commit()
    except Exception as exc:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE meta.ingestion_run SET status='failed', finished_at=now(),
                       error_count=1, message=%s WHERE ingestion_run_id=%s""",
                (f"{type(exc).__name__}: {exc}"[:2000], run_id))
        conn.commit()
        raise
    return counts


def _reject(cur, run_id: int, field_value_id: int, code: str, reason: str,
            raw: str) -> None:
    cur.execute("""
        INSERT INTO meta.rejected_record
               (ingestion_run_id, field_value_id, source_pointer, error_code,
                reason, raw_input, parser_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (run_id, field_value_id, f"field_value:{field_value_id}", code, reason,
         raw[:2000], PARSER_VERSION))


def _load_observation(cur, r: dict, mapping: dict, release_id: int,
                      edition_year: int, run_id: int, unit_ids: dict,
                      currency_ids: dict, counts: dict) -> int:
    value_kind = mapping["value_kind"]
    raw = r["raw_text"]

    if value_kind == "text":
        # A text metric stores the published string as its value. No parsing is
        # attempted and none is appropriate: the phrasing is the claim.
        period, precision = _period(None, edition_year)
        obs_id = _insert_header(cur, r, mapping, release_id, run_id, period,
                                precision, "parsed_exact", None, False, "", None)
        cur.execute("INSERT INTO obs.text_observation (observation_id, value) VALUES (%s, %s)",
                    (obs_id, raw[:4000]))
        return 1

    parsed = parse_value(raw)

    if parsed.is_missing:
        # A stated absence is a real observation with no value: it records that
        # the publisher addressed the field and had nothing to report, which is
        # different from the field being absent entirely.
        period, precision = _period(parsed.reference_year, edition_year)
        _insert_header(cur, r, mapping, release_id, run_id, period, precision,
                       "unparsed", parsed.missing_reason, parsed.is_estimate,
                       parsed.note, None)
        return 1

    if not parsed.ok:
        _reject(cur, run_id, r["field_value_id"],
                parsed.failure_code or "value_unparseable",
                f"no value could be justified for metric {mapping['metric_code']}",
                raw)
        counts["rejected"] += 1
        return 0

    period, precision = _period(parsed.reference_year, edition_year)
    unit_id = mapping["default_unit_id"]
    if parsed.is_percent and "percent" in unit_ids:
        unit_id = unit_ids["percent"]

    # Currency and price basis were modelled, documented and never written --
    # every one of the loaded monetary observations had NULL in both columns
    # while the docs showed them populated. A monetary figure without a currency
    # is not a monetary figure, and the basis matters even more: PPP and nominal
    # GDP differ by a factor of several, so a value with neither is not
    # comparable to anything.
    currency_id = price_basis = None
    if parsed.currency and currency_ids.get(parsed.currency):
        currency_id = currency_ids[parsed.currency]
        code = mapping["metric_code"] or ""
        if code.endswith(".ppp") or ".per_capita_ppp" in code:
            price_basis = "ppp"
        elif "official_exchange" in code:
            price_basis = "official_exchange"
        else:
            price_basis = "nominal"

    obs_id = _insert_header(cur, r, mapping, release_id, run_id, period, precision,
                            parsed.status, None, parsed.is_estimate,
                            "; ".join(filter(None, [parsed.note, parsed.inequality or ""])),
                            unit_id, currency_id, price_basis)

    if value_kind == "integer":
        try:
            ivalue = int(parsed.value)
        except (ValueError, OverflowError):
            _reject(cur, run_id, r["field_value_id"], "value_not_integral",
                    f"{parsed.value} is not representable as an integer", raw)
            counts["rejected"] += 1
            cur.execute("DELETE FROM obs.observation WHERE observation_id=%s", (obs_id,))
            return 0
        cur.execute("INSERT INTO obs.integer_observation (observation_id, value) VALUES (%s,%s)",
                    (obs_id, ivalue))
    else:
        cur.execute("INSERT INTO obs.numeric_observation (observation_id, value) VALUES (%s,%s)",
                    (obs_id, parsed.value))
    return 1


def _insert_header(cur, r: dict, mapping: dict, release_id: int, run_id: int,
                   period: str, precision: str, parse_status: str,
                   missing_reason: str | None, is_estimate: bool,
                   qualifier: str, unit_id: int | None,
                   currency_id: int | None = None,
                   price_basis: str | None = None) -> int:
    cur.execute("""
        INSERT INTO obs.observation
               (entity_id, metric_id, value_kind, reference_period, period_precision,
                release_id, field_value_id, ingestion_run_id, parser_version,
                parse_status, missing_reason, is_estimate, qualifier_text, unit_id,
                currency_id, price_basis, field_mapping_id)
        VALUES (%s, %s, %s, %s::daterange, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING observation_id""",
        (r["entity_id"], mapping["metric_id"], mapping["value_kind"], period,
         precision, release_id, r["field_value_id"], run_id, PARSER_VERSION,
         parse_status, missing_reason, is_estimate, qualifier[:500], unit_id,
         currency_id, price_basis, mapping["field_mapping_id"]))
    return cur.fetchone()[0]


def _load_composition(cur, r: dict, mapping: dict, release_id: int,
                      edition_year: int, run_id: int, counts: dict) -> int:
    members, header = parse_shares(r["raw_text"])
    if not members:
        # A composition that yielded no members is either a stated absence
        # ("NA") or text the splitter could not structure. Both were previously
        # dropped without a trace -- no row, no rejection, no count -- which is
        # precisely the failure mode the whole subsystem forbids. The stated
        # absence is recorded as an absence; the rest is quarantined with its
        # raw text so a better splitter can be run against it.
        if header.missing_reason:
            period, precision = _period(header.reference_year, edition_year)
            cur.execute("""
                INSERT INTO obs.observation
                       (entity_id, metric_id, value_kind, reference_period,
                        period_precision, release_id, field_value_id,
                        ingestion_run_id, parser_version, parse_status,
                        missing_reason, qualifier_text, field_mapping_id)
                VALUES (%s,%s,%s,%s::daterange,%s,%s,%s,%s,%s,'unparsed',%s,%s,%s)""",
                # The metric's own declared kind, never a hard-coded one: an
                # observation's value_kind must match its metric or the
                # composite foreign key rejects it, which is exactly what
                # happened when this recorded every absence as 'text'.
                (r["entity_id"], mapping["metric_id"], mapping["value_kind"],
                 period, precision,
                 release_id, r["field_value_id"], run_id, PARSER_VERSION,
                 header.missing_reason, header.note[:500],
                 mapping["field_mapping_id"]))
            # This row is an observation, and the caller adds what this function
            # returns to the composition tally. Counting it there moved 14 rows
            # out of the observation total and into a count of compositions that
            # were never written, so the printed summary disagreed with the
            # tables by exactly the number of absences recorded.
            counts["observations"] += 1
            return 0
        _reject(cur, run_id, r["field_value_id"],
                header.failure_code or "composition_unparseable",
                f"no composition members could be read for metric "
                f"{mapping['metric_code']}", r["raw_text"])
        counts["rejected"] += 1
        return 0
    # A composition stores its period but not its precision: the members share
    # one header, and the header's qualifier already carries whether the year was
    # the source's or a fallback.
    period, _precision = _period(header.reference_year, edition_year)

    cur.execute("""
        INSERT INTO obs.composition
               (entity_id, metric_id, category_scheme_id, reference_period,
                release_id, field_value_id, ingestion_run_id, parser_version,
                parse_status, is_estimate, qualifier_text, field_mapping_id)
        VALUES (%s,%s,%s,%s::daterange,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING composition_id""",
        (r["entity_id"], mapping["metric_id"], mapping["category_scheme_id"],
         period, release_id, r["field_value_id"], run_id, PARSER_VERSION,
         "parsed_exact", header.is_estimate, header.note[:500],
         mapping["field_mapping_id"]))
    comp_id = cur.fetchone()[0]

    for m in members:
        # ref.percentage rejects anything outside 0-100, and it is right to.
        # Sources do occasionally yield an out-of-range share -- usually because
        # a note was parsed as a member ("percentages add to more than 100%"),
        # occasionally because a count was read as a percent. Letting the domain
        # abort the whole release would lose an entire edition over one bad
        # member, so the member is kept with its raw text and no share, and the
        # failure is quarantined. The value is never clamped into range: a share
        # silently rewritten from 120 to 100 is a fabricated fact. §21, §78.
        share = m.share_percent
        if share is not None and not (0 <= share <= 100):
            _reject(cur, run_id, r["field_value_id"], "share_out_of_range",
                    f"share {share} for {m.label!r} lies outside 0-100 and was not "
                    f"stored as a percentage; the member and its raw text are kept",
                    m.raw)
            share = None
        # Truncation must not leave trailing whitespace: ref.entity_code requires
        # a trimmed, non-empty value, and slicing a long label at 120 characters
        # can land on a space. Strip after slicing, not before.
        code = m.label.lower().strip()[:120].strip()
        label = m.label.strip()[:200].strip()
        if not code:
            _reject(cur, run_id, r["field_value_id"], "category_label_empty",
                    "composition member has no usable category label", m.raw)
            continue
        cur.execute("""
            INSERT INTO ref.category (category_scheme_id, code, label, is_residual)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (category_scheme_id, code) DO UPDATE SET label = EXCLUDED.label
            RETURNING category_id""",
            (mapping["category_scheme_id"], code, label,
             code in ("other", "unspecified", "none", "others")))
        category_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO obs.composition_member
                   (composition_id, category_id, share_percent, ordinal, raw_text,
                    qualifier_text)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (composition_id, category_id, ordinal) DO NOTHING""",
            (comp_id, category_id, share, m.ordinal, m.raw[:500],
             m.note[:300]))
    return 1


def _load_bilateral(cur, r: dict, mapping: dict, release_id: int,
                    edition_year: int, run_id: int, dataset_id: int,
                    counts: dict) -> int:
    partners = parse_partners(r["raw_text"])
    if not partners:
        # Same rule as compositions. "0 km" and "none" are a landlocked
        # country's positive statement that it has no land neighbours -- a fact,
        # not an absence of one -- and 111 such statements were being discarded
        # without any record that the field had been seen at all.
        probe = parse_value(r["raw_text"])
        if probe.missing_reason or probe.value == 0:
            period, precision = _period(None, edition_year)
            cur.execute("""
                INSERT INTO obs.observation
                       (entity_id, metric_id, value_kind, reference_period,
                        period_precision, release_id, field_value_id,
                        ingestion_run_id, parser_version, parse_status,
                        missing_reason, qualifier_text, field_mapping_id)
                VALUES (%s,%s,%s,%s::daterange,%s,%s,%s,%s,%s,'unparsed',%s,%s,%s)""",
                # The metric's own declared kind, never a hard-coded one: an
                # observation's value_kind must match its metric or the
                # composite foreign key rejects it, which is exactly what
                # happened when this recorded every absence as 'text'.
                (r["entity_id"], mapping["metric_id"], mapping["value_kind"],
                 period, precision,
                 release_id, r["field_value_id"], run_id, PARSER_VERSION,
                 probe.missing_reason or "not_applicable",
                 "no land neighbours reported", mapping["field_mapping_id"]))
            # An observation, not a bilateral fact — see the note in the
            # composition path. This one accounted for 2,433 of the 2,447-row
            # disagreement between the load summary and obs.observation.
            counts["observations"] += 1
            return 0
        _reject(cur, run_id, r["field_value_id"], "partner_list_unparseable",
                f"no partners could be read for metric {mapping['metric_code']}",
                r["raw_text"])
        counts["rejected"] += 1
        return 0
    period, _precision = _period(None, edition_year)
    loaded = 0

    for p in partners:
        # "total 1,880 km" leads the text-era boundary field; the total is
        # carried by its own mapping, so it must not also become a partner.
        if p.label.lower() in ("total", "border countries"):
            continue
        # The partner is resolved through the same decision table as any entity,
        # by name. Where it does not resolve, the row is kept with the label the
        # source used rather than being dropped or guessed. §80.
        cur.execute("""
            SELECT er.entity_id FROM core.entity_resolution er
             WHERE er.dataset_id = %s AND er.entity_id IS NOT NULL
               AND lower(er.source_label) = lower(%s)
             -- Deterministic tiebreak. Several source labels legitimately match
             -- more than one entity, and LIMIT 1 without ORDER BY let the
             -- planner decide which -- so a reload could silently reassign a
             -- border to a different neighbour.
             ORDER BY er.entity_id
             LIMIT 1""", (dataset_id, p.label))
        row = cur.fetchone()
        object_entity_id = row[0] if row else None
        if object_entity_id is None:
            cur.execute("""
                SELECT en.entity_id FROM core.entity_name en
                 WHERE lower(btrim(en.name)) = lower(btrim(%s))
                 ORDER BY en.is_preferred DESC, en.entity_id
                 LIMIT 1""", (p.label,))
            row = cur.fetchone()
            object_entity_id = row[0] if row else None

        cur.execute("""
            INSERT INTO obs.bilateral_observation
                   (subject_entity_id, object_entity_id, object_unresolved_label,
                    metric_id, reference_period, value_numeric, unit_id, release_id,
                    field_value_id, ingestion_run_id, parser_version, parse_status,
                    ordinal, raw_text, field_mapping_id)
            VALUES (%s,%s,%s,%s,%s::daterange,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (r["entity_id"], object_entity_id,
             "" if object_entity_id else p.label[:200],
             mapping["metric_id"], period, p.value, mapping["default_unit_id"],
             release_id, r["field_value_id"], run_id, PARSER_VERSION,
             "parsed_exact" if p.value is not None else "parsed_partial",
             p.ordinal, p.raw[:500], mapping["field_mapping_id"]))
        loaded += 1
    return loaded


def _load_coordinate(cur, r: dict, mapping: dict, release_id: int, run_id: int,
                     counts: dict) -> int:
    parsed = parse_coordinate(r["raw_text"])
    if not parsed.ok:
        _reject(cur, run_id, r["field_value_id"],
                parsed.failure_code or "coordinate_malformed",
                "coordinate pair could not be read unambiguously", r["raw_text"])
        counts["rejected"] += 1
        return 0
    cur.execute("""
        INSERT INTO geo.entity_point
               (entity_id, release_id, field_value_id, role, latitude, longitude,
                raw_text, parse_status, parser_version, ingestion_run_id,
                field_mapping_id)
        VALUES (%s,%s,%s,'centroid',%s,%s,%s,%s,%s,%s,%s)""",
        (r["entity_id"], release_id, r["field_value_id"], parsed.latitude,
         parsed.longitude, r["raw_text"][:200], parsed.status, PARSER_VERSION,
         run_id, mapping["field_mapping_id"]))
    return 1


# A field is narrative when it carries a passage rather than a value. The rule is
# deliberately mechanical and stated rather than inferred per field: it has no
# accepted mapping to a metric (or is mapped explicitly as narrative), and it is
# long enough that it is plainly prose rather than a stray label.
#
# 200 characters is a threshold, and thresholds are arbitrary. This one was
# chosen because the shortest genuine Factbook narrative fields -- a one-sentence
# "Environment - current issues" -- sit around 150-250 characters, while the
# longest non-prose values (a partner list, a long area subfield) stay well
# under it. It errs toward excluding a short passage rather than including a long
# value, because a value duplicated into the narrative layer would pollute
# full-text search with numbers.
#
# Nothing is lost either way: every field value, narrative or not, is already in
# source.field_value. content.* is a *view onto the prose* for search, diffing
# and profile reconstruction -- not a second copy of the corpus.
NARRATIVE_MIN_CHARS = 200


def _load_content(cur, release_id: int) -> int:
    """Populate content.document / section / field for one release, set-based.

    Written as three INSERT ... SELECT statements rather than a Python loop over
    rows: this is exactly the kind of transformation SQL does better, and the
    corpus has enough narrative fields that a row-at-a-time loop would dominate
    the load. §154.
    """
    # One document per record that resolved to an entity.
    cur.execute("""
        INSERT INTO content.document (release_id, entity_id, record_id, title,
                                      language_tag, provenance)
        SELECT %s, sr.entity_id, sr.record_id, sr.source_label, 'en',
               'source_published'
          FROM source.record sr
          JOIN source.artifact a ON a.artifact_id = sr.artifact_id
         WHERE a.release_id = %s AND sr.entity_id IS NOT NULL
        ON CONFLICT (release_id, record_id) DO NOTHING""",
        (release_id, release_id))

    # One section per distinct section name within a document, ordered by where
    # the section first appears so the publication's own ordering survives. §160.
    cur.execute("""
        INSERT INTO content.section (document_id, name, ordinal)
        SELECT d.document_id, fd.section_name,
               row_number() OVER (PARTITION BY d.document_id
                                  ORDER BY min(fv.field_value_id)) - 1
          FROM content.document d
          JOIN source.field_value fv ON fv.record_id = d.record_id
          JOIN source.field_definition fd
            ON fd.field_definition_id = fv.field_definition_id
         WHERE d.release_id = %s
         GROUP BY d.document_id, fd.section_name
        ON CONFLICT (document_id, name) DO NOTHING""", (release_id,))

    cur.execute("""
        INSERT INTO content.field (section_id, field_definition_id, name, ordinal,
                                   text_content, raw_markup, field_value_id)
        SELECT s.section_id, fd.field_definition_id, fd.field_name,
               row_number() OVER (PARTITION BY s.section_id
                                  ORDER BY fv.field_value_id) - 1,
               fv.raw_text, fv.raw_markup, fv.field_value_id
          FROM content.document d
          JOIN content.section s ON s.document_id = d.document_id
          JOIN source.field_value fv ON fv.record_id = d.record_id
          JOIN source.field_definition fd
            ON fd.field_definition_id = fv.field_definition_id
           AND fd.section_name = s.name
          LEFT JOIN source.field_mapping fm
                 ON fm.dataset_id = fd.dataset_id
                AND fm.field_pattern = fd.field_name
                AND fm.status = 'accepted'
                AND fm.target_kind <> 'narrative'
         WHERE d.release_id = %s
           AND fm.field_mapping_id IS NULL
           AND length(fv.raw_text) >= %s
        ON CONFLICT (section_id, name, ordinal) DO NOTHING""",
        (release_id, NARRATIVE_MIN_CHARS))
    return cur.rowcount


def cmd_load(args: argparse.Namespace) -> int:
    from .entity import resolve_dataset

    try:
        with connect() as conn:
            if not scalar(conn, "SELECT pg_try_advisory_lock(%s)", (_LOAD_LOCK,)):
                log("error", "another load run holds the lock on this database")
                return 1

            log("info", "resolving entities")
            res = resolve_dataset(conn, args.dataset)
            log("info", f"entities: {res['by_code']} by code, {res['by_name']} by name, "
                        f"{res['unresolved']} unresolved, {res['ambiguous']} ambiguous; "
                        f"{res['records_linked']} records linked")
            emit({"stage": "resolve", **res})

            if getattr(args, "bootstrap_entities", False):
                from .entity import bootstrap_entities, repair_bootstrapped_names
                boot = bootstrap_entities(conn, args.dataset)
                log("info", f"bootstrapped {boot['created']} unclassified entities, "
                            f"linked {boot['records_linked']} records")
                emit({"stage": "bootstrap", **boot})

                repaired = repair_bootstrapped_names(conn, args.dataset)
                if repaired:
                    log("info", f"repaired {repaired} bootstrapped entity names "
                                f"from improved source labels")
                emit({"stage": "repair_names", "repaired": repaired})

            log("info", "loading typed observations")
            totals = load_dataset(conn, args.dataset)
            log("info", f"loaded {totals['observations']} observations, "
                        f"{totals['compositions']} compositions, "
                        f"{totals['bilateral']} bilateral, "
                        f"{totals['coordinates']} coordinates, "
                        f"{totals['narrative']} narrative fields across "
                        f"{totals['releases']} releases")
            log("info", f"{totals['rejected']} values quarantined, "
                        f"{totals['unmapped']} field values had no accepted mapping")
            emit({"stage": "load", **totals})
            return 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1
