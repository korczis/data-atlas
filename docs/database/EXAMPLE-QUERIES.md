# Example queries

Every query here runs against the canonical model or the mart. None scrapes raw
JSONB, because there is none to scrape — the canonical layer is typed.

Run them with `just wh-psql`.

## Population history for one country

```sql
SELECT reference_year, value_number AS population, edition_year, is_estimate
  FROM api.observation_history
 WHERE entity_slug = 'czechia' AND metric = 'demo.population.total'
 ORDER BY reference_year;
```

Note that `reference_year` and `edition_year` differ: a 2025 edition reporting a
2024 estimate contributes a 2024 row.

## Where a number came from

```sql
SELECT source_raw_text, field_name, artifact, sha256, release_label,
       parser_version, retrieval_url
  FROM api.provenance
 WHERE entity_slug = 'czechia' AND metric = 'demo.population.total'
 ORDER BY edition_year DESC LIMIT 3;
```

The whole point of the platform in one query: publisher, edition, file, digest,
the field it came from, its exact original text, and the parser that typed it.

## Do our sources disagree?

```sql
SELECT entity_slug, metric, reference_year, claim_count, distinct_values,
       min_value, max_value, editions
  FROM api.source_claims
 WHERE distinct_values > 1
 ORDER BY (max_value / NULLIF(min_value, 0)) DESC NULLS LAST
 LIMIT 20;
```

With one dataset loaded this already returns rows, because successive editions
revise their own earlier figures for the same year. Ordering by spread ratio puts
likely unit-parsing errors at the top and genuine revisions below.

## Countries ranked by area in one year

```sql
SELECT e.entity_name, f.value AS area_km2
  FROM mart.fact_observation f
  JOIN mart.dim_entity e ON e.entity_key = f.entity_key
  JOIN mart.dim_metric m ON m.metric_key = f.metric_key
 WHERE m.metric_code = 'geo.area.total'
   AND f.reference_year = 2020 AND f.value IS NOT NULL
 ORDER BY f.value DESC LIMIT 15;
```

## Year-over-year change

```sql
SELECT reference_year, value_number,
       value_number - lag(value_number) OVER (ORDER BY reference_year) AS change,
       round(100 * (value_number / NULLIF(lag(value_number)
              OVER (ORDER BY reference_year), 0) - 1), 2) AS pct_change
  FROM api.observation_history
 WHERE entity_slug = 'czechia' AND metric = 'demo.population.total'
 ORDER BY reference_year;
```

## Borders as data, not as a string

```sql
SELECT edition_year, object_slug, object_unresolved_label, value_numeric, unit
  FROM api.bilateral
 WHERE subject_slug = 'czechia' AND metric = 'geo.land_boundary.bilateral'
 ORDER BY edition_year, object_slug;
```

`"Austria 402 km; Germany 704 km"` became one row per neighbour, joinable and
comparable across editions. Watch the Austria figure change between the 1990s
and the 2020s — that is a real revision, visible because nothing was overwritten.

## Language composition

```sql
SELECT category_label, share_percent, is_residual
  FROM api.composition
 WHERE entity_slug = 'czechia' AND scheme = 'language' AND edition_year = 2025
 ORDER BY ordinal;
```

The shares will not sum to exactly 100, and that is the source being accurate.

## How a field's name changed over 36 years

```sql
SELECT field_name, first_seen_year, last_seen_year, edition_count, record_count
  FROM source.field_definition
 WHERE field_name ILIKE 'Area%' OR field_name ILIKE 'Population%'
 ORDER BY record_count DESC;
```

Shows `Area / total area` giving way to `Area / total`, and bare `Population`
gaining a `total` subfield — the schema history of a publication.

## Historical entities and their successors

```sql
SELECT s.slug AS subject, t.label AS relation, o.slug AS object,
       lower(r.validity) AS from_date
  FROM core.entity_relation r
  JOIN core.entity s ON s.entity_id = r.subject_entity_id
  JOIN core.entity o ON o.entity_id = r.object_entity_id
  JOIN core.entity_relation_type t
    ON t.entity_relation_type_id = r.entity_relation_type_id
 ORDER BY from_date;
```

## The same code, two countries, different decades

```sql
SELECT slug, scheme, value, valid_from, valid_until, status
  FROM api.entity_identifier
 WHERE scheme = 'iso3166_1_alpha2' AND value IN ('CS', 'CZ')
 ORDER BY value, valid_from;
```

The query that explains why an ISO code cannot be a primary key.

## What a country was called, when

```sql
SELECT slug, name, name_kind, valid_from, valid_until, is_preferred
  FROM api.entity_name
 WHERE slug IN ('czechia', 'czechoslovakia')
 ORDER BY slug, valid_from NULLS FIRST;
```

## Coverage: what is loaded and what is not

```sql
SELECT edition_year, parser_family, role, status, records, raw_field_values
  FROM api.dataset_coverage
 ORDER BY edition_year;
```

Rows with `records = 0` are artifacts fetched and verified but not parsed. That
is a fact about coverage, and the view reports it rather than hiding it.

## What the parsers refused

```sql
SELECT error_code, count(*), min(raw_input) AS example
  FROM api.rejected_values
 GROUP BY error_code ORDER BY 2 DESC;
```
