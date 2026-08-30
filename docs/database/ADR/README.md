# Architecture decision records

One file per decision that would be expensive to reverse. Each states what was
decided, what it costs, and what evidence would justify changing it — that last
part matters most, because a decision with no stated reversal condition is a
prejudice.

| ADR | Decision |
|---|---|
| [0001](0001-canonical-versus-dimensional.md) | Canonical 3NF and the dimensional mart are separate layers |
| [0002](0002-key-strategy.md) | `bigint` identity surrogate keys; natural keys are unique constraints |
| [0003](0003-raw-artifact-storage.md) | Content-addressed immutable artifacts, outside git |
| [0004](0004-extension-policy.md) | Extensions must beat PostgreSQL core at a real problem |
| [0005](0005-observation-model.md) | One typed observation core, explicit tables only where grain differs |
| [0006](0006-temporal-semantics.md) | Three clocks, half-open ranges, explicit precision |
| [0007](0007-entity-identity.md) | Opaque entity keys; codes are temporal attributes |
| [0008](0008-provenance-and-derivation.md) | Source claims immutable; derived values in their own layer |
| [0009](0009-timescaledb.md) | TimescaleDB not used |
| [0010](0010-vector-and-search.md) | Postgres FTS and trigram now; pgvector modelled, not populated |
| [0011](0011-h3.md) | H3 available as a derived index, never as geometry |
