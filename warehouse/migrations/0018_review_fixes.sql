-- 0018_review_fixes — defects found by an adversarial review of the schema.
--
-- Each of these was demonstrated against the populated database, not inferred.

-- ── 1. the subtype invariant could be broken after commit ───────────────────
--
-- The deferred trigger installed in 0005 fires only on obs.observation. Deleting
-- a value row in a later transaction therefore left a header with no value and
-- no error, and inserting a value row against an already-committed `unparsed`
-- header produced a row that was simultaneously "carries no typed value" and
-- carrying one. Both were reproduced live.
--
-- The composite foreign keys stop a value row attaching to a header of the
-- WRONG KIND. Nothing stopped a header from ceasing to have one at all. The
-- assertion is therefore moved into a shared function and attached to the
-- subtype tables as well, so any DML that could break the invariant re-checks
-- it.

CREATE FUNCTION obs.observation_value_count(p_observation_id bigint)
RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT count(*)::integer FROM (
        SELECT 1 FROM obs.integer_observation     WHERE observation_id = p_observation_id
        UNION ALL
        SELECT 1 FROM obs.numeric_observation     WHERE observation_id = p_observation_id
        UNION ALL
        SELECT 1 FROM obs.boolean_observation     WHERE observation_id = p_observation_id
        UNION ALL
        SELECT 1 FROM obs.categorical_observation WHERE observation_id = p_observation_id
        UNION ALL
        SELECT 1 FROM obs.text_observation        WHERE observation_id = p_observation_id
    ) s;
$$;
COMMENT ON FUNCTION obs.observation_value_count(bigint) IS
  'How many typed value rows an observation has, across every subtype. Extracted so the header trigger and the subtype triggers apply exactly the same rule rather than two rules that can drift apart.';

CREATE FUNCTION obs.assert_observation_value(p_observation_id bigint) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    v_status obs.parse_status;
    v_found  integer;
BEGIN
    SELECT parse_status INTO v_status
      FROM obs.observation WHERE observation_id = p_observation_id;
    IF NOT FOUND THEN
        -- The header is gone; a cascade removed the value with it.
        RETURN;
    END IF;

    v_found := obs.observation_value_count(p_observation_id);

    IF v_status = 'unparsed' THEN
        IF v_found > 0 THEN
            RAISE EXCEPTION
                'observation % is unparsed but carries % typed value row(s)',
                p_observation_id, v_found
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN;
    END IF;

    IF v_found <> 1 THEN
        RAISE EXCEPTION
            'observation % has % typed value rows, expected exactly 1',
            p_observation_id, v_found
            USING ERRCODE = 'integrity_constraint_violation',
                  HINT = 'Insert or keep exactly one obs.<kind>_observation row.';
    END IF;
END;
$$;
COMMENT ON FUNCTION obs.assert_observation_value(bigint) IS
  'The disjoint-subtype invariant, in one place: a parsed observation has exactly one typed value row, an unparsed one has none. Called from the header trigger and from every subtype trigger.';

CREATE OR REPLACE FUNCTION obs.assert_observation_has_value() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM obs.assert_observation_value(NEW.observation_id);
    RETURN NULL;
END;
$$;
COMMENT ON FUNCTION obs.assert_observation_has_value() IS
  'Header-side guard. Now delegates to obs.assert_observation_value so the header and the subtypes cannot enforce different rules.';

CREATE FUNCTION obs.assert_subtype_value() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM obs.assert_observation_value(
        COALESCE(NEW.observation_id, OLD.observation_id));
    RETURN NULL;
END;
$$;
COMMENT ON FUNCTION obs.assert_subtype_value() IS
  'Subtype-side guard. Without it, deleting a value row after commit left an orphaned header that no constraint ever re-examined — reproduced live before this migration.';

CREATE CONSTRAINT TRIGGER integer_observation_value_consistent
    AFTER INSERT OR UPDATE OR DELETE ON obs.integer_observation
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION obs.assert_subtype_value();
CREATE CONSTRAINT TRIGGER numeric_observation_value_consistent
    AFTER INSERT OR UPDATE OR DELETE ON obs.numeric_observation
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION obs.assert_subtype_value();
CREATE CONSTRAINT TRIGGER boolean_observation_value_consistent
    AFTER INSERT OR UPDATE OR DELETE ON obs.boolean_observation
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION obs.assert_subtype_value();
CREATE CONSTRAINT TRIGGER categorical_observation_value_consistent
    AFTER INSERT OR UPDATE OR DELETE ON obs.categorical_observation
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION obs.assert_subtype_value();
CREATE CONSTRAINT TRIGGER text_observation_value_consistent
    AFTER INSERT OR UPDATE OR DELETE ON obs.text_observation
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION obs.assert_subtype_value();

-- ── 2. provenance was enforced on observations only ────────────────────────
-- The other three fact tables carry field_value_id and were 100% populated in
-- practice, but by convention rather than by constraint — and the documentation
-- claimed enforcement. Convention is what breaks when a new loader path is
-- added.

ALTER TABLE obs.composition
    ADD CONSTRAINT composition_has_provenance
    CHECK (field_value_id IS NOT NULL OR btrim(notes) <> '');
COMMENT ON CONSTRAINT composition_has_provenance ON obs.composition IS
  'A composition must cite the raw field it was read from, or explain itself. The same rule obs.observation has carried since 0005; its absence here was an omission, not a decision.';

ALTER TABLE obs.bilateral_observation
    ADD CONSTRAINT bilateral_has_provenance
    CHECK (field_value_id IS NOT NULL OR btrim(raw_text) <> '');
COMMENT ON CONSTRAINT bilateral_has_provenance ON obs.bilateral_observation IS
  'As composition_has_provenance. raw_text is accepted in place of a field reference because a bilateral row always retains the fragment it was split from.';

ALTER TABLE geo.entity_point
    ADD CONSTRAINT entity_point_has_provenance
    CHECK (field_value_id IS NOT NULL OR btrim(raw_text) <> '');
COMMENT ON CONSTRAINT entity_point_has_provenance ON geo.entity_point IS
  'As above. A coordinate with neither a source field nor its original text cannot be re-parsed or audited.';

-- ── 3. unindexed RESTRICT foreign keys on the largest table ────────────────
-- Migrations 0015 and 0017 fixed this class for source.field_value and
-- meta.rejected_record. These three were missed: deleting a single row from the
-- small ref.unit, ref.currency or meta.ingestion_run tables forces a sequential
-- scan of obs.observation to prove the RESTRICT holds.

CREATE INDEX observation_unit_idx ON obs.observation (unit_id)
    WHERE unit_id IS NOT NULL;
CREATE INDEX observation_currency_idx ON obs.observation (currency_id)
    WHERE currency_id IS NOT NULL;
CREATE INDEX observation_run_idx ON obs.observation (ingestion_run_id);
COMMENT ON INDEX obs.observation_run_idx IS
  'Supports the ON DELETE RESTRICT check against meta.ingestion_run, and the "everything this run produced" query used when auditing a parser change.';

CREATE INDEX composition_metric_idx ON obs.composition (metric_id);
CREATE INDEX composition_run_idx ON obs.composition (ingestion_run_id);
CREATE INDEX bilateral_metric_idx ON obs.bilateral_observation (metric_id);
CREATE INDEX bilateral_run_idx ON obs.bilateral_observation (ingestion_run_id);
CREATE INDEX quality_issue_observation_idx ON meta.quality_issue (observation_id)
    WHERE observation_id IS NOT NULL;
COMMENT ON INDEX meta.quality_issue_observation_idx IS
  'Supports the ON DELETE CASCADE from obs.observation. Partial: most findings are not tied to a specific observation.';

-- ── 4. indexes made redundant by a wider unique constraint ─────────────────
-- A B-tree serves an equality lookup on the leading column of a wider index, so
-- each of these duplicated the prefix of a UNIQUE constraint on the same table:
-- write amplification and storage for no read benefit.

DROP INDEX content.content_document_release_idx;
DROP INDEX content.content_field_section_idx;
DROP INDEX core.entity_relation_subject_idx;
DROP INDEX obs.composition_member_composition_idx;
DROP INDEX source.field_value_record_idx;
DROP INDEX source.record_artifact_idx;
DROP INDEX staging_cwf.staging_entry_artifact_idx;
DROP INDEX staging_cwf.staging_entry_field_entry_idx;

-- ── 5. the read contract dropped two value kinds ───────────────────────────
-- api.observation LEFT JOINed integer, numeric and text but not boolean or
-- categorical, so an observation of either kind would show every value column
-- NULL — indistinguishable from a missing value. Dormant (no such metric is
-- seeded yet) and guaranteed to bite the first one that is.
--
-- The dependent views select * from this one, so the chain is rebuilt.

DROP VIEW api.observation_history;
DROP VIEW api.source_claims;
DROP VIEW api.observation_latest_by_edition;
DROP VIEW api.observation_latest_by_period;
DROP VIEW api.observation;

CREATE VIEW api.observation AS
SELECT o.observation_id,
       e.entity_id, e.slug AS entity_slug,
       m.metric_id,
       m.code  AS metric, m.label AS metric_label,
       d.path  AS metric_domain,
       o.value_kind,
       io.value::numeric AS value_integer,
       no.value          AS value_numeric,
       tx.value          AS value_text,
       bo.value          AS value_boolean,
       cat.code          AS value_category,
       COALESCE(io.value::numeric, no.value) AS value_number,
       u.code   AS unit, u.symbol AS unit_symbol,
       cur.code AS currency, o.price_basis,
       lower(o.reference_period)                    AS period_start,
       upper(o.reference_period)                    AS period_end,
       EXTRACT(YEAR FROM lower(o.reference_period))::int AS reference_year,
       o.period_precision,
       rel.edition_year, rel.label AS release_label,
       ds.code AS dataset, pub.name AS publisher,
       o.is_estimate, o.parse_status, o.missing_reason, o.qualifier_text,
       o.parser_version, o.recorded_at,
       fv.raw_text AS source_raw_text
  FROM obs.observation o
  JOIN core.entity e   ON e.entity_id = o.entity_id
  JOIN ref.metric m    ON m.metric_id = o.metric_id
  JOIN ref.metric_domain d ON d.metric_domain_id = m.metric_domain_id
  JOIN source.release rel ON rel.release_id = o.release_id
  JOIN source.dataset ds  ON ds.dataset_id = rel.dataset_id
  JOIN source.publisher pub ON pub.publisher_id = ds.publisher_id
  LEFT JOIN obs.integer_observation io ON io.observation_id = o.observation_id
  LEFT JOIN obs.numeric_observation no ON no.observation_id = o.observation_id
  LEFT JOIN obs.text_observation   tx ON tx.observation_id = o.observation_id
  LEFT JOIN obs.boolean_observation bo ON bo.observation_id = o.observation_id
  LEFT JOIN obs.categorical_observation co ON co.observation_id = o.observation_id
  LEFT JOIN ref.category cat ON cat.category_id = co.category_id
  LEFT JOIN ref.unit u ON u.unit_id = o.unit_id
  LEFT JOIN ref.currency cur ON cur.currency_id = o.currency_id
  LEFT JOIN source.field_value fv ON fv.field_value_id = o.field_value_id;
COMMENT ON VIEW api.observation IS
  'Grain: one row per source claim — one metric, one entity, one reference period, one release. Deliberately NOT deduplicated: two releases reporting different populations for the same country-year are two rows, and choosing between them is derived.preferred_value''s job. NULL semantics: exactly one of value_integer / value_numeric / value_text / value_boolean / value_category is populated for a parsed observation, selected by value_kind; ALL of them are NULL when the observation records an absence, in which case missing_reason says which kind. value_number is the numeric-comparable projection and is NULL for text, boolean and categorical kinds as well as for absences — check value_kind before treating it as "no data". reference_year is derived from period_start; check period_precision, because ''unknown'' means the platform fell back to the edition year rather than the publisher stating one. currency and price_basis are populated only for monetary metrics.';

CREATE VIEW api.observation_latest_by_period AS
SELECT DISTINCT ON (o.entity_id, o.metric_id) *
  FROM api.observation o
 ORDER BY o.entity_id, o.metric_id, o.period_start DESC NULLS LAST,
          o.edition_year DESC, o.observation_id DESC;
COMMENT ON VIEW api.observation_latest_by_period IS
  'Grain: one row per (entity, metric) — the claim describing the most recent reference period. "Latest" here means latest *about*, not latest *published*: a 2010 edition reporting 2009 data outranks a 2012 edition reporting 2005 data. For the other reading use api.observation_latest_by_edition. Ties break on edition year then observation id, so the result is deterministic.';

CREATE VIEW api.observation_latest_by_edition AS
SELECT DISTINCT ON (o.entity_id, o.metric_id) *
  FROM api.observation o
 ORDER BY o.entity_id, o.metric_id, o.edition_year DESC,
          o.period_start DESC NULLS LAST, o.observation_id DESC;
COMMENT ON VIEW api.observation_latest_by_edition IS
  'Grain: one row per (entity, metric) — the claim from the most recently published edition, whatever period it describes. A different question from api.observation_latest_by_period. Deterministic ordering.';

CREATE VIEW api.observation_history AS
SELECT entity_slug, metric, reference_year, value_number, unit, currency,
       price_basis, is_estimate, edition_year, release_label, parse_status,
       source_raw_text
  FROM api.observation
 WHERE value_number IS NOT NULL;
COMMENT ON VIEW api.observation_history IS
  'Grain: one row per numeric claim that carries a value. Absences are excluded because this view exists for time series — query api.observation directly when the absences themselves matter. Ordering is not guaranteed; order explicitly.';

CREATE VIEW api.source_claims AS
SELECT entity_slug, metric, reference_year,
       count(*)                       AS claim_count,
       count(DISTINCT value_number)   AS distinct_values,
       min(value_number)              AS min_value,
       max(value_number)              AS max_value,
       array_agg(DISTINCT dataset)    AS datasets,
       array_agg(DISTINCT edition_year ORDER BY edition_year) AS editions
  FROM api.observation
 WHERE value_number IS NOT NULL
 GROUP BY entity_slug, metric, reference_year;
COMMENT ON VIEW api.source_claims IS
  'Grain: one row per (entity, metric, reference year), aggregating every claim about it. The view that answers "do our sources agree?" — distinct_values > 1 means they do not. Non-empty with a single dataset loaded, because successive editions revise their own earlier figures.';
