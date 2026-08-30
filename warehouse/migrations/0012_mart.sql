-- 0012_mart — the dimensional projection, generated from the canonical model.
--
-- This layer is never a source of truth. Every table here is rebuildable from
-- `core`, `ref`, `obs` and `source` by `atlas-data mart build`, and if the two
-- ever disagree the canonical model is right. Keeping them apart is what stops
-- analytics convenience from leaking into the evidence store. ADR-0001.
--
-- Every fact table below states its grain before it is created, because a fact
-- table without a stated grain is a table nobody can safely aggregate. §61.
--
-- Materialised views rather than physical tables with a load script: the
-- transformation IS the definition, refresh is one command, and there is no
-- second place where the logic could drift. They carry unique indexes so they
-- can be refreshed CONCURRENTLY once they are large enough for that to matter.

-- ── dimensions ───────────────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW mart.dim_entity AS
SELECT e.entity_id                                   AS entity_key,
       e.slug,
       t.code                                        AS entity_type,
       t.label                                       AS entity_type_label,
       t.is_sovereign,
       t.is_territorial,
       COALESCE(
         (SELECT n.name FROM core.entity_name n
           WHERE n.entity_id = e.entity_id AND n.is_preferred AND upper_inf(n.validity)
           ORDER BY n.entity_name_id LIMIT 1),
         (SELECT n.name FROM core.entity_name n
           WHERE n.entity_id = e.entity_id
           ORDER BY n.is_preferred DESC, n.entity_name_id LIMIT 1),
         e.slug)                                     AS entity_name,
       (SELECT i.value FROM core.entity_identifier i
          JOIN core.identifier_scheme s
            ON s.identifier_scheme_id = i.identifier_scheme_id
         WHERE i.entity_id = e.entity_id AND s.code = 'iso3166_1_alpha2'
           AND i.status = 'current'
         ORDER BY i.entity_identifier_id LIMIT 1)    AS iso_alpha2,
       lower(e.existence)                            AS existed_from,
       upper(e.existence)                            AS existed_until,
       upper_inf(e.existence)                        AS is_current
  FROM core.entity e
  JOIN core.entity_type t ON t.entity_type_id = e.entity_type_id;
COMMENT ON MATERIALIZED VIEW mart.dim_entity IS
  'Grain: one row represents one canonical entity in its current state. A type-1 dimension: it carries today''s preferred name rather than a history of names. That is a deliberate simplification for analytics — the full name history is in core.entity_name and in api.entity_name, and a type-2 name dimension would be added only if a real report needed to label a 1992 row with its 1992 name. §63.';

CREATE UNIQUE INDEX dim_entity_key_idx ON mart.dim_entity (entity_key);

CREATE MATERIALIZED VIEW mart.dim_metric AS
SELECT m.metric_id                AS metric_key,
       m.code                     AS metric_code,
       m.label                    AS metric_label,
       d.path::text               AS domain_path,
       subpath(d.path, 0, 1)::text AS domain_top,
       d.label                    AS domain_label,
       m.value_kind::text,
       u.code                     AS preferred_unit,
       u.symbol                   AS unit_symbol,
       qk.code                    AS quantity_kind,
       m.is_deprecated
  FROM ref.metric m
  JOIN ref.metric_domain d ON d.metric_domain_id = m.metric_domain_id
  LEFT JOIN ref.unit u ON u.unit_id = m.preferred_unit_id
  LEFT JOIN ref.quantity_kind qk ON qk.quantity_kind_id = u.quantity_kind_id;
COMMENT ON MATERIALIZED VIEW mart.dim_metric IS
  'Grain: one row represents one canonical metric. domain_top is the first ltree label, precomputed so a BI tool can group by domain without knowing ltree.';

CREATE UNIQUE INDEX dim_metric_key_idx ON mart.dim_metric (metric_key);

CREATE MATERIALIZED VIEW mart.dim_release AS
SELECT rel.release_id       AS release_key,
       rel.code             AS release_code,
       rel.label            AS release_label,
       rel.edition_year,
       rel.published_on,
       rel.published_precision,
       ds.code              AS dataset_code,
       ds.title             AS dataset_title,
       ds.status            AS dataset_status,
       pub.code             AS publisher_code,
       pub.name             AS publisher_name
  FROM source.release rel
  JOIN source.dataset ds ON ds.dataset_id = rel.dataset_id
  JOIN source.publisher pub ON pub.publisher_id = ds.publisher_id;
COMMENT ON MATERIALIZED VIEW mart.dim_release IS
  'Grain: one row represents one edition of one dataset. Doubles as the source dimension: publisher and dataset are denormalised onto it so a comparison across sources needs one join rather than three. This is the dimension that makes "CIA versus Eurostat" answerable without losing provenance. §65.';

CREATE UNIQUE INDEX dim_release_key_idx ON mart.dim_release (release_key);

-- The time dimension is generated over the span the data actually covers, plus
-- headroom, rather than over a hard-coded range. Annual grain is what this
-- corpus has; the columns below are month- and quarter-capable so a future
-- higher-frequency source does not force a redesign. §64.
CREATE MATERIALIZED VIEW mart.dim_period AS
WITH bounds AS (
    SELECT COALESCE(min(lower(reference_period)), DATE '1990-01-01') AS lo,
           COALESCE(max(upper(reference_period)), DATE '2030-01-01') AS hi
      FROM obs.observation)
SELECT d::date                                   AS period_key,
       EXTRACT(YEAR    FROM d)::int              AS year,
       EXTRACT(QUARTER FROM d)::int              AS quarter,
       EXTRACT(MONTH   FROM d)::int              AS month,
       to_char(d, 'YYYY-MM')                     AS year_month,
       (EXTRACT(MONTH FROM d) = 1)               AS is_year_start
  FROM bounds b,
       generate_series(date_trunc('year', b.lo)::date,
                       (date_trunc('year', b.hi) + interval '1 year')::date,
                       interval '1 month') AS g(d);
COMMENT ON MATERIALIZED VIEW mart.dim_period IS
  'Grain: one row represents one calendar month within the span the loaded data covers. Monthly rather than annual so that a future monthly source needs no schema change; annual facts join on the January row, which is why is_year_start exists. Distinct from publication time — a fact references both a reference period and a release, and conflating them is the error this whole model is built to avoid. §64.';

CREATE UNIQUE INDEX dim_period_key_idx ON mart.dim_period (period_key);

-- ── facts ────────────────────────────────────────────────────────────────────

-- One row represents one quantitative metric, for one geographic entity, for
-- one reference period, as reported by one source release.
CREATE MATERIALIZED VIEW mart.fact_observation AS
SELECT o.observation_id                              AS observation_key,
       o.entity_id                                   AS entity_key,
       o.metric_id                                   AS metric_key,
       o.release_id                                  AS release_key,
       lower(o.reference_period)                     AS period_key,
       EXTRACT(YEAR FROM lower(o.reference_period))::int AS reference_year,
       rel.edition_year,
       COALESCE(io.value::numeric, no.value)         AS value,
       u.code                                        AS unit_code,
       o.is_estimate,
       o.parse_status::text,
       o.period_precision,
       (o.missing_reason IS NOT NULL)                AS is_missing,
       o.missing_reason::text
  FROM obs.observation o
  JOIN source.release rel ON rel.release_id = o.release_id
  LEFT JOIN obs.integer_observation io ON io.observation_id = o.observation_id
  LEFT JOIN obs.numeric_observation no ON no.observation_id = o.observation_id
  LEFT JOIN ref.unit u ON u.unit_id = o.unit_id
 WHERE o.value_kind IN ('integer', 'numeric');
COMMENT ON MATERIALIZED VIEW mart.fact_observation IS
  'GRAIN: one row represents one quantitative metric, for one geographic entity, for one reference period, as reported by one source release. Text and categorical observations are excluded because they do not aggregate and would break SUM over this table. Rows where is_missing is true carry a NULL value and a missing_reason — they are kept so that "no data" is countable rather than invisible, and every aggregate must therefore filter on value IS NOT NULL or on is_missing = false.';

CREATE UNIQUE INDEX fact_observation_key_idx ON mart.fact_observation (observation_key);
CREATE INDEX fact_observation_entity_metric_idx
    ON mart.fact_observation (entity_key, metric_key, reference_year);
CREATE INDEX fact_observation_metric_year_idx
    ON mart.fact_observation (metric_key, reference_year)
    WHERE value IS NOT NULL;
COMMENT ON INDEX mart.fact_observation_metric_year_idx IS
  'Partial index over rows that carry a value, supporting cross-country ranking for one metric and year — the commonest analytic query and the one in the performance suite. Excluding missing rows keeps it small, and no ranking query wants them.';

-- One row represents one category's share of one composition, for one entity,
-- one reference period and one source release.
CREATE MATERIALIZED VIEW mart.fact_composition AS
SELECT cm.composition_member_id       AS composition_member_key,
       c.composition_id               AS composition_key,
       c.entity_id                    AS entity_key,
       c.metric_id                    AS metric_key,
       c.release_id                   AS release_key,
       lower(c.reference_period)      AS period_key,
       EXTRACT(YEAR FROM lower(c.reference_period))::int AS reference_year,
       cs.code                        AS scheme_code,
       cat.code                       AS category_code,
       cat.label                      AS category_label,
       cat.is_residual,
       cm.share_percent,
       cm.ordinal
  FROM obs.composition_member cm
  JOIN obs.composition c ON c.composition_id = cm.composition_id
  JOIN ref.category cat ON cat.category_id = cm.category_id
  JOIN ref.category_scheme cs ON cs.category_scheme_id = c.category_scheme_id;
COMMENT ON MATERIALIZED VIEW mart.fact_composition IS
  'GRAIN: one row represents one category''s share within one composition, for one entity, one reference period and one source release. Separate from fact_observation because the grain differs — a share is only meaningful alongside the other members of its composition_key, so aggregating across compositions without grouping by composition_key is a category error. Shares are not normalised to 100. §62.';

CREATE UNIQUE INDEX fact_composition_key_idx
    ON mart.fact_composition (composition_member_key);
CREATE INDEX fact_composition_entity_idx
    ON mart.fact_composition (entity_key, metric_key, reference_year);
CREATE INDEX fact_composition_category_idx ON mart.fact_composition (category_code);

-- One row represents one directed relationship between two entities, for one
-- metric, one reference period and one source release.
CREATE MATERIALIZED VIEW mart.fact_bilateral AS
SELECT b.bilateral_observation_id     AS bilateral_key,
       b.subject_entity_id            AS subject_entity_key,
       b.object_entity_id             AS object_entity_key,
       b.object_unresolved_label,
       b.metric_id                    AS metric_key,
       b.release_id                   AS release_key,
       lower(b.reference_period)      AS period_key,
       EXTRACT(YEAR FROM lower(b.reference_period))::int AS reference_year,
       b.value_numeric                AS value,
       u.code                         AS unit_code,
       (b.object_entity_id IS NOT NULL) AS object_resolved
  FROM obs.bilateral_observation b
  LEFT JOIN ref.unit u ON u.unit_id = b.unit_id;
COMMENT ON MATERIALIZED VIEW mart.fact_bilateral IS
  'GRAIN: one row represents one directed relationship between a subject entity and an object entity (or an unresolved partner name), for one metric, one reference period and one source release. Rows with object_resolved = false are included on purpose: the source published the relationship, and excluding it from analytics because this platform has not yet curated the partner would understate the data. Filter on object_resolved when a join to dim_entity is required. §35.';

CREATE UNIQUE INDEX fact_bilateral_key_idx ON mart.fact_bilateral (bilateral_key);
CREATE INDEX fact_bilateral_subject_idx
    ON mart.fact_bilateral (subject_entity_key, metric_key, reference_year);
