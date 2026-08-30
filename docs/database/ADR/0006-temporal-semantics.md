# ADR-0006 — Three clocks, half-open ranges, explicit precision

**Status**: accepted

## Context

The single most common way a historical dataset becomes quietly wrong is
collapsing publication time into observation time. The Factbook makes the
distinction unavoidable: the 2025 edition reports population as "2024 est.",
and its underlying JSON cache was last committed in January 2026. Three
different years, one fact.

## Decision

Three clocks, stored separately and never conflated:

| Clock | Where | Question |
|---|---|---|
| Reference time | `obs.observation.reference_period` | what period does this describe |
| Publication time | `source.release.published_on` / `edition_year` | when was it said |
| System time | `obs.observation.recorded_at` | when did we store it |

`reference_period` is a `daterange`, half-open `[start, end)` throughout, so
adjacent years abut without overlapping and `&&` means what it should.

Crucially, `period_precision` records **how the period was determined**. When
the source stated a year, it is `'year'`. When it did not and the edition year
was used as a fallback, it is `'unknown'` — so a consumer can always distinguish
a period the publisher asserted from one this platform inferred. Without that
column the fallback would be indistinguishable from a statement, which is
exactly the failure the three-clock model exists to prevent.

"Latest" is never used unqualified. `api.observation_latest_by_period` and
`api.observation_latest_by_edition` answer different questions and say so.

## Consequences

- `edition_year = observation_year` is never assumed and cannot be, because
  they are different columns on different tables.
- Range queries use GiST indexes; equality on a range is not enough.
- Entity existence, name validity and identifier validity are all ranges too,
  which is what makes exclusion constraints able to express "one preferred name
  at a time" without forbidding renames.

## What would reverse this

Nothing about the model. A source with sub-annual data would use narrower
ranges, which the type already supports; `mart.dim_period` is monthly for that
reason.
