# Provenance

## The chain

Every number must be traceable to bytes:

```
obs.observation
  → source.field_value      the exact string that was parsed
  → source.field_definition the field and section it came from
  → source.record           the entry (country) inside the artifact
  → source.artifact         the file, its SHA-256, and how that digest is known
  → source.retrieval        every URL those bytes have been fetched from
  → source.release          the edition, and when it was published
  → source.dataset          the dataset
  → source.publisher        who published it
plus
  → meta.ingestion_run      when it ran, which git revision, which parser version
```

One view walks it for observations: `api.provenance`.

**Every fact family now cites the exact value it was read from.** Observations,
compositions, bilateral facts and coordinates carry `field_value_id` and are
enforced to (migration 0018); `content.field` does too, and is `NOT NULL`
(migration 0021).

That last one was a real gap, not a formality. `content.field` previously
carried only `field_definition_id` — a dataset-wide *dictionary* entry that
identifies a field's name, not the value a passage came from. Recovering the
instance meant joining on `record_id` and `field_definition_id`, which left
105,548 of 116,617 rows with one candidate and 11,069 with between two and
thirty; equality on the passage text settled the rest, but only by convention,
and nothing stopped two identical passages in one record from making even that
ambiguous. The loader's own `INSERT` already had the right id in scope. It is
stored now, and the backfill resolved every existing row, which is why the
column could be made `NOT NULL` in the same migration.

Two related gaps closed with it. `geo.entity_point` had no `ingestion_run_id`,
so "which run produced this coordinate" was unanswerable for all 7,199 rows; it
is populated from every load onward, and left nullable for older rows rather
than backfilled with a guess. And `source.field_mapping` had no incoming foreign
key from anywhere, so *which curated decision* produced a fact was recoverable
only by re-running the pattern match — inference over data that can be edited
afterwards. Observations, compositions, bilateral facts and coordinates now
store `field_mapping_id`.

```sql
SELECT entity_slug, metric, source_raw_text, field_name,
       artifact, sha256, release_label, parser_version, retrieval_url
  FROM api.provenance
 WHERE entity_slug = 'czechia' AND metric = 'demo.population.total';
```

## Enforced, not encouraged

```sql
CONSTRAINT observation_has_provenance
    CHECK (field_value_id IS NOT NULL OR btrim(notes) <> '')
```

An observation must point at the raw field it came from, or explain in writing
how it was derived. There is no third option, and `warehouse/tests/test_schema.py`
asserts the database refuses one.

The foreign keys along the chain are `ON DELETE RESTRICT`, deliberately —
deleting a field value that an observation cites is refused. One link is
`ON DELETE CASCADE` and it is the right exception: `source.retrieval` describes
where an artifact's bytes were fetched from, and a retrieval without its
artifact is meaningless, so it goes when the artifact goes. This surfaced during
development: re-staging an artifact failed because loaded observations still
referenced its field values. That is the constraint doing its job — the fix was
to remove the derived rows first, not to weaken the key.

## Raw text always survives

`$2.14 trillion (2023 est.)` becomes:

| Stored | Where |
|---|---|
| the string itself | `source.field_value.raw_text` |
| `2140000000000` | `obs.numeric_observation.value` |
| USD | `obs.observation.currency_id` |
| `[2023-01-01,2024-01-01)` | `obs.observation.reference_period` |
| estimate = true | `obs.observation.is_estimate` |
| `parsed_with_qualifier` | `obs.observation.parse_status` |
| parser version | `obs.observation.parser_version` |

A better parser can re-read the original at any time. Nothing about parsing is
irreversible.

## Versioning

Three versions are recorded so that a change in output can be attributed:

| Version | Where | Why |
|---|---|---|
| Parser | `obs.observation.parser_version`, on every run | a human-readable version, not only a commit |
| Code revision | `meta.ingestion_run.code_revision` | the exact commit, as well |
| Schema | `meta.schema_migration` | which migrations were applied |
| Mapping | `source.field_mapping.version` | mappings are superseded, never edited |

Mapping versioning matters more than it looks: without it, improving a
field-to-metric mapping would silently rewrite decades of values with no record
that anything changed.

## Status, not confidence

`obs.parse_status` is an enumerated status, not a number:

| Status | Meaning |
|---|---|
| `parsed_exact` | a clean value, no qualifiers |
| `parsed_with_qualifier` | carried an estimate marker, a note or a year |
| `parsed_partial` | some of a compound field recovered; the rest is in the raw text |
| `unparsed` | nothing was invented; `missing_reason` says why |

A calibrated numeric confidence would be better if it were calibrated. An
uncalibrated one — `0.873` — is a decoration that invites arithmetic it cannot
support.

## Citation

`source.citation` renders a reference per release, so a generated profile can
attribute every published value without the presentation layer knowing how to
format one.
