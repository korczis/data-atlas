# ADR-0005 — One typed observation core, explicit tables where grain differs

**Status**: accepted

## Context

Two failure modes to avoid, in opposite directions.

Pure EAV — `(entity, field_name, value_text)` — is a key-value store wearing SQL
as a disguise. Nothing is typed, nothing is constrained, and every query
reinvents parsing. Explicitly forbidden by the brief, and rightly.

Pure per-field modelling — a column or table per Factbook field — means 400+
tables, most of them nearly empty, and a schema migration every time a
publication renames something. Over thirty-six editions this corpus renamed and
restructured fields constantly.

A third option, per-domain schemas (`demo`, `econ`, `energy`, …), was in the
brief and was not adopted.

## Decision

**One strongly-typed observation core**, plus **explicit relational tables only
where the grain genuinely differs**.

The core is a shared header with disjoint typed subtypes, wired so that a
metric's declared `value_kind` dictates which subtype may attach. This is not
EAV: the value is typed, the metric is a foreign key into a registry with a
unit and a domain, and the database rejects a type mismatch.

Explicit tables exist for compositions, bilateral facts, ranks, points and
narrative, because in each case one row of the scalar model would misrepresent
the shape of the fact.

The domain is an `ltree` path on `ref.metric_domain`, not a schema name.
Reclassifying a metric is an update, not a table move, and "every economic
indicator for this country" is a filter rather than a union across schemas.

## Consequences

- Adding a metric is one row plus a mapping row. No DDL, no reprocessing.
- `population = 'Tuesday'` is refused by a foreign key.
- An observation without exactly one value row is refused at commit — except one
  that deliberately records an absence, which must carry a `missing_reason`.
- Queries join more than they would against a wide table. `api.observation`
  exists so consumers never write those joins.
- The subtype mechanism is unusual and needs the explanation in ARCHITECTURE.md;
  it is not something a reader will infer from the DDL alone.

## What would reverse this

If one domain grew a dozen tightly-coupled metrics always queried together —
a full national-accounts model, say — a dedicated relational table for that
domain would beat the generic core, and could coexist with it.
