-- 0015_foreign_key_indexes — index the referencing side of provenance keys.
--
-- Found by measurement, not by inspection. Re-staging an artifact deletes its
-- source.field_value rows, and four tables reference that column with
-- ON DELETE RESTRICT. PostgreSQL does not index the referencing side of a
-- foreign key automatically, so every deleted row triggered a sequential scan
-- of each referencing table to prove no row pointed at it. One artifact's
-- delete was still running after 55 seconds.
--
-- This is the case where §68's "index foreign-key columns when the query,
-- delete or update pattern requires it" is not optional: the delete pattern
-- requires it, and the requirement is invisible until a table has rows in it.
--
-- obs.observation already had such an index for a different reason (walking
-- provenance from a raw value to what was made of it), which is why it was not
-- the bottleneck.

CREATE INDEX composition_field_value_idx
    ON obs.composition (field_value_id);
COMMENT ON INDEX obs.composition_field_value_idx IS
  'Supports the ON DELETE RESTRICT check when a source.field_value is removed during re-staging, and the provenance walk from a raw value to the composition built from it. Without it a re-stage degrades to a sequential scan per deleted row.';

CREATE INDEX bilateral_field_value_idx
    ON obs.bilateral_observation (field_value_id);
COMMENT ON INDEX obs.bilateral_field_value_idx IS
  'Same purpose as obs.composition_field_value_idx: makes the referential check on delete an index lookup rather than a scan.';

CREATE INDEX entity_point_field_value_idx
    ON geo.entity_point (field_value_id);
COMMENT ON INDEX geo.entity_point_field_value_idx IS
  'Same purpose: referential check on delete, and provenance from a raw coordinate string to the parsed point.';

CREATE INDEX rejected_record_field_value_idx
    ON meta.rejected_record (field_value_id);
COMMENT ON INDEX meta.rejected_record_field_value_idx IS
  'Same purpose, plus the query that asks what a given raw value has failed to parse into.';

CREATE INDEX composition_release_idx ON obs.composition (release_id);
CREATE INDEX bilateral_release_idx ON obs.bilateral_observation (release_id);
CREATE INDEX entity_point_release_idx ON geo.entity_point (release_id);
COMMENT ON INDEX obs.composition_release_idx IS
  'The loader rewrites one release at a time and deletes by release_id; without this each reload scans the table.';
