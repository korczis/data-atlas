-- 0003_core_entity — canonical identity for places.
--
-- The rule this schema exists to enforce: **an ISO code is not an identity.**
-- Codes are reassigned, retired and invented; Yugoslavia, Zaire, the USSR,
-- Czechoslovakia, Serbia and Montenegro and East Timor all appear in this
-- corpus, several of them under names and codes that no longer resolve to
-- anything. An entity therefore has an opaque surrogate key, and every external
-- code is an attribute with a validity period pointing at it.
--
-- The corpus also is not a list of countries. It contains oceans, Antarctica,
-- disputed territories, dependencies, the European Union, and a "World"
-- aggregate. Forcing those into a sovereign-state schema is how a model starts
-- lying, so `core.entity_type` is a reference table and nothing assumes
-- statehood. §168-§170.

CREATE TABLE core.entity_type (
    entity_type_id  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    is_territorial  boolean NOT NULL DEFAULT true,
    is_sovereign    boolean NOT NULL DEFAULT false,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT entity_type_code_unique UNIQUE (code)
);
COMMENT ON TABLE core.entity_type IS
  'What kind of thing an entity is. A reference table rather than an enum because this list has grown twice already while writing the schema and will grow again — supranational unions, condominiums and unrecognised states all arrive without warning. ADR-0004.';
COMMENT ON COLUMN core.entity_type.is_territorial IS
  'Whether the entity occupies definable ground. False for statistical aggregates such as "World" or "European Union" considered as a reporting unit, which must never acquire a boundary geometry by accident.';

INSERT INTO core.entity_type (code, label, is_territorial, is_sovereign, description) VALUES
  ('sovereign_state',     'Sovereign state',        true,  true,
   'A state generally recognised as sovereign at some point in its existence.'),
  ('dependency',          'Dependency',             true,  false,
   'A territory administered by another entity: overseas territories, external territories, crown dependencies.'),
  ('disputed_territory',  'Disputed territory',     true,  false,
   'Territory whose sovereignty is contested by two or more entities. Recorded as its own entity so competing claims can both be represented without either being asserted.'),
  ('autonomous_region',   'Autonomous region',      true,  false,
   'A sub-state territory with a distinct entry in the source, such as Hong Kong or Greenland.'),
  ('ocean',               'Ocean',                  true,  false,
   'An ocean or major sea given its own entry. Territorial in the sense of occupying space, never sovereign.'),
  ('uninhabited_territory','Uninhabited territory', true,  false,
   'Islands, reefs and Antarctic areas with no permanent population.'),
  ('supranational_union', 'Supranational union',    false, false,
   'A union of states reported as a unit, such as the European Union.'),
  ('world_aggregate',     'World aggregate',        false, false,
   'The "World" entry and any other whole-planet total. A statistical aggregate, not a place with a border or an ISO code. §169.'),
  ('historical_state',    'Historical state',       true,  true,
   'A sovereign state that has ceased to exist: the USSR, Yugoslavia, Czechoslovakia. Kept as a first-class entity so its observations remain attached to what actually reported them.'),
  ('other',               'Other',                  true,  false,
   'Anything the source treats as an entry that fits none of the above. Deliberately available so an unclassifiable record is typed honestly rather than forced.');

CREATE TABLE core.entity (
    entity_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type_id  integer NOT NULL
                    REFERENCES core.entity_type (entity_type_id) ON DELETE RESTRICT,
    -- A short slug for humans and command lines. Stable by policy, not by
    -- nature: if it ever has to change, the surrogate key absorbs the change and
    -- nothing that references this entity breaks. That is the whole reason the
    -- surrogate key exists.
    slug            ref.entity_code NOT NULL,
    existence       daterange NOT NULL DEFAULT daterange(NULL, NULL, '[)'),
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT entity_slug_unique UNIQUE (slug)
);
COMMENT ON TABLE core.entity IS
  'A place or reporting unit, with an opaque and permanent identity. Everything that changes about it over time — names, codes, borders, sovereignty — lives in a related table with a validity period. Observations reference entity_id and never a code, so a country that changes its ISO code does not orphan thirty years of data. §173.';
COMMENT ON COLUMN core.entity.existence IS
  'When the entity existed, as a half-open date range [start, end). An unbounded end means "still existing as far as this database knows", which is different from "will exist forever" and different from "unknown". Half-open throughout this schema so adjacent periods abut without overlapping — see docs/database/TEMPORAL-MODEL.md.';
COMMENT ON COLUMN core.entity.slug IS
  'Human-readable handle for CLI and debugging, e.g. ''czechia'', ''world'', ''yugoslavia''. Unique, but not the identity: joins use entity_id.';

CREATE INDEX entity_type_idx ON core.entity (entity_type_id);
CREATE INDEX entity_existence_idx ON core.entity USING gist (existence);
COMMENT ON INDEX core.entity_existence_idx IS
  'GiST over the existence range, supporting "which entities existed in 1991". B-tree cannot answer range containment; GiST is the index type for range overlap.';

-- ── names over time ──────────────────────────────────────────────────────────

CREATE TABLE core.name_kind (
    name_kind_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT name_kind_code_unique UNIQUE (code)
);
COMMENT ON TABLE core.name_kind IS
  'The role a name plays: conventional short form, official long form, native form, historical name, source-specific spelling, alias. Distinguishing them is what lets a search match "Burma" while a profile prints "Myanmar".';

INSERT INTO core.name_kind (code, label, description) VALUES
  ('canonical',   'Canonical',        'The name this platform prefers when it must print one.'),
  ('short',       'Conventional short','Everyday short form: "Czechia".'),
  ('long',        'Conventional long', 'Full conventional form: "the Czech Republic".'),
  ('official',    'Official',          'Official form as given by the entity itself.'),
  ('native',      'Native',            'Name in a language of the entity, in its own script.'),
  ('historical',  'Historical',        'A name used in an earlier period: "Zaire", "Burma".'),
  ('alias',       'Alias',             'An alternative form in common use, not preferred.'),
  ('source_form', 'Source form',       'Exactly how one source spelled it, kept for entity resolution and never printed.');

CREATE TABLE core.entity_name (
    entity_name_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE CASCADE,
    name_kind_id    integer NOT NULL
                    REFERENCES core.name_kind (name_kind_id) ON DELETE RESTRICT,
    name            text NOT NULL,
    -- BCP 47-ish. Not a constrained domain: robustly validating a language tag
    -- needs a registry, and a regex that accepts 'en' and 'zh-Hant' while
    -- rejecting real tags would be worse than an honest text column. §13.
    language_tag    text NOT NULL DEFAULT 'en',
    script          text,
    is_preferred    boolean NOT NULL DEFAULT false,
    validity        daterange NOT NULL DEFAULT daterange(NULL, NULL, '[)'),
    source_release_id bigint REFERENCES source.release (release_id) ON DELETE SET NULL,
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT entity_name_present CHECK (btrim(name) <> ''),

    -- At most one preferred name per entity, kind and language at any instant.
    -- Expressed as an exclusion constraint rather than a partial unique index
    -- because the conflict is temporal: two preferred names are fine if their
    -- validity periods do not overlap, which is exactly what happens when a
    -- country renames itself. Needs btree_gist to mix equality on the scalar
    -- columns with overlap on the range.
    CONSTRAINT entity_name_one_preferred_at_a_time
        EXCLUDE USING gist (entity_id WITH =, name_kind_id WITH =,
                            language_tag WITH =, validity WITH &&)
        WHERE (is_preferred)
);
COMMENT ON TABLE core.entity_name IS
  'Every name an entity has been known by, with the kind of name it is, its language, and the period it applied. Multi-row by design: "Burma" and "Myanmar" are both true, of different periods, and a corpus spanning 1990 to 2025 contains both. §15.';
COMMENT ON CONSTRAINT entity_name_one_preferred_at_a_time ON core.entity_name IS
  'Prevents two simultaneously preferred names of the same kind and language. Temporal rather than absolute: a rename is a new preferred name whose validity begins where the old one ends, and that is allowed. Without the range term this would forbid renaming; without the equality terms it would forbid a native name coexisting with an English one.';
COMMENT ON COLUMN core.entity_name.source_release_id IS
  'Which release attested this spelling, where known. ON DELETE SET NULL rather than CASCADE: the name remains true even if the release record is removed, so the fact must survive losing its citation.';

CREATE INDEX entity_name_entity_idx ON core.entity_name (entity_id);
CREATE INDEX entity_name_trgm_idx ON core.entity_name USING gin (lower(name) gin_trgm_ops);
COMMENT ON INDEX core.entity_name_trgm_idx IS
  'Trigram index over lowercased names, supporting fuzzy candidate generation during entity resolution ("Cote d''Ivoire" against "Côte d\''Ivoire"). GIN because trigram matching is a containment problem, not an ordering one. Candidates only: a trigram score never confirms an identity by itself. §81.';

-- ── external identifier schemes ──────────────────────────────────────────────

CREATE TABLE core.identifier_scheme (
    identifier_scheme_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    authority       text NOT NULL DEFAULT '',
    value_pattern   text,
    is_reassignable boolean NOT NULL DEFAULT true,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT identifier_scheme_code_unique UNIQUE (code)
);
COMMENT ON TABLE core.identifier_scheme IS
  'A namespace of external identifiers: ISO 3166-1 alpha-2, FIPS 10-4, GeoNames, Wikidata, NUTS. A table rather than an enum because every new source arrives with its own coding system and adding one must not require a type migration.';
COMMENT ON COLUMN core.identifier_scheme.is_reassignable IS
  'Whether the authority reuses retired codes for different places. True for ISO 3166-1 alpha-2, which is exactly why an ISO code cannot be a primary key: the same two letters can denote different entities in different decades.';
COMMENT ON COLUMN core.identifier_scheme.value_pattern IS
  'Optional regex describing well-formed values in this scheme, used by quality checks rather than enforced as a constraint — a malformed identifier found in a real source is a finding to record, not a row to reject.';

INSERT INTO core.identifier_scheme (code, label, authority, value_pattern, is_reassignable, description) VALUES
  ('iso3166_1_alpha2', 'ISO 3166-1 alpha-2', 'ISO', '^[A-Z]{2}$',   true,
   'Two-letter country code. Reassignable and therefore never used as identity.'),
  ('iso3166_1_alpha3', 'ISO 3166-1 alpha-3', 'ISO', '^[A-Z]{3}$',   true,
   'Three-letter country code.'),
  ('iso3166_1_numeric','ISO 3166-1 numeric', 'ISO', '^[0-9]{3}$',   true,
   'Three-digit country code.'),
  ('fips10_4',         'FIPS 10-4',          'NIST (withdrawn)', '^[A-Z]{2}$', true,
   'US federal country code, withdrawn in 2008 but used throughout the Factbook corpus as its own entry key.'),
  ('cwf_gec',          'GEC / Factbook code','CIA',  '^[a-z]{2}$',  true,
   'The two-letter code the Factbook uses in its own file names and URLs. Source-specific, hence a scheme of its own rather than a pretence of being FIPS.'),
  ('wikidata',         'Wikidata QID',       'Wikimedia', '^Q[1-9][0-9]*$', false,
   'Stable across renames and dissolutions, which makes it the best available bridge to other datasets.'),
  ('geonames',         'GeoNames ID',        'GeoNames', '^[0-9]+$', false,
   'Gazetteer identifier, useful for future geodata joins.'),
  ('nuts',             'NUTS',               'Eurostat', NULL,       true,
   'EU statistical regions. Present so a future Eurostat adapter has somewhere to put its keys without a schema change.');

CREATE TABLE core.entity_identifier (
    entity_identifier_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE CASCADE,
    identifier_scheme_id integer NOT NULL
                    REFERENCES core.identifier_scheme (identifier_scheme_id)
                    ON DELETE RESTRICT,
    value           ref.entity_code NOT NULL,
    validity        daterange NOT NULL DEFAULT daterange(NULL, NULL, '[)'),
    status          text NOT NULL DEFAULT 'current',
    source_release_id bigint REFERENCES source.release (release_id) ON DELETE SET NULL,
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT entity_identifier_status_known
        CHECK (status IN ('current', 'historical', 'provisional', 'erroneous')),

    -- One entity holds a given code in a scheme for one period at a time...
    CONSTRAINT entity_identifier_no_self_overlap
        EXCLUDE USING gist (entity_id WITH =, identifier_scheme_id WITH =,
                            value WITH =, validity WITH &&),
    -- ...and a code, while valid, denotes exactly one entity. Both directions
    -- are needed: the first stops duplicate rows, the second stops 'CS' meaning
    -- Czechoslovakia and Serbia-and-Montenegro at the same instant. Codes marked
    -- erroneous are excluded, since recording a source's mistake must not
    -- collide with the truth.
    CONSTRAINT entity_identifier_code_denotes_one_entity
        EXCLUDE USING gist (identifier_scheme_id WITH =, value WITH =, validity WITH &&)
        WHERE (status <> 'erroneous')
);
COMMENT ON TABLE core.entity_identifier IS
  'An external code for an entity, valid over a period. The corpus needs this to be temporal: ISO reassigned CS from Czechoslovakia to Serbia and Montenegro, and a model that stored one code per country would have to choose which decade to be wrong about. §14, §173.';
COMMENT ON CONSTRAINT entity_identifier_code_denotes_one_entity ON core.entity_identifier IS
  'The constraint that makes external codes safe to look up: within one scheme, one value resolves to at most one entity at any instant. Reassignment across time is permitted, simultaneous ambiguity is not.';

CREATE INDEX entity_identifier_entity_idx ON core.entity_identifier (entity_id);
CREATE INDEX entity_identifier_lookup_idx
    ON core.entity_identifier (identifier_scheme_id, value);
COMMENT ON INDEX core.entity_identifier_lookup_idx IS
  'Supports the hot path of entity resolution: given a scheme and a code from a source record, find the entity. Equality on both columns; B-tree.';

-- ── relations between entities ───────────────────────────────────────────────

CREATE TABLE core.entity_relation_type (
    entity_relation_type_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    is_symmetric    boolean NOT NULL DEFAULT false,
    inverse_code    ref.entity_code,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT entity_relation_type_code_unique UNIQUE (code)
);
COMMENT ON TABLE core.entity_relation_type IS
  'The vocabulary of relations between entities: succession, containment, administration, claims. Kept open because political relations are more varied than any fixed list, and because asserting one requires evidence this platform may not yet have.';

INSERT INTO core.entity_relation_type (code, label, is_symmetric, inverse_code, description) VALUES
  ('succeeded_by',   'Succeeded by',    false, 'preceded_by',
   'The subject ceased to exist and the object continued or replaced it.'),
  ('preceded_by',    'Preceded by',     false, 'succeeded_by', 'Inverse of succeeded_by.'),
  ('split_from',     'Split from',      false, 'split_into',
   'The subject came into being by separating from the object.'),
  ('split_into',     'Split into',      false, 'split_from',  'Inverse of split_from.'),
  ('merged_into',    'Merged into',     false, 'formed_from',
   'The subject ceased to exist by joining the object.'),
  ('formed_from',    'Formed from',     false, 'merged_into', 'Inverse of merged_into.'),
  ('part_of',        'Part of',         false, 'contains',
   'Administrative or statistical containment for the stated period.'),
  ('contains',       'Contains',        false, 'part_of',     'Inverse of part_of.'),
  ('administered_by','Administered by', false, 'administers',
   'The object exercises administration over the subject without necessarily claiming sovereignty.'),
  ('administers',    'Administers',     false, 'administered_by', 'Inverse of administered_by.'),
  ('sovereign_over', 'Sovereign over',  false, 'under_sovereignty_of',
   'The subject holds recognised sovereignty over the object.'),
  ('under_sovereignty_of','Under sovereignty of', false, 'sovereign_over',
   'Inverse of sovereign_over.'),
  ('claimed_by',     'Claimed by',      false, 'claims',
   'The object asserts a claim over the subject. Recording a claim asserts that the claim exists, not that it is valid.'),
  ('claims',         'Claims',          false, 'claimed_by',  'Inverse of claimed_by.'),
  ('borders',        'Borders',         true,  'borders',
   'Shares a land boundary. Symmetric.');

CREATE TABLE core.entity_relation (
    entity_relation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject_entity_id bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE CASCADE,
    object_entity_id bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE CASCADE,
    entity_relation_type_id integer NOT NULL
                    REFERENCES core.entity_relation_type (entity_relation_type_id)
                    ON DELETE RESTRICT,
    validity        daterange NOT NULL DEFAULT daterange(NULL, NULL, '[)'),
    source_release_id bigint REFERENCES source.release (release_id) ON DELETE SET NULL,
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT entity_relation_not_reflexive
        CHECK (subject_entity_id <> object_entity_id),
    CONSTRAINT entity_relation_unique
        UNIQUE (subject_entity_id, object_entity_id, entity_relation_type_id, validity)
);
COMMENT ON TABLE core.entity_relation IS
  'A directed, time-bounded relation between two entities. A graph rather than a parent pointer: a territory can simultaneously be administered by one state, claimed by another and contained in a statistical region, and a single parent_id column cannot express that without lying. §172.';
COMMENT ON CONSTRAINT entity_relation_not_reflexive ON core.entity_relation IS
  'An entity cannot relate to itself. Catches the commonest resolution bug, where an unresolved name is mapped to the entity that is already the subject.';

CREATE INDEX entity_relation_subject_idx ON core.entity_relation (subject_entity_id);
CREATE INDEX entity_relation_object_idx ON core.entity_relation (object_entity_id);

-- ── the deferred link from source.record ─────────────────────────────────────
-- Declared here because core.entity did not exist in 0002. The dependency runs
-- source -> core in the schema and core -> source in the migration order, which
-- is normal for mutually referencing registries.

ALTER TABLE source.record
    ADD CONSTRAINT record_entity_fk
    FOREIGN KEY (entity_id) REFERENCES core.entity (entity_id) ON DELETE RESTRICT;
COMMENT ON CONSTRAINT record_entity_fk ON source.record IS
  'ON DELETE RESTRICT: an entity with source records attached cannot be deleted. Removing it would silently detach evidence from the thing it is evidence about, which is the failure this whole schema is built to prevent.';

CREATE TABLE core.entity_resolution (
    entity_resolution_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id      bigint NOT NULL
                    REFERENCES source.dataset (dataset_id) ON DELETE RESTRICT,
    source_key      text NOT NULL,
    source_label    text NOT NULL DEFAULT '',
    entity_id       bigint REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    status          meta.mapping_status NOT NULL DEFAULT 'proposed',
    method          text NOT NULL,
    evidence        text NOT NULL DEFAULT '',
    decided_by      text,
    decided_at      timestamptz,
    first_seen_year ref.publication_year,
    last_seen_year  ref.publication_year,
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT entity_resolution_unique UNIQUE (dataset_id, source_key),
    CONSTRAINT entity_resolution_method_known
        CHECK (method IN ('exact_code', 'exact_name', 'curated', 'alias',
                          'fuzzy_candidate', 'unresolved')),
    CONSTRAINT entity_resolution_accepted_has_entity
        CHECK (status <> 'accepted' OR entity_id IS NOT NULL),
    CONSTRAINT entity_resolution_fuzzy_is_never_self_accepted
        CHECK (NOT (status = 'accepted' AND method = 'fuzzy_candidate'))
);
COMMENT ON TABLE core.entity_resolution IS
  'The decision table mapping a source''s own key for a place onto a canonical entity, one row per distinct key per dataset. Separate from source.record so that a decision is made once and applied to every edition, and so that changing a decision is an auditable edit rather than a bulk update of thirty years of records. §82.';
COMMENT ON CONSTRAINT entity_resolution_fuzzy_is_never_self_accepted ON core.entity_resolution IS
  'Trigram similarity may propose a match; it may never be the reason one is accepted. Promoting a fuzzy candidate requires re-recording it under a method that reflects the actual evidence — a code match, an alias, or a human decision. Enforced here rather than trusted to the loader. §24, §81.';
COMMENT ON COLUMN core.entity_resolution.evidence IS
  'Why this mapping is believed: the code that matched, the alias relied on, or the reasoning a curator gave. An accepted mapping with empty evidence is a quality finding, not a schema error.';
