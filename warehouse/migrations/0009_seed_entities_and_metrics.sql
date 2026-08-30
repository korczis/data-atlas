-- 0009_seed_entities_and_metrics — a starting vocabulary, not a world model.
--
-- Two seeds, both deliberately small.
--
-- The entity seed covers the historical states this corpus actually contains
-- and whose succession the model has to survive. It is not an attempt to
-- enumerate every country: entities are created by curated resolution as the
-- corpus is read, and seeding hundreds of rows from memory would be exactly the
-- "hardcoded current country names" the design forbids. What is here is what a
-- succession graph needs in order to be testable.
--
-- The metric seed covers high-value fields whose canonical definition is
-- unambiguous. Coverage grows through source.field_mapping, which is data;
-- adding a metric is a migration only because a metric's value kind is part of
-- the schema's type safety.

-- ── entities: the succession cases ───────────────────────────────────────────

INSERT INTO core.entity (entity_type_id, slug, existence, notes)
SELECT t.entity_type_id, v.slug, v.existence::daterange, v.notes
  FROM (VALUES
    ('world_aggregate',  'world',          '[,)',
     'The World entry. A statistical aggregate over all entities, not a place: it has no ISO code, no border and no capital, and the model must not give it one.'),
    ('sovereign_state',  'czechia',        '[1993-01-01,)',
     'Independent from 1 January 1993. Appears as "Czech Republic" throughout the corpus and as "Czechia" only in later editions.'),
    ('sovereign_state',  'slovakia',       '[1993-01-01,)',
     'Independent from 1 January 1993.'),
    ('historical_state', 'czechoslovakia', '[1918-10-28,1993-01-01)',
     'Dissolved into Czechia and Slovakia. Present in the 1992 and earlier editions of this corpus, which is why the entity model cannot key on present-day ISO codes.'),
    ('historical_state', 'soviet_union',   '[1922-12-30,1991-12-26)',
     'Dissolved into fifteen successor states. Its observations remain attached to it rather than being reassigned to Russia.'),
    ('sovereign_state',  'russia',         '[1991-12-25,)',
     'Recognised as the continuator state of the USSR, which is a different relation from succession and is recorded as such.'),
    ('historical_state', 'yugoslavia',     '[1945-11-29,1992-04-27)',
     'The Socialist Federal Republic. Distinct from the later Federal Republic of Yugoslavia, which is why a name alone cannot identify it.'),
    ('sovereign_state',  'germany',        '[1990-10-03,)',
     'Reunified Germany.'),
    ('historical_state', 'east_germany',   '[1949-10-07,1990-10-03)',
     'The German Democratic Republic, which appears in the 1990 edition as "GDR" in border lists.'),
    ('sovereign_state',  'austria',        '[,)', ''),
    ('sovereign_state',  'poland',         '[,)', ''),
    ('sovereign_state',  'france',         '[,)', '')
  ) AS v(type_code, slug, existence, notes)
  JOIN core.entity_type t ON t.code = v.type_code
ON CONFLICT (slug) DO NOTHING;

-- Names. Each is scoped to the period it applied, so a query for 1992 gets
-- "Czechoslovakia" and one for 2025 gets "Czechia" without either being wrong.
INSERT INTO core.entity_name (entity_id, name_kind_id, name, language_tag, is_preferred, validity)
SELECT e.entity_id, k.name_kind_id, v.name, 'en', v.preferred, v.validity::daterange
  FROM (VALUES
    ('world',          'canonical', 'World',                     true,  '[,)'),
    ('czechia',        'canonical', 'Czechia',                   true,  '[2016-05-01,)'),
    ('czechia',        'historical','Czech Republic',            false, '[1993-01-01,)'),
    ('czechia',        'long',      'the Czech Republic',        false, '[1993-01-01,)'),
    ('slovakia',       'canonical', 'Slovakia',                  true,  '[,)'),
    ('czechoslovakia', 'canonical', 'Czechoslovakia',            true,  '[,1993-01-01)'),
    ('soviet_union',   'canonical', 'Soviet Union',              true,  '[,1991-12-26)'),
    ('soviet_union',   'alias',     'USSR',                      false, '[,1991-12-26)'),
    ('russia',         'canonical', 'Russia',                    true,  '[,)'),
    ('yugoslavia',     'canonical', 'Yugoslavia',                true,  '[,1992-04-27)'),
    ('germany',        'canonical', 'Germany',                   true,  '[,)'),
    ('east_germany',   'canonical', 'German Democratic Republic',true,  '[,1990-10-03)'),
    ('east_germany',   'alias',     'GDR',                       false, '[,1990-10-03)'),
    ('austria',        'canonical', 'Austria',                   true,  '[,)'),
    ('poland',         'canonical', 'Poland',                    true,  '[,)'),
    ('france',         'canonical', 'France',                    true,  '[,)')
  ) AS v(slug, kind, name, preferred, validity)
  JOIN core.entity e ON e.slug = v.slug
  JOIN core.name_kind k ON k.code = v.kind
ON CONFLICT DO NOTHING;

-- External identifiers, with validity. 'CS' is the case that justifies the
-- whole design: ISO assigned it to Czechoslovakia, then reassigned it to Serbia
-- and Montenegro. Only the first is asserted here, bounded to the period it was
-- true, so the code can later be recorded for its second holder without either
-- claim contradicting the other.
INSERT INTO core.entity_identifier (entity_id, identifier_scheme_id, value, validity, status, notes)
SELECT e.entity_id, s.identifier_scheme_id, v.value, v.validity::daterange, v.status, v.notes
  FROM (VALUES
    ('czechia',        'iso3166_1_alpha2', 'CZ', '[1993-01-01,)',           'current',    ''),
    ('czechia',        'iso3166_1_alpha3', 'CZE','[1993-01-01,)',           'current',    ''),
    ('czechia',        'cwf_gec',          'ez', '[1993-01-01,)',           'current',    'The Factbook''s own code for Czechia is EZ, not CZ.'),
    ('slovakia',       'iso3166_1_alpha2', 'SK', '[1993-01-01,)',           'current',    ''),
    ('slovakia',       'cwf_gec',          'lo', '[1993-01-01,)',           'current',    ''),
    ('czechoslovakia', 'iso3166_1_alpha2', 'CS', '[1974-01-01,1993-01-01)', 'historical', 'Later reassigned by ISO to Serbia and Montenegro; the reassignment is why an ISO code cannot be an identity.'),
    ('soviet_union',   'iso3166_1_alpha2', 'SU', '[1974-01-01,1992-08-31)', 'historical', ''),
    ('russia',         'iso3166_1_alpha2', 'RU', '[1992-01-01,)',           'current',    ''),
    ('russia',         'cwf_gec',          'rs', '[1992-01-01,)',           'current',    ''),
    ('yugoslavia',     'iso3166_1_alpha2', 'YU', '[1974-01-01,2003-02-04)', 'historical', ''),
    ('germany',        'iso3166_1_alpha2', 'DE', '[1990-10-03,)',           'current',    ''),
    ('germany',        'cwf_gec',          'gm', '[1990-10-03,)',           'current',    ''),
    ('east_germany',   'iso3166_1_alpha2', 'DD', '[1974-01-01,1990-10-03)', 'historical', ''),
    ('austria',        'iso3166_1_alpha2', 'AT', '[,)',                     'current',    ''),
    ('austria',        'cwf_gec',          'au', '[,)',                     'current',    'AU is Austria in the Factbook''s scheme and Australia in ISO 3166-1; the two schemes are not interchangeable.'),
    ('poland',         'iso3166_1_alpha2', 'PL', '[,)',                     'current',    ''),
    ('poland',         'cwf_gec',          'pl', '[,)',                     'current',    ''),
    ('france',         'iso3166_1_alpha2', 'FR', '[,)',                     'current',    ''),
    ('france',         'cwf_gec',          'fr', '[,)',                     'current',    ''),
    ('world',          'cwf_gec',          'xx', '[,)',                     'current',    'The Factbook''s World aggregate entry.')
  ) AS v(slug, scheme, value, validity, status, notes)
  JOIN core.entity e ON e.slug = v.slug
  JOIN core.identifier_scheme s ON s.code = v.scheme
ON CONFLICT DO NOTHING;

-- Succession, as relations rather than as a parent column.
INSERT INTO core.entity_relation
       (subject_entity_id, object_entity_id, entity_relation_type_id, validity, notes)
SELECT s.entity_id, o.entity_id, t.entity_relation_type_id, v.validity::daterange, v.notes
  FROM (VALUES
    ('czechoslovakia', 'czechia',  'split_into',   '[1993-01-01,)',
     'The dissolution of 1 January 1993.'),
    ('czechoslovakia', 'slovakia', 'split_into',   '[1993-01-01,)',
     'The dissolution of 1 January 1993.'),
    ('soviet_union',   'russia',   'succeeded_by', '[1991-12-26,)',
     'Russia is the continuator state; fourteen other successors are not yet recorded because this corpus has not been read for them.'),
    ('east_germany',   'germany',  'merged_into',  '[1990-10-03,)',
     'Accession of the GDR to the Federal Republic.')
  ) AS v(subject, object, rel, validity, notes)
  JOIN core.entity s ON s.slug = v.subject
  JOIN core.entity o ON o.slug = v.object
  JOIN core.entity_relation_type t ON t.code = v.rel
ON CONFLICT DO NOTHING;

-- ── metrics ──────────────────────────────────────────────────────────────────

INSERT INTO ref.metric (code, label, description, metric_domain_id, value_kind,
                        preferred_unit_id, expected_min, expected_max)
SELECT v.code, v.label, v.description, d.metric_domain_id, v.value_kind::ref.value_kind,
       u.unit_id, v.emin, v.emax
  FROM (VALUES
    ('demo.population.total', 'Population, total',
     'Resident population as reported by a source for the associated reference period. Sources differ on whether this is a mid-year estimate, a census count or a projection; the qualifier and the original text are retained on each observation rather than being normalised away.',
     'demo.population', 'integer', 'person', 0::numeric, 2e9::numeric),
    ('demo.population.male', 'Population, male',
     'Resident population recorded as male. Present only in editions that break the total down by sex.',
     'demo.structure', 'integer', 'person', 0::numeric, 1e9::numeric),
    ('demo.population.female', 'Population, female',
     'Resident population recorded as female.',
     'demo.structure', 'integer', 'person', 0::numeric, 1e9::numeric),
    ('demo.population.growth_rate', 'Population growth rate',
     'Annual rate of change of the resident population, in percent. Legitimately negative, so it is plain numeric rather than the percentage domain, which forbids values below zero.',
     'demo.population', 'numeric', 'percent', -20::numeric, 20::numeric),
    ('demo.birth_rate', 'Birth rate',
     'Live births per 1,000 population over a year, as reported.',
     'demo.vital', 'numeric', 'per_1000', 0::numeric, 100::numeric),
    ('demo.death_rate', 'Death rate',
     'Deaths per 1,000 population over a year, as reported.',
     'demo.vital', 'numeric', 'per_1000', 0::numeric, 100::numeric),
    ('demo.life_expectancy.total', 'Life expectancy at birth',
     'Mean years a newborn would live under the mortality rates of the reference period. A synthetic cohort measure, not a prediction about any individual.',
     'demo.vital', 'numeric', 'year', 0::numeric, 120::numeric),
    ('demo.infant_mortality.total', 'Infant mortality rate',
     'Deaths of infants under one year per 1,000 live births.',
     'demo.vital', 'numeric', 'per_1000', 0::numeric, 400::numeric),
    ('demo.fertility_rate', 'Total fertility rate',
     'Children a woman would bear under the age-specific fertility rates of the reference period.',
     'demo.vital', 'numeric', 'one', 0::numeric, 15::numeric),
    ('geo.area.total', 'Area, total',
     'Sum of land and water areas within international boundaries and coastlines, as the source reported it. Definitions of what counts as inland water changed across editions, so figures are comparable within a source and only cautiously across sources.',
     'geo.area', 'numeric', 'km2', 0::numeric, 6e8::numeric),
    ('geo.area.land', 'Area, land',
     'Land area excluding inland water bodies, as reported.',
     'geo.area', 'numeric', 'km2', 0::numeric, 6e8::numeric),
    ('geo.area.water', 'Area, water',
     'Inland water area, as reported.',
     'geo.area', 'numeric', 'km2', 0::numeric, 6e8::numeric),
    ('geo.coastline', 'Coastline length',
     'Length of the boundary between land and sea, as reported. Highly sensitive to measurement resolution — the coastline paradox is a real limit on comparing these figures between sources.',
     'geo.boundary', 'numeric', 'km', 0::numeric, 1e6::numeric),
    ('geo.land_boundary.total', 'Land boundaries, total',
     'Total length of land borders with all neighbours, as reported. The per-neighbour breakdown is held separately as bilateral observations.',
     'geo.boundary', 'numeric', 'km', 0::numeric, 1e6::numeric),
    ('geo.land_boundary.bilateral', 'Land boundary with a neighbour',
     'Length of the land border between two specific entities, as reported by one source. Stored per ordered pair so it can be joined, compared between editions, and checked for symmetry.',
     'geo.boundary', 'numeric', 'km', 0::numeric, 1e6::numeric),
    ('econ.gdp.ppp', 'GDP (purchasing power parity)',
     'Gross domestic product converted at purchasing-power-parity rates. Not comparable with the nominal figure: for many economies the two differ by a factor of several, which is why they are separate metrics rather than one metric with a flag.',
     'econ.gdp', 'numeric', 'usd', 0::numeric, 1e15::numeric),
    ('econ.gdp.official_exchange', 'GDP (official exchange rate)',
     'Gross domestic product converted at official exchange rates.',
     'econ.gdp', 'numeric', 'usd', 0::numeric, 1e15::numeric),
    ('econ.gdp.per_capita_ppp', 'GDP per capita (PPP)',
     'Purchasing-power-parity GDP divided by population, as the source reported it. Recorded as published rather than recomputed, so it reflects the source''s own population figure.',
     'econ.gdp', 'numeric', 'usd', 0::numeric, 1e7::numeric),
    ('econ.gdp.real_growth_rate', 'GDP real growth rate',
     'Annual change in real GDP, in percent. Legitimately negative.',
     'econ.gdp', 'numeric', 'percent', -100::numeric, 100::numeric),
    ('econ.inflation_rate', 'Inflation rate (consumer prices)',
     'Annual change in consumer prices, in percent. Legitimately negative, and occasionally enormous.',
     'econ.prices', 'numeric', 'percent', -100::numeric, 1e7::numeric),
    ('econ.unemployment_rate', 'Unemployment rate',
     'Share of the labour force recorded as unemployed. Definitions vary between national sources far more than the single number suggests.',
     'econ.labour', 'numeric', 'percent', 0::numeric, 100::numeric),
    ('econ.labour_force', 'Labour force',
     'Number of people in the labour force, as reported.',
     'econ.labour', 'integer', 'person', 0::numeric, 2e9::numeric),
    ('econ.public_debt', 'Public debt',
     'Gross government debt as a share of GDP, as reported.',
     'econ.finance', 'numeric', 'percent', 0::numeric, 1000::numeric),
    ('infra.internet_users', 'Internet users',
     'Number of people recorded as using the internet. The definition of a user changed repeatedly across this corpus.',
     'infra.comms', 'integer', 'person', 0::numeric, 1e10::numeric),
    ('infra.airports', 'Airports',
     'Count of airports, as reported. Inclusion criteria (paved, unpaved, minimum runway length) vary by edition.',
     'infra.transport', 'integer', 'one', 0::numeric, 100000::numeric),
    ('infra.railways.total', 'Railways, total length',
     'Total route length of railways, as reported.',
     'infra.transport', 'numeric', 'km', 0::numeric, 1e7::numeric),
    ('infra.roadways.total', 'Roadways, total length',
     'Total length of the road network, as reported.',
     'infra.transport', 'numeric', 'km', 0::numeric, 1e8::numeric),
    ('society.literacy.total', 'Literacy rate',
     'Share of the population meeting the source''s literacy criterion, which differs between sources and over time.',
     'society.education', 'numeric', 'percent', 0::numeric, 100::numeric),
    ('society.languages', 'Language composition',
     'Breakdown of a population by language, as reported. A composition rather than a scalar: it is a set of named shares and is stored as one row per language.',
     'society.language', 'text', NULL, NULL::numeric, NULL::numeric),
    ('society.religions', 'Religious composition',
     'Breakdown of a population by religious affiliation, as reported.',
     'society.religion', 'text', NULL, NULL::numeric, NULL::numeric),
    ('society.ethnic_groups', 'Ethnic composition',
     'Breakdown of a population by ethnic group, as reported.',
     'society.ethnicity', 'text', NULL, NULL::numeric, NULL::numeric),
    ('gov.capital.name', 'Capital city name',
     'Name of the capital as the source gave it. Text because it is a name; the capital''s location is a separate geographic fact.',
     'gov', 'text', NULL, NULL::numeric, NULL::numeric),
    ('gov.government_type', 'Government type',
     'The source''s own characterisation of the form of government, as published text. Deliberately not normalised into a closed vocabulary: the phrasing is itself the claim, and flattening "parliamentary republic" and "parliamentary democracy" into one code would assert an equivalence the source did not make.',
     'gov', 'text', NULL, NULL::numeric, NULL::numeric)
  ) AS v(code, label, description, domain, value_kind, unit, emin, emax)
  JOIN ref.metric_domain d ON d.path = v.domain::ltree
  LEFT JOIN ref.unit u ON u.code = v.unit
ON CONFLICT (code) DO NOTHING;
