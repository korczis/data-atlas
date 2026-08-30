# The Data Atlas warehouse

A source-agnostic data platform on PostgreSQL. Its first corpus is the CIA World
Factbook, 1990–2025; its shape is not.

This is a **second subsystem** in this repository, not a replacement for the
first. The Data Atlas catalogue remains a static site built from curated JSON,
with no database and no runtime dependencies. Nothing here is in its build path.

## The distinction that matters

The word "source" means two different things in this repository, and conflating
them makes both incoherent:

| | The catalogue (`data/sources/*.json`) | The warehouse (this) |
|---|---|---|
| Answers | *which* data sources exist, and what you can get from them | *what those sources actually said*, and when |
| Source of truth for | source discovery and classification | ingested observations and their provenance |
| Grain | one row per source | one row per claim about one metric, entity and period |
| Storage | committed JSON → CSV → static site | PostgreSQL |
| Needs | nothing | a database, and once, the network |

They are linked by one plain text pointer, `source.dataset.catalog_source_id`.
Neither is generated from the other, and neither validates the other.

## What it is for

The long-term goal is not "the Factbook in PostgreSQL". It is an evidence layer
that can eventually carry dozens of sources and answer, for any number it holds:

- where exactly did this come from — publisher, edition, file, byte digest, the
  record and field inside it, the original text, the parser version;
- what period does it describe, as distinct from when it was published;
- is it an estimate;
- do other sources say something different, and if so what;
- which value did we publish, under what rule, and from which candidates.

Answering the last two requires never overwriting a source claim, which is why
the canonical layer keeps every contradiction and resolution happens elsewhere.

## Documents

| Document | What it covers |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | The layers, the pipeline, and what each schema is responsible for |
| [`SOURCE-AUDIT-CIA-WORLD-FACTBOOK.md`](SOURCE-AUDIT-CIA-WORLD-FACTBOOK.md) | What was established about the corpus before anything was downloaded |
| [`RAW-DATA.md`](RAW-DATA.md) | Artifact storage, digests, and what a hash does and does not prove |
| [`SCHEMA-3NF.md`](SCHEMA-3NF.md) | The canonical model, domain by domain, with grains and invariants |
| [`TEMPORAL-MODEL.md`](TEMPORAL-MODEL.md) | The three clocks, range conventions, and "latest" |
| [`ENTITY-IDENTITY.md`](ENTITY-IDENTITY.md) | Why an ISO code is not an identity |
| [`PROVENANCE.md`](PROVENANCE.md) | The chain from a number back to bytes |
| [`DIMENSIONAL-MODEL.md`](DIMENSIONAL-MODEL.md) | The mart, its grains, and why it is not the truth |
| [`DATA-QUALITY.md`](DATA-QUALITY.md) | Checks, quarantine, and the bugs they caught |
| [`GEOSPATIAL.md`](GEOSPATIAL.md) | PostGIS, versioned geometry, H3 as a derived index |
| [`EXTENSIONS.md`](EXTENSIONS.md) | Every extension considered, with the decision and its cost |
| [`ADDING-A-SOURCE.md`](ADDING-A-SOURCE.md) | The adapter contract, and how to add the second dataset |
| [`OPERATIONS.md`](OPERATIONS.md) | Setup, running the pipeline, backup, and what is irreplaceable |
| [`SECURITY.md`](SECURITY.md) | Download safety, roles, secrets |
| [`PERFORMANCE.md`](PERFORMANCE.md) | Measured query plans, and the indexes that exist because of them |
| [`EXAMPLE-QUERIES.md`](EXAMPLE-QUERIES.md) | Real queries against the canonical model and the mart |
| [`ROADMAP.md`](ROADMAP.md) | What is built, what is not, and what is next |
| [`ADR/`](ADR/) | The decisions, with their trade-offs and what would reverse them |
| [`SCHEMA-REFERENCE.md`](SCHEMA-REFERENCE.md) | **Generated.** Every table, column, constraint and comment |
| [`ERD.md`](ERD.md) | **Generated.** Mermaid diagrams, one per bounded context |

Coverage, field-evolution, storage and reconciliation reports are generated into
[`warehouse/reports/`](../../warehouse/reports/).

## A note on the `§NNN` references

SQL comments and these documents carry references like `§25` or `§105`. They
point at numbered requirements in the design brief this subsystem was built to,
which is not itself in the repository. They are kept because they record *why* a
constraint exists and let a reviewer with the brief check the work against it.

Where one appears, the surrounding prose always states the reason in full as
well — the reference is corroboration, never the only explanation. The ones in
`warehouse/migrations/` cannot be edited in any case: an applied migration is
immutable, and rewriting one would change its recorded checksum and make the
runner refuse to proceed.

## Getting started

```bash
just wh-install                     # one dependency: psycopg 3
createdb atlas_data                 # or point ATLAS_DATABASE_URL somewhere
just wh-migrate                     # apply the schema
just wh-fetch --family json_factbook_cache   # ~29 MB, five editions
just wh-stage --family json_factbook_cache
just wh-load --bootstrap-entities
just wh-mart
just wh-quality
```

`warehouse/.env.example` documents the environment. Fetching is the only step
that needs the network; everything after it works offline.

The full corpus is 2.8 GB compressed. `just wh-fetch --all` will say what it is
about to transfer and refuse if the disk cannot take it with headroom.

## Conventions

- **snake_case**, schema-qualified everywhere in migrations and views.
- **`timestamptz`** for real moments, always UTC; `date` for dates without time.
- **`numeric`** for money and published decimals; `double precision` only where
  float is genuinely the right type, which here means coordinates and geometry.
- **Half-open ranges**, `[start, end)`, throughout — so adjacent periods abut
  without overlapping.
- **`generated always as identity`** for surrogate keys — `bigint` for tables
  that grow, `integer` for small reference tables. Natural keys are unique
  constraints rather than primary keys, because they change; the one exception
  is `meta.schema_migration`, keyed on filename, where the filename *is* the
  identity. ADR-0002.
- Every relation carries a `COMMENT ON` explaining what it *means*.

## The rules that shaped it

Written out in [`warehouse/AGENTS.md`](../../warehouse/AGENTS.md). The short
version: raw artifacts are immutable, parsers never guess, `NULL` is never an
answer on its own, an ISO code is never an identity, source claims are never
overwritten, and no check may report success for work it did not do.
