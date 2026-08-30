-- 0006_content_geo — narrative text as published, and spatial features over time.
--
-- Two schemas in one migration because neither is large and both exist for the
-- same reason: some of what a source publishes is not a number, and forcing it
-- into the observation model would destroy it.

-- ── content: prose, preserved ────────────────────────────────────────────────
-- The Factbook is roughly half prose — background essays, descriptions of legal
-- systems, transnational disputes. That text is the substrate for full-text
-- search, for diffing what changed between editions, and eventually for
-- embeddings. It is preserved with its structure and ordering intact, not
-- normalised into forty nullable columns. §33, §38.

CREATE TABLE content.document (
    document_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    entity_id       bigint REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    record_id       bigint REFERENCES source.record (record_id) ON DELETE RESTRICT,
    title           text NOT NULL,
    language_tag    text NOT NULL DEFAULT 'en',
    provenance      content.provenance_kind NOT NULL DEFAULT 'source_published',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT document_unique_per_record UNIQUE (release_id, record_id)
);
COMMENT ON TABLE content.document IS
  'One entity''s narrative content in one release: "Czechia, The World Factbook 2015". The container that gives sections and fields their edition and their subject.';
COMMENT ON COLUMN content.document.provenance IS
  'Who wrote this. ''source_published'' is the publisher''s own prose. ''model_generated'' would be a language model''s, which is never treated as evidence and never mixed into source claims. ADR-0008.';

CREATE TABLE content.section (
    section_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id     bigint NOT NULL
                    REFERENCES content.document (document_id) ON DELETE CASCADE,
    name            text NOT NULL,
    ordinal         integer NOT NULL,
    CONSTRAINT section_unique_in_document UNIQUE (document_id, name),
    CONSTRAINT section_ordinal_non_negative CHECK (ordinal >= 0)
);
COMMENT ON TABLE content.section IS
  'A top-level division of a document — Geography, People and Society, Economy. Ordinal preserved so a profile can be rebuilt in the order it was published rather than alphabetically. §160.';

CREATE TABLE content.field (
    content_field_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    section_id      bigint NOT NULL
                    REFERENCES content.section (section_id) ON DELETE CASCADE,
    field_definition_id bigint
                    REFERENCES source.field_definition (field_definition_id) ON DELETE RESTRICT,
    name            text NOT NULL,
    ordinal         integer NOT NULL,
    text_content    text NOT NULL,
    raw_markup      text,
    CONSTRAINT content_field_unique UNIQUE (section_id, name, ordinal)
);
COMMENT ON TABLE content.field IS
  'One named passage within a section, with its cleaned text and, where the source was HTML, the original markup. Cleaned and raw are kept side by side so that stripping markup is never lossy — a later parser can recover a table this one flattened to prose. §161.';
COMMENT ON COLUMN content.field.text_content IS
  'Whitespace-normalised plain text, with entities decoded and markup removed. Normalised for reading and searching; the authoritative bytes remain the artifact and the raw markup beside this column.';

CREATE INDEX content_field_section_idx ON content.field (section_id);
CREATE INDEX content_document_entity_idx ON content.document (entity_id);
CREATE INDEX content_document_release_idx ON content.document (release_id);

CREATE TABLE content.asset (
    asset_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    entity_id       bigint REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    kind            text NOT NULL,
    source_url      text,
    member_path     text,
    media_type      ref.media_type,
    sha256          ref.sha256_hex,
    byte_size       bigint,
    width_px        integer,
    height_px       integer,
    caption         text NOT NULL DEFAULT '',
    license_id      bigint REFERENCES source.license (license_id) ON DELETE RESTRICT,
    captured_on     date,
    is_stored       boolean NOT NULL DEFAULT false,
    CONSTRAINT asset_kind_known CHECK (kind IN ('map', 'flag', 'photo', 'audio', 'other')),
    CONSTRAINT asset_dimensions_positive
        CHECK ((width_px IS NULL OR width_px > 0) AND (height_px IS NULL OR height_px > 0))
);
COMMENT ON TABLE content.asset IS
  'Metadata for maps, flags and photographs found in a release. Metadata only by default: `is_stored` says whether the bytes were actually retained. Media is catalogued now and fetched only where there is a reason, because downloading a corpus of images to prove they exist is not one. §100.';
COMMENT ON COLUMN content.asset.license_id IS
  'Assets need their own licence reference. Public-domain status of US Government text does not automatically extend to every image reproduced alongside it, and assuming it does is how an attribution problem gets baked into a dataset. §99.';

-- ── geo: features and their versions ─────────────────────────────────────────
-- The rule: geometry never belongs to an entity directly. `country.geometry`
-- would force one polygon to be the truth for all time, and borders move. An
-- entity is linked to a versioned feature for a period, from a named source, at
-- a stated generalisation. §29.

CREATE TABLE geo.feature (
    feature_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    label           text NOT NULL,
    feature_kind    text NOT NULL,
    notes           text NOT NULL DEFAULT '',
    CONSTRAINT feature_code_unique UNIQUE (code),
    CONSTRAINT feature_kind_known
        CHECK (feature_kind IN ('boundary', 'point', 'coastline', 'admin_area',
                                'maritime_zone', 'other'))
);
COMMENT ON TABLE geo.feature IS
  'A spatial thing that persists while its geometry changes — "the land boundary of Poland", "the capital point of Berlin". Stable across versions, so a reference to a feature survives a boundary revision.';

CREATE TABLE geo.feature_version (
    feature_version_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    feature_id      bigint NOT NULL
                    REFERENCES geo.feature (feature_id) ON DELETE CASCADE,
    release_id      bigint REFERENCES source.release (release_id) ON DELETE RESTRICT,
    validity        daterange NOT NULL DEFAULT daterange(NULL, NULL, '[)'),
    -- Canonical storage is EPSG:4326 for interoperability. The CRS the source
    -- actually supplied is recorded separately so reprojection remains auditable
    -- and the original is never merely assumed. §28.
    geom            geometry(Geometry, 4326),
    source_srid     integer,
    generalisation  text NOT NULL DEFAULT 'source',
    is_disputed     boolean NOT NULL DEFAULT false,
    precision_note  text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT feature_version_generalisation_known
        CHECK (generalisation IN ('source', 'high', 'medium', 'low')),
    CONSTRAINT feature_version_geom_valid
        CHECK (geom IS NULL OR ST_IsValid(geom))
);
COMMENT ON TABLE geo.feature_version IS
  'One version of a feature''s geometry, from one source, valid over one period, at one generalisation. Several may coexist for the same feature and period: two boundary sources disagreeing about a disputed border are two rows, and the model does not have to pick. §29.';
COMMENT ON COLUMN geo.feature_version.geom IS
  'Geometry in EPSG:4326. Stored as `geometry` rather than `geography` because 4326 geometry is what every exchange format and every other spatial tool expects; geodesic work (areas, distances) casts to geography or projects explicitly at query time rather than being baked into storage. Naive planar arithmetic on lon/lat is never correct at global scale. §28.';
COMMENT ON COLUMN geo.feature_version.source_srid IS
  'The CRS the source supplied, before reprojection to 4326. Kept so a reprojection can be reviewed or redone; losing it makes the transformation unauditable.';
COMMENT ON CONSTRAINT feature_version_geom_valid ON geo.feature_version IS
  'Rejects self-intersecting and otherwise invalid geometry at insert. An invalid polygon silently produces wrong areas and wrong intersections rather than an error, so it is refused at the boundary.';

CREATE INDEX feature_version_geom_idx ON geo.feature_version USING gist (geom);
COMMENT ON INDEX geo.feature_version_geom_idx IS
  'GiST over geometry: the standard spatial index, supporting bounding-box and containment queries (point-in-country, features intersecting a viewport). Nothing else can answer those without a full scan.';

CREATE INDEX feature_version_validity_idx ON geo.feature_version USING gist (validity);

CREATE TABLE geo.entity_feature (
    entity_feature_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    feature_id      bigint NOT NULL
                    REFERENCES geo.feature (feature_id) ON DELETE RESTRICT,
    role            text NOT NULL DEFAULT 'extent',
    validity        daterange NOT NULL DEFAULT daterange(NULL, NULL, '[)'),
    CONSTRAINT entity_feature_role_known
        CHECK (role IN ('extent', 'capital', 'claimed_extent', 'administered_extent',
                        'coastline', 'other')),
    CONSTRAINT entity_feature_unique UNIQUE (entity_id, feature_id, role, validity)
);
COMMENT ON TABLE geo.entity_feature IS
  'Links an entity to a feature for a period and in a role. The role matters: an entity''s administered extent and its claimed extent are different polygons, and a model with one link per entity would have to choose which claim to encode as fact.';

-- ── coordinates as published ─────────────────────────────────────────────────
-- Sources give coordinates as text ("50 05 N, 14 28 E"). The parsed decimal
-- degrees and the raw string are both kept: DMS conversion is deterministic but
-- not always unambiguous, and the original is the evidence. §77.

CREATE TABLE geo.entity_point (
    entity_point_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id       bigint NOT NULL
                    REFERENCES core.entity (entity_id) ON DELETE RESTRICT,
    release_id      bigint NOT NULL
                    REFERENCES source.release (release_id) ON DELETE RESTRICT,
    field_value_id  bigint REFERENCES source.field_value (field_value_id) ON DELETE RESTRICT,
    role            text NOT NULL DEFAULT 'centroid',
    latitude        ref.latitude NOT NULL,
    longitude       ref.longitude NOT NULL,
    geom            geometry(Point, 4326)
                    GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) STORED,
    raw_text        text NOT NULL,
    parse_status    obs.parse_status NOT NULL,
    parser_version  text NOT NULL,
    recorded_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT entity_point_role_known
        CHECK (role IN ('centroid', 'capital', 'reference', 'other'))
);
COMMENT ON TABLE geo.entity_point IS
  'A point a source published for an entity, with the original text beside the parsed degrees. Roles are distinguished because the Factbook''s country coordinate is an approximate centroid while its capital coordinate is a city location, and averaging the two would be meaningless.';
COMMENT ON COLUMN geo.entity_point.geom IS
  'Generated from latitude and longitude, so the point and its coordinates cannot drift apart. A generated column is right here precisely because the derivation is immutable and trivial; anything with judgement in it does not belong in one. §156.';
COMMENT ON COLUMN geo.entity_point.raw_text IS
  'The coordinate exactly as published, e.g. "50 05 N, 14 28 E". Retained because DMS parsing has real edge cases — the antimeridian, poles, hemispheres written after rather than before the number — and the original is what a corrected parser would be re-run against. §77.';

CREATE INDEX entity_point_geom_idx ON geo.entity_point USING gist (geom);
CREATE INDEX entity_point_entity_idx ON geo.entity_point (entity_id);
