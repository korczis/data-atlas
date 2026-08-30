# The canonical model

Normalised, constrained, provenance-bearing. Denormalisation lives in `mart`
and `api`, never here. ADR-0001.

The generated, always-current listing of every table, column, constraint and
index is [`SCHEMA-REFERENCE.md`](SCHEMA-REFERENCE.md). This document explains
the parts that need reasoning rather than enumeration.

## Grain, by table

| Table | One row represents |
|---|---|
| `source.publisher` | one organisation that publishes data |
| `source.dataset` | one named, repeatedly published body of data |
| `source.release` | one edition of a dataset |
| `source.artifact` | one file belonging to a release, identified by its bytes |
| `source.retrieval` | one place those bytes have been obtained from |
| `source.record` | one entry (a country) inside an artifact |
| `source.field_definition` | one distinct section-and-field name a dataset uses |
| `source.field_value` | the raw text of one field of one record |
| `core.entity` | one place or reporting unit, with permanent identity |
| `core.entity_name` | one name, of one kind and language, over one period |
| `core.entity_identifier` | one external code, valid over one period |
| `core.entity_relation` | one directed relation between two entities, over a period |
| `ref.metric` | one thing that can be measured |
| `ref.unit` | one unit of measure |
| `obs.observation` | one source's claim about one metric, entity and period |
| `obs.composition` | one breakdown of one entity by one classification |
| `obs.composition_member` | one category's share within that breakdown |
| `obs.bilateral_observation` | one fact about an ordered pair of entities |
| `obs.source_rank` | one rank a source published |
| `geo.feature_version` | one version of one feature's geometry, from one source |
| `geo.entity_point` | one point a source published for an entity |
| `content.field` | one named passage of prose |
| `meta.ingestion_run` | one execution of one pipeline stage over one artifact |
| `meta.rejected_record` | one value a parser refused, with the text that defeated it |

## Invariants worth knowing

**An observation's type is dictated by its metric.** `ref.metric` declares
`value_kind`; `obs.observation` references `(metric_id, value_kind)` as a
composite foreign key; each subtype table has a constant generated `value_kind`
and references `(observation_id, value_kind)`. A population cannot hold a word.

**Every observation has exactly one value row, or deliberately none.** Foreign
keys cannot express "a parent must have a child", so a deferred constraint
trigger checks at commit. An `unparsed` observation must have *no* value row and
*must* have a `missing_reason`.

**NULL is never an answer by itself.**

```sql
CHECK ((parse_status = 'unparsed') = (missing_reason IS NOT NULL))
```

A biconditional: every absent value states which kind of absence it is
(`not_applicable`, `not_reported`, `unknown`, `negligible`, `suppressed`,
`parse_failure`), and a parsed value may not also claim to be missing.

**Shares are not normalised to 100.** Rounding, unlisted residuals and
overlapping categories are all real. A composition summing to 99.7 is correct
data. A quality check audits the sum with a wide tolerance; no constraint
enforces it.

**Contradiction is permitted.** There is no unique constraint on
(entity, metric, period). Two releases disagreeing are two rows. ADR-0008.

## Domains

Constraints expressed once in the type rather than in forty CHECK clauses that
will eventually disagree:

| Domain | Base | Constraint | Note |
|---|---|---|---|
| `ref.sha256_hex` | `text` | 64 lowercase hex | identity of bytes |
| `ref.percentage` | `numeric(9,6)` | 0–100 | *not* for growth rates, which are legitimately negative |
| `ref.non_negative_numeric` | `numeric` | ≥ 0 | areas, lengths, counts |
| `ref.latitude` / `ref.longitude` | `double precision` | ±90 / ±180 | float because this feeds geometry |
| `ref.publication_year` | `smallint` | 1500–2200 | loose on purpose |
| `ref.media_type` | `text` | shape only | not a registry check |
| `ref.entity_code` | `text` | trimmed, non-empty | per-scheme shape lives on the scheme |

URLs are deliberately **not** a domain. A regex strict enough to be worth having
rejects valid URLs; one loose enough to be safe asserts nothing. Validated in
the application, at the boundary.

## Types

- `numeric` for money and published decimals. Never `money` — it carries a
  locale-dependent currency assumption and cannot represent a currency reference.
  Monetary values are `numeric` + `currency_id` + `price_basis`.
- `double precision` only for coordinates and geometry, where float is the
  native and correct representation.
- `timestamptz` for real moments, UTC. `date` for dates without time semantics.
- `generated always as identity` for surrogate keys: `bigint` where the table
  grows with the data, `integer` on small reference tables. `meta.schema_migration`
  is the one table keyed on a natural value, its filename. ADR-0002.

## Enum versus reference table

`ENUM` only for closed internal states the pipeline defines: `run_status`,
`artifact_status`, `value_kind`, `parse_status`, `missing_reason`,
`mapping_status`, `issue_severity`, `derivation_status`, `provenance_kind`.

Everything describing the world is a reference table with a foreign key —
entity types, name kinds, identifier schemes, relation types, categories,
units, currencies, metrics. `core.entity_type` grew twice during development,
which is precisely the argument. ADR-0004.

## Foreign key policy

Every one is deliberate:

| Policy | Where | Why |
|---|---|---|
| `RESTRICT` | provenance chains, entity references from observations | deleting would silently orphan evidence |
| `CASCADE` | subtype value rows, composition members, retrievals | meaningless without their parent |
| `SET NULL` | `source_release_id` on names and identifiers | the name stays true even if its citation is removed |

`RESTRICT` is the default choice here, not the database's default of `NO ACTION`
by omission. A default is not a decision.
