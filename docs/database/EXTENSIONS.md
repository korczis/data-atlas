# PostgreSQL extensions

The rule: an extension earns its place by solving a problem core PostgreSQL
solves worse, and the problem must exist now. ADR-0004.

Measured against PostgreSQL 18.6 with PostGIS 3.6.4.

| Extension | Status | Tier | Purpose here | Actual use | Cost | Portability | Backup | Managed PG | Decision |
|---|---|---|---|---|---|---|---|---|---|
| `postgis` | **enabled** | required | spatial types and indexes | `geo.feature_version.geom`, `geo.entity_point.geom`, GiST | large extension; version-coupled | ubiquitous | schema dump carries it | universal | **use** |
| `pg_trgm` | **enabled** | required | fuzzy candidate generation | GIN on lowercased entity names | small | core contrib | trivial | universal | **use** |
| `btree_gist` | **enabled** | required | mix `=` and `&&` in EXCLUDE | the two constraints that make temporal identity work | small | core contrib | trivial | universal | **use** |
| `unaccent` | **enabled** | recommended | search normalisation | diacritic-insensitive matching | small | core contrib | trivial | universal | **use** |
| `ltree` | **enabled** | recommended | metric domain taxonomy | `ref.metric_domain.path`, GiST, subtree queries | small | core contrib | trivial | universal | **use** |
| `vector` | available | optional | semantic search | **modelled, not populated** — no embeddings, no index | moderate | widely available | dump-safe | most | **defer** — ADR-0010 |
| `h3` | available | optional | derived spatial bucketing | none yet; reserved for derived views | needed a source build for PG 18 | poor — not packaged | dump-safe | rare | **available, not load-bearing** — ADR-0011 |
| `h3_postgis` | available | — | H3 ↔ PostGIS bridge | none | **hard-requires `postgis_raster`** | poor | — | rare | **decline** — the dependency is not worth bridge functions we do not need |
| `timescaledb` | available | — | time-series | none | large; constrains schema, backup, hosting | poor | complicates dump/restore | some | **decline** — ADR-0009 |
| `hypopg` | available | dev only | hypothetical index evaluation | index sizing before creation | none in production | poor | n/a | rare | **dev only**, never in a migration |
| `pg_stat_statements` | preloaded, not created in this DB | dev only | query statistics | performance work | shared memory, small | core contrib | n/a | universal | **observability, not schema** — it is in `shared_preload_libraries` but no `CREATE EXTENSION` has been run in `atlas_data`, so its views are not queryable here until someone does |
| `pgrouting` | available | — | network routing | none | large | fair | — | some | **decline** — no routable network ingested |
| `postgis_raster` | available | — | raster in DB | none | large | fair | bloats dumps | some | **decline** — rasters belong in COG + STAC, with PostgreSQL holding metadata |
| `postgis_topology` | available | — | topological model | none | moderate | fair | — | some | **decline** — no topology use case |
| `postgis_tiger_geocoder` | available | — | US geocoding | none | large; needs Census data | poor | large | rare | **decline** — a US Census ecosystem; this catalogue is European and global |
| `address_standardizer` | available | — | address parsing | none | moderate | fair | — | some | **decline** — no address data |
| `pgcrypto` | available | — | crypto functions | none — hashing happens in Python at retrieval | small | core contrib | trivial | universal | **decline** — no use |
| `pg_cron` | preloaded, not created in this DB | — | in-database scheduling | none | small | poor | — | some | **decline** — orchestration belongs outside the database |
| `pgaudit` | not installed | — | audit logging | none | moderate | poor | — | some | **consider for production only** |
| Citus | not installed | — | distribution | none | very large | poor | — | some | **decline** — 160k rows is not a sharding problem |
| Apache AGE | not installed | — | graph queries | none | large | poor | — | rare | **decline** — FKs, relation tables and recursive CTEs suffice |
| Elasticsearch etc. | n/a | — | search | none | a second datastore | — | separate | — | **decline** — Postgres FTS is the baseline to beat first |

## Portability

The platform runs on **stock PostgreSQL 18 with PostGIS plus three contrib
extensions**. All of them ship with PostgreSQL or are universally available on
managed hosting.

`h3` and `hypopg` are the only ones that needed work on this machine — a source
build against PG 18 and a Homebrew formula respectively — and neither is
required to run the platform. Losing them costs a derived view and a
development tool, never a fact.

## Installing the optional two

```bash
just wh-extensions
```

Idempotent, and skips anything already present. Neither extension is required:
the platform runs on stock PostgreSQL with PostGIS and three contrib
extensions, and losing `h3` or `hypopg` costs a derived view and a development
tool respectively, never a fact.

## Installation notes

`h3-pg` moved from `zachasme/h3-pg` (now archived) to `postgis/h3-pg`; v4.5.0
supports PostgreSQL 18. On macOS with Homebrew it needs `gettext` on the include
path, because PostgreSQL's `c.h` includes `libintl.h` and Homebrew keeps
`gettext` keg-only:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_C_FLAGS="-I$(brew --prefix gettext)/include" \
      -DCMAKE_SHARED_LINKER_FLAGS="-L$(brew --prefix gettext)/lib"
cmake --build build && cmake --install build --component h3-pg
```

`hypopg` is `brew install hypopg`, which builds against postgresql@17 and @18
and links into both.
