#!/usr/bin/env bash
# Install the two optional PostgreSQL extensions that are not packaged for
# PostgreSQL 18 on macOS: h3 (built from source) and hypopg (Homebrew).
#
# NEITHER IS REQUIRED. The platform runs on stock PostgreSQL with PostGIS,
# pg_trgm, btree_gist, unaccent and ltree. h3 is available for derived spatial
# indexes (ADR-0011); hypopg is a development tool for evaluating hypothetical
# indexes and must never appear in a migration.
#
# Idempotent: skips anything already present.
set -euo pipefail

PG_BIN="${PG_BIN:-$(brew --prefix postgresql@18 2>/dev/null || true)/bin}"
[ -d "$PG_BIN" ] || { echo "postgresql@18 not found; set PG_BIN" >&2; exit 1; }
export PATH="$PG_BIN:$PATH"

echo "PostgreSQL: $(pg_config --version)"
SHARE="$(pg_config --sharedir)/extension"

# ── hypopg ───────────────────────────────────────────────────────────────────
if [ -f "$SHARE/hypopg.control" ]; then
  echo "hypopg: already installed"
else
  echo "hypopg: installing via Homebrew"
  brew install hypopg
  # The formula builds against postgresql@17 and @18 and links both into place.
fi

# ── h3 ───────────────────────────────────────────────────────────────────────
if [ -f "$SHARE/h3.control" ]; then
  echo "h3: already installed"
else
  echo "h3: building from source"
  command -v cmake >/dev/null || { echo "cmake required: brew install cmake" >&2; exit 1; }

  # h3-pg moved from zachasme/h3-pg (archived) to the PostGIS organisation.
  # v4.5.0 is the first release supporting PostgreSQL 18.
  WORK="$(mktemp -d)"
  trap 'rm -rf "$WORK"' EXIT
  git clone --depth 1 --branch v4.5.0 https://github.com/postgis/h3-pg.git "$WORK/h3-pg"

  # PostgreSQL's c.h includes libintl.h, and Homebrew keeps gettext keg-only, so
  # the include and library paths have to be supplied explicitly or the build
  # fails with "'libintl.h' file not found".
  GETTEXT="$(brew --prefix gettext)"
  cmake -B "$WORK/h3-pg/build" -S "$WORK/h3-pg" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_FLAGS="-I$GETTEXT/include" \
        -DCMAKE_SHARED_LINKER_FLAGS="-L$GETTEXT/lib"
  cmake --build "$WORK/h3-pg/build" -j4
  cmake --install "$WORK/h3-pg/build" --component h3-pg
fi

echo
echo "Available to PostgreSQL now:"
psql -d postgres -Atc "
  SELECT '  ' || name || ' ' || default_version
    FROM pg_available_extensions
   WHERE name IN ('h3','h3_postgis','hypopg','postgis','vector')
   ORDER BY name;"
echo
echo "Note: h3_postgis is installed by the h3 build but is NOT enabled by any"
echo "migration — it hard-requires postgis_raster. See docs/database/EXTENSIONS.md."
