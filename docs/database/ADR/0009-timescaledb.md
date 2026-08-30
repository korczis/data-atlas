# ADR-0009 — TimescaleDB not used

**Status**: accepted

## Context

TimescaleDB 2.29 is installed on the development machine and available. The
temptation is to use it because the data has dates in it.

## Decision

Not used. No hypertables, no continuous aggregates, no compression or retention
policies.

## Reasoning

The workload is not a time series. `obs.observation` holds on the order of
10^5 rows across a few hundred entities and 36 annual editions — a few hundred
rows per entity, appended once per edition and then effectively static. Current
figures are in `warehouse/reports/STORAGE.md`. Hypertables solve high-ingest,
high-cardinality, time-ordered workloads with time-window queries over millions
to billions of rows. None of those adjectives applies here.

Plain PostgreSQL answers the representative queries in single-digit
milliseconds on this data; the measurements are in PERFORMANCE.md. Adding
Timescale would introduce a significant extension dependency, complicate backup
and restore, restrict managed-hosting options, and change how the tables can be
constrained — in exchange for optimising a query pattern that is not slow.

Retention and compression policies would be actively harmful: this is archival
data, and the whole point is that nothing ages out.

## Consequences

- The database runs on any stock PostgreSQL 18 with PostGIS.
- If a genuinely high-frequency source is ingested later, it can get its own
  hypertable *for its own facts*. Canonical dimensions and source metadata would
  stay ordinary tables regardless — "everything becomes a hypertable" is a
  documented anti-pattern in the brief and would be as wrong then as now.

## What would reverse this

A source with sub-daily observations, or a fact table past roughly 10^8 rows
where time-window queries dominate and measurement shows plain partitioning is
insufficient. Measure first: native PostgreSQL partitioning is the cheaper
intermediate step and should be tried before an extension.
