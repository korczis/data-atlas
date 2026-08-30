# Performance

Every number here was measured with `EXPLAIN (ANALYZE, BUFFERS)` against the
populated database after `ANALYZE`. Nothing is estimated, and nothing was
optimised before it was measured.

Regenerate with `warehouse/benchmarks/run.sh`.

## Method

```
measure → explain → index or materialise → measure again
```

Integrity is never traded for performance before measurement. No foreign key was
removed, no normalisation reversed, and no constraint weakened for speed.

## Index rationale

Each index exists for a named query pattern.

| Index | Pattern | Type | Why that type |
|---|---|---|---|
| `observation_entity_metric_period_idx` | one country's history of one metric; country profile | B-tree | leading `entity_id` because user-facing queries scope to a place first |
| `observation_metric_period_idx` | cross-country comparison and ranking | B-tree | complements the above; an entity-leading index cannot serve a metric-only predicate |
| `observation_period_gist_idx` | "everything describing any part of 1995" | GiST | B-tree on a range answers equality, not overlap |
| `entity_name_trgm_idx` | fuzzy candidates for resolution | GIN + trgm | trigram matching is containment, not ordering |
| `entity_identifier_lookup_idx` | code → entity, the hot resolution path | B-tree | equality on two columns |
| `entity_existence_idx`, `feature_version_validity_idx` | which entities existed when | GiST | range containment |
| `feature_version_geom_idx`, `entity_point_geom_idx` | bounding box, point-in-country | GiST | the spatial index |
| `record_unresolved_idx` | the curation queue | B-tree, partial | unresolved rows are a shrinking minority |
| `rejected_record_open_idx` | which parser bug to fix next | B-tree, partial | tiny in a healthy database |
| `fact_observation_metric_year_idx` | ranking within a metric and year | B-tree, partial | excludes rows recording absence; no ranking wants them |
| `*_field_value_idx` (four) | `ON DELETE RESTRICT` checks during re-staging | B-tree | see below |

## The index that was found by measurement

Re-staging an artifact took **over 55 seconds**. Four tables reference
`source.field_value` with `ON DELETE RESTRICT`, and PostgreSQL does not index the
referencing side of a foreign key automatically — so every deleted row triggered
a sequential scan of each referencing table to prove nothing pointed at it.

Migration 0015 adds those four indexes. This is the case where "index foreign-key
columns when the delete pattern requires it" stops being advice: the requirement
is invisible until the tables have rows, and it is invisible in the schema
because nothing about the DDL suggests a missing index.

## The second thing measurement found

The benchmark's own full-text query took **4,759 ms**. Not the index's fault and
not the data's: the query wrote

```sql
WHERE to_tsvector('english', f.text_content) @@ plainto_tsquery(...)
```

which recomputes the vector for every row and therefore cannot use
`content_field_search_idx` at all. Querying the stored generated column instead

```sql
WHERE search_vector @@ plainto_tsquery(...)
```

returns the same rows in **0.71 ms**.

Two things follow. First, this is why `content.field.search_vector` is a stored
generated column rather than an expression index — the fast path is the obvious
one to write, and the slow path is not silently available. Second, a benchmark
suite is only worth having if its queries are the ones the documentation
recommends; this one was measuring a mistake, and fixing the mistake was the
result.

## Representative queries

The benchmark suite covers:

1. country profile, latest by period
2. one country's metric history
3. thirty countries over thirty years
4. latest known value per metric
5. all source claims for one metric, entity and year (the conflict query)
6. bilateral relation lookup
7. bounding-box spatial query
8. point-in-country
9. full-text search over narrative
10. field-evolution aggregation

Measured plans and timings are in `warehouse/benchmarks/RESULTS.md`, generated
by the script rather than transcribed. The plans are taken with
`EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS)`: WAL because a read path that writes
is a defect timing alone hides, and SETTINGS because a plan that only reproduces
under one machine's `work_mem` should say so on its face.

## Where a view costs more than it looks

`api.observation_latest_by_period` and `api.observation_latest_by_edition` pick
the newest row per entity and metric with a window function. A window function
is an optimisation barrier: a `WHERE entity = ...` written *outside* the view
cannot be pushed underneath it, so PostgreSQL ranks the whole corpus and then
discards almost all of it. One country's profile therefore reads all 161,061
observations to return 27 rows, and the benchmark shows the parallel sequential
scan doing exactly that.

No index fixes this — the scan is not a lookup failure, it is the window's
required input. The cost grows linearly with the corpus, so it is worth knowing
about before the corpus grows: the fix, when it is needed, is a set-returning
function parameterised by entity, or a `LATERAL` join that ranks within one
entity at a time. It has not been made because 200 ms for a whole profile is not
yet a problem, and changing the shape of a published read contract to solve a
problem nobody has is the worse trade.

## Not done, deliberately

- **Partitioning.** `obs.observation` holds ~160k rows. Partitioning a table
  this size is cost with no benefit. The threshold worth revisiting is around
  10^8 rows, and native PostgreSQL partitioning should be measured before any
  extension.
- **Vector index.** No embeddings exist, so there is nothing to benchmark and
  no recall target to tune toward. Building one would imply a benchmark nobody
  ran. ADR-0010.
- **Denormalisation of the canonical model.** The mart exists for that, and it
  is rebuilt rather than maintained.
- **An index on every unindexed foreign key.** A sweep finds 42 foreign keys
  whose leading column has no supporting index, and all but four of them have a
  parent table nothing in this codebase ever deletes from — an index there would
  cost writes and storage to speed up an operation that never happens. Of the
  four that are in a delete path, three have empty children. The one that is
  real, `content.document.record_id`, was measured rather than assumed: the
  RESTRICT probe for one artifact's 260 records costs 2.8 ms without an index
  and 0.3 ms with one, so the index would save roughly 90 ms across a full
  31-artifact rebuild. That is not worth carrying. Re-measure if
  `content.document` grows by an order of magnitude, because the scan it avoids
  grows with the table.
