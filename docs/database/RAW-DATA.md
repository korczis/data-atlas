# Raw data

## What a digest proves

A SHA-256 identifies **a sequence of bytes**. It says nothing about where those
bytes came from or whether they are what a publisher issued. Treating it as
proof of provenance is the most common way an archive fools itself.

This system therefore records three things separately:

| Concept | Table | Identity |
|---|---|---|
| The logical artifact | `source.artifact` | a surrogate key; carries the digest |
| Its bytes | the digest itself | SHA-256 |
| Where they were obtained | `source.retrieval` | a URL or a VCS commit |

The same bytes reachable through the publisher, a Wayback capture and a mirror
are **one artifact with three retrievals**, not three artifacts.

`source.artifact.checksum_origin` grades the claim:

| Value | Means | Strength |
|---|---|---|
| `computed_on_retrieval` | we hashed what we received | attests to our copy, from that moment |
| `upstream_published` | the publisher published this digest | attests to the publisher's copy |
| `secondary_manifest` | a third party asserted it | weakest; useful, not authoritative |

Every artifact in the Factbook corpus is currently `secondary_manifest`,
independently confirmed by re-downloading and re-hashing.

## Why URLs are not identities

Project Gutenberg rewrites its own boilerplate. The 1990 edition:

| | Size | SHA-256 |
|---|---|---|
| Archived copy | 1,970,952 | `2198e8ef…` |
| Live `pg14.txt`, fetched 2026-08-30 | 1,970,908 | `dfdbecad…` |

They differ in **190 lines**: a byte-order mark, "eBook" versus "ebook", the
position of a trademark symbol, and reworded licence text. **No CIA content
differs.** The work is the same; the bytes are not.

So each retrieval carries `byte_stable`:

- `true` — an immutable GitHub release asset. Fetching reproduces the digest.
- `false` — a live Gutenberg file, or a `git archive` of a commit. Reproduces
  *content*, not bytes.

The downloader only fetches from `byte_stable` locators. Pinning a hash against
a mutable URL would turn an unrelated upstream edit into a corruption alarm.

## Storage

```
warehouse/raw/<sha256>/<original-filename>
```

Content-addressed, so a changed remote file lands somewhere new instead of
overwriting the copy the database's provenance points at. `raw/` is gitignored;
the manifest that describes it is committed. ADR-0003.

Downloads go to `.partial`, are hashed, and are renamed into place only on a
match. A mismatch keeps the bytes as `<filename>.rejected-<digest>` and raises —
never overwrites, never retries over the top, never downgrades to a warning.

## Storage footprint, measured

| | Size |
|---|---|
| Corpus, compressed on disk | 2.8 GB (2,981,435,015 bytes across 38 artifacts) |
| Largest single artifact | `factbook-2020.zip`, 385 MB |
| Extraction | none — archives are read in-place with `zipfile`, never unpacked |
| PostgreSQL after full load | see `warehouse/reports/STORAGE.md` |

Nothing is extracted to disk. Archives are streamed from inside the zip, which
removes an entire class of extraction bugs and a few gigabytes of scratch space.

## Archive safety

The zip reader refuses rather than trusts:

- a member whose path is absolute or contains `..` (zip-slip);
- a member that **decompresses** past 8 MB, when a country page is tens of
  kilobytes — counted as it is read, not taken from the member's declared size,
  which the archive's author writes and can therefore lie about;
- an archive holding more country pages than an edition plausibly has;
- anything outside `geos/`, which is where country pages live.

Nothing downloaded is ever executed. Refusals become quarantine rows.

The filename an artifact is stored under is checked where the `Artifact` is
constructed, not only where a manifest is loaded, so no code path can hold one
whose name would escape the raw directory when joined to it.

## Verification

```bash
just wh-verify --all      # full re-hash of every artifact
just wh-status            # cheap: manifest versus disk, by size
```

`wh-verify` is the check that means something. `wh-status` is a cheap
approximation and says so. "Absent" is reported separately from "corrupt",
because not-yet-fetched is a normal state and must not read as a failure.

## Retention

None. Factbook artifacts are archival: the publisher has stopped publishing and
redirects its own archive away, so these bytes may outlive their source. No
retention policy applies, and Timescale-style retention is explicitly rejected
for source data.
