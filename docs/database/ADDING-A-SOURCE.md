# Adding a source

The test of whether this generalises: a second dataset should need a manifest, a
parser and some mapping rows — and **no changes above `staging_*`**.

## The adapter contract

Every adapter provides, in order:

| Stage | Responsibility | Where |
|---|---|---|
| **discover** | what releases and artifacts exist | a manifest in `warehouse/manifests/` |
| **fetch** | get bytes, verify digests | generic; `atlasdata/fetch.py` |
| **extract** | open the container safely | in the parser |
| **parse** | bytes → `RawEntry` / `RawField`, no interpretation | `atlasdata/parsers/<family>.py` |
| **stage** | records → `staging_*` and `source.*` | generic; `atlasdata/staging.py` |
| **map** | source field names → canonical metrics | rows in `source.field_mapping` |
| **resolve** | source keys → `core.entity` | generic; `atlasdata/entity.py` |
| **load** | staging → typed observations | generic; `atlasdata/loader.py` |
| **validate** | quality checks | generic; `atlasdata/quality.py` |

Only two of those are source-specific: the manifest and the parser. Everything
else is shared, which is the point.

## Steps

**1. Write a manifest.** `warehouse/manifests/<dataset-code>.json`, schema
version 1. Every artifact needs a digest and at least one `byte_stable`
retrieval, or the manifest validator refuses it — an artifact whose digest can
never be reproduced is not verifiable.

**2. Write a parser.** One function:

```python
def parse_artifact(path: Path, *, limit_entities: int | None = None) -> ParseOutcome
```

Returns `RawEntry` objects holding `RawField` values: a section, a field name,
an optional subfield, an ordinal, and the text **exactly as published**. No
units, no numbers, no entity resolution — interpretation happens later, driven
by mappings.

Anything it cannot read goes into `ParseOutcome.failures` and becomes a
quarantine row. A parser that returns entries and drops its failures makes the
corpus look cleaner than it is.

Register it in `atlasdata/parsers/__init__.py::get_parser`.

**3. Add a staging schema** if the source's shape differs meaningfully:
`staging_<code>`, in a migration. Reusing `staging_cwf` for a non-Factbook
source would be a naming lie.

**4. Profile before mapping.** Stage first, then look at what is actually there:

```sql
SELECT field_name, section_name, edition_count, record_count, example_value
  FROM source.field_definition ORDER BY record_count DESC LIMIT 50;
```

Write mappings against the names that exist, not the names you expect. In this
corpus the same measurement appears as `Population`, `Population / total`,
`Area / total` and `Area / total area` depending on the decade.

**5. Add metrics only if genuinely new.** Reuse `ref.metric` wherever the
concept is the same — that reuse is what makes cross-source comparison possible.
A new metric is a migration, because its `value_kind` is part of the schema's
type safety.

**6. Add mappings.** Rows in `source.field_mapping`, `status = 'accepted'`,
`method = 'curated'`. `target_kind = 'ignore'` is a first-class decision and
should be used: it distinguishes a field examined and found to carry no
canonical value from one nobody has looked at.

**7. Resolve entities.** Existing entities are matched by identifier or exact
name. Genuinely new ones can be bootstrapped as `unclassified`; merging them
with entities from another source is curation, and the merge is the interesting
decision.

## Link to the catalogue

If the source is also in `data/sources/*.json`, set
`source.dataset.catalog_source_id` to that entry's `id`.

It is a **plain text pointer**, not a foreign key. The catalogue remains the
source of truth for source *discovery*; this database is the source of truth for
ingested *data*; neither is generated from the other. Changing the catalogue
schema to carry ingestion details would merge two things that should stay
separate, and would need its own ADR first.

The catalogue's own vocabularies still apply and still mean what they mean:
`access` says whether you can get in, `data` says what you can take away. A
browsable register is `search`, never `api` or `bulk` — and a source that is
`data: search` generally cannot be ingested at all, which is useful to know
before writing an adapter.

## The question to ask

For every schema change: *would this work just as well if tomorrow's dataset
came from Eurostat or a national statistical office?*

If not, either it belongs in `staging_*`, or something canonical has
accidentally been made source-specific.
