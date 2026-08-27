# Geodata Atlas — katalog GIS a geodatových zdrojů
#
# `just` vypíše všechny recepty, `just help` shrne workflow.

set shell := ["bash", "-uc"]

_default:
    @just --list --unsorted

# Shrnutí hlavních workflow
[group('info')]
help:
    @echo "Geodata Atlas"
    @echo
    @echo "  just install      instalace npm závislostí"
    @echo "  just build        postaví dist/index.html z data/*.csv"
    @echo "  just test         ověří, že stránka odpovídá datům"
    @echo "  just serve        lokální náhled na http://localhost:8000"
    @echo "  just check        build + test, tohle běží i v CI"
    @echo
    @echo "Data (jen lokálně, potřebuje Chrome profil na disku):"
    @echo "  just refresh      celý řetěz extract → scan → catalog → sanitize → build"
    @echo
    @echo "Katalog v data/catalog.csv se edituje ručně nebo přes tools/build_catalog.py."

# ── build ─────────────────────────────────────────────────────────────────────

# Instalace npm závislostí
[group('build')]
install:
    npm install

# Postaví jednosouborovou stránku do dist/
[group('build')]
build:
    python3 tools/build_page.py

# Vygeneruje docs/CATALOG.md z data/catalog.csv
[group('build')]
docs:
    python3 tools/build_docs.py

# Build + testy — stejné, co běží v CI
[group('build')]
check: build test

# ── testy ─────────────────────────────────────────────────────────────────────

# Ověří, že se stránka nastartuje a souhlasí s CSV
[group('test')]
test:
    node tests/smoke.mjs
    node tests/interact.mjs

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

# Sestaví kurátorovaný katalog a syrový long list
[group('data')]
catalog:
    python3 tools/build_catalog.py

# Vyčistí long list do zveřejnitelné podoby
[group('data')]
sanitize:
    python3 tools/sanitize.py

# Celý datový řetěz od Chrome až po postavenou stránku
[group('data')]
refresh: extract scan catalog sanitize docs build

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
