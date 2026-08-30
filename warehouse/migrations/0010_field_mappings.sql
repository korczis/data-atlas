-- 0010_field_mappings — source field names to canonical metrics.
--
-- Every row here was written after querying `source.field_definition` for the
-- names that actually occur, not from the names a reader might expect. That
-- matters because the same measurement is labelled differently across eras:
--
--     Population              1992-2001 text        (bare field)
--     Population / total      2002-2025 html, json  (subfield)
--     Area / total area       1992-1995 text
--     Area / total            1997-2025
--     Languages               most editions
--     Languages / Languages   json era, where the field nests inside itself
--
-- Absorbing that variation here rather than in the parsers is the point of the
-- table: the parsers stay faithful to their sources, and the knowledge that
-- three labels denote one metric lives in data that can be corrected without
-- reprocessing bytes. §24.
--
-- `section_pattern` is empty throughout, which the loader reads as "any
-- section". Sections genuinely differ between generations -- "People" became
-- "People and Society", and generation B of the HTML exposes no section at all
-- -- so matching on them would fragment a metric's history by edition rather
-- than by meaning.
--
-- Everything is inserted as 'accepted' with method 'curated' because a human
-- wrote and checked each line. Nothing in this file was produced by fuzzy
-- matching; the schema forbids a fuzzy match being self-accepted anyway.

INSERT INTO source.field_mapping
       (dataset_id, section_pattern, field_pattern, subfield_pattern,
        metric_id, category_scheme_id, target_kind, transform, default_unit_id,
        status, method, evidence, decided_by, decided_at, notes)
SELECT d.dataset_id, '', v.field_pattern, '',
       m.metric_id, cs.category_scheme_id, v.target_kind, v.transform, u.unit_id,
       'accepted', 'curated', v.evidence, 'seed-migration-0010', now(), v.notes
  FROM (VALUES
    -- demography ------------------------------------------------------------
    ('Population',                     'demo.population.total',       NULL, 'observation', 'scalar',   'person',
     'Bare "Population" in the text era carries the total; later editions move it to a "total" subfield.',
     'Text-era editions 1992-2001.'),
    ('Population / total',             'demo.population.total',       NULL, 'observation', 'scalar',   'person',
     'The same measurement as bare "Population", relabelled when the field gained subfields.', ''),
    ('Population / male',              'demo.population.male',        NULL, 'observation', 'scalar',   'person',
     'Sex breakdown, present only where the source published one.', ''),
    ('Population / female',            'demo.population.female',      NULL, 'observation', 'scalar',   'person', '', ''),
    ('Population growth rate',         'demo.population.growth_rate', NULL, 'observation', 'scalar',   'percent', '', ''),
    ('Birth rate',                     'demo.birth_rate',             NULL, 'observation', 'scalar',   'per_1000', '', ''),
    ('Death rate',                     'demo.death_rate',             NULL, 'observation', 'scalar',   'per_1000', '', ''),
    ('Total fertility rate',           'demo.fertility_rate',         NULL, 'observation', 'scalar',   'one', '', ''),
    ('Life expectancy at birth / total population', 'demo.life_expectancy.total', NULL, 'observation', 'scalar', 'year', '', ''),
    ('Infant mortality rate / total',  'demo.infant_mortality.total', NULL, 'observation', 'scalar',   'per_1000', '', ''),

    -- geography ---------------------------------------------------------------
    ('Area / total',                   'geo.area.total',              NULL, 'observation', 'scalar',   'km2', '', ''),
    ('Area / total area',              'geo.area.total',              NULL, 'observation', 'scalar',   'km2',
     'The 1990s text editions label the same figure "total area".', ''),
    ('Area / land',                    'geo.area.land',               NULL, 'observation', 'scalar',   'km2', '', ''),
    ('Area / land area',               'geo.area.land',               NULL, 'observation', 'scalar',   'km2', '', ''),
    ('Area / water',                   'geo.area.water',              NULL, 'observation', 'scalar',   'km2', '', ''),
    ('Coastline',                      'geo.coastline',               NULL, 'observation', 'scalar',   'km', '', ''),
    ('Land boundaries / total',        'geo.land_boundary.total',     NULL, 'observation', 'scalar',   'km', '', ''),
    ('Land boundaries / border countries', 'geo.land_boundary.bilateral', NULL, 'bilateral', 'partners', 'km',
     'A partner list: "Austria 402 km; Germany 704 km". Becomes one bilateral row per neighbour.', ''),
    ('Land boundaries',                'geo.land_boundary.bilateral', NULL, 'bilateral', 'partners', 'km',
     'The text era puts the total and the per-neighbour lengths in one string; the loader takes the named partners and leaves the leading total to the total mapping.', ''),
    ('Geographic coordinates',         NULL,                          NULL, 'coordinate', 'dms',      NULL,
     'Parsed into geo.entity_point, not into an observation: a coordinate pair is not a scalar measurement.', ''),

    -- economy -----------------------------------------------------------------
    ('GDP (purchasing power parity)',  'econ.gdp.ppp',                NULL, 'observation', 'scalar',   'usd', '', ''),
    ('GDP - real growth rate',         'econ.gdp.real_growth_rate',   NULL, 'observation', 'scalar',   'percent', '', ''),
    ('GDP - per capita (PPP)',         'econ.gdp.per_capita_ppp',     NULL, 'observation', 'scalar',   'usd', '', ''),
    ('GDP (official exchange rate)',   'econ.gdp.official_exchange',  NULL, 'observation', 'scalar',   'usd', '', ''),
    ('Inflation rate (consumer prices)', 'econ.inflation_rate',       NULL, 'observation', 'scalar',   'percent', '', ''),
    ('Unemployment rate',              'econ.unemployment_rate',      NULL, 'observation', 'scalar',   'percent', '', ''),
    ('Labor force',                    'econ.labour_force',           NULL, 'observation', 'scalar',   'person', '', ''),
    ('Public debt',                    'econ.public_debt',            NULL, 'observation', 'scalar',   'percent', '', ''),

    -- infrastructure ----------------------------------------------------------
    ('Airports',                       'infra.airports',              NULL, 'observation', 'scalar',   'one', '', ''),
    ('Railways / total',               'infra.railways.total',        NULL, 'observation', 'scalar',   'km', '', ''),
    ('Roadways / total',               'infra.roadways.total',        NULL, 'observation', 'scalar',   'km', '', ''),

    -- society: compositions ---------------------------------------------------
    ('Languages',                      'society.languages',           'language', 'composition', 'shares', NULL,
     'A share list: "Czech (official) 88.4%, Slovak 1.5%". One row per language, never a stored string.', ''),
    ('Languages / Languages',          'society.languages',           'language', 'composition', 'shares', NULL,
     'The JSON era nests the field inside itself; same measurement.', ''),
    ('Religions',                      'society.religions',           'religion', 'composition', 'shares', NULL, '', ''),
    ('Ethnic groups',                  'society.ethnic_groups',       'ethnic_group', 'composition', 'shares', NULL, '', ''),

    -- government ---------------------------------------------------------------
    ('Capital',                        'gov.capital.name',            NULL, 'observation', 'text',     NULL, '', ''),
    ('Capital / name',                 'gov.capital.name',            NULL, 'observation', 'text',     NULL, '', ''),
    ('Government type',                'gov.government_type',         NULL, 'observation', 'text',     NULL, '', ''),

    -- deliberate non-mappings --------------------------------------------------
    -- 'ignore' is a decision, and it is recorded so that the coverage report can
    -- tell a field nobody has looked at from one that was looked at and found to
    -- carry no canonical value. §105.
    ('Area / comparative area',        NULL, NULL, 'ignore', 'none', NULL,
     'Prose comparison to a US state ("slightly smaller than South Carolina"). Carries no measurement.', ''),
    ('Area - comparative',             NULL, NULL, 'ignore', 'none', NULL,
     'As above, under the later label.', ''),
    ('Map references',                 NULL, NULL, 'ignore', 'none', NULL,
     'Names the reference map the entry appears on. An artefact of the printed publication.', ''),
    ('Capital / time difference',      NULL, NULL, 'ignore', 'none', NULL,
     'UTC offset expressed as prose relative to Washington DC; not modelled.', ''),
    ('Capital / etymology',            NULL, NULL, 'ignore', 'none', NULL,
     'Narrative; belongs to content, not to a metric.', '')
  ) AS v(field_pattern, metric_code, scheme_code, target_kind, transform, unit_code,
         evidence, notes)
  CROSS JOIN source.dataset d
  LEFT JOIN ref.metric m ON m.code = v.metric_code
  LEFT JOIN ref.category_scheme cs ON cs.code = v.scheme_code
  LEFT JOIN ref.unit u ON u.code = v.unit_code
 WHERE d.code = 'cia_world_factbook'
ON CONFLICT (dataset_id, section_pattern, field_pattern, subfield_pattern, version)
DO NOTHING;
