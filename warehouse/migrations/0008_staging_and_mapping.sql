-- 0008_staging_and_mapping — the source-shaped landing zone, and the bridge out of it.
--
-- Two halves with opposite obligations.
--
-- `staging_cwf` is allowed to look like the CIA World Factbook, because that is
-- its job: land the source losslessly, in the source's own shape, before any
-- interpretation. It is the only schema in this database permitted to be
-- source-specific, and nothing outside the Factbook adapter may read it. §9.
--
-- `source.field_mapping` is the bridge. It is source-neutral in shape and
-- versioned, because a mapping from a raw field name to a canonical metric is a
-- decision that will be revised, and revising it must not silently rewrite
-- history. §24, §116.

-- ── staging ──────────────────────────────────────────────────────────────────
-- Layer B of the coverage ladder in §105: 100% structured staging, no losses,
-- no judgements. Every field of every record of every edition arrives here
-- whether or not a canonical mapping for it exists.

CREATE TABLE staging_cwf.entry (
    entry_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    artifact_id     bigint NOT NULL
                    REFERENCES source.artifact (artifact_id) ON DELETE CASCADE,
    ingestion_run_id bigint NOT NULL
                    REFERENCES meta.ingestion_run (ingestion_run_id) ON DELETE RESTRICT,
    edition_year    ref.publication_year NOT NULL,
    member_path     text NOT NULL,
    source_key      text NOT NULL,
    source_name     text NOT NULL,
    ordinal         integer NOT NULL DEFAULT 0,
    parser_family   text NOT NULL,
    CONSTRAINT staging_entry_unique UNIQUE (artifact_id, source_key)
);
COMMENT ON TABLE staging_cwf.entry IS
  'One country or territory entry as found in one artifact, before any entity resolution. Keyed by the source''s own identifier so that re-running the parser over the same artifact updates rather than duplicates. Cascades from the artifact: staging is derived data and rebuilding it from bytes is always possible.';
COMMENT ON COLUMN staging_cwf.entry.source_name IS
  'The heading the source used for this entry — "Congo, Democratic Republic of the", "Korea, South". Preserved exactly, including the source''s inverted word order, because it is the string entity resolution has to work from.';

CREATE TABLE staging_cwf.entry_field (
    entry_field_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entry_id        bigint NOT NULL
                    REFERENCES staging_cwf.entry (entry_id) ON DELETE CASCADE,
    section_name    text NOT NULL DEFAULT '',
    field_name      text NOT NULL,
    subfield_name   text NOT NULL DEFAULT '',
    ordinal         integer NOT NULL DEFAULT 0,
    raw_text        text NOT NULL,
    raw_markup      text,
    CONSTRAINT staging_entry_field_unique
        UNIQUE (entry_id, section_name, field_name, subfield_name, ordinal)
);
COMMENT ON TABLE staging_cwf.entry_field IS
  'One field of one entry, verbatim. The Factbook nests: "Population" has subfields in later editions and is a bare value in earlier ones, so subfield_name is present and often empty rather than the structure being flattened or forced. Layer A and B of §105 meet here — nothing has been interpreted yet.';
COMMENT ON COLUMN staging_cwf.entry_field.subfield_name IS
  'The nested label where the source nests, empty where it does not. Keeping the two levels apart is what later lets "Age structure / 0-14 years" map to a different metric than "Age structure" as a whole.';

CREATE INDEX staging_entry_field_entry_idx ON staging_cwf.entry_field (entry_id);
CREATE INDEX staging_entry_field_name_idx
    ON staging_cwf.entry_field (section_name, field_name, subfield_name);
COMMENT ON INDEX staging_cwf.staging_entry_field_name_idx IS
  'Supports profiling: "every distinct field name, and how many rows carry it". The query that builds source.field_definition and the field-evolution report, run over the whole corpus rather than one entry.';

CREATE INDEX staging_entry_artifact_idx ON staging_cwf.entry (artifact_id);

-- ── field mapping ────────────────────────────────────────────────────────────

CREATE TABLE source.field_mapping (
    field_mapping_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id      bigint NOT NULL
                    REFERENCES source.dataset (dataset_id) ON DELETE RESTRICT,
    section_pattern text NOT NULL DEFAULT '',
    field_pattern   text NOT NULL,
    subfield_pattern text NOT NULL DEFAULT '',
    metric_id       integer REFERENCES ref.metric (metric_id) ON DELETE RESTRICT,
    category_scheme_id integer
                    REFERENCES ref.category_scheme (category_scheme_id) ON DELETE RESTRICT,
    target_kind     text NOT NULL,
    transform       text NOT NULL DEFAULT 'scalar',
    default_unit_id integer REFERENCES ref.unit (unit_id) ON DELETE RESTRICT,

    -- versioning: a mapping is valid for a span of editions and a version of
    -- itself, so reprocessing an old edition uses the mapping that was in force
    -- rather than today's.
    version         integer NOT NULL DEFAULT 1,
    valid_from_year ref.publication_year,
    valid_to_year   ref.publication_year,

    status          meta.mapping_status NOT NULL DEFAULT 'proposed',
    method          text NOT NULL DEFAULT 'curated',
    evidence        text NOT NULL DEFAULT '',
    decided_by      text,
    decided_at      timestamptz,
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT field_mapping_unique
        UNIQUE (dataset_id, section_pattern, field_pattern, subfield_pattern, version),
    CONSTRAINT field_mapping_target_kind_known
        CHECK (target_kind IN ('observation', 'composition', 'bilateral', 'narrative',
                               'coordinate', 'rank', 'ignore')),
    CONSTRAINT field_mapping_year_span_ordered
        CHECK (valid_to_year IS NULL OR valid_from_year IS NULL
               OR valid_to_year >= valid_from_year),
    -- A mapping that produces an observation must say which metric; one that
    -- produces a composition must say which classification. Neither can be
    -- inferred later without guessing.
    CONSTRAINT field_mapping_observation_needs_metric
        CHECK (target_kind <> 'observation' OR metric_id IS NOT NULL),
    CONSTRAINT field_mapping_composition_needs_scheme
        CHECK (target_kind <> 'composition'
               OR (metric_id IS NOT NULL AND category_scheme_id IS NOT NULL)),
    CONSTRAINT field_mapping_method_known
        CHECK (method IN ('curated', 'exact_name', 'alias', 'fuzzy_candidate')),
    -- The same rule as entity resolution: similarity proposes, it never confirms.
    CONSTRAINT field_mapping_fuzzy_is_never_self_accepted
        CHECK (NOT (status = 'accepted' AND method = 'fuzzy_candidate'))
);
COMMENT ON TABLE source.field_mapping IS
  'The versioned bridge from a source''s own field names to canonical metrics. Separate from ref.metric so that a source renaming a field changes a mapping, not a metric, and separate from the parser so that a mapping change is data rather than code. Over thirty-six editions the Factbook renamed, split and redefined fields repeatedly; this table is where that history is absorbed. §24.';
COMMENT ON COLUMN source.field_mapping.version IS
  'Mappings are superseded, not edited. Reprocessing an edition therefore reproduces what it produced before unless a new version was deliberately introduced — without this, improving a mapping would silently rewrite decades of values with no record that anything changed. §116.';
COMMENT ON COLUMN source.field_mapping.valid_from_year IS
  'Edition range this mapping applies to. Necessary because the same field name does not always mean the same thing: a field''s definition can change under a constant label, and mapping it uniformly across all editions would merge two different measurements.';
COMMENT ON COLUMN source.field_mapping.target_kind IS
  '''ignore'' is a first-class outcome: a deliberate decision that a field carries no canonical value, recorded so that it is distinguishable from a field nobody has looked at yet. Unmapped and deliberately-unmapped are different states and the coverage report reports them separately. §105.';
COMMENT ON COLUMN source.field_mapping.transform IS
  'Which parsing strategy the loader applies: a plain scalar, a quantity with unit, a share list, a partner list, a coordinate pair. Names a parser routine rather than containing executable logic — transformation code lives in Python, not in this column.';

CREATE INDEX field_mapping_lookup_idx
    ON source.field_mapping (dataset_id, field_pattern)
    WHERE status = 'accepted';
COMMENT ON INDEX source.field_mapping_lookup_idx IS
  'Partial index over accepted mappings only, which is the set the loader consults. Proposed and rejected rows are numerous during curation and irrelevant at load time, so keeping them out of the index keeps the hot lookup small.';

-- ── conflicts between sources ────────────────────────────────────────────────

CREATE TABLE derived.conflict (
    conflict_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    metric_id       integer NOT NULL
                    REFERENCES ref.metric (metric_id) ON DELETE RESTRICT,
    reference_period daterange NOT NULL,
    claim_count     integer NOT NULL,
    distinct_values integer NOT NULL,
    spread_ratio    numeric,
    detected_at     timestamptz NOT NULL DEFAULT now(),
    resolution_note text NOT NULL DEFAULT '',
    CONSTRAINT conflict_unique UNIQUE (entity_id, metric_id, reference_period),
    CONSTRAINT conflict_counts_sane
        CHECK (claim_count >= distinct_values AND distinct_values >= 1)
);
COMMENT ON TABLE derived.conflict IS
  'A detected disagreement: several source claims about the same entity, metric and period that do not agree. Recorded rather than resolved — the canonical layer keeps every claim, and choosing between them is a separate act with its own record. Disagreement between the CIA, Eurostat and a national statistical office is expected and is information, not corruption. §55.';
COMMENT ON COLUMN derived.conflict.spread_ratio IS
  'Largest claimed value divided by smallest, for numeric metrics. A cheap triage signal: a ratio near 1 is rounding, a ratio near 1000 is usually a unit-parsing bug in one of the claims.';

CREATE TABLE derived.preferred_value (
    preferred_value_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    metric_id       integer NOT NULL
                    REFERENCES ref.metric (metric_id) ON DELETE RESTRICT,
    reference_period daterange NOT NULL,
    observation_id  bigint REFERENCES obs.observation (observation_id) ON DELETE RESTRICT,
    selection_rule  text NOT NULL,
    rule_version    integer NOT NULL DEFAULT 1,
    status          derived.derivation_status NOT NULL DEFAULT 'active',
    generated_at    timestamptz NOT NULL DEFAULT now(),
    rationale       text NOT NULL DEFAULT '',
    CONSTRAINT preferred_value_unique_active
        UNIQUE (entity_id, metric_id, reference_period, rule_version)
);
COMMENT ON TABLE derived.preferred_value IS
  'This platform''s choice of which claim to publish, kept strictly apart from the claims themselves. A preferred value points at the observation it selected and names the rule that selected it, so a generated profile can always be traced back through the choice to the evidence. Nothing here overwrites a source claim. §55, §56.';
COMMENT ON COLUMN derived.preferred_value.selection_rule IS
  'The named rule applied, such as ''most_recent_publication'' or ''source_priority''. Versioned alongside, so re-deriving under a changed rule produces a new row rather than mutating the old decision.';

CREATE TABLE derived.derivation_input (
    derivation_input_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    preferred_value_id bigint NOT NULL
                    REFERENCES derived.preferred_value (preferred_value_id) ON DELETE CASCADE,
    observation_id  bigint NOT NULL
                    REFERENCES obs.observation (observation_id) ON DELETE RESTRICT,
    role            text NOT NULL DEFAULT 'candidate',
    CONSTRAINT derivation_input_unique UNIQUE (preferred_value_id, observation_id),
    CONSTRAINT derivation_input_role_known
        CHECK (role IN ('selected', 'candidate', 'rejected'))
);
COMMENT ON TABLE derived.derivation_input IS
  'Every observation that fed a derivation, including the ones not chosen. Explicit rows with real foreign keys rather than a polymorphic identifier column: lineage that cannot be joined is lineage nobody will check. Answers "what did this value depend on" without a graph database. §109.';
