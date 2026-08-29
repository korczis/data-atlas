# Data Atlas — katalog geodat, otevřených dat, registrů a OSINT/DD zdrojů EU
#
# `just` vypíše všechny recepty, `just help` shrne workflow.

set shell := ["bash", "-uc"]

_default:
    @just --list --unsorted

# Shrnutí hlavních workflow
[group('info')]
help:
    @echo "Data Atlas"
    @echo
    @echo "  just install      instalace npm závislostí"
    @echo "  just catalog      složí data/catalog.csv z data/sources/*.json"
    @echo "  just build        postaví dist/index.html z data/catalog.csv"
    @echo "  just validate     kontrola kurátorovaných dat (schéma + kvalita)"
    @echo "  just test         ověří, že stránka odpovídá datům"
    @echo "  just serve        lokální náhled na http://localhost:8000"
    @echo "  just lint         konvence Flowbite + Alpine (docs/UI-RULES.md)"
    @echo "  just responsive   měření rozvržení v headless Chrome"
    @echo "  just shots        screenshoty do .cache/shots/ (mrkni se na ně)"
    @echo "  just a11y         audit přístupnosti přes axe-core"
    @echo "  just links        ověření odkazů v katalogu (chodí po síti)"
    @echo "                    zúžení: --country AT · --topic companies · --changed"
    @echo "  just check        build + lint + test + responsive + a11y"
    @echo "  just assets       přegeneruje ikony a OG kartu"
    @echo
    @echo "Data (jen lokálně, potřebuje Chrome profil na disku):"
    @echo "  just refresh      extract → scan → longlist → provenance → catalog → build"
    @echo
    @echo "Zdrojem pravdy jsou data/sources/*.json — jeden soubor na zemi nebo rozsah."
    @echo "data/catalog.csv, docs/CATALOG.md i docs/COVERAGE.md se z nich generují."
    @echo "Jak přidat zemi nebo zdroj: docs/EU-EXPANSION-PLAN.md"

# ── build ─────────────────────────────────────────────────────────────────────

# Instalace npm závislostí
[group('build')]
install:
    npm install

# Složí data/catalog.csv z kurátorovaných zdrojů v data/sources/
[group('build')]
catalog:
    python3 tools/build_catalog.py

# Postaví jednosouborovou stránku do dist/
[group('build')]
build:
    python3 tools/build_page.py

# Vygeneruje docs/CATALOG.md a docs/COVERAGE.md z data/catalog.csv
[group('build')]
docs:
    python3 tools/build_docs.py

# Přegeneruje ikony a OG kartu do static/ (potřebuje Chrome + ImageMagick)
[group('build')]
assets:
    python3 tools/build_assets.py

# Přegeneruje sprite s vlajkami ze zdrojového repozitáře (síť + ImageMagick)
[group('build')]
flags:
    python3 tools/build_flags.py

# Build + testy — stejné, co běží v CI
[group('build')]
check: validate catalog build lint test responsive a11y

# ── testy ─────────────────────────────────────────────────────────────────────

# Ověří, že se stránka nastartuje a souhlasí s CSV
[group('test')]
test:
    node tests/smoke.mjs
    node tests/interact.mjs
    node tests/meta.mjs
    node tests/flowbite.mjs

# Vynutí konvence Flowbite + Alpine nad src/template.html
[group('test')]
lint:
    python3 tools/lint_ui.py
    python3 tools/check_runtime_classes.py

# Ověří kurátorovaná data: schéma, duplicity, kvalita popisů
[group('test')]
validate:
    python3 tools/validate_sources.py

# Změří vodorovné přetečení v headless Chrome na 320–1536 px
[group('test')]
responsive:
    python3 tools/check_responsive.py

# Screenshoty stránky do .cache/shots/ — na vady, které měření nepozná
[group('test')]
shots *ARGS:
    python3 tools/shoot.py {{ ARGS }}

# Audit přístupnosti (axe-core) v obou motivech a na dvou šířkách
[group('test')]
a11y:
    python3 tools/check_a11y.py

# Ověří odkazy (síť, mimo `check`); zúžení: --country AT --topic companies --changed
[group('test')]
links *ARGS:
    python3 tools/check_links.py {{ ARGS }}

# Lokální náhled postavené stránky
[group('test')]
serve: build
    @echo "http://localhost:8000"
    python3 -m http.server 8000 --directory dist

# ── data ──────────────────────────────────────────────────────────────────────
# Tyhle recepty potřebují Chrome profil na disku a v CI neběží.

# Vytáhne záložky a historii z Chrome profilu do .cache/
[group('data')]
extract profile="":
    python3 tools/extract.py {{ if profile != "" { "--profile " + profile } else { "" } }}

# Projede .cache/raw.json keyword filtrem na geo kandidáty
[group('data')]
scan:
    python3 tools/scan.py

# Vyrobí syrový long list kandidátů z .cache/candidates.json
[group('data')]
longlist:
    python3 tools/build_longlist.py

# Přepočítá doložení z prohlížeče do data/provenance.csv (chce .cache/raw.json)
[group('data')]
provenance:
    python3 tools/build_provenance.py

# Vyčistí long list do zveřejnitelné podoby
[group('data')]
sanitize:
    python3 tools/sanitize.py

# Celý datový řetěz od Chrome až po postavenou stránku
[group('data')]
refresh: extract scan longlist sanitize provenance catalog docs build

# ── údržba ────────────────────────────────────────────────────────────────────

# Smaže build výstupy a mezivýsledky
[confirm("Smazat dist/ a .cache/?")]
[group('maint')]
clean:
    rm -rf dist .cache

# Smaže i node_modules
[confirm("Smazat dist/, .cache/ a node_modules/?")]
[group('maint')]
clean-all: 
    rm -rf dist .cache node_modules
