-- 0001_foundation — schemas, extensions, shared domains, enumerated states.
--
-- Naming rule for every schema below: a schema is named after what the data
-- *means*, never after where it came from. `demo.population`, not
-- `cia.population`. Source-specific structure is confined to `staging_*`
-- schemas and to `source.*` registry rows. See ADR-0001.
--
-- Enum versus reference table (ADR-0004): an ENUM is used only for closed
-- internal machine states that the pipeline itself defines — a run either
-- succeeded or it did not. Anything describing the world (entity types,
-- languages, religions, energy sources, government forms) is a reference table
-- with a foreign key, because the world adds members and `ALTER TYPE` in a
-- migration is a bad way to find that out.

-- ── extensions ───────────────────────────────────────────────────────────────
-- Each one is justified in docs/database/EXTENSIONS.md. The rule applied there:
-- an extension earns its place by solving a problem PostgreSQL core solves
-- worse, not by existing.

CREATE EXTENSION IF NOT EXISTS postgis;      -- required: real spatial types in geo.*
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- required: fuzzy entity-name candidates
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- required: EXCLUDE mixing = and &&
CREATE EXTENSION IF NOT EXISTS unaccent;     -- recommended: search normalisation
CREATE EXTENSION IF NOT EXISTS ltree;        -- recommended: metric domain taxonomy

-- Deliberately NOT enabled here, with reasons, so the absence is a decision and
-- not an oversight:
--   timescaledb  — annual observations are not a time-series workload. ADR-0009.
--   vector       — enabled by 0013 only, alongside the tables that use it.
--   h3           — enabled by 0007 only, for a derived spatial index.
--   postgis_raster / topology / tiger — no raster, topology or US-geocoding
--                  use case exists; tiger is a US Census ecosystem and this
--                  catalogue is European and global. ADR-0004.
--   hypopg, pg_stat_statements — diagnostics, not schema. Operations docs.
--   pgrouting, pgcrypto, pg_cron — no use case. ADR-0004.

-- ── schemas ──────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS source;
CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS obs;
CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS derived;
CREATE SCHEMA IF NOT EXISTS publication;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS search;
CREATE SCHEMA IF NOT EXISTS api;
CREATE SCHEMA IF NOT EXISTS staging_cwf;

COMMENT ON SCHEMA meta IS
  'Operational record of the platform itself: schema version, ingestion runs, quality checks and their findings, and the curation decisions a human has made. Nothing here describes the world; it describes what this system did and when.';
COMMENT ON SCHEMA source IS
  'Registry of where evidence comes from: publishers, datasets, releases, the byte-identified artifacts retrieved from them, and the raw records and field names found inside. Source-neutral in shape — a Eurostat release and a Factbook edition are the same kind of row.';
COMMENT ON SCHEMA ref IS
  'Controlled vocabularies shared across datasets: metrics, units, quantity kinds, currencies, languages, and the other taxonomies that observations point at. Reference tables rather than enums, because these grow.';
COMMENT ON SCHEMA core IS
  'Canonical identity. Geographic and political entities, their names over time, their external identifiers in every scheme, and the relations between them. An entity is a stable surrogate key; ISO codes are attributes with validity periods, never identity.';
COMMENT ON SCHEMA obs IS
  'Typed, provenance-bearing observations: one source''s claim about one metric for one entity over one reference period. Strongly typed via disjoint subtypes so a population can never hold a word.';
COMMENT ON SCHEMA geo IS
  'Spatial features and their versions. Geometry belongs to a versioned feature linked to an entity for a period, never to the entity itself — borders move, and an entity outlives any one polygon.';
COMMENT ON SCHEMA content IS
  'Narrative text preserved as published: documents, sections, fields and revisions, with the original ordering intact so a profile can be reconstructed. The substrate for full-text search, diffing between editions, and future embeddings.';
COMMENT ON SCHEMA derived IS
  'Values this platform computed rather than received, and the lineage that produced them. Kept apart from source claims so a derived preference can never be mistaken for something a publisher said.';
COMMENT ON SCHEMA publication IS
  'Assembled outputs: a profile release built by selecting among conflicting source claims, with every published value traceable to the claims behind it.';
COMMENT ON SCHEMA mart IS
  'Dimensional projection for analytics. Generated from the canonical model and rebuildable from it; never a source of truth. ADR-0001.';
COMMENT ON SCHEMA search IS
  'Search infrastructure: full-text vectors, trigram helpers, and embedding metadata. Indexes over canonical data, never the canonical data itself.';
COMMENT ON SCHEMA api IS
  'The stable read contract. Consumers select from these views and never from staging or canonical tables directly, so internal shape can change without breaking them. Each view documents its grain and its NULL semantics.';
COMMENT ON SCHEMA staging_cwf IS
  'Source-specific staging for the CIA World Factbook adapter. Lossless and shaped like the source, not like the canonical model. Deliberately isolated: nothing outside the adapter may read it, and the canonical schemas know nothing about it.';

-- ── enumerated internal states ───────────────────────────────────────────────
-- Closed sets that this pipeline defines and controls. Adding a member is a
-- deliberate migration, which is the point.

CREATE TYPE meta.run_status AS ENUM
  ('running', 'succeeded', 'failed', 'aborted');
COMMENT ON TYPE meta.run_status IS
  'Lifecycle of one ingestion run. A run left in ''running'' means the process died without recording an outcome, which is itself the finding — it is never silently promoted to success.';

CREATE TYPE source.artifact_status AS ENUM
  ('declared', 'retrieved', 'verified', 'corrupt', 'superseded');
COMMENT ON TYPE source.artifact_status IS
  'How far an artifact got. ''declared'' exists in a manifest but is not on disk; ''verified'' has been re-hashed since retrieval; ''corrupt'' failed verification and is retained as evidence rather than deleted; ''superseded'' is a known-bad artifact kept so the failure stays auditable (the 2001 Factbook zip).';

CREATE TYPE ref.value_kind AS ENUM
  ('integer', 'numeric', 'boolean', 'categorical', 'text');
COMMENT ON TYPE ref.value_kind IS
  'Which typed subtype table carries an observation''s value. Declared on the metric and enforced by composite foreign key, so an observation''s storage type is fixed by its metric rather than chosen per row.';

CREATE TYPE obs.parse_status AS ENUM
  ('parsed_exact', 'parsed_with_qualifier', 'parsed_partial', 'unparsed');
COMMENT ON TYPE obs.parse_status IS
  'How completely the raw text became a typed value. ''parsed_exact'' is a clean number; ''parsed_with_qualifier'' carried an estimate marker or note; ''parsed_partial'' recovered some of a compound field; ''unparsed'' means the raw text is preserved and nothing was invented from it. Deliberately not a numeric confidence — see ADR-0006 and §166 of the design brief.';

CREATE TYPE obs.missing_reason AS ENUM
  ('not_applicable', 'not_reported', 'unknown', 'negligible', 'suppressed', 'parse_failure');
COMMENT ON TYPE obs.missing_reason IS
  'Why a value is absent. NULL alone conflates at least six different states — a country with no coastline, a field the publisher omitted, a value the publisher printed as "NA", and a parser that failed are not the same fact. An observation with no typed value must give one of these.';

CREATE TYPE meta.mapping_status AS ENUM
  ('proposed', 'accepted', 'rejected', 'superseded');
COMMENT ON TYPE meta.mapping_status IS
  'State of a source-field-to-metric mapping, or of an entity resolution. ''proposed'' may be machine-generated; only a human or an explicit deterministic rule moves it to ''accepted''. Fuzzy matching proposes and never confirms.';

CREATE TYPE meta.issue_severity AS ENUM ('info', 'warning', 'error');
COMMENT ON TYPE meta.issue_severity IS
  'Severity of a data-quality finding. ''error'' blocks a release gate; ''warning'' is recorded and counted but does not block; ''info'' is observational. Every finding is queryable regardless of severity — nothing is written only to a log.';

CREATE TYPE derived.derivation_status AS ENUM
  ('draft', 'active', 'superseded', 'withdrawn');
COMMENT ON TYPE derived.derivation_status IS
  'Lifecycle of a derived value. Derived facts are superseded rather than updated in place, so the history of what this platform believed remains readable.';

CREATE TYPE content.provenance_kind AS ENUM
  ('source_published', 'source_derived', 'platform_derived', 'model_generated', 'human_curated');
COMMENT ON TYPE content.provenance_kind IS
  'Who authored a piece of content or a value. The distinction that matters most is ''model_generated'': language-model output is evidence about nothing and is never written into source claims. ADR-0008.';

-- ── shared domains ───────────────────────────────────────────────────────────
-- Constraints expressed once, in the type, rather than repeated in forty CHECK
-- clauses that will eventually disagree with each other.

CREATE DOMAIN ref.sha256_hex AS text
  CONSTRAINT sha256_hex_is_64_lowercase_hex CHECK (VALUE ~ '^[0-9a-f]{64}$');
COMMENT ON DOMAIN ref.sha256_hex IS
  'Lowercase hex SHA-256. Identity of a byte sequence; deliberately not a claim about origin — see docs/database/RAW-DATA.md on what a digest does and does not prove.';

CREATE DOMAIN ref.publication_year AS smallint
  CONSTRAINT publication_year_is_plausible CHECK (VALUE BETWEEN 1500 AND 2200);
COMMENT ON DOMAIN ref.publication_year IS
  'A four-digit year a document was published in. The range is loose on purpose: it rejects a parsed page number or a two-digit year without pretending to know the corpus''s real bounds.';

CREATE DOMAIN ref.percentage AS numeric(9, 6)
  CONSTRAINT percentage_within_0_100 CHECK (VALUE >= 0 AND VALUE <= 100);
COMMENT ON DOMAIN ref.percentage IS
  'A share expressed in percent, 0 to 100 inclusive. Six decimal places because published shares reach three and rounding twice loses more than it saves. Not used for growth rates or changes, which are legitimately negative and are plain numeric.';

CREATE DOMAIN ref.non_negative_numeric AS numeric
  CONSTRAINT non_negative CHECK (VALUE >= 0);
COMMENT ON DOMAIN ref.non_negative_numeric IS
  'A quantity that cannot be below zero: an area, a length, a count of airports. Growth rates and balances are not this type.';

CREATE DOMAIN ref.latitude AS double precision
  CONSTRAINT latitude_within_range CHECK (VALUE >= -90 AND VALUE <= 90);
COMMENT ON DOMAIN ref.latitude IS
  'Degrees north, WGS 84. double precision rather than numeric because this feeds geometric computation, where float is the native and appropriate representation.';

CREATE DOMAIN ref.longitude AS double precision
  CONSTRAINT longitude_within_range CHECK (VALUE >= -180 AND VALUE <= 180);
COMMENT ON DOMAIN ref.longitude IS
  'Degrees east, WGS 84, normalised to [-180, 180]. The antimeridian is representable at both ends; parsers must not clamp 180 to 179.999.';

CREATE DOMAIN ref.media_type AS text
  CONSTRAINT media_type_shape CHECK (VALUE ~ '^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$');
COMMENT ON DOMAIN ref.media_type IS
  'An IANA media type such as application/zip. Shape only — this does not assert the type is registered.';

CREATE DOMAIN ref.entity_code AS text
  CONSTRAINT entity_code_is_trimmed_and_present CHECK (VALUE = btrim(VALUE) AND length(VALUE) > 0);
COMMENT ON DOMAIN ref.entity_code IS
  'A stable, human-readable code within some scheme. Case and shape vary by scheme (ISO alpha-2 is upper, Wikidata is Q-prefixed), so only emptiness and stray whitespace are rejected here; per-scheme shape lives on ref.identifier_scheme.';

-- URLs are deliberately NOT a constrained domain. A regex strict enough to be
-- worth having rejects valid URLs, and one loose enough to be safe asserts
-- nothing. Validated in the application, at the boundary. §13.

-- ── migration ledger ─────────────────────────────────────────────────────────

CREATE TABLE meta.schema_migration (
    filename        text        PRIMARY KEY,
    checksum        ref.sha256_hex NOT NULL,
    applied_at      timestamptz NOT NULL DEFAULT now(),
    applied_by      text        NOT NULL DEFAULT current_user,
    duration_ms     integer     NOT NULL,
    CONSTRAINT duration_is_non_negative CHECK (duration_ms >= 0)
);
COMMENT ON TABLE meta.schema_migration IS
  'One row per applied migration file, in application order. The checksum makes a migration immutable after the fact: editing an applied file changes its digest and the runner refuses to proceed, which is what stops a schema from drifting away from the SQL that supposedly produced it.';
COMMENT ON COLUMN meta.schema_migration.checksum IS
  'SHA-256 of the file''s bytes as applied. Compared on every run; a mismatch is a hard error, never a warning.';
COMMENT ON COLUMN meta.schema_migration.duration_ms IS
  'Wall-clock time to apply, kept because a migration that suddenly takes minutes on a populated database is worth noticing before it runs in production.';
