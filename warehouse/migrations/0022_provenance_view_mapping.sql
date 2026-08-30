-- 0022_provenance_view_mapping — expose the curated decision in api.provenance.
--
-- 0021 stored field_mapping_id on every fact family. Storing it and not
-- publishing it would leave the read contract answering "where did this number
-- come from" with everything except the step that decided what it means: which
-- curated rule chose this metric, this unit and this type for a field whose
-- name changed four times across the corpus. That is the step most likely to be
-- wrong, and the one a reader most needs named.

CREATE OR REPLACE VIEW api.provenance AS
SELECT o.observation_id,
       e.slug AS entity_slug, m.code AS metric,
       fv.raw_text        AS source_raw_text,
       fd.section_name, fd.field_name,
       sr.source_key, sr.source_label,
       a.code AS artifact, a.filename, a.sha256, a.checksum_origin,
       rel.label AS release_label, rel.edition_year,
       ds.code AS dataset, pub.name AS publisher,
       o.parser_version, ir.code_revision, o.recorded_at,
       (SELECT r2.url FROM source.retrieval r2
         WHERE r2.artifact_id = a.artifact_id
         ORDER BY r2.priority LIMIT 1) AS retrieval_url,
       -- Appended, not inserted: CREATE OR REPLACE VIEW may add columns only at
       -- the end. Reordering them would mean dropping the view, and dropping a
       -- published read contract to make a diff tidier is the wrong trade.
       fm.field_mapping_id, fm.field_pattern AS mapped_from_field,
       fm.method AS mapping_method, fm.decided_by AS mapping_decided_by
  FROM obs.observation o
  JOIN core.entity e ON e.entity_id = o.entity_id
  JOIN ref.metric m  ON m.metric_id = o.metric_id
  JOIN source.field_value fv ON fv.field_value_id = o.field_value_id
  JOIN source.field_definition fd
    ON fd.field_definition_id = fv.field_definition_id
  JOIN source.record sr ON sr.record_id = fv.record_id
  JOIN source.artifact a ON a.artifact_id = sr.artifact_id
  JOIN source.release rel ON rel.release_id = a.release_id
  JOIN source.dataset ds ON ds.dataset_id = rel.dataset_id
  JOIN source.publisher pub ON pub.publisher_id = ds.publisher_id
  LEFT JOIN meta.ingestion_run ir ON ir.ingestion_run_id = o.ingestion_run_id
  LEFT JOIN source.field_mapping fm ON fm.field_mapping_id = o.field_mapping_id;

COMMENT ON VIEW api.provenance IS
  'Grain: one row per observation that has a raw source field behind it. The answer to "where exactly did this number come from" — publisher, edition, file, its digest, the record and field inside it, the original text, the parser version that typed it, and the curated mapping that decided which metric and unit it belongs to. Observations without a field_value (none at present; the schema permits explained derivations) do not appear here, which is why this is an inner join and not a left one. The mapping join is left: a future derived value need not come from one.';
