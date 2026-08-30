# Source audit — CIA World Factbook

What was established by looking, before anything was downloaded. Every claim
here was checked against the artifacts or the upstream services named; where
something could not be checked, it says so.

Verified 2026-08-30.

## Findings that changed the design

**1. The official archive is gone.** `https://www.cia.gov/the-world-factbook/`
and `.../about/archives/` both return HTTP 302 to a farewell story. CIA retired
The World Factbook in February 2026. The first-priority source in any sensible
ordering — the publisher's own archive — no longer exists, which makes the
Internet Archive's captures of the CIA's own download files the most
authoritative retrievable bytes, and makes the preservation of those bytes
genuinely irreplaceable rather than merely convenient.

**2. A digest identifies bytes, not a work.** Project Gutenberg rewrites its own
boilerplate. Fetching `pg14.txt` (the 1990 edition) today returns 1,970,908
bytes hashing to `dfdbecad…`; the archived copy is 1,970,952 bytes hashing to
`2198e8ef…`. The two differ in **190 lines**, every one of them Gutenberg's
wrapper — a byte-order mark, "eBook" versus "ebook", the placement of a trademark
symbol — and **none** of them CIA text. A pipeline that pinned hashes against the
live URL would report corruption every time Gutenberg edited its licence
footer. This is why `source.artifact` (bytes) and `source.retrieval` (where they
came from) are separate tables, and why each retrieval carries `byte_stable`.

**3. The secondary manifest is honest, and is still secondary.** The
preservation project's `MANIFEST.json` was checked against its own release
assets: the 1990 asset hashes to exactly the digest the manifest claims. Its
per-file totals also reconcile — 38 files at 2,981,435,015 bytes, plus three
metadata files, equals the 41 assets and 2,981,473,675 bytes the GitHub API
reports. Two pinned JSON-era commits were confirmed to exist upstream with the
dates claimed. None of that makes its digests *our* evidence: they are recorded
as `checksum_origin = 'secondary_manifest'`, the weakest of the three strengths
the schema distinguishes.

**4. "Parser eras" is too coarse.** The working hypothesis of text / HTML / JSON
survives only at the top level. Measured across the eleven text artifacts, the
country-and-section boundary is marked **five different ways**, and two editions
mark it not at all. The HTML zips contain **three** structurally different site
generations. Details below.

**5. The JSON era's `value` fields are not CIA data.** Each field in the
2021-2025 JSON carries `content` (the CIA's text) alongside `value`, `suffix`,
`estimated` and `info_date` — which are the archiving project's own parse. The
parser here reads `content` and derives its own values; the upstream parse is
useful as a cross-check and is never presented as what the publisher said.

## Artifact inventory

38 artifacts across 36 editions, 2,981,435,015 bytes compressed. All 38 were
downloaded and all 38 verified by full re-hash against the manifest: 0 corrupt.

| Publication year | Edition label | Family | Publisher | Provider | Upstream origin | Mirror | Type | Priority | Original format | Available format | Compressed | Checksum | Alg. | Licence basis | Retrieval | Parser family | Completeness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1990 | The World Factbook 1990 | world_factbook | CIA | Project Gutenberg | `gutenberg.org` ebook 14 | GitHub release | digitised text | 2 | print | plain text | 1.97 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | **not parsed** |
| 1991 | 1991 | world_factbook | CIA | Project Gutenberg | ebook 25 | GitHub release | digitised text | 2 | print | plain text | 2.24 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | **not parsed** |
| 1992 | 1992 | world_factbook | CIA | Project Gutenberg | ebook 48 | GitHub release | digitised text | 2 | print | plain text | 2.48 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | parsed |
| 1993 | 1993 | world_factbook | CIA | Project Gutenberg | ebook 87 | GitHub release | digitised text | 2 | print | plain text | 2.65 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | parsed |
| 1994 | 1994 | world_factbook | CIA | Project Gutenberg | ebook 180 | GitHub release | digitised text | 2 | print | plain text | 2.83 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | parsed |
| 1995 | 1995 | world_factbook | CIA | Project Gutenberg | ebook 571 | GitHub release | digitised text | 2 | print | plain text | 3.01 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | parsed |
| 1996 | 1996 | world_factbook | CIA | Project Gutenberg | ebook 27675 | GitHub release | digitised text | 2 | print | plain text | 2.93 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | **not parsed** |
| 1996 | 1996 (repair) | world_factbook | CIA | Wayback (odci.gov, 1997-05-28) | Wayback capture | GitHub release | archived original | 2 | web | plain text | 3.82 MB | yes | SHA-256 | US Gov work | verified | text_cia_wayback | **not parsed** |
| 1997 | 1997 | world_factbook | CIA | Project Gutenberg | ebook 1662 | GitHub release | digitised text | 2 | print | plain text | 3.10 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | parsed |
| 1998 | 1998 | world_factbook | CIA | Project Gutenberg | ebook 2016 | GitHub release | digitised text | 2 | print | plain text | 3.48 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | parsed |
| 1999 | 1999 | world_factbook | CIA | Project Gutenberg | ebook 27676 | GitHub release | digitised text | 2 | print | plain text | 3.45 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | **not parsed** |
| 2000–2020 | 21 editions | world_factbook | CIA | Wayback capture of cia.gov download archive | `web.archive.org/…/factbook-YYYY.zip` | GitHub release | archived official | 2 | website | zipped HTML | 31–385 MB each | yes | SHA-256 | US Gov work | verified | html_cia_zip | 19 of 21 parsed |
| 2001 | 2001 (text fallback) | world_factbook | CIA | Project Gutenberg | ebook 27638 | GitHub release | digitised text | 2 | print | plain text | 7.20 MB | yes | SHA-256 | US Gov work | verified | text_gutenberg | parsed |
| 2021–2025 | 5 editions | world_factbook | CIA | `factbook/cache.factbook.json` at pinned commits | git commit | GitHub release | third-party structuring | 3 | website | zipped JSON | 4.9–6.4 MB each | yes | SHA-256 | US Gov work (+ CC0 on additions) | verified | json_factbook_cache | parsed |

Sizes and digests per artifact are in
[`warehouse/manifests/cia-world-factbook.json`](../../warehouse/manifests/cia-world-factbook.json);
they are not repeated here because a number copied into prose goes stale.

### The two special cases

**2001** has two artifacts. The HTML zip is recorded upstream as corrupt and was
never parsed; it is kept with `role = 'superseded'` so the failure stays
auditable rather than becoming an unexplained gap. The edition is carried by the
Gutenberg text.

**1996** has a repair artifact — a 1997 Wayback capture of `odci.gov` — which
upstream used to fix seven truncated countries in the Gutenberg text. Both are
held; neither is parsed yet, because 1996 uses a marker convention this parser
does not implement.

## Sub-formats, measured

The counts below come from scanning every text artifact for each marker
convention. They are why "the text era" is not one parser.

| Edition | Marker convention | Example | Parsed |
|---|---|---|---|
| 1990 | section only, `- Geography`, country heading elsewhere | — | no |
| 1991 | section only, `_*_Geography` | — | no |
| 1992 | colon prefix, space separator | `:Afghanistan Geography` | yes |
| 1993 | star prefix, comma separator | `*Afghanistan, Geography` | yes |
| 1994 | at prefix, comma separator | `@Afghanistan, Geography` | yes |
| 1995, 1997, 1998 | at prefix, colon separator | `@Czech Republic:Geography` | yes |
| 1996, 1999 | bare section headings, no country marker | `Geography` | no |
| 2001 | country and section, run of spaces | `Czech Republic    Geography` | yes |

HTML generations, distinguished by markup signature:

| Editions | Generation | Signature | Sections exposed | Parsed |
|---|---|---|---|---|
| 2000 | pre-A | none of the three signatures matched | — | no |
| 2001 | — | corrupt archive, superseded | — | no |
| 2002–2008 | A | `td class="FieldLabel"` | yes, via `<a name="Geo">` anchors | yes |
| 2009–2016 | B | `div id='field' class='category…'` | no | yes |
| 2017–2020 | C | `id="field-anchor-<section>-<field>"` | yes, in the id | yes |

Generation B does not mark sections in its country pages, so section is recorded
empty for those editions rather than guessed. Mappings match on field name, so
this costs nothing; inventing a section would split a field's history in two.

## Pre-1990

Not ingested. What was established about availability:

| Period | Title | Status | Format | Notes |
|---|---|---|---|---|
| 1962–1970 | *National Basic Intelligence Factbook* | classified at publication | — | Not publicly available as a series. |
| 1971–1974 | *National Basic Intelligence Factbook* | first unclassified companion 1971 | scan/print | **not found** as digital text. |
| 1975–1980 | *National Basic Intelligence Factbook* | public in print from 1975 | scan/print | **not found** as digital text. |
| 1981–1989 | *The World Factbook* (title adopted 1981) | HathiTrust page images | **scan/PDF only** | Would need OCR. |
| **1982** | *The World Factbook 1982* | **WikiSource, proofread** | **digitised text** | **192 subpages**, one per entry, transcribed from a DjVu scan. Machine-readable. Excludes reference maps. |

`not found` is not `does not exist`. These were checked against the Online Books
Page serial index, HathiTrust and WikiSource; a deeper search of institutional
repositories was not attempted.

**1982 is the most valuable pre-1990 target** and is the recommended next
acquisition: it is already transcribed and proofread, so it needs no OCR, and it
predates every edition currently held by ten years. It contains Yugoslavia, the
USSR, Czechoslovakia, East and West Germany and Zaire as live entries, which
exercises the entity-succession model far harder than anything from 1992.
Acquiring it means adding a `wikisource_1982` parser family and a manifest entry
per subpage or one for a bulk export; the schema needs no change.

OCR of 1981 and 1983–1989 is possible but deliberately out of scope: OCR-derived
text is not original text, and if it is ever added it must be recorded with its
own provenance and confidence rather than mixed in with transcribed editions.

## Licensing

- **CIA text and data**: works of the U.S. Government, not subject to domestic
  copyright (17 U.S.C. §105). This covers the substance of every artifact held.
- **Project Gutenberg wrapper**: PG's own boilerplate and trademark terms are
  not CIA content. The parser strips it and it is not ingested.
- **The preservation project's compilation**: released under CC0-1.0. That is
  its choice about *its own* additions — its database, its derived fields, its
  ETL — and is not a licence over the underlying public-domain text.
- **`factbook/cache.factbook.json`**: ships a CC0 statement covering its
  restructuring of the CIA content.
- **Images and maps**: not ingested. Public-domain status of US Government text
  does not automatically extend to every image reproduced alongside it, so
  `content.asset` carries its own `license_id`.

Licence provenance is stored per dataset *and* per artifact, because those are
not the same claim.

## What would make this audit stale

- A change to the preservation project's release assets. They are immutable
  GitHub release assets, so this is unlikely but not impossible.
- Wayback removing or re-serving the CIA zip captures.
- Any new digitisation of a pre-1990 edition.

`just wh-verify --all` re-hashes everything on disk and is the check that would
notice the first two.
