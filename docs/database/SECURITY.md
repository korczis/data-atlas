# Security

## Acquisition

The downloader is the part that touches the outside world, so it is the part
with rules.

- **HTTPS only.** Redirects are followed manually so every hop is re-checked;
  urllib would follow a cross-scheme redirect to plain HTTP without comment.
  Wayback redirects between captures routinely, so redirects must be handled
  rather than disabled.
- **Public addresses only.** Every hop's hostname is resolved and refused if any
  of its addresses is loopback, private, link-local or otherwise non-global.
  Following redirects is what makes this necessary: without the check, one
  redirect from a mirror the manifest already trusts reaches
  `169.254.169.254`, and the cloud metadata service answers over HTTPS from a
  host no manifest ever named. This does not close DNS rebinding — the name is
  resolved for the check and again by urllib, and a short-TTL record can differ
  between the two — which would need the socket pinned to the checked address.
  It does close the redirect and misconfigured-manifest cases, which are the
  reachable ones.
- **Explicit timeouts**, bounded retries, exponential backoff, one connection at
  a time. Range resumption where the server offers it.
- **An identifying User-Agent**, overridable and never absent. A crawler that
  does not say what it is deserves to be blocked.
- **Nothing downloaded is executed.** Ever.
- **No CAPTCHA circumvention, no authentication bypass, no aggressive crawling.**
  The manifest lists specific artifacts; there is no crawler.

## Archive handling

Archives are read in place, never extracted to disk. Members are refused when:

| Condition | Handling |
|---|---|
| absolute path, or `..` in the path | refused, quarantined |
| decompresses past 8 MB | refused, quarantined |
| more members than the ceiling | refused, run abandoned |
| outside `geos/` | skipped and **counted**, not quarantined |

**"Decompresses past" is not "declares".** A zip member's `file_size` is written
by whoever built the archive, so bounding a read with it bounds nothing: a
member declaring one kilobyte inflated to 60 MB, and the memory was spent before
zipfile truncated what it returned — a 61 KB archive costing 120 MB of resident
memory, with the parser reporting success. Members are now read through a
ceiling that counts bytes actually decompressed, one past the limit being enough
to refuse; the same archive now costs 2.8 MB. The declared size is still tested
first, because it rejects an honestly oversized member without decompressing
anything, but it is a shortcut and not the guarantee.

The last row is a deliberate distinction. Everything outside `geos/` is site
apparatus — field listings, rank orders, stylesheets, tens of thousands of
images — and quarantining each one would bury the real failures in noise. They
are counted instead, so "we ignored 40,000 files" is a visible number and a
change in archive layout shows up as a jump rather than as missing countries.
The first three are genuine refusals and do become quarantine rows.

## Secrets

- **No password, connection string or key is committed anywhere.**
- `warehouse/.env.example` documents shape only and contains no secrets.
- Connection errors redact credentials before printing — `_redact()` in
  `atlasdata/db.py` — so a password cannot reach a terminal, a log or a CI
  transcript via an error message the user asked for.
- `meta.ingestion_run.config_fingerprint` is a **digest** of configuration, not
  the configuration. It cannot leak a value.
- Real passwords belong in `~/.pgpass` (mode 0600), not in an environment
  variable that appears in a process listing.

## Roles

Development runs as the owner. For a deployment, least privilege:

```sql
CREATE ROLE atlas_owner     NOLOGIN;   -- owns the schema; runs migrations
CREATE ROLE atlas_ingest    LOGIN;     -- INSERT/UPDATE on source, staging, obs, meta
CREATE ROLE atlas_analytics LOGIN;     -- SELECT on mart and api
CREATE ROLE atlas_read      LOGIN;     -- SELECT on api only

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA source, core, obs FROM PUBLIC;

GRANT USAGE ON SCHEMA api TO atlas_read, atlas_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO atlas_read, atlas_analytics;
GRANT USAGE ON SCHEMA mart TO atlas_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO atlas_analytics;
```

`PUBLIC` gets no write access anywhere. Read access is granted to `api` and
`mart` — never to `staging_*`, which is deliberately internal.

Not applied by a migration: role names and authentication are deployment
decisions, and a migration that invents roles on a developer's machine is noise.

## Network exposure

PostgreSQL binds to localhost in development. Nothing in this subsystem opens a
port, serves HTTP, or expects to be reachable.

## Privacy

This subsystem touches no personal data. The corpus is country-level statistics
and government publications.

It also has **no contact with the catalogue's privacy boundary**: nothing here
reads `.cache/`, the browser export, or anything derived from a browser profile.
That boundary is enforced on the catalogue side by `tools/validate_sources.py`,
and this subsystem stays entirely outside it — a separate directory, a separate
gate, and no shared code.
