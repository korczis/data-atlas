# ADR-0004 — Extensions must beat PostgreSQL core at a real problem

**Status**: accepted

## Context

PostgreSQL's extension ecosystem makes it easy to accumulate dependencies that
look sophisticated and are never used. Every extension is a portability cost, a
backup consideration, an upgrade risk, and a thing that may not exist on managed
hosting.

## Decision

An extension is enabled when it solves a problem core PostgreSQL solves worse,
and the problem exists *now*. Four tiers, recorded in EXTENSIONS.md with the
full table.

**Required** — the schema does not work without them:
`postgis`, `pg_trgm`, `btree_gist`.

**Recommended** — meaningfully better, degradable:
`unaccent`, `ltree`.

**Optional, enabled with the feature that needs it**:
`vector` (search schema), `h3` (derived spatial index).

**Development only, never in a migration**:
`hypopg`, `pg_stat_statements`.

**Considered and declined**: `timescaledb` (ADR-0009), `postgis_raster`,
`postgis_topology`, `postgis_tiger_geocoder`, `address_standardizer`,
`pgrouting`, `pgcrypto`, `pg_cron`, `pgaudit`, Citus, Apache AGE.

`btree_gist` deserves note as genuinely required: without it, the exclusion
constraints that stop one ISO code denoting two entities simultaneously cannot
be written at all, because they mix equality on scalars with overlap on a range.

## Related enums

The same restraint applies to types. `ENUM` is used only for closed internal
states the pipeline itself defines — run status, parse status, value kind.
Anything describing the world is a reference table with a foreign key, because
the world adds members and `ALTER TYPE` in a migration is a bad way to discover
that. `core.entity_type` grew twice while the schema was being written.

## Consequences

- The database runs on stock PostgreSQL 18 plus PostGIS and two small
  extensions. `h3` and `hypopg` needed a source build and a Homebrew formula
  respectively; neither is required to run the platform.
- `postgis_tiger_geocoder` is explicitly rejected rather than merely unused: it
  is a US Census ecosystem, and this catalogue is European and global.
- `h3_postgis` is not enabled because it hard-requires `postgis_raster`, which
  is a real dependency cost for a bridge function this system does not need.

## What would reverse this

A concrete workload. Raster analysis would justify `postgis_raster`; a routable
transport network would justify `pgrouting`; DB-internal scheduling would
justify `pg_cron`. None exists today, and adding them speculatively is how a
database becomes unportable for no benefit.
