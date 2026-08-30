# ADR-0002 — `bigint` identity surrogate keys

**Status**: accepted

## Context

Three candidates: natural keys, UUIDs, or generated integers.

Natural keys are disqualified for anything historical. An ISO alpha-2 code looks
like a perfect primary key for a country and is not one: ISO reassigned `CS`
from Czechoslovakia to Serbia and Montenegro, so the "key" identifies different
entities in different decades. Using it would mean either losing history or
corrupting it.

UUIDs solve a problem this system does not have — offline generation and
cross-system merging without coordination. They cost 16 bytes against 8, index
worse, and make every debugging session harder to read.

## Decision

`generated always as identity` for surrogate keys, `bigint` on anything that
grows with the data and `integer` on small reference tables (units, currencies,
entity types, identifier schemes, metric domains — tables with tens to hundreds
of rows, whose keys are foreign keys in large tables where four bytes against
eight is worth having). No UUIDs anywhere.

Natural identifiers are `UNIQUE` constraints rather than primary keys, with one
deliberate exception: `meta.schema_migration` is keyed on the filename. A
migration's identity *is* its filename — that is the whole point of the
immutability check — and a surrogate key there would add a number that means
nothing and permit two rows for one file.

## Consequences

- Keys are compact, index well, and are readable in a `psql` session.
- Entity identity survives every code change, rename and dissolution.
- Keys are database-local. Exporting to another system requires exporting a
  natural key alongside — `core.entity.slug` and `core.entity_identifier` both
  serve, and the mart carries `iso_alpha2` for this reason.
- Merging two databases would need a key remap. Accepted: there is one database.

## What would reverse this

Genuine multi-writer distribution, or a need to generate keys offline before
insertion. Neither is on the roadmap; if either arrives, the change is additive
— a UUID column alongside the identity key, not a replacement of it.
