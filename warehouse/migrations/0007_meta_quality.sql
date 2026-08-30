-- 0007_meta_quality — what the pipeline did, what it refused, and what a human decided.
--
-- Three concerns that all answer "why does the data look like this":
--   ingestion runs   — what executed, with which code, producing what counts
--   quarantine       — what could not be parsed, kept rather than discarded
--   quality          — assertions about the result, queryable rather than logged
--
-- The governing rule is §21: a parser may not drop a value, coerce it to NULL,
-- or guess. Anything it cannot handle lands in quarantine with the raw input and
-- a reason. Zero warnings is not a realistic goal; zero *silent* failures is.

CREATE TABLE meta.ingestion_run (
    ingestion_run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id      bigint NOT NULL
                    REFERENCES source.dataset (dataset_id) ON DELETE RESTRICT,
    release_id      bigint REFERENCES source.release (release_id) ON DELETE RESTRICT,
    artifact_id     bigint REFERENCES source.artifact (artifact_id) ON DELETE RESTRICT,
    stage           text NOT NULL,
    status          meta.run_status NOT NULL DEFAULT 'running',
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,

    -- what code ran
    parser_version  text NOT NULL,
    code_revision   text NOT NULL DEFAULT '',
    schema_version  text NOT NULL DEFAULT '',
    config_fingerprint text NOT NULL DEFAULT '',

    -- what it did, counted at every step so they can be reconciled
    rows_read       bigint NOT NULL DEFAULT 0,
    rows_staged     bigint NOT NULL DEFAULT 0,
    rows_loaded     bigint NOT NULL DEFAULT 0,
    rows_rejected   bigint NOT NULL DEFAULT 0,
    warning_count   integer NOT NULL DEFAULT 0,
    error_count     integer NOT NULL DEFAULT 0,
    message         text NOT NULL DEFAULT '',

    CONSTRAINT ingestion_run_stage_known
        CHECK (stage IN ('fetch', 'stage', 'resolve', 'map', 'load', 'quality',
                         'mart', 'search')),
    CONSTRAINT ingestion_run_finished_after_start
        CHECK (finished_at IS NULL OR finished_at >= started_at),
    CONSTRAINT ingestion_run_terminal_has_finish
        CHECK (status = 'running' OR finished_at IS NOT NULL),
    CONSTRAINT ingestion_run_counts_non_negative
        CHECK (rows_read >= 0 AND rows_staged >= 0 AND rows_loaded >= 0 AND rows_rejected >= 0)
);
COMMENT ON TABLE meta.ingestion_run IS
  'One execution of one pipeline stage over one artifact. The counts exist to be reconciled against each other: rows_read minus rows_rejected should account for rows_staged, and a gap is a finding rather than a rounding error. A run left ''running'' means the process died, which is information the table preserves instead of hiding. §20, §97.';
COMMENT ON COLUMN meta.ingestion_run.config_fingerprint IS
  'Hash of the configuration that shaped this run, so two runs producing different output can be distinguished by input rather than by guesswork. Never contains secrets — it is a digest of settings, not the settings.';
COMMENT ON COLUMN meta.ingestion_run.code_revision IS
  'Git revision, recorded in addition to parser_version rather than instead of it. A commit hash is precise and unreadable; a version is readable and coarse. Both, because each answers a question the other cannot. §115.';
COMMENT ON CONSTRAINT ingestion_run_terminal_has_finish ON meta.ingestion_run IS
  'A run that claims to have succeeded or failed must say when it stopped. Prevents the state where a crashed run is later mistaken for a completed one.';

CREATE INDEX ingestion_run_dataset_idx ON meta.ingestion_run (dataset_id, started_at DESC);
CREATE INDEX ingestion_run_artifact_idx ON meta.ingestion_run (artifact_id);
CREATE INDEX ingestion_run_unfinished_idx ON meta.ingestion_run (started_at)
    WHERE status = 'running';
COMMENT ON INDEX meta.ingestion_run_unfinished_idx IS
  'Partial index over runs that never reported an outcome — the "what died" query. Tiny in a healthy database, which is what makes a partial index the right shape.';

-- Deferred foreign keys from 0005: obs tables reference the run that produced
-- them, but meta.ingestion_run is defined here.
ALTER TABLE obs.observation
    ADD CONSTRAINT observation_ingestion_run_fk
    FOREIGN KEY (ingestion_run_id)
    REFERENCES meta.ingestion_run (ingestion_run_id) ON DELETE RESTRICT;
ALTER TABLE obs.composition
    ADD CONSTRAINT composition_ingestion_run_fk
    FOREIGN KEY (ingestion_run_id)
    REFERENCES meta.ingestion_run (ingestion_run_id) ON DELETE RESTRICT;
ALTER TABLE obs.bilateral_observation
    ADD CONSTRAINT bilateral_ingestion_run_fk
    FOREIGN KEY (ingestion_run_id)
    REFERENCES meta.ingestion_run (ingestion_run_id) ON DELETE RESTRICT;
COMMENT ON CONSTRAINT observation_ingestion_run_fk ON obs.observation IS
  'ON DELETE RESTRICT: a run cannot be deleted while observations point at it. The run record is part of those observations'' provenance, and removing it would leave values whose origin cannot be reconstructed.';

-- ── quarantine ───────────────────────────────────────────────────────────────

CREATE TABLE meta.rejected_record (
    rejected_record_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_run_id bigint NOT NULL
                    REFERENCES meta.ingestion_run (ingestion_run_id) ON DELETE RESTRICT,
    artifact_id     bigint REFERENCES source.artifact (artifact_id) ON DELETE RESTRICT,
    field_value_id  bigint REFERENCES source.field_value (field_value_id) ON DELETE RESTRICT,
    source_pointer  text NOT NULL,
    error_code      text NOT NULL,
    reason          text NOT NULL,
    raw_input       text NOT NULL,
    parser_version  text NOT NULL,
    first_seen_at   timestamptz NOT NULL DEFAULT now(),
    occurrence_count integer NOT NULL DEFAULT 1,
    resolved        boolean NOT NULL DEFAULT false,
    resolved_at     timestamptz,
    resolution_note text NOT NULL DEFAULT '',
    CONSTRAINT rejected_record_reason_present CHECK (btrim(reason) <> ''),
    CONSTRAINT rejected_resolved_has_timestamp
        CHECK (resolved = false OR resolved_at IS NOT NULL)
);
COMMENT ON TABLE meta.rejected_record IS
  'Everything a parser could not turn into a typed value, with the raw input that defeated it. This is the alternative to the two bad options — dropping the value, or coercing it to something plausible. A parser improvement is measured by rows leaving this table, and a parser regression is visible as rows arriving in it. §21.';
COMMENT ON COLUMN meta.rejected_record.source_pointer IS
  'Where in the source the failure occurred, precisely enough to find it by hand: artifact, member path, record key and field name.';
COMMENT ON COLUMN meta.rejected_record.error_code IS
  'Stable machine-readable classification such as ''number_unparseable'' or ''coordinate_malformed'', so failures can be counted by kind rather than by reading prose.';
COMMENT ON COLUMN meta.rejected_record.raw_input IS
  'The exact text that could not be parsed. Without it a rejection is an accusation with no evidence, and the parser cannot be fixed against a real case.';

CREATE INDEX rejected_record_run_idx ON meta.rejected_record (ingestion_run_id);
CREATE INDEX rejected_record_open_idx ON meta.rejected_record (error_code)
    WHERE NOT resolved;
COMMENT ON INDEX meta.rejected_record_open_idx IS
  'Partial index over unresolved rejections grouped by kind — the query that decides which parser bug is worth fixing next.';

-- ── quality ──────────────────────────────────────────────────────────────────

CREATE TABLE meta.quality_check (
    quality_check_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    category        text NOT NULL,
    description     text NOT NULL,
    default_severity meta.issue_severity NOT NULL DEFAULT 'warning',
    is_release_gate boolean NOT NULL DEFAULT false,
    CONSTRAINT quality_check_code_unique UNIQUE (code),
    CONSTRAINT quality_check_category_known
        CHECK (category IN ('structural', 'referential', 'semantic', 'temporal',
                            'range', 'completeness', 'duplicate', 'reconciliation',
                            'parser_coverage'))
);
COMMENT ON TABLE meta.quality_check IS
  'The catalogue of assertions this platform makes about its own data. Declaring checks as rows rather than burying them in code means the set of things being checked is itself queryable, and a check that stops running is visible as a check with no recent run. §54.';
COMMENT ON COLUMN meta.quality_check.is_release_gate IS
  'Whether a failure of this check blocks declaring an ingestion complete. The gate list is deliberately short: a gate that fires on ordinary imperfection gets routed around, and then nothing is gated at all.';

INSERT INTO meta.quality_check (code, label, category, description, default_severity, is_release_gate) VALUES
  ('observation_without_provenance', 'Observation without provenance', 'referential',
   'An observation that cannot be traced to a raw field value or an explained derivation.', 'error', true),
  ('unresolved_entity', 'Unresolved source entity', 'referential',
   'A source record whose entity could not be resolved and is awaiting curation. Expected to be non-zero; tracked so it cannot grow unnoticed.', 'warning', false),
  ('composition_share_sum', 'Composition shares out of tolerance', 'semantic',
   'The named shares of a composition sum to something implausible. Tolerance is wide because rounding and unlisted residuals are normal; only gross deviation is a finding.', 'warning', false),
  ('reference_period_after_publication', 'Reference period after publication', 'temporal',
   'A value describing a period that begins after the edition that reported it was published. Usually a parser misreading a note; occasionally a genuine projection.', 'warning', false),
  ('value_outside_expected_range', 'Value outside expected range', 'range',
   'A value beyond the metric''s plausibility bounds. Frequently a unit or magnitude parsing error.', 'warning', false),
  ('duplicate_observation', 'Duplicate observation', 'duplicate',
   'The same release reporting the same metric for the same entity and period more than once.', 'warning', false),
  ('parser_coverage', 'Raw fields with no canonical mapping', 'parser_coverage',
   'Fields present in the source that no accepted mapping turns into a metric. Expected to be large early and to shrink; the number is the honest measure of normalisation coverage.', 'info', false),
  ('record_count_reconciliation', 'Record counts do not reconcile', 'reconciliation',
   'Rows read, staged, loaded and rejected do not account for one another for an artifact.', 'error', true),
  ('artifact_digest_mismatch', 'Artifact digest mismatch', 'structural',
   'An artifact on disk no longer hashes to its recorded digest.', 'error', true);

CREATE TABLE meta.quality_run (
    quality_run_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    status          meta.run_status NOT NULL DEFAULT 'running',
    dataset_id      bigint REFERENCES source.dataset (dataset_id) ON DELETE RESTRICT,
    checks_run      integer NOT NULL DEFAULT 0,
    issues_found    integer NOT NULL DEFAULT 0,
    CONSTRAINT quality_run_finished_after_start
        CHECK (finished_at IS NULL OR finished_at >= started_at)
);
COMMENT ON TABLE meta.quality_run IS
  'One execution of the quality suite. `checks_run` is recorded so that a run which executed nothing cannot be mistaken for a run that found nothing — the distinction this repository has already been bitten by five times on the catalogue side.';

CREATE TABLE meta.quality_issue (
    quality_issue_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quality_run_id  bigint NOT NULL
                    REFERENCES meta.quality_run (quality_run_id) ON DELETE CASCADE,
    quality_check_id integer NOT NULL
                    REFERENCES meta.quality_check (quality_check_id) ON DELETE RESTRICT,
    severity        meta.issue_severity NOT NULL,
    subject         text NOT NULL,
    detail          text NOT NULL,
    entity_id       bigint REFERENCES core.entity (entity_id) ON DELETE SET NULL,
    release_id      bigint REFERENCES source.release (release_id) ON DELETE SET NULL,
    observation_id  bigint REFERENCES obs.observation (observation_id) ON DELETE CASCADE
);
COMMENT ON TABLE meta.quality_issue IS
  'One finding from one check in one run, pointing at the thing it is about. Queryable by definition — nothing here is written only to a log file, because a log is not something a release gate can read. §54.';

CREATE INDEX quality_issue_run_idx ON meta.quality_issue (quality_run_id);
CREATE INDEX quality_issue_check_idx ON meta.quality_issue (quality_check_id, severity);

-- ── curation ─────────────────────────────────────────────────────────────────

CREATE TABLE meta.curation_decision (
    curation_decision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subject_kind    text NOT NULL,
    subject_key     text NOT NULL,
    previous_state  jsonb,
    new_state       jsonb NOT NULL,
    rationale       text NOT NULL,
    decided_by      text NOT NULL,
    decided_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT curation_subject_kind_known
        CHECK (subject_kind IN ('entity_resolution', 'field_mapping', 'conflict',
                                'metric_definition', 'entity_relation', 'other')),
    CONSTRAINT curation_rationale_present CHECK (btrim(rationale) <> '')
);
COMMENT ON TABLE meta.curation_decision IS
  'An append-only record of every human decision: what was decided, what it replaced, and why. This is the part of the database that cannot be regenerated by re-running the pipeline, which makes it the part that actually needs backing up. §110, §145.';
COMMENT ON COLUMN meta.curation_decision.previous_state IS
  'The state being replaced, as JSON. JSONB is appropriate here precisely because the shape varies by subject_kind and this is an audit trail rather than queryable canonical data — the exception that proves the rule against JSONB blobs. §10.';
COMMENT ON COLUMN meta.curation_decision.decided_by IS
  'Who or what made the decision. For single-user local work this is a username; the column exists so that a shared deployment does not require a schema change to become attributable.';

CREATE INDEX curation_decision_subject_idx
    ON meta.curation_decision (subject_kind, subject_key, decided_at DESC);
