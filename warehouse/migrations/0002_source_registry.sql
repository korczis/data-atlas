-- 0002_source_registry — where every value came from.
--
-- The chain this schema has to make walkable, in both directions:
--
--   publisher -> dataset -> release -> artifact -> retrieval
--                                   -> record -> field -> (canonical observation)
--
-- Given any number in this database, it must be possible to name the publisher,
-- the edition, the file, its digest, the record inside it, the raw text of the
-- field, and the parser version that typed it. That is the whole point of the
-- platform, so it is modelled first and everything else references it.
--
-- Nothing here is Factbook-shaped. A Eurostat dataset, a national register dump
-- and a Natural Earth download are all publisher/dataset/release/artifact.

-- ── who publishes ────────────────────────────────────────────────────────────

CREATE TABLE source.publisher (
    publisher_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    name            text NOT NULL,
    country_code    text,
    homepage_url    text,
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT publisher_code_unique UNIQUE (code),
    CONSTRAINT publisher_name_present CHECK (btrim(name) <> '')
);
COMMENT ON TABLE source.publisher IS
  'An organisation that publishes data: a statistical office, an intelligence agency, a ministry, an NGO, a commercial provider. Distinct from the dataset it publishes, because publishers outlive and rename their datasets and one publisher issues many.';
COMMENT ON COLUMN source.publisher.country_code IS
  'Where the publisher is based, as free text rather than a foreign key to core.entity: this is an administrative fact about an organisation, and making it depend on the entity model would mean no publisher could be recorded before the entity graph was populated.';

-- ── what is published ────────────────────────────────────────────────────────

CREATE TABLE source.license (
    license_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    name            text NOT NULL,
    url             text,
    is_open         boolean NOT NULL,
    requires_attribution boolean NOT NULL DEFAULT false,
    statement       text NOT NULL DEFAULT '',
    CONSTRAINT license_code_unique UNIQUE (code)
);
COMMENT ON TABLE source.license IS
  'Licensing terms, stored per dataset AND per artifact because they differ. The CIA text is a US Government work and uncopyrightable in the US; the Project Gutenberg wrapper around it and a preservation project''s own compiled database are neither. Recording one licence for "the Factbook" would assert something false about the bytes actually held.';
COMMENT ON COLUMN source.license.is_open IS
  'Whether the terms permit redistribution and reuse without individual permission. A coarse flag for filtering, never a substitute for reading `statement`.';

CREATE TABLE source.dataset (
    dataset_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    publisher_id    bigint NOT NULL
                    REFERENCES source.publisher (publisher_id) ON DELETE RESTRICT,
    code            ref.entity_code NOT NULL,
    title           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    license_id      bigint REFERENCES source.license (license_id) ON DELETE RESTRICT,
    -- Link back to the Data Atlas catalogue when the source is catalogued there.
    -- Text, not a foreign key: the catalogue is a set of committed JSON files,
    -- not a table in this database, and inventing a table to mirror it would
    -- create a second source of truth for the thing the catalogue already owns.
    -- See docs/database/ADDING-A-SOURCE.md on the two meanings of "source of truth".
    catalog_source_id text,
    status          text NOT NULL DEFAULT 'active',
    first_release_year ref.publication_year,
    last_release_year  ref.publication_year,
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT dataset_code_unique UNIQUE (code),
    CONSTRAINT dataset_status_known
        CHECK (status IN ('active', 'discontinued', 'superseded', 'planned')),
    CONSTRAINT dataset_year_span_ordered
        CHECK (last_release_year IS NULL OR first_release_year IS NULL
               OR last_release_year >= first_release_year)
);
COMMENT ON TABLE source.dataset IS
  'A named, repeatedly published body of data — The World Factbook, a Eurostat indicator collection, a national cadastre extract. The unit an ingestion adapter is written against. `code` is the stable identifier used in manifests and on the command line.';
COMMENT ON COLUMN source.dataset.catalog_source_id IS
  'The `id` of the matching entry in data/sources/*.json, when this dataset is also catalogued by Data Atlas. Deliberately a plain text pointer: the catalogue remains the source of truth for source *discovery*, this database is the source of truth for ingested *data*, and neither is generated from the other.';
COMMENT ON COLUMN source.dataset.status IS
  'Whether more releases are expected. The Factbook is ''discontinued'': CIA retired it in February 2026, which makes the corpus closed and the archived bytes irreplaceable.';

-- ── one edition of it ────────────────────────────────────────────────────────

CREATE TABLE source.release (
    release_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id      bigint NOT NULL
                    REFERENCES source.dataset (dataset_id) ON DELETE RESTRICT,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    edition_year    ref.publication_year,
    published_on    date,
    published_precision text NOT NULL DEFAULT 'year',
    retrieved_on    date,
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT release_code_unique_per_dataset UNIQUE (dataset_id, code),
    CONSTRAINT release_published_precision_known
        CHECK (published_precision IN ('day', 'month', 'year', 'unknown'))
);
COMMENT ON TABLE source.release IS
  'One edition of a dataset: "The World Factbook 2005", "Eurostat demo_pjan v2024-03". The unit that carries publication time. Every observation points at a release, which is how the platform can say when a claim was published as distinct from what period it describes.';
COMMENT ON COLUMN source.release.edition_year IS
  'The year the edition is named for. NOT the year its data describes and NOT the date it was published — the Factbook 2025 edition carries figures labelled "2024 est." and its JSON cache was last committed in January 2026. Those are three different years and this column is only the first. See docs/database/TEMPORAL-MODEL.md.';
COMMENT ON COLUMN source.release.published_precision IS
  'How precisely `published_on` is known. Most historical editions are known only to the year, and recording 1 January as if it were a real publication date would invent precision.';
COMMENT ON COLUMN source.release.retrieved_on IS
  'When this platform obtained the release. Distinct from publication: for archived material the gap is decades, and it is the retrieval date that bounds what a digest can attest to.';

-- ── the bytes ────────────────────────────────────────────────────────────────

CREATE TABLE source.artifact (
    artifact_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    code            ref.entity_code NOT NULL,
    filename        text NOT NULL,
    media_type      ref.media_type NOT NULL,
    compression     text NOT NULL DEFAULT 'none',
    size_bytes      bigint NOT NULL,
    sha256          ref.sha256_hex NOT NULL,
    checksum_origin text NOT NULL,
    parser_family   text NOT NULL,
    role            text NOT NULL DEFAULT 'primary',
    status          source.artifact_status NOT NULL DEFAULT 'declared',
    license_id      bigint REFERENCES source.license (license_id) ON DELETE RESTRICT,
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT artifact_code_unique UNIQUE (code),
    CONSTRAINT artifact_size_positive CHECK (size_bytes > 0),
    CONSTRAINT artifact_role_known
        CHECK (role IN ('primary', 'repair', 'superseded', 'supplementary')),
    CONSTRAINT artifact_checksum_origin_known
        CHECK (checksum_origin IN ('computed_on_retrieval', 'upstream_published',
                                   'secondary_manifest'))
);
COMMENT ON TABLE source.artifact IS
  'One logical file belonging to a release, identified by the SHA-256 of its bytes. A digest fixes *which bytes*; it is not evidence of origin. Where the checksum came from is recorded separately in `checksum_origin`, because "we hashed this ourselves on download" and "a third party told us this hash" are different strengths of claim.';
COMMENT ON COLUMN source.artifact.sha256 IS
  'Identity of the bytes. Not unique across the table by constraint: the same bytes can legitimately be reached through several URLs and be recorded once per release that distributes them. Deduplication by digest is a query, not a constraint. §164.';
COMMENT ON COLUMN source.artifact.checksum_origin IS
  '''computed_on_retrieval'' — we hashed what we received, so it attests to our copy from that moment. ''upstream_published'' — the publisher published this digest, which attests to the publisher''s copy. ''secondary_manifest'' — a preservation project asserted it; useful, and the weakest of the three.';
COMMENT ON COLUMN source.artifact.role IS
  '''primary'' carries the edition. ''repair'' supplements a primary that is known incomplete (the 1996 Wayback capture repairs seven truncated countries in the Gutenberg text). ''superseded'' is retained specifically because it is bad — the 2001 zip is corrupt, and deleting it would erase the evidence that 2001 needed a fallback.';
COMMENT ON COLUMN source.artifact.parser_family IS
  'Which parser reads this artifact. A property of the bytes, not of the year: 2001 has both an HTML artifact and a text artifact, read by different parsers.';

CREATE INDEX artifact_release_idx ON source.artifact (release_id);
COMMENT ON INDEX source.artifact_release_idx IS
  'Supports "every artifact of this release", the join used by every ingestion run and by the coverage report. Foreign-key column with low cardinality per release; B-tree.';

CREATE INDEX artifact_sha256_idx ON source.artifact (sha256);
COMMENT ON INDEX source.artifact_sha256_idx IS
  'Supports identifying an artifact from bytes found on disk, and detecting the same content distributed under several names. Equality only; B-tree.';

CREATE TABLE source.retrieval (
    retrieval_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    artifact_id     bigint NOT NULL
                    REFERENCES source.artifact (artifact_id) ON DELETE CASCADE,
    url             text,
    vcs_repo        text,
    vcs_commit      text,
    role            text NOT NULL,
    priority        smallint NOT NULL DEFAULT 1,
    byte_stable     boolean NOT NULL,
    http_etag       text,
    http_last_modified text,
    retrieved_at    timestamptz,
    verified_at     timestamptz,
    observed_sha256 ref.sha256_hex,
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT retrieval_role_known CHECK (role IN ('origin', 'mirror', 'manual')),
    CONSTRAINT retrieval_has_a_locator
        CHECK (url IS NOT NULL OR (vcs_repo IS NOT NULL AND vcs_commit IS NOT NULL))
);
COMMENT ON TABLE source.retrieval IS
  'A place an artifact''s bytes have been, or could be, obtained from. Many per artifact: the same content reached through the publisher, a Wayback capture and a mirror is one artifact with three retrievals, not three artifacts. Cascades from the artifact because a retrieval has no meaning without it.';
COMMENT ON COLUMN source.retrieval.byte_stable IS
  'Whether fetching this locator again is expected to reproduce the artifact''s recorded digest. False for Project Gutenberg, which rewrites its own boilerplate — the 1990 file on gutenberg.org today differs from the archived copy in 190 lines, none of them CIA text. False for a git commit, which reproduces content but not necessarily archive bytes. A pipeline that pinned hashes against these would report corruption every time an unrelated upstream edit landed.';
COMMENT ON COLUMN source.retrieval.observed_sha256 IS
  'What this locator actually returned, when it has been fetched. Differs from artifact.sha256 exactly when the remote content has drifted, which is a finding worth keeping rather than an error to suppress.';
COMMENT ON COLUMN source.retrieval.role IS
  '''origin'' is where the bytes came from in the first place; ''mirror'' is a copy that may be more durable than the origin. For this corpus the origin (cia.gov) no longer serves the files at all, so the mirror is the only working path — which is precisely why both are recorded.';

CREATE INDEX retrieval_artifact_idx ON source.retrieval (artifact_id);

-- ── what is inside the bytes ─────────────────────────────────────────────────

CREATE TABLE source.record (
    record_id       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    artifact_id     bigint NOT NULL
                    REFERENCES source.artifact (artifact_id) ON DELETE RESTRICT,
    member_path     text NOT NULL,
    source_key      text NOT NULL,
    source_label    text NOT NULL,
    ordinal         integer,
    entity_id       bigint,          -- FK added in 0003, after core.entity exists
    resolution_status meta.mapping_status NOT NULL DEFAULT 'proposed',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT record_unique_within_artifact UNIQUE (artifact_id, source_key),
    CONSTRAINT record_source_key_present CHECK (btrim(source_key) <> '')
);
COMMENT ON TABLE source.record IS
  'One addressable unit inside an artifact: in this corpus, one country or territory entry in one edition. The join point between "bytes we hold" and "entity we believe it is about" — and the place where that belief is allowed to be unresolved.';
COMMENT ON COLUMN source.record.member_path IS
  'Path within the container, e.g. the entry inside a zip, so a value can be traced to the exact file it was read from and not merely to the archive.';
COMMENT ON COLUMN source.record.source_key IS
  'The source''s own identifier for this record — a FIPS-style code, a JSON filename stem, a heading. Kept verbatim, never normalised, because it is evidence.';
COMMENT ON COLUMN source.record.entity_id IS
  'The canonical entity this record is about, once resolved. NULL means unresolved, which is a legitimate and preserved state: a record naming "Congo" in 1995 is not silently attached to either present-day republic. Unresolved records are queued for curation, never dropped and never guessed. §80.';
COMMENT ON COLUMN source.record.ordinal IS
  'Position within the artifact, preserved so the original ordering of a publication can be reconstructed. §160.';

CREATE INDEX record_artifact_idx ON source.record (artifact_id);
CREATE INDEX record_unresolved_idx ON source.record (artifact_id)
    WHERE entity_id IS NULL;
COMMENT ON INDEX source.record_unresolved_idx IS
  'Partial index over the curation queue. Unresolved records are a small and shrinking fraction of the table, so a partial index keeps the "what still needs a human" query fast without carrying the resolved majority.';

CREATE TABLE source.field_definition (
    field_definition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id      bigint NOT NULL
                    REFERENCES source.dataset (dataset_id) ON DELETE RESTRICT,
    section_name    text NOT NULL DEFAULT '',
    field_name      text NOT NULL,
    first_seen_year ref.publication_year,
    last_seen_year  ref.publication_year,
    edition_count   integer NOT NULL DEFAULT 0,
    record_count    bigint NOT NULL DEFAULT 0,
    example_value   text NOT NULL DEFAULT '',
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT field_definition_unique UNIQUE (dataset_id, section_name, field_name),
    CONSTRAINT field_definition_span_ordered
        CHECK (last_seen_year IS NULL OR first_seen_year IS NULL
               OR last_seen_year >= first_seen_year)
);
COMMENT ON TABLE source.field_definition IS
  'Every distinct section-and-field name a dataset has ever used, with the span of editions it appears in. Built by profiling the real data rather than declared in advance — a field name is discovered, not assumed. This table is what makes the schema history of a thirty-six-year publication queryable. §102.';
COMMENT ON COLUMN source.field_definition.example_value IS
  'One real value, retained so a human deciding on a mapping can see the shape of what they are mapping instead of guessing from the field name. "Population" is not always a number. §104.';

CREATE TABLE source.field_value (
    field_value_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id       bigint NOT NULL
                    REFERENCES source.record (record_id) ON DELETE RESTRICT,
    field_definition_id bigint NOT NULL
                    REFERENCES source.field_definition (field_definition_id)
                    ON DELETE RESTRICT,
    ordinal         integer NOT NULL DEFAULT 0,
    raw_text        text NOT NULL,
    raw_markup      text,
    CONSTRAINT field_value_unique UNIQUE (record_id, field_definition_id, ordinal)
);
COMMENT ON TABLE source.field_value IS
  'The raw text of one field of one record, exactly as published. This is the bottom of the provenance chain and the reason no parsing decision is irreversible: whatever a parser makes of "$2.14 trillion (2023 est.)", the string itself is still here and can be re-parsed by a better parser later. §22.';
COMMENT ON COLUMN source.field_value.raw_text IS
  'Verbatim source text, whitespace-normalised only. Never the parsed value, never a cleaned-up rendering, never NULL for a field that was present but empty.';
COMMENT ON COLUMN source.field_value.raw_markup IS
  'Original markup where the source was HTML and the markup carried meaning (tables, lists). NULL for text and JSON sources. Kept so that a later parser can recover structure this one flattened. §161.';

CREATE INDEX field_value_record_idx ON source.field_value (record_id);
CREATE INDEX field_value_definition_idx ON source.field_value (field_definition_id);
COMMENT ON INDEX source.field_value_definition_idx IS
  'Supports "every raw value ever recorded for this field name", which is how mapping candidates are reviewed and how the field-evolution report is built.';

CREATE TABLE source.citation (
    citation_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE CASCADE,
    style           text NOT NULL DEFAULT 'default',
    text            text NOT NULL,
    CONSTRAINT citation_unique_per_style UNIQUE (release_id, style)
);
COMMENT ON TABLE source.citation IS
  'A renderable citation for a release, so a generated country profile can attribute every published value without the presentation layer having to know how to format a reference. §165.';
