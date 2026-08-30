# Data Atlas — EU catalogue of geodata, open data, registers and OSINT/DD sources.
#
# `just` lists every recipe, `just help` summarises the workflows.
# Agent-facing rules: AGENTS.md. Claude Code specifics: CLAUDE.md.

set shell := ["bash", "-uc"]

_default:
    @just --list --unsorted

# Summary of the main workflows
[group('info')]
help:
    @echo "Data Atlas"
    @echo
    @echo "Source of truth: data/sources/*.json — one file per country or scope."
    @echo "data/catalog.csv, docs/CATALOG.md and docs/COVERAGE.md are generated from them."
    @echo "Adding a country or a source: docs/DATA-MODEL.md"
    @echo
    @echo "Build:"
    @echo "  just install      install npm dependencies"
    @echo "  just catalog      data/sources/*.json  -> data/catalog.csv"
    @echo "  just docs         data/catalog.csv     -> docs/CATALOG.md, docs/COVERAGE.md"
    @echo "  just build        data/catalog.csv     -> dist/ (index, country pages, artifact)"
    @echo "  just assets       regenerate icons and the OG card into static/"
    @echo "  just serve        local preview on http://localhost:8000"
    @echo
    @echo "Checks — offline and deterministic, all of them run in CI:"
    @echo "  just validate     description quality, dates, gaps, topic relations"
    @echo "                    (schema and duplicates are enforced by just catalog)"
    @echo "  just lint         UI conventions, runtime classes, Markdown refs, gate coverage"
    @echo "  just test         built pages agree with the CSV (jsdom)"
    @echo "  just responsive   horizontal overflow at 320-1536 px, headless Chrome"
    @echo "  just typography   line length, field font size, heading hierarchy"
    @echo "  just a11y         axe-core in both themes at two widths"
    @echo "  just e2e          click through the built pages in real Chrome (Playwright)"
    @just _check-line
    @echo
    @echo "Eyes only, not in 'just check':"
    @echo "  just shots        screenshots into .cache/shots/ — for defects measurement cannot see"
    @echo
    @echo "Needs the network, deliberately outside 'just check':"
    @echo "  just links        verify catalogue URLs"
    @echo "                    narrow it: --country AT · --topic companies · --changed"
    @echo
    @echo "Needs a Chrome profile on disk, local only:"
    @echo "  just refresh      extract -> scan -> longlist -> sanitize -> provenance -> catalog -> docs -> build"

# Fails early and legibly when npm install has not run. Without it the first
# symptom is `esbuild selhal` from deep inside the build, which says nothing
# about what to do.
_deps:
    @test -d node_modules || { \
        echo "node_modules/ is missing — run 'just install' first" >&2; exit 1; }

# `check` depends on this first so a machine without Chrome fails in the first
# second, rather than after build, lint and the jsdom suites have all run.
#
# Fails when no Chrome is installed. Without this the three measuring checks
# find no browser, print a note, and return success — `just check` goes green
# having measured no layout, no typography and no accessibility at all.
# Discovery is not reimplemented here; it calls the repository's own locator.
_chrome:
    @python3 -c "import sys; sys.path.insert(0, 'tools'); \
        from check_responsive import find_chrome; sys.exit(0 if find_chrome() else 1)" \
      || { echo "no Chrome found — install Google Chrome, or point CHROME_PATH at it." >&2; \
           echo "responsive, typography, a11y and e2e all measure in a real browser." >&2; \
           exit 1; }

# Prints what `check` actually depends on, read out of this justfile rather than
# copied into prose — a hand-written list goes stale the first time `check` changes.
_check-line:
    @just --dump --dump-format json \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print('  just check        ' + ' + '.join(x['recipe'] for x in d['recipes']['check']['dependencies'] if not x['recipe'].startswith('_')))"

# ── build ─────────────────────────────────────────────────────────────────────

# Install npm dependencies
[group('build')]
install:
    npm install

# Assemble data/catalog.csv from the curated sources in data/sources/
[group('build')]
catalog:
    python3 tools/build_catalog.py

# Build the single-file page and the per-country pages into dist/
[group('build')]
build: _deps
    python3 tools/build_page.py
    python3 tools/build_places.py

# Generate docs/CATALOG.md and docs/COVERAGE.md from data/catalog.csv
[group('build')]
docs:
    python3 tools/build_docs.py

# Regenerate icons and the OG card into static/ (needs Chrome + ImageMagick)
[group('build')]
assets:
    python3 tools/build_assets.py

# Regenerate the flag sprite from the upstream repository (network + ImageMagick)
[group('build')]
flags:
    python3 tools/build_flags.py

# Everything CI runs. Deterministic and offline — `just links` stays out on purpose.
[group('build')]
check: _deps _chrome validate catalog docs build lint test responsive typography a11y e2e wh-test
    @python3 tools/check_generated.py

# ── tests ─────────────────────────────────────────────────────────────────────

# Check that the built pages start up and agree with the CSV
[group('test')]
test: _deps build
    node tests/smoke.mjs
    node tests/interact.mjs
    node tests/meta.mjs
    node tests/flowbite.mjs
    node tests/places.mjs

# Repository conventions: UI templates (docs/UI-RULES.md), the classes Flowbite
# adds at runtime, Markdown references, and that `check` is still the whole gate
[group('test')]
lint: build
    python3 tools/lint_ui.py
    python3 tools/check_runtime_classes.py
    python3 tools/check_docs.py
    python3 tools/check_gate.py

# Check the curated data: schema, duplicates, description quality
[group('test')]
validate:
    python3 tools/validate_sources.py

# Measure horizontal overflow in headless Chrome at 320-1536 px
[group('test')]
responsive: _chrome build
    python3 tools/check_responsive.py
    python3 tools/check_responsive.py --page place

# Screenshots into .cache/shots/ — for the defects measurement cannot see
[group('test')]
shots *ARGS:
    python3 tools/shoot.py {{ ARGS }}

# Click through the built pages in a real browser (Playwright, system Chrome)
[group('test')]
e2e *ARGS: _deps _chrome build
    npx playwright test {{ ARGS }}

# Typography: line length, field font size, heading hierarchy
[group('test')]
typography: _chrome build
    python3 tools/check_typography.py
    python3 tools/check_typography.py --page place

# Accessibility audit (axe-core) in both themes at two widths
[group('test')]
a11y: _deps _chrome build
    python3 tools/check_a11y.py
    python3 tools/check_a11y.py --page place

# Verify links (network, outside `check`); narrow: --country AT --topic companies --changed
[group('test')]
links *ARGS:
    python3 tools/check_links.py {{ ARGS }}

# Local preview of the built site
[group('test')]
serve: build
    @echo "http://localhost:8000"
    python3 -m http.server 8000 --directory dist

# ── data ──────────────────────────────────────────────────────────────────────
# These recipes need a Chrome profile on disk and never run in CI.

# Pull bookmarks and history out of a Chrome profile into .cache/
[group('data')]
extract profile="":
    python3 tools/extract.py {{ if profile != "" { "--profile " + profile } else { "" } }}

# Run .cache/raw.json through the keyword filter for geo candidates
[group('data')]
scan:
    python3 tools/scan.py

# Produce the raw long list of candidates from .cache/candidates.json
[group('data')]
longlist:
    python3 tools/build_longlist.py

# Recompute browser-backed provenance into data/provenance.csv (needs .cache/raw.json)
[group('data')]
provenance:
    python3 tools/build_provenance.py

# Clean the long list down to a publishable form
[group('data')]
sanitize:
    python3 tools/sanitize.py

# The whole data chain, from Chrome to the built site
[group('data')]
refresh: extract scan longlist sanitize provenance catalog docs build

# ── warehouse ─────────────────────────────────────────────────────────────────
# The historical/analytical PostgreSQL subsystem in warehouse/. Entirely
# separate from the static catalogue build: `just check` neither runs these nor
# depends on them, because they need a database and, for `wh-fetch`, the network.
# Rules and layout: warehouse/AGENTS.md · docs: docs/database/README.md

# Install optional PostgreSQL extensions (h3 from source, hypopg via brew)
[group('warehouse')]
wh-extensions:
    bash warehouse/scripts/install-optional-extensions.sh

# Install the one Python dependency the warehouse needs (psycopg 3)
[group('warehouse')]
wh-install:
    uv pip install --python "$(command -v python3)" 'psycopg[binary]>=3.2'

# What the source manifest says exists, and what is on disk
[group('warehouse')]
wh-status:
    PYTHONPATH=warehouse python3 -m atlasdata.cli source status

# Download raw artifacts and verify their digests (network; narrow it)
[group('warehouse')]
wh-fetch *ARGS:
    PYTHONPATH=warehouse python3 -m atlasdata.cli source fetch {{ ARGS }}

# Re-hash every downloaded artifact against the manifest
[group('warehouse')]
wh-verify *ARGS:
    PYTHONPATH=warehouse python3 -m atlasdata.cli source verify {{ ARGS }}

# Apply pending SQL migrations to the database
[group('warehouse')]
wh-migrate:
    PYTHONPATH=warehouse python3 -m atlasdata.cli db migrate

# Applied migrations, extension state and table counts
[group('warehouse')]
wh-db-status:
    PYTHONPATH=warehouse python3 -m atlasdata.cli db status

# Parse artifacts into staging, losslessly (needs the raw files)
[group('warehouse')]
wh-stage *ARGS:
    PYTHONPATH=warehouse python3 -m atlasdata.cli ingest stage {{ ARGS }}

# Resolve entities and load typed canonical observations
[group('warehouse')]
wh-load *ARGS:
    PYTHONPATH=warehouse python3 -m atlasdata.cli ingest load {{ ARGS }}

# Refresh the dimensional mart and update planner statistics
[group('warehouse')]
wh-mart:
    PYTHONPATH=warehouse python3 -m atlasdata.cli mart build
    PYTHONPATH=warehouse python3 -m atlasdata.cli mart analyze

# Run the data-quality suite; non-zero when a release gate fails
[group('warehouse')]
wh-quality:
    PYTHONPATH=warehouse python3 -m atlasdata.cli quality run

# Regenerate coverage, field-evolution, storage and reconciliation reports
[group('warehouse')]
wh-reports:
    PYTHONPATH=warehouse python3 -m atlasdata.cli report coverage
    PYTHONPATH=warehouse python3 -m atlasdata.cli report fields
    PYTHONPATH=warehouse python3 -m atlasdata.cli report storage
    PYTHONPATH=warehouse python3 -m atlasdata.cli report reconcile

# Regenerate the schema reference and ERDs from the live database
[group('warehouse')]
wh-docs:
    PYTHONPATH=warehouse python3 -m atlasdata.cli docs generate

# Lint the warehouse Python package (scoped to warehouse/, not the whole repo)
[group('warehouse')]
wh-lint:
    cd warehouse && python3 -m ruff check atlasdata/ tests/

# Offline unit tests for the parsers; needs neither database nor network
[group('warehouse')]
wh-test:
    python3 warehouse/tests/test_values.py
    python3 warehouse/tests/test_coordinates.py
    python3 warehouse/tests/test_text_era.py
    python3 warehouse/tests/test_html_era.py
    python3 warehouse/tests/test_json_era.py
    python3 warehouse/tests/test_manifest.py

# Schema and constraint tests against the live database
[group('warehouse')]
wh-test-db:
    python3 warehouse/tests/test_schema.py
    python3 warehouse/tests/test_api_views.py

# Everything the warehouse can check offline against an existing database
[group('warehouse')]
wh-check: wh-lint wh-test wh-migrate wh-test-db wh-quality

# Open a psql session on the warehouse database
[group('warehouse')]
wh-psql:
    psql "${ATLAS_DATABASE_URL:-${DATABASE_URL:-postgresql:///atlas_data}}"

# DROP every warehouse schema. Curated mappings are re-seeded; entity curation is not.
[confirm("Drop every warehouse schema, including curated entity and mapping decisions?")]
[group('warehouse')]
wh-reset:
    PYTHONPATH=warehouse python3 -m atlasdata.cli db reset --yes

# ── maintenance ───────────────────────────────────────────────────────────────

# Delete build outputs and intermediates
[confirm("Delete dist/ and .cache/?")]
[group('maint')]
clean:
    rm -rf dist .cache

# Delete node_modules as well
[confirm("Delete dist/, .cache/ and node_modules/?")]
[group('maint')]
clean-all:
    rm -rf dist .cache node_modules
