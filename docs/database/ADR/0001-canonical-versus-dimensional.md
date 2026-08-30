# ADR-0001 — Canonical 3NF and the dimensional mart are separate layers

**Status**: accepted

## Context

Analytics wants wide, denormalised, pre-joined tables. Evidence wants narrow,
normalised, heavily constrained ones. A single model cannot be both without one
side losing, and the side that loses is usually integrity, because the pressure
to make a dashboard fast is immediate and the cost of a lost provenance chain
arrives years later.

## Decision

Two layers, one direction of dependency.

- `source`, `core`, `ref`, `obs`, `geo`, `content` are canonical. Normalised,
  constrained, provenance-bearing. This is the truth.
- `mart` is a projection: seven materialised views over the canonical model,
  rebuilt by `just wh-mart`.

The mart is never written to directly and never a source of truth. If the two
disagree, the canonical model is right and the mart is stale.

## Consequences

- The mart can be dropped and rebuilt at any time. It is not backed up.
- A canonical schema change may break a mart view, which is the correct
  direction for breakage to travel.
- Analysts join more tables in `api.*` than in `mart.*`, and that is fine
  because `api.*` exists to hide exactly that.
- Materialised views rather than tables with a load script: the view definition
  *is* the transformation, so there is no second place for the logic to drift to.

## What would reverse this

If the mart's refresh time became a problem — minutes rather than the current
sub-second — incremental physical tables with a load script would be worth the
duplicated logic. The row counts that would justify it are in PERFORMANCE.md.
