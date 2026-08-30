# Entity identity

## The problem, concretely

Between 1990 and 2025 this corpus contains: Czechoslovakia dissolving into two
states, the USSR dissolving into fifteen, Germany reunifying, Yugoslavia
breaking up in stages, Zaire becoming the Democratic Republic of the Congo, and
Burma appearing as Myanmar. It also contains oceans, Antarctica, disputed
territories, dependencies and a "World" aggregate — none of which is a country.

And ISO reassigns codes. `CS` denoted Czechoslovakia; after 1993 it denoted
Serbia and Montenegro.

Any model that keys a country on its present ISO code must therefore either lose
history or corrupt it.

## The model

```
core.entity              opaque bigint key + slug + existence period
  ├─ entity_type         reference table, not an enum
  ├─ entity_name         name × kind × language × validity period
  ├─ entity_identifier   scheme × value × validity period × status
  └─ entity_relation     subject → object × type × validity period
```

Nothing that can change is on `core.entity`. Everything that can change is a
related row with a period.

## The two constraints that carry the weight

**One preferred name at a time**

```sql
EXCLUDE USING gist (entity_id WITH =, name_kind_id WITH =,
                    language_tag WITH =, validity WITH &&)
WHERE (is_preferred)
```

Temporal, not absolute. Two preferred canonical English names are fine if their
periods do not overlap — which is exactly what a rename is. Drop the range term
and renaming becomes impossible; drop the equality terms and a native name
cannot coexist with an English one.

**A code denotes one entity at a time**

```sql
EXCLUDE USING gist (identifier_scheme_id WITH =, value WITH =, validity WITH &&)
WHERE (status <> 'erroneous')
```

`CS` may be Czechoslovakia until 1993 and Serbia and Montenegro after. It may
not be both at once. Recording a source's *mistake* is still possible via
`status = 'erroneous'`, which is excluded so an error cannot collide with truth.

Both need `btree_gist`, which is why that extension is required rather than
recommended: mixing `=` on scalars with `&&` on a range is not otherwise
expressible.

Consequence for consumers: **a code lookup must filter on a period**, or it will
legitimately match more than one entity. `api.entity_identifier` says so.

## Resolution

`core.entity_resolution` maps a source's own key to an entity, once per
(dataset, source key) rather than once per record — so a decision applies to
every edition and changing it is a single auditable edit.

Evidence, strongest first:

1. **identifier match** — the source key matches a recorded code, with periods
   overlapping the editions it appears in. Deterministic; accepted.
2. **exact name match** — the heading matches exactly one recorded name, within
   its validity period. Accepted, with the matched name as evidence.
3. **nothing** — unresolved, and it stays that way.

There is no fourth rule. `pg_trgm` can rank candidates for a human, and a CHECK
constraint forbids a fuzzy match being accepted:

```sql
CHECK (NOT (status = 'accepted' AND method = 'fuzzy_candidate'))
```

"Congo" is the case that settles it: in this corpus it can mean either republic
depending on edition, and picking one is not resolution, it is fabrication. An
unresolved record keeps every raw field value and becomes loadable the moment
someone decides — no bytes are re-read.

## Bootstrapping

`just wh-load --bootstrap-entities` creates one entity per unresolved source
entry, typed **`unclassified`**.

What it asserts: *this source has a distinct entry with this identifier, and
called it this.* That is a restatement of the source.

What it deliberately does not assert:

- **a kind** — the Factbook does not reliably say whether an entry is a
  sovereign state, a dependency, an ocean or a disputed territory. Defaulting to
  `sovereign_state` would have classified Antarctica and the Indian Ocean as
  countries;
- **an existence period** — left unbounded rather than inferred from which
  editions mention it;
- **identity across sources** — one entity per source key. A future Eurostat
  adapter that also has Czechia produces a separate entity until someone merges
  them, and that merge is the interesting decision.

Identifiers created this way are `status = 'provisional'`. The `unclassified`
type is deliberately uncomfortable: it appears in `api.entity` and in the
coverage report, and reads as unfinished work because it is.

## Curated entities

Twelve entities are seeded by migration with real types, names and codes:
Czechoslovakia, the USSR, Yugoslavia, East Germany, their successors, and a few
neighbours. Succession *relations* are seeded for three of them — Czechoslovakia
splitting, the USSR being succeeded by Russia, and East Germany merging into
Germany. Yugoslavia is seeded as an entity with its historical ISO code but
**no** succession relation, because its break-up was staged over a decade and
recording it needs evidence this corpus has not yet been read for. They exist to make the succession model testable and to
demonstrate the `CS` reassignment case. They are not an attempt to enumerate the
world; the rest arrives through bootstrap and, eventually, curation.
