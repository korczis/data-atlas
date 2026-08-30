# Operations

## Setup

```bash
just wh-install                 # psycopg 3, the only runtime dependency
createdb atlas_data             # or point ATLAS_DATABASE_URL elsewhere
just wh-migrate
just wh-db-status               # migrations, extensions, table counts
```

`warehouse/.env.example` documents the environment. `ATLAS_DATABASE_URL` wins
over `DATABASE_URL`, so this subsystem can be pointed somewhere without
disturbing another tool in the same shell.

No container is required. There is no compose file because a local PostgreSQL
with PostGIS is what this was built against, and adding one would imply the
containerised path is tested when it is not.

## Running the pipeline

```bash
just wh-fetch --family json_factbook_cache   # network; ~29 MB
just wh-verify --all                         # full re-hash
just wh-stage --all                          # bytes → staging, offline
just wh-load --bootstrap-entities            # staging → typed observations
just wh-mart                                 # refresh materialised views + ANALYZE
just wh-quality                              # data-quality suite
just wh-reports                              # coverage, fields, storage, reconciliation
just wh-docs                                 # schema reference and ERDs
```

Only `wh-fetch` needs the network. Everything after it works offline, which is
the point of separating acquisition from processing.

Selections are explicit by design. `--all`, `--year`, `--from/--to`, `--family`
or `--artifact`; a bare command refuses rather than defaulting. A command that
silently means "everything" is how 3 GB gets downloaded by accident; one that
silently means "nothing" reports success having done no work.

## Concurrency

`stage` and `load` each take a PostgreSQL advisory lock. A second run is
refused, not queued.

This is not caution: two concurrent `stage --all` runs during development
deleted each other's rows and left editions silently empty with plausible
totals. The lock is session-level, so a crashed process releases it
automatically and cannot wedge the pipeline.

## Backup: what is reproducible and what is not

The distinction that matters. Most of this database can be rebuilt from bytes
and code; a small part cannot be rebuilt at all.

| Category | Contents | Backup |
|---|---|---|
| **Irreplaceable** | curated entity resolutions, field mappings, conflict decisions, `meta.curation_decision`, manual overrides | **must be backed up**; represents human judgement that no rerun reproduces |
| **Expensive to reacquire** | `raw/` — the publisher has stopped publishing and redirects its archive away | back up, or accept that the mirror may not outlive us |
| **Reproducible** | staging, observations, compositions, points | rebuildable from `raw/` + code |
| **Disposable** | `mart.*`, `search.*`, reports, generated docs | rebuild with one command |

```bash
# schema only — small, diffable, the thing to keep in version history
pg_dump --schema-only --no-owner atlas_data > schema.sql

# the irreplaceable part
pg_dump --data-only --no-owner \
        -t core.entity -t core.entity_name -t core.entity_identifier \
        -t core.entity_relation -t core.entity_resolution \
        -t source.field_mapping -t meta.curation_decision \
        atlas_data > curated.sql

# everything
pg_dump -Fc atlas_data > atlas_data.dump
```

Restoring the curated state onto a rebuilt database is the recovery path that
actually matters. Everything else is `just wh-stage && just wh-load`.

## Rebuilding from nothing

```bash
git clone … && cd gis-catalog
just wh-install && createdb atlas_data && just wh-migrate
just wh-fetch --all          # 2.8 GB
just wh-verify --all
just wh-stage --all
just wh-load --bootstrap-entities
just wh-mart && just wh-quality && just wh-reports
psql atlas_data < curated.sql   # if restoring curated decisions
```

No manual steps, no undocumented ordering.

## Resetting

```bash
just wh-reset      # confirms first; drops every managed schema
```

Destroys conflict decisions and any entity curation done by hand. The curated
**field mappings** survive: they live in migration 0010 and are re-applied by
`source.seed_field_mappings()`, which the loader calls on every run.

That was not true until it was tested. The seed ran as a migration, joined to
`source.dataset` — a row that staging writes *after* every migration has been
applied — and so inserted nothing on any database built from zero, silently. A
rebuild from this repository staged 1.8 million field values, mapped none of
them, produced zero observations, and exited 0. The developer's database only
had mappings because it happened to be built in an order no clean install
repeats. Migration 0020 moves the seed to a point where the dataset is
guaranteed to exist, and the loader now refuses to run against an empty mapping
set rather than quietly loading narrative content and calling it a load.

Entity resolution is the part still worth exporting before a reset.

## Monitoring

- `api.ingestion_status` — a row stuck in `running` with an old `started_at` is
  a process that died without recording an outcome. Visible rather than
  mistaken for success.
- `api.data_quality_summary` — findings by check and severity.
- `api.rejected_values` — quarantine, grouped by `error_code`, which is how to
  decide which parser bug to fix next.
- `warehouse/reports/STORAGE.md` — table, index and total sizes.
- `pg_stat_statements` is in the cluster's `shared_preload_libraries` but has
  **not** been created in this database, so its views are not queryable until
  someone runs `CREATE EXTENSION pg_stat_statements`. It is observability, not
  part of the model, which is why no migration does it.

## Upgrades

Migrations are immutable once applied; their checksums are recorded and the
runner refuses to proceed if an applied file has changed. To alter something,
add a new migration. Never renumber, and never insert a migration below one
already applied — it would be skipped silently, and the runner detects and
refuses that too.
