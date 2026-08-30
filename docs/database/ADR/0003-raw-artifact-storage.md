# ADR-0003 — Content-addressed immutable artifacts, outside git

**Status**: accepted

## Context

The corpus is 2.8 GB compressed across 38 files. It has to be verifiable,
auditable, reproducible, and it must not be re-downloadable-only, because the
publisher has stopped publishing: cia.gov now redirects the Factbook and its
archive to a farewell story.

Committing it is out. Git stores it forever, in every clone, and a repository
whose static-site build is a few hundred kilobytes would become gigabytes.
Git LFS and DVC were considered and rejected: both introduce a storage system,
a server and a failure mode, to solve a problem that a digest and a manifest
already solve.

## Decision

An artifact lives at `raw/<sha256>/<filename>`. `raw/` is gitignored. The
manifest — which *is* committed — carries the digest, size, media type, parser
family and every known retrieval URL.

Immutability is structural, not a convention: because the path contains the
digest, a changed remote file cannot land on top of the old one. It gets a new
directory, and both exist.

Downloads write to `.partial`, are hashed, and are renamed into place only on a
match. A mismatch is an error that keeps the bad bytes as
`<filename>.rejected-<digest>` for inspection.

## Consequences

- A clone is small; the corpus is one command away.
- "The file exists" and "the file is correct" are the same statement.
- Two artifacts with identical bytes and different names cannot collide.
- Disk holds every superseded version. Deliberate — that is what makes a change
  in an upstream file visible instead of silent.
- The digest is recorded with its *origin*: `computed_on_retrieval` is stronger
  evidence than `secondary_manifest`, and the schema distinguishes them.

## What would reverse this

A corpus large enough that per-developer copies become unreasonable — hundreds
of gigabytes — would justify shared object storage. The manifest already models
multiple retrievals, so adding an S3-style locator is a new row, not a redesign.
