# AGENTS.md — rules for the warehouse subsystem

This directory is a **separate subsystem** from the Data Atlas catalogue. The
catalogue is a static site built from curated JSON with no runtime dependencies;
this is a PostgreSQL data platform. The rules in the repository root
[`AGENTS.md`](../AGENTS.md) still apply to everything outside this directory,
and nothing here may weaken them.

The one rule that spans both: **`just check` must never depend on this.** It has
to pass on a clean clone with no database, no downloaded corpus and no network.
The warehouse has its own recipes (the `wh-` group in the justfile) and its
own gate (`just wh-check`).

Architecture and rationale: [`docs/database/README.md`](../docs/database/README.md).
Decisions and their trade-offs: [`docs/database/ADR/`](../docs/database/ADR/).

## Two meanings of "source of truth"

Get this wrong and the whole system becomes incoherent.

| For | The source of truth is | Never |
|---|---|---|
| **Which sources exist** (the catalogue) | `data/sources/*.json` | this database |
| **Ingested observations and their provenance** | this database | `data/sources/*.json` |
| **Which artifacts a dataset has** | `warehouse/manifests/*.json` | the filesystem |
| **The schema** | `warehouse/migrations/*.sql` | any ORM or dump |

`source.dataset.catalog_source_id` is a plain text pointer between the two. It is
not a foreign key and neither side is generated from the other.

## Raw artifacts are immutable

- A downloaded artifact lives at `raw/<sha256>/<filename>` and is **never
  overwritten**. If the remote file changes, that is a *new artifact* with a new
  digest and a new manifest entry — the old one stays.
- `raw/` is gitignored. Never commit it: it is 2.8 GB, and it is reproducible
  from the manifest.
- A digest mismatch is an error, never a warning, and is never repaired by
  re-downloading over the top.
- A SHA-256 identifies **bytes**, not origin. It attests to what we received at
  retrieval time and nothing more. See
  [`docs/database/RAW-DATA.md`](../docs/database/RAW-DATA.md) — Project Gutenberg
  demonstrably rewrites its own boilerplate, so its live files no longer hash to
  what the archive recorded.

## Migrations

- SQL only, in `migrations/`, numbered `NNNN_name.sql`, applied in order.
- **An applied migration is immutable.** Its checksum is recorded; editing it
  makes the runner refuse to proceed. To change something, add a new migration.
- Never insert a migration with a number below one already applied — it would be
  skipped silently. The runner detects this and refuses.
- Every schema, table, column, view, domain and enum gets a `COMMENT ON` that
  explains its *meaning*, not its name. "population: Population." is not a
  comment. `atlas-data docs generate` reads these back out, so an uncommented
  relation shows up as a warning.

## No silent failures

This is the rule the whole subsystem is built around.

- A parser may **never** discard a value, coerce it to NULL, or guess. Anything
  it cannot justify becomes a row in `meta.rejected_record` with its raw input.
- A number is never invented from a malformed token. `l,600` (a real typo in the
  1995 edition) is refused, not read as 600.
- `NULL` alone is not an answer. An observation with no value must carry a
  `missing_reason` saying which kind of absence it is — the database enforces
  this biconditionally.
- Raw text is always preserved alongside any parsed value. A better parser must
  be able to re-read the original.
- A count reported by a run must be the count of rows that actually landed.
  Counting attempts instead of insertions produced a real reconciliation failure
  here; the check that caught it is `record_count_reconciliation`.

## Entity identity

- **Never** key on an ISO code. Codes are reassigned — ISO moved `CS` from
  Czechoslovakia to Serbia and Montenegro — so every external identifier is an
  attribute with a validity period pointing at an opaque `core.entity` key.
- Fuzzy matching may **propose** an entity resolution. It may never accept one.
  The database enforces this
  (`entity_resolution_fuzzy_is_never_self_accepted`).
- An unresolvable source entry stays unresolved and goes to the curation queue.
  Guessing which "Congo" was meant is fabrication.
- `bootstrap-entities` creates one entity per source entry, typed
  `unclassified`. It asserts that the entry exists, never what kind of thing it
  is. Do not "improve" it by inferring sovereignty from the text.

## Provenance and derived values

- Every observation points at the `source.field_value` it came from. An
  observation with neither that nor a written explanation is rejected.
- Source claims are **never** overwritten or deduplicated. Two editions
  disagreeing is data. Choosing between them happens in `derived.*`, with the
  rule and the inputs recorded.
- Language-model output is never written into `obs.*` or `source.*`. It is
  content with `provenance = 'model_generated'`, and it is not evidence.

## Verification

```bash
just wh-test        # parser unit tests; no database, no network
just wh-test-db     # constraint tests against the live database
just wh-check       # both, plus migrations and the quality suite
```

`just wh-check` is this subsystem's gate. It does not run in the repository's
CI-wide `just check`, and must not be added to it.

Say which commands you actually ran. If a check needed a database or the corpus
and you did not have one, report it as **NOT RUN** with the reason — never as
passing.

## Generated files

| Generated | By | Never edit |
|---|---|---|
| `docs/database/SCHEMA-REFERENCE.md` | `just wh-docs` | ✓ |
| `docs/database/ERD.md` | `just wh-docs` | ✓ |
| `warehouse/reports/*.md` | `just wh-reports` | ✓ |

Everything else here is hand-written source, including the manifests and the
migrations.

## Do not

- Add a dependency without a reason that could not be met by the standard
  library. The whole subsystem has one runtime dependency, and that is a feature.
- Weaken a foreign key, a CHECK or an EXCLUDE constraint to make something pass.
  If re-staging trips `ON DELETE RESTRICT`, the fix is to remove the derived rows
  first — that constraint is preventing evidence from being silently orphaned.
- Turn off a quality check because it is noisy. Fix the parser, widen the bound
  with a reason, or change the severity in a migration that says why.
- Put business logic in PL/pgSQL, or an HTML parser anywhere near the database.
- Type a count into prose. Query it.
- Optimise before measuring. `EXPLAIN (ANALYZE, BUFFERS)` on populated tables
  first; see [`docs/database/PERFORMANCE.md`](../docs/database/PERFORMANCE.md).
