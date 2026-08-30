-- 0004_ref_registry — metrics, units, and the taxonomies observations point at.
--
-- The metric registry is the source-independent half of the mapping problem.
-- A source calls something "Population" or "Population (July est.)" or
-- "population_total"; the platform calls it `demo.population.total` and knows
-- what kind of value that is, what unit it is in, and what range is plausible.
-- Source field names are mapped onto these in 0009, versioned, and never fused
-- with them — otherwise renaming a field in one source would rewrite history in
-- every other. §23, §116.
--
-- Note where the domain lives. There is no `demo` schema, no `econ` schema and
-- no `energy` schema; a metric's domain is an attribute of the metric, held as
-- an ltree path. Eight sparsely populated schemas would put the *classification*
-- of a fact into its *storage location*, which means reclassifying a metric
-- becomes a table move. ADR-0005 sets out the trade-off in full.

CREATE TABLE ref.metric_domain (
    metric_domain_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path            ltree NOT NULL,
    label           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT metric_domain_path_unique UNIQUE (path)
);
COMMENT ON TABLE ref.metric_domain IS
  'Hierarchical classification of what a metric is about, as an ltree path such as ''econ.gdp'' or ''demo.mortality''. Genuinely a tree — each domain has exactly one parent — which is what makes ltree the right type rather than a general graph. §46.';
COMMENT ON COLUMN ref.metric_domain.path IS
  'Dotted path, most general first. Supports subtree queries (``path <@ ''econ''``) so a report can ask for every economic metric without enumerating them.';

CREATE INDEX metric_domain_path_idx ON ref.metric_domain USING gist (path);
COMMENT ON INDEX ref.metric_domain_path_idx IS
  'GiST over the ltree path, supporting ancestor/descendant operators (@>, <@). The whole reason for choosing ltree over a self-referencing parent_id with recursive CTEs.';

INSERT INTO ref.metric_domain (path, label, description) VALUES
  ('geo',            'Geography',      'Location, area, boundaries, terrain, natural resources.'),
  ('geo.area',       'Area',           'Total, land and water area.'),
  ('geo.boundary',   'Boundaries',     'Land boundaries, coastline, maritime claims.'),
  ('geo.position',   'Position',       'Coordinates and elevation.'),
  ('demo',           'Demography',     'Population and its structure and dynamics.'),
  ('demo.population','Population',     'Counts and growth of people.'),
  ('demo.structure', 'Age and sex structure', 'Distribution of a population by age and sex.'),
  ('demo.vital',     'Vital rates',    'Births, deaths, fertility, life expectancy, migration.'),
  ('demo.settlement','Settlement',     'Urbanisation and distribution.'),
  ('society',        'Society',        'Language, religion, ethnicity, education, health.'),
  ('society.language','Languages',     'Languages spoken and their shares.'),
  ('society.religion','Religions',     'Religious affiliation and its shares.'),
  ('society.ethnicity','Ethnic groups','Ethnic composition.'),
  ('society.education','Education',    'Literacy and schooling.'),
  ('society.health', 'Health',         'Health expenditure, physician density, disease prevalence.'),
  ('econ',           'Economy',        'Output, prices, labour, trade and public finance.'),
  ('econ.gdp',       'Gross domestic product', 'GDP on its several bases, which are not interchangeable.'),
  ('econ.sector',    'Sector composition', 'Shares of output or employment by sector.'),
  ('econ.labour',    'Labour',         'Labour force, employment and unemployment.'),
  ('econ.prices',    'Prices',         'Inflation and exchange rates.'),
  ('econ.finance',   'Public finance', 'Budget, debt, reserves.'),
  ('econ.trade',     'Trade',          'Exports, imports, current account, partners.'),
  ('energy',         'Energy',         'Production, consumption, capacity and reserves.'),
  ('energy.electricity','Electricity', 'Generation, capacity and generating mix.'),
  ('energy.fuel',    'Fuels',          'Oil, gas and coal production, consumption and reserves.'),
  ('infra',          'Infrastructure', 'Transport and communications networks.'),
  ('infra.transport','Transport',      'Airports, railways, roadways, waterways, ports.'),
  ('infra.comms',    'Communications', 'Telephony, broadband and internet use.'),
  ('gov',            'Government',     'Sovereignty, institutions, membership and symbols.'),
  ('env',            'Environment',    'Environmental conditions, emissions and agreements.'),
  ('security',       'Security',       'Military expenditure and personnel.'),
  ('meta_field',     'Uncategorised',  'Metrics discovered in a source but not yet classified. A holding area that must be visible in reports, never a place things quietly stay.');

CREATE TABLE ref.quantity_kind (
    quantity_kind_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT quantity_kind_code_unique UNIQUE (code)
);
COMMENT ON TABLE ref.quantity_kind IS
  'What physical or economic dimension a unit measures — length, area, currency, energy, a dimensionless count. Units convert within a kind and never across it, which is the check that stops kilometres becoming square kilometres.';

INSERT INTO ref.quantity_kind (code, label, description) VALUES
  ('dimensionless', 'Dimensionless', 'Pure counts and ratios with no physical dimension.'),
  ('length',        'Length',        'Distances, boundary and network lengths.'),
  ('area',          'Area',          'Land, water and total areas.'),
  ('mass',          'Mass',          'Weights, typically of commodities or emissions.'),
  ('volume',        'Volume',        'Volumes, typically of oil, gas or water.'),
  ('energy',        'Energy',        'Energy produced or consumed.'),
  ('power',         'Power',         'Installed generating capacity.'),
  ('currency',      'Currency',      'Monetary amounts. Always accompanied by a currency and a price basis.'),
  ('time',          'Time',          'Durations, such as life expectancy in years.'),
  ('person',        'Person',        'Counts of people. Distinguished from dimensionless so a population cannot be divided by an area and silently keep its unit.'),
  ('ratio',         'Ratio',         'Shares, rates and percentages.');

CREATE TABLE ref.unit (
    unit_id         integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    symbol          text NOT NULL,
    label           text NOT NULL,
    quantity_kind_id integer NOT NULL
                    REFERENCES ref.quantity_kind (quantity_kind_id) ON DELETE RESTRICT,
    -- Conversion to the canonical unit of the same kind, as a multiplier.
    -- numeric, not float: converting an area with a binary fraction introduces
    -- error into a published decimal figure for no benefit. §51.
    factor_to_base  numeric NOT NULL DEFAULT 1,
    is_base         boolean NOT NULL DEFAULT false,
    ucum_code       text,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT unit_code_unique UNIQUE (code),
    CONSTRAINT unit_factor_positive CHECK (factor_to_base > 0),
    CONSTRAINT unit_base_has_unit_factor
        CHECK (NOT is_base OR factor_to_base = 1)
);
COMMENT ON TABLE ref.unit IS
  'Units of measure with a conversion factor to the base unit of their quantity kind. Conversion is available but never destructive: an observation records the unit the source used, and any converted figure is derived. Nothing in this schema rewrites a published number into different units in place. §52.';
COMMENT ON COLUMN ref.unit.ucum_code IS
  'The UCUM code where one applies, so units can be exchanged with systems that speak UCUM. Advisory: this schema does not compute with UCUM, it records it.';
COMMENT ON COLUMN ref.unit.factor_to_base IS
  'Multiply a value in this unit by this factor to get the base unit of the same quantity kind. Exact numeric so that 1 sq km -> 1e6 sq m is exact rather than nearly exact.';

INSERT INTO ref.unit (code, symbol, label, quantity_kind_id, factor_to_base, is_base, ucum_code) VALUES
  ('one',      '',      'one',                (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='dimensionless'), 1, true,  '1'),
  ('person',   'people','people',             (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='person'),        1, true,  NULL),
  ('percent',  '%',     'percent',            (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='ratio'),         1, true,  '%'),
  ('per_1000', '/1000', 'per 1,000 population',(SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='ratio'),        1, false, NULL),
  ('m',        'm',     'metre',              (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='length'),        1, true,  'm'),
  ('km',       'km',    'kilometre',          (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='length'),     1000, false, 'km'),
  ('nm',       'nm',    'nautical mile',      (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='length'),     1852, false, '[nmi_i]'),
  ('m2',       'm²',    'square metre',       (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='area'),          1, true,  'm2'),
  ('km2',      'km²',   'square kilometre',   (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='area'),    1000000, false, 'km2'),
  ('year',     'a',     'year',               (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='time'),          1, true,  'a'),
  ('usd',      '$',     'US dollar',          (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='currency'),      1, true,  NULL),
  ('kwh',      'kWh',   'kilowatt-hour',      (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='energy'),        1, true,  'kW.h'),
  ('kw',       'kW',    'kilowatt',           (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='power'),         1, true,  'kW'),
  ('bbl_day',  'bbl/d', 'barrels per day',    (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='volume'),        1, true,  NULL),
  ('m3',       'm³',    'cubic metre',        (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='volume'),        1, false, 'm3'),
  ('tonne',    't',     'tonne',              (SELECT quantity_kind_id FROM ref.quantity_kind WHERE code='mass'),          1, true,  't');

CREATE TABLE ref.currency (
    currency_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    name            text NOT NULL,
    minor_unit      smallint,
    validity        daterange NOT NULL DEFAULT daterange(NULL, NULL, '[)'),
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT currency_code_unique UNIQUE (code, validity)
);
COMMENT ON TABLE ref.currency IS
  'Currencies with validity periods, because a corpus spanning 1990 to 2025 contains the Deutsche Mark, the Italian lira and pre-redenomination currencies alongside the euro. Monetary observations carry a currency reference; the `money` type is never used. §50.';

INSERT INTO ref.currency (code, name, minor_unit) VALUES
  ('USD', 'United States dollar', 2),
  ('EUR', 'Euro', 2),
  ('XXX', 'Currency not applicable or unknown', NULL);
COMMENT ON COLUMN ref.currency.code IS
  'ISO 4217 alphabetic code where one exists. ''XXX'' is the ISO code for "no currency", used when a source gives a monetary figure without saying in what.';

-- ── the metric registry ──────────────────────────────────────────────────────

CREATE TABLE ref.metric (
    metric_id       integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    description     text NOT NULL,
    metric_domain_id integer NOT NULL
                    REFERENCES ref.metric_domain (metric_domain_id) ON DELETE RESTRICT,
    value_kind      ref.value_kind NOT NULL,
    preferred_unit_id integer REFERENCES ref.unit (unit_id) ON DELETE RESTRICT,
    -- Plausibility bounds, used by quality checks rather than as CHECK
    -- constraints on the value: a figure outside the expected range is usually a
    -- parser bug and occasionally a real outlier, and both need to be visible
    -- rather than rejected at insert time.
    expected_min    numeric,
    expected_max    numeric,
    is_deprecated   boolean NOT NULL DEFAULT false,
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT metric_code_unique UNIQUE (code),
    CONSTRAINT metric_description_present CHECK (btrim(description) <> ''),
    CONSTRAINT metric_range_ordered
        CHECK (expected_min IS NULL OR expected_max IS NULL OR expected_max >= expected_min),
    -- Quantitative metrics must declare a unit. A number with no unit is not a
    -- measurement, and "it was obvious from the field name" is how square
    -- kilometres get added to square miles.
    CONSTRAINT metric_quantitative_has_unit
        CHECK (value_kind NOT IN ('integer', 'numeric') OR preferred_unit_id IS NOT NULL),

    -- Referenced by obs.observation as a composite foreign key. This is the
    -- mechanism that makes the observation model type-safe: an observation
    -- inherits its value_kind from its metric and cannot contradict it.
    CONSTRAINT metric_id_value_kind_unique UNIQUE (metric_id, value_kind)
);
COMMENT ON TABLE ref.metric IS
  'What is being measured, defined independently of any source that measures it. A metric owns its value kind and its preferred unit, so those are properties of the concept rather than choices made per row. Source field names map onto metrics through source.field_mapping and are never merged into this table. §23.';
COMMENT ON COLUMN ref.metric.value_kind IS
  'The storage type of every observation of this metric, enforced through a composite foreign key from obs.observation. This is what makes ``population = ''Tuesday''`` impossible at the database level rather than merely unlikely. §25.';
COMMENT ON CONSTRAINT metric_id_value_kind_unique ON ref.metric IS
  'Redundant as a uniqueness claim — metric_id is already the primary key — and required as a foreign-key target: PostgreSQL will only accept a composite FK that references a unique constraint. Its purpose is to let obs.observation reference (metric_id, value_kind) as a pair.';
COMMENT ON COLUMN ref.metric.expected_min IS
  'Lower plausibility bound for quality checking, not a constraint. A percentage metric bounded 0-100 is typed with the ref.percentage domain, which does reject out-of-range values; these columns are for softer expectations such as "a life expectancy above 100 is probably a parse error".';

CREATE INDEX metric_domain_idx ON ref.metric (metric_domain_id);

CREATE TABLE ref.metric_alias (
    metric_alias_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    metric_id       integer NOT NULL
                    REFERENCES ref.metric (metric_id) ON DELETE CASCADE,
    alias           text NOT NULL,
    context         text NOT NULL DEFAULT '',
    CONSTRAINT metric_alias_unique UNIQUE (alias, context)
);
COMMENT ON TABLE ref.metric_alias IS
  'Alternative names for a metric, used to propose mappings for source fields not yet mapped. A proposal only: an alias match is evidence a human can act on, never an accepted mapping in itself. §24.';

-- ── taxonomies that observations classify against ────────────────────────────
-- One table with a kind discriminator rather than six near-identical tables.
-- The alternative — ref.language, ref.religion, ref.ethnic_group, … — would
-- differ only in name, and every composition query would need to know which one
-- to join. The categories are all "a named member of a named classification",
-- which is one relation.

CREATE TABLE ref.category_scheme (
    category_scheme_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    CONSTRAINT category_scheme_code_unique UNIQUE (code)
);
COMMENT ON TABLE ref.category_scheme IS
  'A classification whose members a composition can be broken down by: languages, religions, ethnic groups, economic sectors, energy sources. Kept as data because these lists are open-ended and source-dependent — "other" and "unspecified" are real members that appear constantly.';

INSERT INTO ref.category_scheme (code, label, description) VALUES
  ('language',     'Languages',        'Languages, as named by sources. Not ISO 639: sources say "Serbo-Croatian" and "Moldovan", and normalising those away would destroy the historical claim.'),
  ('religion',     'Religions',        'Religious affiliations as named by sources.'),
  ('ethnic_group', 'Ethnic groups',    'Ethnic groups as named by sources.'),
  ('econ_sector',  'Economic sectors', 'Agriculture, industry, services and finer breakdowns.'),
  ('energy_source','Energy sources',   'Fossil, nuclear, hydro and other renewable generation sources.'),
  ('age_band',     'Age bands',        'Age groupings used in population structure.'),
  ('sex',          'Sex',              'Sex categories as reported.'),
  ('commodity',    'Commodities',      'Traded goods named in export and import fields.');

CREATE TABLE ref.category (
    category_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_scheme_id integer NOT NULL
                    REFERENCES ref.category_scheme (category_scheme_id) ON DELETE RESTRICT,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    is_residual     boolean NOT NULL DEFAULT false,
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT category_unique_in_scheme UNIQUE (category_scheme_id, code)
);
COMMENT ON TABLE ref.category IS
  'One member of a classification. Created on demand as sources introduce members, which is why it is a table and not an enum: a corpus of thirty-six editions names hundreds of languages and there is no closed list to declare in advance.';
COMMENT ON COLUMN ref.category.is_residual IS
  'Marks catch-all members such as "other" and "unspecified". Composition checks need to tell them apart from named members, because a set of shares summing to 100 only with the residual included is normal, and one summing to 100 without it is suspicious.';

INSERT INTO ref.category (category_scheme_id, code, label, is_residual, notes)
SELECT s.category_scheme_id, v.code, v.label, v.is_residual, v.notes
  FROM ref.category_scheme s
  JOIN (VALUES
        ('language',     'other',       'other',       true,  'Residual bucket used by sources.'),
        ('language',     'unspecified', 'unspecified', true,  'Explicitly unspecified by the source.'),
        ('religion',     'other',       'other',       true,  'Residual bucket used by sources.'),
        ('religion',     'none',        'none',        false, 'Explicitly unaffiliated; a named member, not a residual.'),
        ('religion',     'unspecified', 'unspecified', true,  'Explicitly unspecified by the source.'),
        ('ethnic_group', 'other',       'other',       true,  'Residual bucket used by sources.'),
        ('ethnic_group', 'unspecified', 'unspecified', true,  'Explicitly unspecified by the source.'),
        ('econ_sector',  'agriculture', 'agriculture', false, ''),
        ('econ_sector',  'industry',    'industry',    false, ''),
        ('econ_sector',  'services',    'services',    false, ''),
        ('sex',          'male',        'male',        false, ''),
        ('sex',          'female',      'female',      false, ''),
        ('sex',          'total',       'total',       false, 'Both sexes combined, as reported.')
       ) AS v(scheme, code, label, is_residual, notes)
    ON v.scheme = s.code;
