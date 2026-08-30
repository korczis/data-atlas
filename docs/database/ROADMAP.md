# Roadmap

## Built

- Reproducible acquisition: manifest, content-addressed immutable storage,
  digest verification, safe archive handling.
- SQL-first migrations with checksum immutability and ordering guards.
- Source registry carrying the full provenance chain, publisher to raw field.
- Canonical entity identity with temporal names, codes and relations.
- Typed observation core with database-enforced type safety, plus explicit
  models for compositions, bilateral facts, ranks, points and narrative.
- Four parser families across the corpus's genuinely different sub-formats.
- Field dictionary and versioned field-to-metric mappings.
- Quarantine and a queryable quality suite with release gates.
- Dimensional mart, `api` read contract, generated schema docs and ERDs.
- Reports: coverage, field evolution, storage, reconciliation.

## Not built, and why

| Not built | Reason |
|---|---|
| 1990, 1991, 1996, 1999 text editions | Four further marker conventions; two mark sections without marking countries, needing a different strategy |
| 2000 HTML edition | Its markup matches none of the three known generations |
| Pre-1990 editions | Researched, not acquired. 1982 is transcribed and ready; 1981 and 1983–1989 are page scans needing OCR |
| Embeddings and a vector index | No embeddings generated, so no benchmark to justify index parameters. ADR-0010 |
| Boundary geometry | No boundary dataset ingested; `geo.feature_version` is empty |
| `publication.*` population | Schema exists; no profile has been generated |
| Prismatic integration | Not verified as present in this workspace, so no interfaces were invented |

## Known gaps the review found and this pass did not close

Recorded rather than quietly carried, because a known gap left undocumented
becomes an unknown one.

| Gap | Impact | Why not now |
|---|---|---|
| The 2000 HTML edition is a **fourth** generation — paragraph-based (`<p><b>Location:</b>`), no `td.FieldLabel`, no `category_data`, no `field-anchor-` | one whole edition, ~267 entries, unparsed | Needs a fourth extraction routine; mechanical, and the markup is now characterised |
| No **load-stage reconciliation** check | the check that would have caught the silent composition/bilateral drops does not exist; `record_count_reconciliation` stops at the staging boundary | The drops themselves are fixed; the structural check that would catch the *next* one is the real work |
| Narrative provenance is weaker than numeric | `content.field` traces to artifact and record, but not to an individual `source.field_value` | Needs a column and a backfill; the traceability that exists is genuine, just coarser. Documented in PROVENANCE.md |
| `api.provenance` covers observations only | no equivalent walk for compositions, bilateral facts, points or narrative | Straightforward to add once the narrative link above is decided |
| `geo.entity_point` has no `ingestion_run_id` | a coordinate cannot cite the run that produced it, unlike every other fact table | One column, one migration |
| Staging duplicates raw text when a `(record, field, ordinal)` collides | the losing row's text is dropped by `ON CONFLICT DO NOTHING`; the *count* is now honest, the *data* is still lost | Rare (the 2015/2017 editions); needs a disambiguating ordinal rather than a suppression |
| `json_era` skips fields with an empty name or content without recording it | currently zero occurrences across the whole corpus | Latent; worth closing when that parser is next touched |

## Next, in order of value

**1. The 1982 edition.** The highest-value single addition. Already transcribed
and proofread on WikiSource across 192 subpages, so it needs no OCR. It predates
everything currently held by ten years and contains Yugoslavia, the USSR,
Czechoslovakia, both Germanies and Zaire as live entries — which exercises the
succession model far harder than anything from 1992. Needs a `wikisource_1982`
parser family and manifest entries. No schema change.

**2. The four unparsed text editions and the 2000 HTML.** Mechanical work,
well-scoped: each needs a marker convention added to `text_era.py`, or a fourth
generation in `html_era.py`. The measurement of what each uses is already in the
source audit.

**3. Mapping coverage.** The largest gap in the system. Most distinct source
fields have no canonical mapping, so their values are preserved as raw text but
not typed. Every mapping added converts more of the corpus **without re-reading
a byte** — that is what the layered design bought. Profile with
`just wh-reports` and work down `source.field_definition` by frequency.

**4. A second dataset.** The real test of source-agnosticism. Eurostat or a
national statistical office would exercise the conflict model with genuinely
independent claims about the same metric, entity and period — which at present
only occurs between Factbook editions revising themselves.

**5. Entity curation.** Bootstrapped entities are `unclassified` by design.
Classifying them, and merging entities across future sources, is the curation
work the schema is built to record.

**6. Boundary geometry.** Natural Earth or GISCO into `geo.feature_version`.
Needs no schema change, and would make the H3 and spatial-index decisions
concrete rather than prospective.

## Deferred until there is evidence

- **Partitioning** — `obs.observation` is ~160k rows. Revisit past ~10^8.
- **TimescaleDB** — needs a genuinely high-frequency source. ADR-0009.
- **dbt or SQLMesh** — the mart is seven views. Revisit at tens of models.
- **An external search engine** — Postgres FTS has not been shown insufficient.
- **A UI** — out of scope; `api.*` is the contract one would build against.
