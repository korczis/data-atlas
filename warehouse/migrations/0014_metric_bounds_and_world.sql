-- 0014_metric_bounds_and_world — plausibility bounds that account for the World entry.
--
-- The value_outside_expected_range check fired on
-- `world/demo.population.total = 5,515,617,484`, which is not a parse error: it
-- is the world population in 1993, correctly parsed from the Factbook's own
-- "World" entry. The bound was wrong, not the data.
--
-- This is the failure mode a plausibility bound has to avoid. A metric's range
-- has to hold for every entity that can carry it, and this corpus carries a
-- planetary aggregate alongside Pitcairn. Bounds are widened to the largest
-- entity the metric can legitimately describe; they still catch the errors they
-- exist for, which are unit and magnitude mistakes off by three orders of
-- magnitude or more, not off by four.
--
-- Bounds are a quality signal, never a CHECK constraint on the value: a real
-- outlier must land in the database and be reported, not be rejected at insert
-- and lost. §49, §54.

UPDATE ref.metric SET expected_max = 1e10,
       notes = 'Upper bound accommodates the World aggregate entry, which the Factbook publishes alongside individual entities. A per-entity bound is not expressible here and would belong to a quality rule keyed on entity type.'
 WHERE code = 'demo.population.total';

UPDATE ref.metric SET expected_max = 5e9
 WHERE code IN ('demo.population.male', 'demo.population.female');

UPDATE ref.metric SET expected_max = 1e10,
       notes = 'Upper bound accommodates the World aggregate.'
 WHERE code IN ('econ.labour_force', 'infra.internet_users');

UPDATE ref.metric SET expected_max = 6e8,
       notes = 'The World entry reports total land area of roughly 510 million sq km including oceans.'
 WHERE code IN ('geo.area.total', 'geo.area.land', 'geo.area.water');

UPDATE ref.metric SET expected_max = 2e15,
       notes = 'Upper bound accommodates world GDP, which the Factbook publishes.'
 WHERE code IN ('econ.gdp.ppp', 'econ.gdp.official_exchange');

UPDATE ref.metric SET expected_max = 1e7,
       notes = 'Coastline and boundary totals for the World entry aggregate every coastline on earth.'
 WHERE code IN ('geo.coastline', 'geo.land_boundary.total', 'geo.land_boundary.bilateral');

UPDATE ref.metric SET expected_max = 1e6
 WHERE code = 'infra.airports';
