-- 0011_api_views — the stable read contract.
--
-- Consumers select from `api.*` and never from staging or canonical tables, so
-- the internal shape can change without breaking them. Every view documents
-- three things, because leaving any of them implicit is how a contract becomes
-- a guess: its **grain** (what one row is), its **NULL semantics**, and its
-- **ordering guarantees**.
--
-- On the word "latest". It is ambiguous by nature — latest by reference period,
-- by publication, or by ingestion are three different rows — so no view here is
-- called simply `latest`. Each says which clock it uses in its name. §158.

-- ── entities ─────────────────────────────────────────────────────────────────

CREATE VIEW api.entity AS
SELECT e.entity_id,
       e.slug,
       t.code                       AS entity_type,
       t.label                      AS entity_type_label,
       t.is_sovereign,
       t.is_territorial,
       lower(e.existence)           AS existed_from,
       upper(e.existence)           AS existed_until,
       upper_inf(e.existence)       AS exists_currently,
       (SELECT n.name FROM core.entity_name n
         WHERE n.entity_id = e.entity_id AND n.is_preferred
           AND upper_inf(n.validity)
         ORDER BY n.entity_name_id LIMIT 1) AS current_name
  FROM core.entity e
  JOIN core.entity_type t ON t.entity_type_id = e.entity_type_id;
COMMENT ON VIEW api.entity IS
  'Grain: one row per canonical entity, of any kind — sovereign states, dependencies, oceans, historical states and the World aggregate all appear. NULL semantics: existed_from/existed_until are NULL where the bound is unknown or open; exists_currently distinguishes "still exists" from "end date unknown". current_name is NULL for an entity with no currently-valid preferred name, which is normal for a dissolved state. No ordering guarantee.';

CREATE VIEW api.entity_name AS
SELECT e.entity_id, e.slug, k.code AS name_kind, n.name, n.language_tag,
       n.is_preferred, lower(n.validity) AS valid_from, upper(n.validity) AS valid_until
  FROM core.entity_name n
  JOIN core.entity e ON e.entity_id = n.entity_id
  JOIN core.name_kind k ON k.name_kind_id = n.name_kind_id;
COMMENT ON VIEW api.entity_name IS
  'Grain: one row per name an entity has held, per kind and language. An entity legitimately has many rows: "Czech Republic" and "Czechia" are both true, of different periods. Use is_preferred with a period filter to pick one. No ordering guarantee.';

CREATE VIEW api.entity_identifier AS
SELECT e.entity_id, e.slug, s.code AS scheme, i.value, i.status,
       lower(i.validity) AS valid_from, upper(i.validity) AS valid_until
  FROM core.entity_identifier i
  JOIN core.entity e ON e.entity_id = i.entity_id
  JOIN core.identifier_scheme s ON s.identifier_scheme_id = i.identifier_scheme_id;
COMMENT ON VIEW api.entity_identifier IS
  'Grain: one row per (entity, scheme, code, validity period). A code may appear against different entities in different periods — ISO reassigned CS from Czechoslovakia to Serbia and Montenegro — so a lookup by code MUST filter on a period or it will match more than one entity legitimately. NULL bounds mean open-ended.';

-- ── observations ─────────────────────────────────────────────────────────────

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
       COALESCE(io.value::numeric, no.value) AS value_number,
       u.code   AS unit, u.symbol AS unit_symbol,
       o.currency_id, o.price_basis,
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
  LEFT JOIN ref.unit u ON u.unit_id = o.unit_id
  LEFT JOIN source.field_value fv ON fv.field_value_id = o.field_value_id;
COMMENT ON VIEW api.observation IS
  'Grain: one row per source claim — one metric, one entity, one reference period, one release. Deliberately NOT deduplicated: two releases reporting different populations for the same country-year are two rows, and picking between them is derived.preferred_value''s job, not this view''s. NULL semantics: value_number is NULL exactly when the observation records an absence, in which case missing_reason says which kind; unit is NULL for text metrics. reference_year is derived from period_start — check period_precision before trusting it, because ''unknown'' means the platform fell back to the edition year rather than the publisher stating one. source_raw_text is the original string and is never NULL for a parsed value.';

CREATE VIEW api.observation_latest_by_period AS
SELECT DISTINCT ON (o.entity_id, o.metric_id) *
  FROM api.observation o
 ORDER BY o.entity_id, o.metric_id, o.period_start DESC NULLS LAST,
          o.edition_year DESC, o.observation_id DESC;
COMMENT ON VIEW api.observation_latest_by_period IS
  'Grain: one row per (entity, metric) — the claim describing the most recent reference period. "Latest" here means latest *about*, not latest *published*: a 2010 edition reporting 2009 data outranks a 2012 edition reporting 2005 data. For the other reading use api.observation_latest_by_edition. Ties are broken by edition year then observation id, so the result is deterministic. §158.';

CREATE VIEW api.observation_latest_by_edition AS
SELECT DISTINCT ON (o.entity_id, o.metric_id) *
  FROM api.observation o
 ORDER BY o.entity_id, o.metric_id, o.edition_year DESC,
          o.period_start DESC NULLS LAST, o.observation_id DESC;
COMMENT ON VIEW api.observation_latest_by_edition IS
  'Grain: one row per (entity, metric) — the claim from the most recently published edition, regardless of which period it describes. This is what "what does the newest Factbook say" means, and it is a different question from api.observation_latest_by_period. Deterministic ordering. §158.';

CREATE VIEW api.observation_history AS
SELECT entity_slug, metric, reference_year, value_number, unit, is_estimate,
       edition_year, release_label, parse_status, source_raw_text
  FROM api.observation
 WHERE value_number IS NOT NULL;
COMMENT ON VIEW api.observation_history IS
  'Grain: one row per numeric claim, filtered to those that carry a value. Intended for time-series work, so absences are excluded — query api.observation directly when the absences themselves matter. Ordering is not guaranteed; order explicitly.';

-- ── conflict and provenance ──────────────────────────────────────────────────

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
  'Grain: one row per (entity, metric, reference year), aggregating every claim about it. The view that answers "do our sources agree?" — distinct_values > 1 means they do not. With one dataset loaded this already fires, because successive Factbook editions revise their own earlier figures for the same year. That is expected and is data, not corruption. §55.';

CREATE VIEW api.provenance AS
SELECT o.observation_id,
       e.slug AS entity_slug, m.code AS metric,
       fv.raw_text        AS source_raw_text,
       fd.section_name, fd.field_name,
       sr.source_key, sr.source_label,
       a.code AS artifact, a.filename, a.sha256, a.checksum_origin,
       rel.label AS release_label, rel.edition_year,
       ds.code AS dataset, pub.name AS publisher,
       o.parser_version, ir.code_revision, o.recorded_at,
       (SELECT r2.url FROM source.retrieval r2
         WHERE r2.artifact_id = a.artifact_id
         ORDER BY r2.priority LIMIT 1) AS retrieval_url
  FROM obs.observation o
  JOIN core.entity e ON e.entity_id = o.entity_id
  JOIN ref.metric m  ON m.metric_id = o.metric_id
  JOIN source.field_value fv ON fv.field_value_id = o.field_value_id
  JOIN source.field_definition fd
    ON fd.field_definition_id = fv.field_definition_id
  JOIN source.record sr ON sr.record_id = fv.record_id
  JOIN source.artifact a ON a.artifact_id = sr.artifact_id
  JOIN source.release rel ON rel.release_id = a.release_id
  JOIN source.dataset ds ON ds.dataset_id = rel.dataset_id
  JOIN source.publisher pub ON pub.publisher_id = ds.publisher_id
  LEFT JOIN meta.ingestion_run ir ON ir.ingestion_run_id = o.ingestion_run_id;
COMMENT ON VIEW api.provenance IS
  'Grain: one row per observation that has a raw source field behind it. The answer to "where exactly did this number come from" — publisher, edition, file, its digest, the record and field inside it, the original text, and the parser version that typed it. Observations without a field_value (none at present; the schema permits explained derivations) do not appear here, which is why this is an inner join and not a left one.';

-- ── compositions and bilateral facts ─────────────────────────────────────────

CREATE VIEW api.composition AS
SELECT c.composition_id, e.slug AS entity_slug, m.code AS metric,
       cs.code AS scheme,
       EXTRACT(YEAR FROM lower(c.reference_period))::int AS reference_year,
       rel.edition_year, c.is_estimate,
       cat.code AS category, cat.label AS category_label, cat.is_residual,
       cm.share_percent, cm.ordinal, cm.raw_text
  FROM obs.composition c
  JOIN obs.composition_member cm ON cm.composition_id = c.composition_id
  JOIN core.entity e ON e.entity_id = c.entity_id
  JOIN ref.metric m  ON m.metric_id = c.metric_id
  JOIN ref.category_scheme cs ON cs.category_scheme_id = c.category_scheme_id
  JOIN ref.category cat ON cat.category_id = cm.category_id
  JOIN source.release rel ON rel.release_id = c.release_id;
COMMENT ON VIEW api.composition IS
  'Grain: one row per member of a breakdown — one language, one religion, one ethnic group. Shares within a composition_id are NOT guaranteed to sum to 100: rounding, unlisted residuals and overlapping categories all occur in the sources, and normalising them would falsify the publication. Use is_residual to separate "other"/"unspecified" from named members. Order by ordinal to recover the source''s own ordering.';

CREATE VIEW api.bilateral AS
SELECT b.bilateral_observation_id,
       s.slug AS subject_slug,
       o.slug AS object_slug,
       b.object_unresolved_label,
       m.code AS metric, b.value_numeric, u.code AS unit,
       EXTRACT(YEAR FROM lower(b.reference_period))::int AS reference_year,
       rel.edition_year, b.parse_status, b.raw_text
  FROM obs.bilateral_observation b
  JOIN core.entity s ON s.entity_id = b.subject_entity_id
  LEFT JOIN core.entity o ON o.entity_id = b.object_entity_id
  JOIN ref.metric m ON m.metric_id = b.metric_id
  LEFT JOIN ref.unit u ON u.unit_id = b.unit_id
  JOIN source.release rel ON rel.release_id = b.release_id;
COMMENT ON VIEW api.bilateral IS
  'Grain: one row per ordered pair and metric and period — a border length, a trade partner share. NULL semantics: object_slug is NULL when the partner could not be resolved to a canonical entity, and object_unresolved_label then holds the name the source used. Those rows are kept deliberately: the fact was published and dropping it would be a silent loss. Filter on object_slug IS NOT NULL for joinable pairs only.';

-- ── operations ───────────────────────────────────────────────────────────────

CREATE VIEW api.dataset_coverage AS
SELECT ds.code AS dataset, rel.edition_year, a.parser_family, a.role, a.status,
       count(DISTINCT sr.record_id)                        AS records,
       count(DISTINCT sr.entity_id)                        AS resolved_entities,
       count(fv.field_value_id)                            AS raw_field_values,
       count(DISTINCT fd.field_definition_id)              AS distinct_fields
  FROM source.artifact a
  JOIN source.release rel ON rel.release_id = a.release_id
  JOIN source.dataset ds  ON ds.dataset_id = rel.dataset_id
  LEFT JOIN source.record sr ON sr.artifact_id = a.artifact_id
  LEFT JOIN source.field_value fv ON fv.record_id = sr.record_id
  LEFT JOIN source.field_definition fd
         ON fd.field_definition_id = fv.field_definition_id
 GROUP BY ds.code, rel.edition_year, a.parser_family, a.role, a.status;
COMMENT ON VIEW api.dataset_coverage IS
  'Grain: one row per artifact. An artifact with records = 0 has been fetched and verified but not parsed — either its parser family is unimplemented or it is a deliberately superseded artifact. The distinction is in `role` and `status`, and a zero here is a fact about coverage, never a failure to report it. §197.';

CREATE VIEW api.ingestion_status AS
SELECT ir.ingestion_run_id, ds.code AS dataset, rel.edition_year, a.code AS artifact,
       ir.stage, ir.status, ir.started_at, ir.finished_at,
       ir.rows_read, ir.rows_staged, ir.rows_loaded, ir.rows_rejected,
       ir.parser_version, ir.code_revision, ir.message
  FROM meta.ingestion_run ir
  JOIN source.dataset ds ON ds.dataset_id = ir.dataset_id
  LEFT JOIN source.release rel ON rel.release_id = ir.release_id
  LEFT JOIN source.artifact a ON a.artifact_id = ir.artifact_id;
COMMENT ON VIEW api.ingestion_status IS
  'Grain: one row per pipeline run. A row with status ''running'' and an old started_at is a process that died without recording an outcome — visible here rather than mistaken for success.';

CREATE VIEW api.unresolved_entities AS
SELECT er.dataset_id, ds.code AS dataset, er.source_key, er.source_label,
       er.method, er.status, er.evidence,
       er.first_seen_year, er.last_seen_year,
       (SELECT count(*) FROM source.record sr
         WHERE sr.source_key = er.source_key) AS record_count
  FROM core.entity_resolution er
  JOIN source.dataset ds ON ds.dataset_id = er.dataset_id
 WHERE er.entity_id IS NULL;
COMMENT ON VIEW api.unresolved_entities IS
  'Grain: one row per source key with no canonical entity — the curation queue. Expected to be non-empty and to shrink as entities are curated. A source key here is not lost: its records and raw field values are fully staged, and resolving it later makes its observations loadable without re-reading any bytes. §80, §105.';

CREATE VIEW api.data_quality_summary AS
SELECT qc.code AS check_code, qc.label, qc.category, qc.is_release_gate,
       qi.severity, count(*) AS issue_count,
       max(qr.started_at) AS last_run_at
  FROM meta.quality_issue qi
  JOIN meta.quality_check qc ON qc.quality_check_id = qi.quality_check_id
  JOIN meta.quality_run qr ON qr.quality_run_id = qi.quality_run_id
 GROUP BY qc.code, qc.label, qc.category, qc.is_release_gate, qi.severity;
COMMENT ON VIEW api.data_quality_summary IS
  'Grain: one row per (check, severity). An empty result means either that nothing was found or that no quality run has happened — those are different states, and api.ingestion_status distinguishes them. A check with no row here after a run genuinely found nothing.';

CREATE VIEW api.rejected_values AS
SELECT rr.rejected_record_id, ds.code AS dataset, rel.edition_year,
       rr.error_code, rr.reason, rr.raw_input, rr.source_pointer,
       rr.parser_version, rr.first_seen_at, rr.resolved
  FROM meta.rejected_record rr
  JOIN meta.ingestion_run ir ON ir.ingestion_run_id = rr.ingestion_run_id
  JOIN source.dataset ds ON ds.dataset_id = ir.dataset_id
  LEFT JOIN source.release rel ON rel.release_id = ir.release_id;
COMMENT ON VIEW api.rejected_values IS
  'Grain: one row per value a parser refused, with the raw text that defeated it. This view existing and being non-empty is the system working as designed: the alternative to a quarantine row is a silently invented number. Group by error_code to decide which parser bug is worth fixing next. §21.';
