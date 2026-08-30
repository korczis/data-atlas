# AGENTS.md — operating rules for coding agents

Data Atlas is a static catalogue of EU public data sources: geodata, open data,
registers, and OSINT/due-diligence sources. Curated JSON in `data/sources/` is
compiled into a CSV, and the CSV is compiled into a site, a set of per-country
pages, and two Markdown documents. Nothing here is a database of people.

Everything you need is reachable from this file. The deep documents it links to
are written in Czech; this file and [`CLAUDE.md`](CLAUDE.md) are not.

## Read before you edit

| Before you touch | Read first | Enforced by |
|---|---|---|
| `src/template.html`, `src/country.html`, `src/js/place.js` | [`docs/UI-RULES.md`](docs/UI-RULES.md) | `tools/lint_ui.py`, `tools/check_runtime_classes.py` |
| `src/js/flowbite-entry.js`, `src/js/badges.js` | [`docs/UI-RULES.md`](docs/UI-RULES.md) | `tests/e2e/` only — the linter does not read these |
| `data/sources/*.json` | [`docs/DATA-MODEL.md`](docs/DATA-MODEL.md) | `tools/build_catalog.py` (schema) + `tools/validate_sources.py` (quality) |
| `data/topics.json`, `data/countries.json`, `data/gaps.json` | [`docs/DATA-MODEL.md`](docs/DATA-MODEL.md) | `tools/validate_sources.py` |
| anything at all | this file | partly `just check` — see below |

The UI rules are architecture, not style advice. Every rule in them exists
because the failure it prevents happened, was silent, and cost a debugging
session. The document says which.

Of this file, `just check` mechanically enforces only that the recipes, paths,
links and heading anchors named in it resolve. Nothing checks that you obeyed
the rest — a green run is not evidence that you complied with this document.

## Source of truth

```
data/sources/<CODE>.json  ─┐
data/topics.json           ├─→ tools/build_catalog.py ─→ data/catalog.csv ─┐
data/countries.json        │                                               ├─→ site + docs
data/provenance.csv       ─┘                                               │
data/gaps.json      ───────────────────────────────────────────────────────┤
data/longlist.csv   ───────────────────────────────────────────────────────┘
                             tools/build_provenance.py ←─ .cache/raw.json  (local only)
```

`data/gaps.json` and `data/longlist.csv` reach the page directly — `build_page.py`
reads them itself, so editing either means rebuilding, not regenerating the CSV.

One file per country or scope; `EU` and `GLOBAL` are scopes, not countries, and
pan-European sources live there once rather than being copied into every
country file.

## Never edit by hand — these are generated

| Generated | From | Regenerate with |
|---|---|---|
| `data/catalog.csv` | `data/sources/*.json` + the taxonomies | `just catalog` |
| `docs/CATALOG.md`, `docs/COVERAGE.md` | `data/catalog.csv` | `just docs` |
| `data/longlist.csv` | `.cache/longlist.raw.csv` via `tools/sanitize.py` | `just sanitize` |
| `data/provenance.csv` | a local Chrome profile | `just provenance` |
| `dist/**` | `data/catalog.csv` + `src/` | `just build` |
| `static/*.png`, `static/favicon.*` | `src/assets/icon.svg`, `src/assets/og.html`, `src/assets/social.html` | `just assets` |
| `src/assets/flags.png`, `src/assets/flags.json` | upstream flag repository | `just flags` |

Editing `data/catalog.csv` or `docs/*.md` changes nothing durable: `just check`
overwrites them and CI compares the result against what you committed. **The
other rows have no such guard** — nothing in `check` runs `sanitize`,
`provenance`, `assets` or `flags`, and CI compares none of their outputs, so a
hand edit there survives silently until someone reruns the recipe. Change the
input in every case. `src/assets/` is mixed — `icon.svg`, `og.html` and `social.html`
are hand-written sources, the two `flags.*` files next to them are not.

`dist/` and `.cache/` are gitignored. Never commit them.

## Never hard-code a count

Item counts, country counts and coverage numbers are derived from
`data/catalog.csv` — in the page description, on the OG card, in the top bar, in
the country pages and in the tests. A number typed into prose is wrong the first
time anyone adds a source. This applies to Markdown too.

## Verify

```bash
just              # every public recipe (private `_`-prefixed ones are hidden)
just help         # the workflows, and what `just check` actually runs
just check        # everything CI runs; deterministic and offline
```

`just check` is the gate. Do not weaken it, and do not declare work finished on
a narrower command. Run the narrow checks while iterating — `just lint`,
`just test`, `just validate`, `just responsive`, `just typography`, `just a11y`,
`just e2e` — then `just check` before you hand anything back.

`just build` alone proves nothing. A broken Flowbite binding builds cleanly,
renders correct-looking markup, and does nothing when clicked, with no console
error. That is what `just e2e` and `tests/flowbite.mjs` are for.

CI runs `just check` plus one step the justfile cannot do for itself:
`git diff --exit-code` over `data/catalog.csv` and `docs/*.md`, asserting that
what `check` regenerated is what you committed. Every other check belongs in the
`check` recipe, and `.github/workflows/` then needs no edit.

`tools/check_gate.py` fails the build if a checker exists but no recipe runs it,
if a recipe in the test group is missing from `check`, or if `check` stops
depending on `catalog`, `docs` or `build` — that last one because CI's diff would
otherwise pass by finding nothing, the files never having been regenerated.

`tools/check_docs.py` fails the build if Markdown names a recipe, a path or a
link that does not exist, so documentation cannot quietly outlive what it
describes.

`just links` is **not** in `just check` — it goes out to the network, and a
deterministic clean-clone check must not depend on someone else's uptime.
It runs monthly in [its own workflow](.github/workflows/links.yml).

## Traps specific to this repository

- **Public search is not open data.** `access` says whether you can get in;
  `data` says what you can take away. A register anyone can query but nobody can
  download is `access: open, data: search`, never `api` or `bulk`. Getting this
  wrong is the single most damaging error in the catalogue, because telling
  those two apart is the reason it exists. Vocabularies:
  [`docs/DATA-MODEL.md`](docs/DATA-MODEL.md).
- **Do not infer classification from a website's own description.** Verify the
  URL, then write the description — never the other way round. Licence unknown
  means `unknown`, not a guess.
- **The site is not one page.** `tools/build_places.py` builds `dist/<code>/`
  for every country that has at least one source, plus the `dist/zeme/` index, and it is what writes the final
  `sitemap.xml` — `build_page.py` leaves a sitemap with a single URL. Country
  pages load the shared runtime from `dist/assets/`, so anything you change in
  the shared JS or CSS reaches them too.
- **Flowbite binds through the `x-flowbite` Alpine directive.** Instances are
  created by `src/js/flowbite-entry.js` when Alpine creates the node and
  destroyed when it discards it. Flowbite `data-*` attributes and
  `initFlowbite()` do not belong in this project — nothing scans for them, so
  they would silently do nothing. Enforced by the `flowbite/binding` rule; the
  reasoning is in [`docs/UI-RULES.md`](docs/UI-RULES.md). Do not replace this
  with generic upstream Flowbite advice.
- **Nothing is fetched from a remote host.** `dist/index.html` and
  `dist/artifact.html` inline everything — Tailwind, Flowbite, Alpine, the data —
  so they work from disk, offline and under a strict CSP; country pages load the
  shared runtime from `dist/assets/` and nothing else. That rules out the
  ordinary way of adding a library: no `<script src="https://…">`, no Google
  Fonts `<link>`, no `@import`, no `url(//…)`, no `fetch()`, `XMLHttpRequest`,
  `WebSocket` or `EventSource`. Add a dependency through `package.json` and the
  bundling in `tools/build_page.py`.
  **Know the gap:** `remoteResources()` in `tests/helpers.mjs` is applied by
  `tests/smoke.mjs` to `index.html` and `artifact.html` only, and
  `tests/e2e/artifact.spec.mjs` watches real requests only on the artifact. A
  remote resource added to `src/country.html` is currently caught by nothing.
- **`dist/artifact.html` is a third output, not a copy of the page.** It is one
  self-contained file for Claude Artifacts and for e-mail: it carries no `href`
  or `src` to any companion file, and it must not offer links to country pages,
  which do not exist beside it. The switch is `window.__PAGES__`, written by
  `tools/build_page.py` and read once in the template as `hasPlacePages`. A new
  link to `/<code>/` in the shared markup has to go through it.
- **jsdom does not do layout.** `tests/` catch structure and behaviour, not
  geometry. Horizontal overflow, line length and font sizes are only visible to
  `just responsive` and `just typography`, which measure in headless Chrome.
- **The public build must never read the personal browser export.** The
  catalogue has to regenerate on a clean clone with no Chrome profile present.
  `tools/validate_sources.py` enforces it by denying every script in `tools/` a
  string literal naming `raw.json` or `candidates.json`, permitting five by name:
  the four that produce or consume the export (`extract`, `scan`,
  `build_longlist`, `build_provenance`) and the validator itself, which has to
  name the tokens it searches for.
  Two limits worth knowing: the check reads string literals only, so comments and
  composed paths slip past it, and `.cache/` is otherwise **ordinary build
  scratch** — `build_page.py` writes `page.src.html`, `out.css` and
  `flowbite-min.js` there on every build. The rule is about the export, not the
  directory.
- **Verify catalogue URLs, do not invent them.** `just links --changed` checks
  only what you added; `just links` checks everything. Redirects and anti-bot
  403s are not failures — see the table in [`README.md`](README.md).

## Privacy

The data chain reads real browser history, so the boundary is structural rather
than a matter of care:

- all raw output stays in `.cache/`, which is gitignored;
- `data/longlist.csv` only ever receives what `tools/sanitize.py` passed, and
  the sanitizer is allowlist-first;
- hostnames from a private network belong in `config/private-hosts.txt`, which
  is gitignored — a committed pattern leaks as much as a committed hostname, so
  `tools/sanitize.py` keeps only generic patterns. Template:
  [`config/private-hosts.example.txt`](config/private-hosts.example.txt).

Never weaken the sanitizer, never widen what leaves `.cache/`, and never commit
anything derived from a browser profile other than the two files listed above.

## The warehouse subsystem

`warehouse/` is a **second subsystem**: a PostgreSQL data platform whose first
corpus is the CIA World Factbook. It is not in this build's path and must not
become so.

- It has its own rules: [`warehouse/AGENTS.md`](warehouse/AGENTS.md).
- It has its own gate, `just wh-check`, which is **deliberately not** part of
  `just check` — it needs a database, and a clean-clone gate must not.
- Its offline half, `just wh-test`, **is** in `just check`. Those tests need no
  database, no network and no downloaded corpus, so the clean-clone rule does
  not exclude them, and leaving them out meant a one-token change could silence
  an entire generation of the HTML parser with every gate still green.
- `just check` must keep passing with no database, no downloaded corpus and no
  network. Nothing in `warehouse/` may change that.
- Its recipes are the `wh-*` group; `tools/check_gate.py` does not scan
  `warehouse/`, so a script there is wired up by its recipe rather than by that
  checker.

Two meanings of "source of truth" now coexist, and conflating them makes both
incoherent: `data/sources/*.json` remains authoritative for **which sources
exist**; the database is authoritative for **ingested observations and their
provenance**. They are joined by one plain text pointer and neither is generated
from the other. See [`docs/database/README.md`](docs/database/README.md).

## Layout

| Path | What is in it |
|---|---|
| `data/sources/*.json` | **Source of truth.** One file per country or scope. |
| `data/topics.json`, `data/countries.json` | Topic and country vocabularies; array order is UI order. Schemas and the invariants the validator enforces: [`docs/DATA-MODEL.md`](docs/DATA-MODEL.md). |
| `data/gaps.json` | Documented absences — a verified "there is nothing here", as opposed to an unexamined blank. |
| `data/provenance.csv` | Browser-backed evidence, keyed by `id`. |
| `src/template.html` | Markup and Alpine component of the main page. |
| `src/country.html`, `src/js/place.js` | Second template: one country's page. Same UI rules apply. |
| `src/js/flowbite-entry.js` | The Flowbite ↔ Alpine binding. Read the UI rules before touching it. |
| `src/input.css` | Base shared by both templates — background, `x-cloak`, focus, reduced motion. |
| `tools/` | The data chain, the build, and every checker. |
| `tests/` | jsdom suites: `smoke` · `interact` · `meta` · `flowbite` · `places`. |
| `tests/e2e/` | Playwright, real Chrome; page list read from `dist/sitemap.xml`. |
| `static/` | Generated icons and social cards, committed so CI renders nothing. |

## Definition of done

1. The change is in the source, not in a generated artefact.
2. `just check` passes.
3. `git status --short` shows only files you meant to change — including any
   generated file your change legitimately regenerated, which must be committed
   with it.
4. Documentation that described the old behaviour now describes the new one, and
   no count was typed in by hand.
5. If catalogue URLs changed, `just links --changed` passes.

## Flowbite reference

Flowbite 2.5, open source (MIT). Copy component markup from
[`llms.txt`](https://raw.githubusercontent.com/themesberg/flowbite/refs/heads/main/llms.txt)
or [`llms-full.txt`](https://raw.githubusercontent.com/themesberg/flowbite/refs/heads/main/llms-full.txt),
not from memory — the class names move between versions.
