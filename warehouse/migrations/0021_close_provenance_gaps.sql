-- 0021_close_provenance_gaps — make three inferred links into stored ones.
--
-- The provenance audit traced 100 facts and could answer all five provenance
-- questions for observations, compositions and bilateral facts. It could not
-- for narrative content or coordinates, and could never answer "which mapping
-- decided this" for anything. All three gaps were recoverable by inference, and
-- inference is exactly what provenance is supposed to replace: a join a caller
-- has to know to write is not a guarantee, it is a convention that holds until
-- someone loads data that breaks it.
--
-- 1. content.field had no link to source.field_value. Instance-level provenance
--    ran through record_id + field_definition_id, which identifies the field
--    *dictionary entry*, not the value: 105,548 of 116,617 rows resolved to one
--    candidate, and 11,069 resolved to between 2 and 30. Equality on the text
--    itself disambiguated all of them, but nothing prevents two identical
--    passages in one record from making that ambiguous too. The column the
--    loader's own INSERT already had in hand is stored instead.
--
-- 2. geo.entity_point had no ingestion_run_id, though every other fact table
--    has one. "Which run produced this coordinate" was unanswerable by any
--    query, for all 7,199 rows. Existing rows cannot be backfilled -- the
--    information was never recorded -- so the column is nullable and is
--    populated from the next load onward, rather than pretending to a history
--    that was not kept.
--
-- 3. source.field_mapping had no incoming foreign key from anywhere. Which
--    curated decision produced a fact was recoverable only by re-running the
--    pattern match, which is inference over data that can be edited later.

ALTER TABLE content.field
    ADD COLUMN field_value_id bigint;

-- Deterministic backfill: the record and the field definition narrow it, the
-- text settles the remainder, and least() makes the tie-break stable rather
-- than whatever the planner happened to return first.
UPDATE content.field f
   SET field_value_id = (
       SELECT min(fv.field_value_id)
         FROM content.section s
         JOIN content.document d ON d.document_id = s.document_id
         JOIN source.field_value fv ON fv.record_id = d.record_id
        WHERE s.section_id = f.section_id
          AND fv.field_definition_id = f.field_definition_id
          AND fv.raw_text = f.text_content)
 WHERE field_value_id IS NULL;

ALTER TABLE content.field
    ALTER COLUMN field_value_id SET NOT NULL,
    ADD CONSTRAINT field_field_value_id_fkey
        FOREIGN KEY (field_value_id) REFERENCES source.field_value (field_value_id)
        ON DELETE RESTRICT;

CREATE INDEX content_field_field_value_idx ON content.field (field_value_id);

COMMENT ON COLUMN content.field.field_value_id IS
    'The exact raw value this passage was read from. Stored rather than inferred: '
    'field_definition_id identifies the dictionary entry, which up to 30 values '
    'in one record can share.';

ALTER TABLE geo.entity_point
    ADD COLUMN ingestion_run_id bigint REFERENCES meta.ingestion_run (ingestion_run_id);

CREATE INDEX geo_entity_point_run_idx ON geo.entity_point (ingestion_run_id);

COMMENT ON COLUMN geo.entity_point.ingestion_run_id IS
    'Nullable only because rows loaded before this column existed cannot be '
    'attributed to a run: that fact was never recorded. Populated from every '
    'load onward.';

ALTER TABLE obs.observation
    ADD COLUMN field_mapping_id bigint REFERENCES source.field_mapping (field_mapping_id);
ALTER TABLE obs.composition
    ADD COLUMN field_mapping_id bigint REFERENCES source.field_mapping (field_mapping_id);
ALTER TABLE obs.bilateral_observation
    ADD COLUMN field_mapping_id bigint REFERENCES source.field_mapping (field_mapping_id);
ALTER TABLE geo.entity_point
    ADD COLUMN field_mapping_id bigint REFERENCES source.field_mapping (field_mapping_id);

CREATE INDEX observation_field_mapping_idx ON obs.observation (field_mapping_id);
CREATE INDEX composition_field_mapping_idx ON obs.composition (field_mapping_id);
CREATE INDEX bilateral_field_mapping_idx ON obs.bilateral_observation (field_mapping_id);
CREATE INDEX entity_point_field_mapping_idx ON geo.entity_point (field_mapping_id);

COMMENT ON COLUMN obs.observation.field_mapping_id IS
    'The curated mapping that decided this fact''s metric, unit and type. '
    'Nullable because a future derived value need not come from one.';
