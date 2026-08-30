# Dimensional model

Seven materialised views over the canonical model. Rebuildable, disposable,
never a source of truth. ADR-0001.

```bash
just wh-mart      # refresh, then ANALYZE
```

## Grains

Stated before each table was created, because a fact table without a stated
grain cannot be safely aggregated.

**`mart.fact_observation`**

> One row represents one quantitative metric, for one geographic entity, for one
> reference period, as reported by one source release.

Text and categorical observations are excluded — they do not aggregate and would
break `SUM` over the table. Rows recording an absence *are* included, with a NULL
value and a `missing_reason`, so "no data" is countable; every aggregate must
therefore filter on `value IS NOT NULL` or `is_missing = false`.

**`mart.fact_composition`**

> One row represents one category's share within one composition, for one
> entity, one reference period and one source release.

A separate fact table because the grain differs. A share is only meaningful
alongside the other members of its `composition_key`; aggregating across
compositions without grouping by it is a category error.

**`mart.fact_bilateral`**

> One row represents one directed relationship between a subject entity and an
> object entity (or an unresolved partner name), for one metric, one reference
> period and one source release.

Rows with `object_resolved = false` are included deliberately: the source
published the relationship, and excluding it because this platform has not
curated the partner would understate the data.

Three fact tables rather than one, because three incompatible grains in one
table is how a warehouse starts producing confident nonsense.

## Dimensions

| Dimension | Grain | Note |
|---|---|---|
| `dim_entity` | one canonical entity | Type 1: today's preferred name |
| `dim_metric` | one metric | `domain_top` precomputed so BI need not know `ltree` |
| `dim_release` | one edition of one dataset | doubles as the source dimension |
| `dim_period` | one calendar month in the covered span | monthly, not annual |

**Why `dim_entity` is Type 1.** A Type 2 name dimension would let a 1992 row be
labelled "Czechoslovakia" rather than by its current name. The full history
exists in `core.entity_name` and `api.entity_name`; the SCD would be a
convenience for one report shape that nobody has asked for. Adding it later is
additive. Stated here so the simplification is a decision rather than an
oversight.

**Why `dim_period` is monthly.** The corpus is annual, and annual facts join on
the January row (`is_year_start`). Monthly grain means a future higher-frequency
source needs no redesign. The dimension is generated over the span the data
actually covers, not a hard-coded range.

**Why `dim_release` carries publisher and dataset.** So comparing sources is one
join rather than three. This is the dimension that makes "CIA versus Eurostat"
answerable without losing provenance.

## BI compatibility

Plain tables, plain types, no proprietary features. Usable from Metabase,
Superset, Tableau, Power BI, notebooks or `psql`. Every fact table has a unique
index on its key, so `REFRESH MATERIALIZED VIEW CONCURRENTLY` is available once
the views are populated.
