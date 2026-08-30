-- 0005_observations — typed, provenance-bearing claims.
--
-- Grain of obs.observation:
--   One row represents one value for one metric, about one entity, over one
--   reference period, as reported by one source release, produced by one parser
--   version.
--
-- That grain is the reason there is no unique constraint on
-- (entity, metric, period): two releases legitimately disagree, and the same
-- release can revise. Conflict is data here, not an error — resolution happens
-- in `derived`, never by overwriting. §55.
--
-- The typing mechanism, which is the point of this file:
--
--   ref.metric declares value_kind and exposes UNIQUE (metric_id, value_kind).
--   obs.observation carries value_kind and references that pair, so an
--     observation's type is dictated by its metric.
--   obs.observation also exposes UNIQUE (observation_id, value_kind).
--   Each subtype table has a GENERATED value_kind column fixed to its own kind
--     and references that pair, so a numeric row can only ever attach to an
--     observation whose metric is numeric.
--
-- Net effect: `population = 'Tuesday'` is rejected by the database. Not by a
-- validator that someone might skip. §25.

CREATE TABLE obs.observation (
    observation_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- what it is about
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    metric_id       integer NOT NULL
                    REFERENCES ref.metric (metric_id) ON DELETE RESTRICT,
    value_kind      ref.value_kind NOT NULL,

    -- when it is about, and when it was said
    reference_period daterange NOT NULL,
    period_precision text NOT NULL DEFAULT 'year',
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    recorded_at     timestamptz NOT NULL DEFAULT now(),

    -- where it came from, precisely
    field_value_id  bigint REFERENCES source.field_value (field_value_id) ON DELETE RESTRICT,
    ingestion_run_id bigint,      -- FK added in 0008, after meta.ingestion_run exists
    parser_version  text NOT NULL,

    -- how well it was understood
    parse_status    obs.parse_status NOT NULL,
    missing_reason  obs.missing_reason,
    is_estimate     boolean NOT NULL DEFAULT false,
    qualifier_text  text NOT NULL DEFAULT '',

    -- units as the source gave them
    unit_id         integer REFERENCES ref.unit (unit_id) ON DELETE RESTRICT,
    currency_id     integer REFERENCES ref.currency (currency_id) ON DELETE RESTRICT,
    price_basis     text,

    notes           text NOT NULL DEFAULT '',

    CONSTRAINT observation_metric_value_kind_fk
        FOREIGN KEY (metric_id, value_kind)
        REFERENCES ref.metric (metric_id, value_kind) ON DELETE RESTRICT,
    CONSTRAINT observation_id_value_kind_unique UNIQUE (observation_id, value_kind),

    CONSTRAINT observation_period_precision_known
        CHECK (period_precision IN ('day', 'month', 'quarter', 'year', 'multi_year', 'unknown')),
    CONSTRAINT observation_period_not_empty
        CHECK (NOT isempty(reference_period)),
    CONSTRAINT observation_price_basis_known
        CHECK (price_basis IS NULL OR price_basis IN ('nominal', 'ppp', 'constant', 'official_exchange')),
    -- A monetary figure without a currency is not a monetary figure.
    CONSTRAINT observation_currency_needs_price_basis
        CHECK (currency_id IS NULL OR price_basis IS NOT NULL),
    -- An unparsed observation must say why there is no value; a parsed one must
    -- not claim to be missing. This is what stops NULL from meaning six things.
    CONSTRAINT observation_missing_reason_iff_unparsed
        CHECK ((parse_status = 'unparsed') = (missing_reason IS NOT NULL)),
    -- Provenance is not optional. An observation with no field_value must say in
    -- its notes what produced it; derived values live in `derived`, not here.
    CONSTRAINT observation_has_provenance
        CHECK (field_value_id IS NOT NULL OR btrim(notes) <> '')
);
COMMENT ON TABLE obs.observation IS
  'One source''s claim about one metric for one entity over one reference period. The shared header of a disjoint subtype hierarchy: the value itself lives in exactly one of the obs.*_observation tables, selected by value_kind. Deliberately allows contradiction — two releases reporting different populations for the same country-year are two valid rows, and choosing between them is a separate, recorded act. §55.';
COMMENT ON COLUMN obs.observation.reference_period IS
  'The period the value describes, as a half-open date range. NOT the edition year: the 2025 Factbook reports population "2024 est.", which is reference_period [2024-01-01,2025-01-01) on a release whose edition_year is 2025. Conflating the two is the single most common way a historical dataset becomes quietly wrong. §16.';
COMMENT ON COLUMN obs.observation.period_precision IS
  'How precisely the source specified the period. ''year'' is by far the commonest here; ''unknown'' is used when a figure carries no date at all, in which case reference_period is the edition year and this column is what stops that inference from being mistaken for the source''s own statement.';
COMMENT ON COLUMN obs.observation.recorded_at IS
  'When this platform stored the row: system time, the third of the three clocks. Publication time comes from source.release, reference time from reference_period. docs/database/TEMPORAL-MODEL.md sets out all three.';
COMMENT ON COLUMN obs.observation.parser_version IS
  'Version of the parser that produced this value, as a human-readable version rather than only a commit hash. Required so that reprocessing which changes historical values can be attributed to a specific parser change. §115.';
COMMENT ON COLUMN obs.observation.is_estimate IS
  'True when the source marked the figure as an estimate ("2024 est."). A property of the claim, preserved because dropping it silently converts an estimate into a measurement. §53.';
COMMENT ON COLUMN obs.observation.qualifier_text IS
  'Any qualifying words the source attached that are not captured by is_estimate — "approximately", "provisional", a parenthetical note. Kept verbatim so nothing the publisher hedged is presented as unhedged.';
COMMENT ON COLUMN obs.observation.unit_id IS
  'The unit as the source expressed it, not a canonical unit. Conversion is a query or a derived value; rewriting the stored figure into different units would destroy the published number. §52.';
COMMENT ON COLUMN obs.observation.price_basis IS
  'For monetary values: nominal, purchasing-power-parity, constant prices, or official exchange rate. GDP is not one number — PPP and nominal GDP differ by a factor of several for many countries, and a schema that stored "GDP" without this would be averaging incompatible figures. §34.';
COMMENT ON CONSTRAINT observation_missing_reason_iff_unparsed ON obs.observation IS
  'Biconditional on purpose. It forces every absent value to state which kind of absence it is — not applicable, not reported, unknown, negligible, suppressed, or a parse failure — and forbids a successfully parsed value from also claiming to be missing. This is the constraint that keeps NULL from meaning everything. §76, §150.';

CREATE INDEX observation_entity_metric_period_idx
    ON obs.observation (entity_id, metric_id, reference_period);
COMMENT ON INDEX obs.observation_entity_metric_period_idx IS
  'The primary access path: one country''s history of one metric, and the country-profile query that asks for many metrics at one entity. Leading with entity_id because every user-facing query is scoped to a place first.';

CREATE INDEX observation_metric_period_idx
    ON obs.observation (metric_id, reference_period);
COMMENT ON INDEX obs.observation_metric_period_idx IS
  'Supports cross-entity comparison: "every country''s population in 2010", and the ranking queries in docs/database/PERFORMANCE.md. Complements rather than duplicates the entity-leading index, which cannot serve a metric-only predicate efficiently.';

CREATE INDEX observation_release_idx ON obs.observation (release_id);
CREATE INDEX observation_field_value_idx ON obs.observation (field_value_id);
COMMENT ON INDEX obs.observation_field_value_idx IS
  'Walks provenance in the other direction: from a raw field value to whatever was made of it. Used by the reconciliation report and when auditing a parser change.';

CREATE INDEX observation_period_gist_idx ON obs.observation USING gist (reference_period);
COMMENT ON INDEX obs.observation_period_gist_idx IS
  'GiST over the reference period for containment queries — "everything describing any part of 1995". B-tree on a range answers equality and ordering but not overlap.';

-- ── typed subtypes ───────────────────────────────────────────────────────────
-- Each holds the value for exactly one value_kind. The generated column plus the
-- composite foreign key is what makes the hierarchy disjoint and type-correct.

CREATE TABLE obs.integer_observation (
    observation_id  bigint PRIMARY KEY
                    REFERENCES obs.observation (observation_id) ON DELETE CASCADE,
    value_kind      ref.value_kind NOT NULL GENERATED ALWAYS AS ('integer') STORED,
    value           bigint NOT NULL,
    CONSTRAINT integer_observation_kind_fk
        FOREIGN KEY (observation_id, value_kind)
        REFERENCES obs.observation (observation_id, value_kind) ON DELETE CASCADE
);
COMMENT ON TABLE obs.integer_observation IS
  'Whole-number values: population counts, numbers of airports, kilometres of railway. The value_kind column is generated and constant, so the composite foreign key can only be satisfied when the parent observation''s metric is declared integer.';
COMMENT ON COLUMN obs.integer_observation.value_kind IS
  'Always ''integer''. Exists solely as the second column of the composite foreign key that enforces subtype correctness; it is not data.';

CREATE TABLE obs.numeric_observation (
    observation_id  bigint PRIMARY KEY
                    REFERENCES obs.observation (observation_id) ON DELETE CASCADE,
    value_kind      ref.value_kind NOT NULL GENERATED ALWAYS AS ('numeric') STORED,
    value           numeric NOT NULL,
    CONSTRAINT numeric_observation_kind_fk
        FOREIGN KEY (observation_id, value_kind)
        REFERENCES obs.observation (observation_id, value_kind) ON DELETE CASCADE
);
COMMENT ON TABLE obs.numeric_observation IS
  'Exact decimal values: monetary amounts, rates, percentages, areas. numeric rather than double precision throughout, because these are published decimal figures and binary floating point cannot represent them exactly. double precision is reserved for coordinates and geometry, where it is the correct type. §51.';

CREATE TABLE obs.boolean_observation (
    observation_id  bigint PRIMARY KEY
                    REFERENCES obs.observation (observation_id) ON DELETE CASCADE,
    value_kind      ref.value_kind NOT NULL GENERATED ALWAYS AS ('boolean') STORED,
    value           boolean NOT NULL,
    CONSTRAINT boolean_observation_kind_fk
        FOREIGN KEY (observation_id, value_kind)
        REFERENCES obs.observation (observation_id, value_kind) ON DELETE CASCADE
);
COMMENT ON TABLE obs.boolean_observation IS
  'Yes/no facts, such as whether an entity is landlocked. Rare, and kept typed rather than encoded as an integer so that no query has to remember which way round 1 means.';

CREATE TABLE obs.categorical_observation (
    observation_id  bigint PRIMARY KEY
                    REFERENCES obs.observation (observation_id) ON DELETE CASCADE,
    value_kind      ref.value_kind NOT NULL GENERATED ALWAYS AS ('categorical') STORED,
    category_id     bigint NOT NULL
                    REFERENCES ref.category (category_id) ON DELETE RESTRICT,
    CONSTRAINT categorical_observation_kind_fk
        FOREIGN KEY (observation_id, value_kind)
        REFERENCES obs.observation (observation_id, value_kind) ON DELETE CASCADE
);
COMMENT ON TABLE obs.categorical_observation IS
  'A value drawn from a controlled vocabulary rather than free text — a government type, a predominant religion. Points at ref.category so the set of possible answers is queryable and shared, instead of being a string that differs by a comma between editions.';

CREATE TABLE obs.text_observation (
    observation_id  bigint PRIMARY KEY
                    REFERENCES obs.observation (observation_id) ON DELETE CASCADE,
    value_kind      ref.value_kind NOT NULL GENERATED ALWAYS AS ('text') STORED,
    value           text NOT NULL,
    CONSTRAINT text_observation_kind_fk
        FOREIGN KEY (observation_id, value_kind)
        REFERENCES obs.observation (observation_id, value_kind) ON DELETE CASCADE
);
COMMENT ON TABLE obs.text_observation IS
  'Short free-text values that are genuinely the fact — a capital city name, a currency name. Long narrative belongs in content.*, not here: the distinction is whether the text is a value or a passage. §38.';

-- ── every observation must have exactly one value row ────────────────────────
-- A foreign key can require that a subtype row points at a valid parent; it
-- cannot require that a parent has a child. That gap is closed with a deferred
-- constraint trigger, checked at commit so a normal insert order (header, then
-- value) is legal within the transaction.

CREATE FUNCTION obs.assert_observation_has_value() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    found integer;
BEGIN
    SELECT count(*) INTO found FROM (
        SELECT 1 FROM obs.integer_observation     WHERE observation_id = NEW.observation_id
        UNION ALL
        SELECT 1 FROM obs.numeric_observation     WHERE observation_id = NEW.observation_id
        UNION ALL
        SELECT 1 FROM obs.boolean_observation     WHERE observation_id = NEW.observation_id
        UNION ALL
        SELECT 1 FROM obs.categorical_observation WHERE observation_id = NEW.observation_id
        UNION ALL
        SELECT 1 FROM obs.text_observation        WHERE observation_id = NEW.observation_id
    ) s;

    -- An unparsed observation is a deliberate record of absence: raw text was
    -- preserved, nothing was invented from it, and missing_reason says why.
    -- Those rows carry no typed value and must not.
    IF NEW.parse_status = 'unparsed' THEN
        IF found > 0 THEN
            RAISE EXCEPTION
                'observation % is unparsed but carries a typed value', NEW.observation_id
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NULL;
    END IF;

    IF found <> 1 THEN
        RAISE EXCEPTION
            'observation % has % typed value rows, expected exactly 1',
            NEW.observation_id, found
            USING ERRCODE = 'integrity_constraint_violation',
                  HINT = 'Insert the matching obs.<kind>_observation row in the same transaction.';
    END IF;
    RETURN NULL;
END;
$$;
COMMENT ON FUNCTION obs.assert_observation_has_value() IS
  'Closes the one hole foreign keys leave in a subtype hierarchy: FKs stop a value row from attaching to the wrong header, but cannot require that a header has a value row at all. Deferred to commit so the natural insert order works, and enforced in the database rather than trusted to the loader. §25.';

CREATE CONSTRAINT TRIGGER observation_has_exactly_one_value
    AFTER INSERT OR UPDATE ON obs.observation
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION obs.assert_observation_has_value();
COMMENT ON TRIGGER observation_has_exactly_one_value ON obs.observation IS
  'DEFERRABLE INITIALLY DEFERRED: checked once at commit, not on every insert, so a bulk load can write headers and values in separate set-based statements. §152 — deferral is used here because there is a real ordering need, not as a global default.';

-- ── compositions: shares that belong together ────────────────────────────────

CREATE TABLE obs.composition (
    composition_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    metric_id       integer NOT NULL
                    REFERENCES ref.metric (metric_id) ON DELETE RESTRICT,
    category_scheme_id integer NOT NULL
                    REFERENCES ref.category_scheme (category_scheme_id) ON DELETE RESTRICT,
    reference_period daterange NOT NULL,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    field_value_id  bigint REFERENCES source.field_value (field_value_id) ON DELETE RESTRICT,
    ingestion_run_id bigint,
    parser_version  text NOT NULL,
    parse_status    obs.parse_status NOT NULL,
    is_estimate     boolean NOT NULL DEFAULT false,
    qualifier_text  text NOT NULL DEFAULT '',
    recorded_at     timestamptz NOT NULL DEFAULT now(),
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT composition_period_not_empty CHECK (NOT isempty(reference_period))
);
COMMENT ON TABLE obs.composition IS
  'The header of a breakdown: "the language composition of Belgium as reported in the 2010 edition". Exists so that the members of one breakdown are grouped and can be validated together — a share is meaningless without knowing what else was in the same list. §78.';

CREATE TABLE obs.composition_member (
    composition_member_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    composition_id  bigint NOT NULL
                    REFERENCES obs.composition (composition_id) ON DELETE CASCADE,
    category_id     bigint NOT NULL
                    REFERENCES ref.category (category_id) ON DELETE RESTRICT,
    share_percent   ref.percentage,
    value_numeric   numeric,
    unit_id         integer REFERENCES ref.unit (unit_id) ON DELETE RESTRICT,
    ordinal         integer NOT NULL DEFAULT 0,
    raw_text        text NOT NULL DEFAULT '',
    qualifier_text  text NOT NULL DEFAULT '',
    CONSTRAINT composition_member_unique UNIQUE (composition_id, category_id, ordinal),
    CONSTRAINT composition_member_has_a_quantity
        CHECK (share_percent IS NOT NULL OR value_numeric IS NOT NULL OR btrim(raw_text) <> '')
);
COMMENT ON TABLE obs.composition_member IS
  'One member of a breakdown: "Dutch 60%". This is what replaces storing "Dutch 60%, French 40%" as a string — the M:N relationship between an entity and the categories it is composed of is a table, so it can be joined, aggregated and compared across editions. §26, §78.';
COMMENT ON COLUMN obs.composition_member.share_percent IS
  'The share as published. Deliberately NOT constrained so that the members of a composition sum to 100: real breakdowns fall short because of rounding, unlisted residuals and overlapping categories, and a source that publishes 99.7% is reporting accurately. Whether a composition sums plausibly is a quality check with a tolerance, not a constraint that would reject correct data. §78.';
COMMENT ON COLUMN obs.composition_member.ordinal IS
  'Order of appearance in the source, preserved because sources list shares in descending order and that ordering is information when two shares are equal.';

CREATE INDEX composition_entity_metric_idx
    ON obs.composition (entity_id, metric_id, reference_period);
CREATE INDEX composition_member_composition_idx
    ON obs.composition_member (composition_id);
CREATE INDEX composition_member_category_idx
    ON obs.composition_member (category_id);
COMMENT ON INDEX obs.composition_member_category_idx IS
  'Supports the reverse question — "which countries report Catalan, and with what share" — which is the query a composition table exists to make possible at all.';

-- ── bilateral facts ──────────────────────────────────────────────────────────

CREATE TABLE obs.bilateral_observation (
    bilateral_observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject_entity_id bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    object_entity_id bigint
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    object_unresolved_label text NOT NULL DEFAULT '',
    metric_id       integer NOT NULL
                    REFERENCES ref.metric (metric_id) ON DELETE RESTRICT,
    reference_period daterange NOT NULL,
    value_numeric   numeric,
    unit_id         integer REFERENCES ref.unit (unit_id) ON DELETE RESTRICT,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    field_value_id  bigint REFERENCES source.field_value (field_value_id) ON DELETE RESTRICT,
    ingestion_run_id bigint,
    parser_version  text NOT NULL,
    parse_status    obs.parse_status NOT NULL,
    ordinal         integer NOT NULL DEFAULT 0,
    raw_text        text NOT NULL DEFAULT '',
    qualifier_text  text NOT NULL DEFAULT '',
    recorded_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT bilateral_not_reflexive
        CHECK (object_entity_id IS NULL OR subject_entity_id <> object_entity_id),
    CONSTRAINT bilateral_object_identified
        CHECK (object_entity_id IS NOT NULL OR btrim(object_unresolved_label) <> '')
);
COMMENT ON TABLE obs.bilateral_observation IS
  'A fact about an ordered pair of entities: the length of the border between Austria and Germany, a trade share with a named partner. This is what "Austria 784 km; Germany 646 km" becomes — two rows with real entity references, a number and a unit, instead of one string nobody can join on. §27, §35.';
COMMENT ON COLUMN obs.bilateral_observation.object_unresolved_label IS
  'The partner as the source named it, when it could not be resolved to an entity. Keeping the row with an unresolved label is the alternative to two bad options: guessing which "Congo" was meant, or discarding the fact. It appears in the curation queue and the fact survives until someone decides. §80.';

CREATE INDEX bilateral_subject_idx
    ON obs.bilateral_observation (subject_entity_id, metric_id, reference_period);
CREATE INDEX bilateral_object_idx
    ON obs.bilateral_observation (object_entity_id, metric_id)
    WHERE object_entity_id IS NOT NULL;
COMMENT ON INDEX obs.bilateral_object_idx IS
  'Partial index for the reverse lookup ("who borders Germany"), excluding unresolved partners which by definition cannot answer it.';

-- ── ranks as published ───────────────────────────────────────────────────────

CREATE TABLE obs.source_rank (
    source_rank_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    metric_id       integer NOT NULL
                    REFERENCES ref.metric (metric_id) ON DELETE RESTRICT,
    reference_period daterange NOT NULL,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    rank            integer NOT NULL,
    ranking_universe text NOT NULL DEFAULT '',
    field_value_id  bigint REFERENCES source.field_value (field_value_id) ON DELETE RESTRICT,
    CONSTRAINT source_rank_positive CHECK (rank > 0)
);
COMMENT ON TABLE obs.source_rank IS
  'A rank the source itself published, kept separate from the value it ranks. A rank is not a measurement: it depends on which entities were in the comparison set and how ties were broken, neither of which is recoverable from the number alone. Stored as source metadata so it can be compared against a rank this platform derives, rather than being mistaken for one. §159.';
COMMENT ON COLUMN obs.source_rank.ranking_universe IS
  'What the rank was among, as far as the source stated it. Usually vague in the corpus, which is itself the reason a published rank cannot be recomputed or trusted as a value.';
