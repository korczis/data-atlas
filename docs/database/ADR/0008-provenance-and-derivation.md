# ADR-0008 — Source claims immutable; derived values in their own layer

**Status**: accepted

## Context

The platform will eventually hold several sources reporting the same metric for
the same place and period, and they will disagree. Even with one source it
already happens: successive Factbook editions revise their own earlier figures.

The tempting design is an upsert — newest value wins. It is wrong, and it is
wrong irreversibly: once a claim is overwritten, the fact that sources disagreed
is gone, and so is the ability to explain why a published number changed.

## Decision

`obs.*` holds **every** claim. There is no unique constraint on
(entity, metric, period) and there deliberately never will be. Contradiction is
data.

Choosing between claims happens in `derived.preferred_value`, which records the
selection rule, its version, and — through `derived.derivation_input` — every
candidate considered, including the rejected ones.

Every observation must point at the `source.field_value` it came from, or carry
a written explanation of how it was derived. A CHECK constraint enforces this.

Corrections are made by superseding, never by mutation. Raw artifacts are never
deleted automatically.

Language-model output is never written into `obs.*` or `source.*`. It is
`content.*` with `provenance = 'model_generated'`, and it is not evidence.

## Consequences

- `api.source_claims` shows disagreement directly; it is already non-empty with
  one dataset loaded.
- A published profile can cite the claim behind every value, and say which other
  claims existed and were not chosen.
- Storage grows with every edition rather than being deduplicated. Accepted:
  that growth is the historical record.
- `ON DELETE RESTRICT` on the provenance foreign keys means re-staging an
  artifact must first remove the derived rows. That surfaced during development
  as a hard failure — which is the constraint working, not an obstacle.

## What would reverse this

Nothing. This is the platform's reason for existing.
