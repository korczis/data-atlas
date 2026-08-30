# ADR-0010 — Postgres FTS and trigram now; pgvector modelled, not populated

**Status**: accepted

## Context

Three search needs: exact and alias lookup of entity names, fuzzy matching for
entity resolution, and full-text search over narrative content. A fourth,
semantic search, is plausible later.

## Decision

- **Exact and alias lookup**: B-tree on normalised names. Nothing beats it.
- **Fuzzy candidates**: `pg_trgm` GIN index on lowercased names. Used to
  *propose* entity matches for human review, never to accept one.
- **Full text**: PostgreSQL `tsvector` with GIN, plus `unaccent` for
  normalisation.
- **Semantic**: `search.embedding_model` and `search.embedding` are modelled and
  the `vector` extension is available. **No embeddings are generated and no
  vector index exists.**

No external search engine. Elasticsearch, OpenSearch and Meilisearch are all
rejected for now: Postgres FTS is the baseline that has to be shown insufficient
first, and an external index would be a second store to keep consistent.

## Why no vector index

Building an HNSW index requires choosing an operator class, a distance metric,
`m` and `ef_construction`, and then a search-time `ef_search` — and every one of
those choices is meaningless without rows to measure against and a recall target
to measure toward. Creating one over an empty table would be a decoration that
implies a benchmark nobody ran.

The metadata table exists because the *hard* part of embeddings is
reproducibility, not the index: an embedding must be tied to the exact text
version, model, model version, dimensionality, distance metric and chunking
algorithm that produced it, or it cannot be regenerated or trusted. That schema
is worth having before the first embedding, not after.

## Consequences

- Search works today with no extra infrastructure.
- Similarity is never treated as evidence. A trigram or vector score may surface
  a candidate; confirming an identity requires deterministic evidence or a
  human, and the database enforces it.
- When embeddings are added, the index decision comes with a benchmark against
  exact search, documented in PERFORMANCE.md.

## What would reverse this

Measured full-text queries that are too slow, or a real semantic-search
requirement with enough content to benchmark. Both are additive.
