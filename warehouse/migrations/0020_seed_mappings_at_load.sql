-- 0020_seed_mappings_at_load — make the curated mappings actually get created.
--
-- 0010 seeds source.field_mapping with `CROSS JOIN source.dataset WHERE code =
-- 'cia_world_factbook'`. On a clean database that row does not exist when
-- migrations run: `source.dataset` is written by staging.py when it first reads
-- the manifest. Measured on a from-zero rebuild, 0010 applied at 16:29:12.308
-- and the dataset row appeared at 16:29:12.490 — 182 ms too late. The insert
-- matched nothing, inserted nothing, and reported success.
--
-- The consequence is not a missing convenience. A warehouse rebuilt from this
-- repository loaded 1,796,020 field values, mapped none of them, and produced
-- zero observations, zero compositions, zero bilateral facts and zero
-- coordinates — while every command exited 0 and the quality suite reported two
-- informational findings. The developer's database only had mappings because it
-- was built incrementally, with staging run before 0010 was ever written. That
-- makes the curated mapping set an artefact of one machine's history rather
-- than of the repository, which is the definition of unreproducible.
--
-- The fix is to seed at a moment when the dataset is guaranteed to exist. The
-- same curated rows move into a function that the loader calls before it maps
-- anything, and the loader refuses to run when the result is still empty, so
-- this can never again fail into silence. 0010 is left exactly as it is:
-- migrations are checksummed and immutable, and rewriting applied history to
-- hide a defect is worse than carrying it. On a database where 0010 did insert,
-- the ON CONFLICT clause makes this a no-op.

CREATE OR REPLACE FUNCTION source.seed_field_mappings()
RETURNS integer
LANGUAGE plpgsql
AS $seed$
DECLARE
    inserted integer;
BEGIN
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
DO NOTHING    ;
    GET DIAGNOSTICS inserted = ROW_COUNT;
    RETURN inserted;
END
$seed$;

COMMENT ON FUNCTION source.seed_field_mappings() IS
    'Idempotently insert the curated field mappings for the CIA World Factbook '
    'dataset. Called by the loader rather than run as a migration, because the '
    'source.dataset row it depends on is written by staging, after migrations.';
