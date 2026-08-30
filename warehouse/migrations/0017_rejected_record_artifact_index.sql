-- 0017_rejected_record_artifact_index — index the quarantine's artifact column.
--
-- Re-staging now clears an artifact's parse-time quarantine rows by artifact_id.
-- Without an index that delete scans the whole table on every artifact, which is
-- the same unindexed-foreign-key problem migration 0015 fixed for
-- source.field_value — found there by a 55-second delete, and anticipated here
-- rather than waited for.

CREATE INDEX rejected_record_artifact_idx ON meta.rejected_record (artifact_id);
COMMENT ON INDEX meta.rejected_record_artifact_idx IS
  'Supports clearing an artifact''s parse-time quarantine rows when it is re-staged, and the "what failed in this artifact" query. Parse-time rejections carry an artifact but no field value, which is why they need their own index rather than being reachable through the field-value one.';
