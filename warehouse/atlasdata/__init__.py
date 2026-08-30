"""Ingestion and warehouse tooling for the Data Atlas data platform.

This package is source-agnostic. Nothing in it above `atlasdata.sources` knows
what the CIA World Factbook is; the Factbook is the first dataset an adapter
happens to describe, not the shape of the system.

Layout mirrors the pipeline in docs/database/ARCHITECTURE.md:

    manifest  -> what artifacts exist, and how their bytes are identified
    fetch     -> get bytes, verify them, never overwrite them
    archive   -> open containers safely (zip-slip, bombs, size ceilings)
    parsers   -> bytes -> raw records, with no silent failures
    db        -> connection, migrations, schema version
    staging   -> raw records -> source-specific staging tables
    entity    -> source entity strings -> canonical entities, or a curation queue
    mapping   -> source field names -> canonical metrics
    loader    -> staging -> typed canonical observations
    quality   -> queryable assertions about what landed
    reports   -> coverage, field evolution, storage, reconciliation
"""

# Bumped when the parsed output of any parser can change. Stored on every
# ingestion run so a value can be traced to the code that produced it, and so a
# reprocess that changes history is visible rather than silent.
PARSER_VERSION = "1.0.0"

__all__ = ["PARSER_VERSION"]
