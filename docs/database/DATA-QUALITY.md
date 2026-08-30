# Data quality

## The principle

A parser may never discard a value, coerce it to NULL, or guess. Anything it
cannot justify becomes a row in `meta.rejected_record` with the raw input that
defeated it.

Zero warnings is not a realistic goal for a thirty-six-year corpus of
hand-edited publications. **Zero silent failures is.**

## Quarantine

```sql
SELECT error_code, count(*) FROM api.rejected_values
 GROUP BY error_code ORDER BY 2 DESC;
```

Each row keeps the raw text, the reason, the parser version and a pointer to
where in the source it occurred. A parser improvement is measured by rows
leaving this table; a regression is visible as rows arriving in it.

This table being non-empty is the system working. The alternative to a
quarantine row is an invented number.

## Checks

Declared as rows in `meta.quality_check` and implemented in
`warehouse/atlasdata/quality.py`. Declaring them as data means the set of things
being checked is itself queryable — and a check declared but not implemented is
*itself reported*, so the catalogue cannot overstate what is verified.

| Check | Category | Gate | What it looks for |
|---|---|---|---|
| `observation_without_provenance` | referential | yes | a value with no raw field and no explanation |
| `record_count_reconciliation` | reconciliation | yes | a run's reported counts against the rows present |
| `artifact_digest_mismatch` | structural | yes | on-disk bytes diverging from the manifest |
| `unresolved_entity` | referential | no | source keys awaiting curation |
| `composition_share_sum` | semantic | no | shares far from 100 |
| `value_outside_expected_range` | range | no | values beyond a metric's plausibility bounds |
| `reference_period_after_publication` | temporal | no | a period later than the edition reporting it |
| `duplicate_observation` | duplicate | no | the same claim twice in one release |
| `parser_coverage` | coverage | no | how much of the source has no canonical mapping |
| `value_contradicts_unit` | semantic | no | a value that cannot mean what its unit says |

Gates are deliberately few. A gate that fires on ordinary imperfection gets
routed around, and then nothing is gated.

```bash
just wh-quality      # non-zero exit if a gate fails
```

Findings land in `meta.quality_issue`, queryable via `api.data_quality_summary`.
Nothing is written only to a log, because a release gate can read a table and
cannot read a log.

### Why `value_contradicts_unit` exists

A range check cannot find a number lifted out of a sentence. Australia's 2009
public debt is recorded as **2006** — the year in "the Commonwealth government
eliminated its net debt in 2006" — carrying the unit `percent`, and 2006 is not
an implausible percentage of GDP for an indebted state. China's is 10.72
trillion, an absolute renminbi figure, also filed as a percentage and also
carrying a currency. Every one of these rows has valid provenance to a real
field value; nothing about them is structurally wrong.

What gives them away is the value contradicting its own unit: a percentage is
not denominated in a currency, and a percentage that is exactly a year inside
this corpus's publication range is almost never a measurement. The check finds
30 such rows. It is a warning rather than a release gate, because the rows are
wrong in the extractor, and gating on them would block every load until prose
extraction is solved rather than making the problem visible now.

## Bugs these checks actually caught

Not hypothetical. Each of these was found by running the suite against loaded
data, and each is now fixed with a regression test.

**A rate's denominator read as its value.** `"NA births/1,000 population"` has no
value — but it contains exactly one number, and the parser took it. Every such
field became a birth rate of **1000**. Caught by
`value_outside_expected_range`. Fixed by stripping rate denominators before any
number is read, and by treating a leading absence token as an absence even when
it carries unit text. Regression tests in `warehouse/tests/test_values.py`.

**Counts that counted attempts.** Staging reported more field values than the
table held for the 2015 and 2017 editions, because `ON CONFLICT DO NOTHING`
silently skips a duplicate and the counter incremented regardless. Caught by
`record_count_reconciliation`. Fixed by counting `cur.rowcount`.

**A plausibility bound that was simply wrong.** `world/demo.population.total =
5,515,617,484` was flagged as out of range. It is the world population in 1993,
correctly parsed from the Factbook's own "World" entry; the bound had been set
for countries. Fixed in migration 0014 — the data was right and the check was
wrong, which is a finding about the checks worth recording.

**Two staging runs racing.** Two concurrent `ingest stage --all` processes
deleted each other's rows, leaving editions silently empty with plausible-looking
totals. Only a per-artifact query revealed it. Fixed with a PostgreSQL advisory
lock so the database refuses the second run.

**Unindexed foreign keys.** Re-staging took over 55 seconds per artifact because
four tables reference `source.field_value` with `ON DELETE RESTRICT` and none had
an index on the referencing column. Fixed in migration 0015.

## What an adversarial review found afterwards

The checks above were written by the same person who wrote the parsers, which is
a known weakness. A ten-stream adversarial review of the finished subsystem
found the following, every one confirmed against the loaded database before
being acted on. They are recorded because the *class* of each is more useful
than the individual bug.

**Entity names taken from the publisher.** Four HTML editions title every page
"The World Factbook — Central Intelligence Agency", with the country only in a
`class="country"` span. The parser fell back to the title, and the resolver then
chose the representative label with `min(source_label)` — where "Central
Intelligence Agency" sorts before almost every country name. Result: 206
entities named after the publisher, carrying **65.6% of all observations**. Fixed
by reading the country element, and by choosing the *modal* label rather than
the alphabetically first.

**Back matter absorbed into the last country, in four more editions.** The 2001
fix described earlier did not generalise: 1995 delimits its appendices with `_`
rather than `=`, and 1992-1994 use no rule at all, just a heading. Zimbabwe held
17× to 27× the median field count in those editions. Fixed by recognising
appendix headings and all rule characters — and by making the heading match
case-insensitive, which is what 1992's title-case "Notes, Definitions, and
Abbreviations" needed.

**A heuristic that discarded real data.** The rule that rejected front matter —
"a section whose unattached lines outnumber its fields" — was applied to every
section, not just the preamble. In 1993 it silently dropped twelve real sections,
including whole "Flag description" fields, because a page-break artefact left a
few orphaned lines beside genuine content. Now scoped to the preamble only: once
a section has parsed cleanly, the file is in its body and noisy sections keep
their fields.

**Sections mislabelled across two whole editions.** 1997 has no `:Economy`
marker and 1998 has none for `:Communications`, so every country's GDP was filed
under "Government" and its telephones under "Economy". The heading was in the
text all along; the parser just never read a bare section heading inside a body.

**Values paired with the wrong year.** Later editions publish several years in
one field. Taking the first number and the last year paired a 2017 figure with
2015 — and where the field was an explanatory note ("data are in 2010 US
dollars"), the *year itself* became the value: roughly 2,400 GDP observations
were the number 2010 or 2013.

**A landlocked country's neighbour called "0 km".** `parse_partners` treated the
quantity as a partner label, producing 2,312 bilateral rows whose partner was a
distance.

**Silent drops the doctrine forbids.** `_load_composition` and `_load_bilateral`
returned `0` when they could not parse, recording nothing at all — 19 and 111
field values respectively vanished with no row, no rejection and no count. The
sibling `_load_observation` had always handled this correctly; the two were
simply never brought into line.

**Checks that under-reported themselves.** Two quality checks capped their
examples at 500 rows and then returned the *capped* number as the finding count:
4,051 duplicate observations were reported as 500. And `artifact_digest_mismatch`
never compared a digest — it skipped absent files entirely, which is the exact
case its name describes.

**A documented feature that did nothing.** `currency_id` and `price_basis` were
modelled, constrained, documented with a worked example — and never written by
the loader. All monetary observations had NULL in both.

**An invariant enforceable only until commit.** The deferred trigger fired on
`obs.observation` alone, so deleting a value row in a later transaction left an
orphaned header that nothing re-examined. Migration 0018 attaches the same
assertion to every subtype table.

**A test harness that passed for the wrong reason.** `rejects()` treated any
exception whose class name contained "Error" as proof a constraint fired — so a
SQL typo in a fixture counted as a pass, and so did an unrelated NOT NULL
violation firing first. It now checks SQLSTATE and fails loudly when the fixture
itself is broken.

The pattern worth noticing: **most of these were invisible to the quality suite**
because the suite checked the data it had, not the data it should have had. The
reconciliation gap between staging and loading is the structural version of that
blind spot, and it is on the roadmap rather than fixed.

## Bounds are not constraints

`ref.metric.expected_min` / `expected_max` drive a quality check; they are not
CHECK constraints on the value. A genuine outlier must land in the database and
be reported, not be rejected at insert and lost.

The exception is where the *type* makes the bound definitional:
`ref.percentage` really does refuse anything outside 0–100. When a source yields
an out-of-range share, the member is kept with its raw text and no share, and
the failure is quarantined — the value is never clamped into range, because a
share silently rewritten from 120 to 100 is a fabricated fact.

## Composition tolerance

Shares are checked against 100 with a **±25 point** tolerance. Wide on purpose:
rounding, unlisted residuals and overlapping categories are all normal, and a
tight bound would fire constantly on correct data and then be ignored. Only
gross deviation is a finding.
