-- Representative queries for the performance suite.
-- Each is preceded by a \echo naming it; run.sh wraps them in
-- EXPLAIN (ANALYZE, BUFFERS) and writes RESULTS.md.
--
-- These are the queries the indexes exist for. If one of them regresses, the
-- index it depends on is named in docs/database/PERFORMANCE.md.

-- name: country profile, latest by reference period
SELECT metric, value_number, unit, reference_year, edition_year, is_estimate
  FROM api.observation_latest_by_period
 WHERE entity_slug = 'czechia';

-- name: one country's metric history
SELECT reference_year, value_number, edition_year, is_estimate
  FROM api.observation_history
 WHERE entity_slug = 'czechia' AND metric = 'demo.population.total'
 ORDER BY reference_year;

-- name: thirty entities over thirty years, one metric
SELECT e.slug, f.reference_year, f.value
  FROM mart.fact_observation f
  JOIN mart.dim_entity e ON e.entity_key = f.entity_key
  JOIN mart.dim_metric m ON m.metric_key = f.metric_key
 WHERE m.metric_code = 'demo.population.total'
   AND f.value IS NOT NULL
   AND f.reference_year BETWEEN 1992 AND 2025
 ORDER BY e.slug, f.reference_year;

-- name: latest known value per metric for one entity
SELECT metric, value_number, reference_year
  FROM api.observation_latest_by_edition
 WHERE entity_slug = 'czechia' AND value_number IS NOT NULL;

-- name: all source claims for one metric, entity and year
SELECT * FROM api.source_claims
 WHERE entity_slug = 'czechia' AND metric = 'demo.population.total';

-- name: conflicts across the whole corpus
SELECT count(*) FROM api.source_claims WHERE distinct_values > 1;

-- name: bilateral relation lookup
SELECT subject_slug, object_slug, object_unresolved_label, value_numeric, unit,
       edition_year
  FROM api.bilateral
 WHERE subject_slug = 'czechia' AND metric = 'geo.land_boundary.bilateral'
 ORDER BY edition_year, object_slug;

-- name: countries ranked by a metric in one year
SELECT e.entity_name, f.value
  FROM mart.fact_observation f
  JOIN mart.dim_entity e ON e.entity_key = f.entity_key
  JOIN mart.dim_metric m ON m.metric_key = f.metric_key
 WHERE m.metric_code = 'geo.area.total' AND f.reference_year = 2020
   AND f.value IS NOT NULL
 ORDER BY f.value DESC
 LIMIT 20;

-- name: composition members for one entity and year
SELECT category_label, share_percent, is_residual
  FROM api.composition
 WHERE entity_slug = 'czechia' AND scheme = 'language'
   AND edition_year = 2025
 ORDER BY ordinal;

-- name: fuzzy entity-name candidates (trigram)
SELECT e.slug, n.name, similarity(lower(n.name), lower('Cote dIvoire')) AS score
  FROM core.entity_name n JOIN core.entity e ON e.entity_id = n.entity_id
 WHERE similarity(lower(n.name), lower('Cote dIvoire')) > 0.3
 ORDER BY score DESC LIMIT 10;

-- name: bounding-box spatial query over published points
SELECT e.slug, p.latitude, p.longitude
  FROM geo.entity_point p JOIN core.entity e ON e.entity_id = p.entity_id
 WHERE p.geom && ST_MakeEnvelope(12, 48, 19, 51, 4326);

-- name: full-text search over narrative content
-- Queries the stored generated column, which is what content_field_search_idx
-- covers. Recomputing to_tsvector() in the predicate instead cannot use the
-- index and turns this into a full scan with a tsvector built per row -- 4.7
-- seconds against milliseconds. That mistake is the reason the column is
-- generated and stored rather than left as an expression index.
SELECT entity_slug, edition_year, section, left(text_content, 80) AS excerpt
  FROM api.narrative_search
 WHERE search_vector @@ plainto_tsquery('english', 'velvet revolution')
 LIMIT 10;

-- name: full-text search, ranked
SELECT entity_slug, edition_year,
       ts_rank(search_vector, plainto_tsquery('english', 'soviet influence')) AS rank
  FROM api.narrative_search
 WHERE search_vector @@ plainto_tsquery('english', 'soviet influence')
 ORDER BY rank DESC
 LIMIT 10;

-- name: provenance walk for one value
SELECT entity_slug, metric, source_raw_text, artifact, sha256, release_label,
       parser_version
  FROM api.provenance
 WHERE entity_slug = 'czechia' AND metric = 'demo.population.total'
 ORDER BY edition_year DESC LIMIT 5;

-- name: field evolution aggregation
SELECT fd.field_name, fd.first_seen_year, fd.last_seen_year, fd.edition_count,
       fd.record_count
  FROM source.field_definition fd
 ORDER BY fd.record_count DESC LIMIT 25;
