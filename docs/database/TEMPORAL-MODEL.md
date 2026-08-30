# Temporal model

## Three clocks

The 2025 Factbook reports Czechia's population as `10,838,703 (2025 est.)` and
its age structure as `20.5% (2024 est.)`, in an edition whose underlying data
was last committed in January 2026. That is four dates in one document, and at
least three of them are semantically different.

| Clock | Column | Question |
|---|---|---|
| **Reference** | `obs.observation.reference_period` | what period does this value describe |
| **Publication** | `source.release.edition_year`, `published_on` | when was it said |
| **System** | `obs.observation.recorded_at` | when did this platform store it |

`edition_year = reference_year` is never assumed, and cannot be: they live on
different tables.

## Ranges

`daterange`, half-open `[start, end)`, everywhere. Consequences:

- adjacent years abut exactly: `[2020-01-01,2021-01-01)` then
  `[2021-01-01,2022-01-01)` — no gap, no overlap;
- `&&` (overlap) means what it should, which is what makes exclusion constraints
  expressible;
- an unbounded upper bound means "still true as far as this database knows",
  which is different from "forever" and different from "unknown".

Ranges are used for observation reference periods, entity existence, name
validity, identifier validity and relation validity.

## The precision column

`obs.observation.period_precision` is the part that is easy to omit and
important to keep. It records **how the period was determined**:

| Value | Means |
|---|---|
| `year` | the source stated a year — "(2024 est.)" |
| `day`, `month`, `quarter` | the source was more precise |
| `multi_year` | the source gave a span |
| `unknown` | **the source stated nothing; the edition year was used as a fallback** |

Without this column the fallback is indistinguishable from a statement. A
consumer computing a time series can filter to periods the publisher actually
asserted; one that ignores it at least does so knowingly.

## "Latest" is ambiguous

Three different rows can be "the latest":

| Reading | View |
|---|---|
| describing the most recent period | `api.observation_latest_by_period` |
| from the most recently published edition | `api.observation_latest_by_edition` |
| most recently ingested | not exposed — an artefact of when we ran, not of the data |

A 2010 edition reporting 2009 data and a 2012 edition reporting 2005 data:
the first wins by period, the second by edition. Both views break ties
deterministically so results are stable.

No view is called simply `latest`.

## Bitemporality

The model is bitemporal where it matters — valid time (`reference_period`,
`validity`) and system time (`recorded_at`, `source.release.published_on`) are
both recorded — without a full system-versioned implementation.

Corrections are made by **superseding**, not by updating in place: a new
observation from a new release, or a new `derived.preferred_value` with a new
rule version. The history of what this platform believed stays readable.
