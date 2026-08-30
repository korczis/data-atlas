# ADR-0007 — Opaque entity keys; codes are temporal attributes

**Status**: accepted

## Context

The corpus spans 1990 to 2025. In that window Czechoslovakia dissolved, the USSR
dissolved, Germany reunified, Yugoslavia broke up in stages, and dozens of
entities were renamed. It also contains oceans, Antarctica, disputed territories,
dependencies, and a "World" aggregate — none of which is a country.

ISO 3166-1 alpha-2 reassigns retired codes. `CS` was Czechoslovakia and later
Serbia and Montenegro.

## Decision

`core.entity` has an opaque `bigint` key and a human-readable slug. Everything
that can change is a related row with a validity period: names, external
identifiers, relations, geometry links.

`core.entity_type` is a reference table, not an enum, and nothing in the schema
assumes statehood.

Two exclusion constraints carry the weight:

- one preferred name per entity, kind and language *at any instant* — which
  permits a rename and forbids ambiguity;
- one entity per (scheme, code) *at any instant* — which permits reassignment
  across time and forbids simultaneous ambiguity.

Resolution is a decision table, `core.entity_resolution`, keyed per dataset and
source key. Fuzzy matching may propose; a CHECK constraint forbids a fuzzy match
being accepted.

## Consequences

- A code lookup must filter on a period, or it will legitimately match more than
  one entity. `api.entity_identifier` documents this.
- Observations reference `entity_id`, so a code change orphans nothing.
- `bootstrap-entities` creates one entity per source entry typed `unclassified`.
  It asserts the entry exists and nothing about what kind of thing it is —
  defaulting to `sovereign_state` would have classified Antarctica and the
  Indian Ocean as countries.

## What would reverse this

Nothing foreseeable. This is the part of the schema most directly justified by
the corpus itself.
