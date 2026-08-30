-- 0016_search — full-text search over narrative content, and embedding metadata.
--
-- Postgres FTS is the baseline that has to be shown insufficient before an
-- external search engine is worth its operational cost. ADR-0010.

-- A stored generated tsvector rather than an expression index: the vector is
-- computed once on write instead of on every index scan, it is inspectable when
-- a match is surprising, and the configuration is fixed in one place rather
-- than repeated in every query that hopes to match the index.
ALTER TABLE content.field
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(text_content, ''))) STORED;
COMMENT ON COLUMN content.field.search_vector IS
  'Full-text vector over the cleaned narrative text, English configuration. Generated, so it cannot drift from text_content. The configuration is deliberately fixed: this corpus is published in English, and a per-row language would need a language column the source does not reliably provide.';

CREATE INDEX content_field_search_idx ON content.field USING gin (search_vector);
COMMENT ON INDEX content.content_field_search_idx IS
  'GIN over the generated tsvector. GIN rather than GiST because the corpus is static after load and GIN is faster to search and slower to update, which is exactly the right trade for archival text.';

CREATE INDEX content_field_trgm_idx
    ON content.field USING gin (left(text_content, 2000) gin_trgm_ops);
COMMENT ON INDEX content.content_field_trgm_idx IS
  'Trigram index over the first 2000 characters, for substring and misspelling matches that word-based full-text search cannot answer. Truncated because a trigram index over unbounded prose costs far more than the tail of a long passage is worth.';

CREATE VIEW api.narrative_search AS
SELECT f.content_field_id, e.slug AS entity_slug, d.title AS entity_title,
       rel.edition_year, s.name AS section, f.name AS field,
       f.text_content, f.search_vector
  FROM content.field f
  JOIN content.section s ON s.section_id = f.section_id
  JOIN content.document d ON d.document_id = s.document_id
  JOIN source.release rel ON rel.release_id = d.release_id
  LEFT JOIN core.entity e ON e.entity_id = d.entity_id;
COMMENT ON VIEW api.narrative_search IS
  'Grain: one row per narrative field of one entity in one edition. Search with `search_vector @@ plainto_tsquery(''english'', ...)` and rank with ts_rank. entity_slug is NULL only for a document whose entity was never resolved, which the loader currently prevents.';

-- ── embeddings: metadata now, vectors later ──────────────────────────────────
-- The vector extension and an index are deliberately NOT created. There are no
-- embeddings, so there is nothing to benchmark and no recall target to tune
-- toward; an HNSW index over an empty table would imply a benchmark nobody ran.
-- ADR-0010.
--
-- The metadata table exists first because the hard part of embeddings is
-- reproducibility, not the index: an embedding is worthless unless it can be
-- tied to the exact text, model, model version, dimensionality, distance metric
-- and chunking algorithm that produced it.

CREATE TABLE search.embedding_model (
    embedding_model_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            ref.entity_code NOT NULL,
    provider        text NOT NULL,
    model_name      text NOT NULL,
    model_version   text NOT NULL,
    dimensions      integer NOT NULL,
    distance_metric text NOT NULL,
    chunking_algorithm text NOT NULL,
    chunking_version integer NOT NULL DEFAULT 1,
    notes           text NOT NULL DEFAULT '',
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT embedding_model_code_unique UNIQUE (code),
    CONSTRAINT embedding_model_dimensions_positive CHECK (dimensions > 0),
    CONSTRAINT embedding_model_distance_known
        CHECK (distance_metric IN ('cosine', 'l2', 'inner_product'))
);
COMMENT ON TABLE search.embedding_model IS
  'One configuration that can produce embeddings. Everything needed to regenerate a vector identically is here, because an embedding whose provenance is unknown cannot be trusted, compared, or reproduced — and silently mixing two models in one index makes every distance meaningless.';

CREATE TABLE search.embedding (
    embedding_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    embedding_model_id integer NOT NULL
                    REFERENCES search.embedding_model (embedding_model_id)
                    ON DELETE RESTRICT,
    content_field_id bigint
                    REFERENCES content.field (content_field_id) ON DELETE CASCADE,
    chunk_ordinal   integer NOT NULL DEFAULT 0,
    source_text_sha256 ref.sha256_hex NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT embedding_unique UNIQUE (embedding_model_id, content_field_id, chunk_ordinal)
);
COMMENT ON TABLE search.embedding IS
  'Metadata for one embedded chunk. The vector column itself is added by the migration that first generates embeddings, together with an index chosen from a benchmark — not before. `source_text_sha256` binds the embedding to the exact text version it was computed from, so a later edit to that text is detectable rather than silently leaving a stale vector in the index.';
COMMENT ON COLUMN search.embedding.source_text_sha256 IS
  'Digest of the exact chunk text embedded. The check that makes staleness visible: if the content changes, the digest no longer matches and the embedding is known to need regeneration.';
