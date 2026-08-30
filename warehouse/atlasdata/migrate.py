"""SQL-first migrations: numbered files, applied in order, immutable once run.

There is no autogeneration and no model-to-DDL inference. The files in
`warehouse/migrations/` *are* the schema, and they are meant to be read as SQL
by a person deciding whether a constraint is right. ADR-0010.

Guarantees:

  * **Ordered.** Lexical order of `NNNN_name.sql`, which is numeric order while
    the prefix stays four digits.
  * **Transactional.** Each file runs inside one transaction; a failure applies
    none of it. PostgreSQL does transactional DDL, so this is real rather than
    best-effort.
  * **Immutable.** The SHA-256 of every applied file is recorded. Editing an
    applied migration is a hard error, because the alternative is a database
    whose shape no longer matches the SQL that claims to describe it.
  * **Honest about doing nothing.** "0 pending" is reported as such, and never
    as "migrated".
"""
from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

from . import config
from .db import DatabaseUnavailable, connect, dicts, rows, scalar
from .logging import emit, log


class MigrationError(RuntimeError):
    pass


def discover(directory: Path | None = None) -> list[Path]:
    d = directory or config.MIGRATIONS
    if not d.exists():
        raise MigrationError(f"no migrations directory at {d}")
    files = sorted(d.glob("*.sql"))
    bad = [f.name for f in files if not f.name[:4].isdigit() or f.name[4] != "_"]
    if bad:
        raise MigrationError(
            f"migration filenames must start with a four-digit number and an "
            f"underscore: {', '.join(bad)}")
    numbers = [f.name[:4] for f in files]
    dupes = {n for n in numbers if numbers.count(n) > 1}
    if dupes:
        raise MigrationError(
            f"duplicate migration numbers {sorted(dupes)} — two files with the same "
            f"prefix have no defined order between them")
    return files


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ledger_exists(conn) -> bool:
    return bool(scalar(conn, """
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = 'meta' AND table_name = 'schema_migration'"""))


def applied(conn) -> dict[str, str]:
    if not _ledger_exists(conn):
        return {}
    return {f: c for f, c in rows(conn, "SELECT filename, checksum FROM meta.schema_migration")}


def plan(conn, directory: Path | None = None) -> tuple[list[Path], list[str]]:
    """-> (pending files, integrity problems with already-applied ones)."""
    files = discover(directory)
    done = applied(conn)
    pending, problems = [], []
    for f in files:
        if f.name not in done:
            pending.append(f)
            continue
        actual = checksum(f)
        if actual != done[f.name]:
            problems.append(
                f"{f.name} was already applied but its contents have changed\n"
                f"      recorded {done[f.name][:16]}…  now {actual[:16]}…\n"
                f"      An applied migration is immutable. Add a new migration that "
                f"alters what this one created; do not edit it.")
    # A migration inserted *behind* one already applied would silently never run.
    if pending and done:
        highest_done = max(n for n in done)
        for f in pending:
            if f.name < highest_done:
                problems.append(
                    f"{f.name} is pending but sorts before {highest_done}, which is "
                    f"already applied — it would be skipped by ordering. Renumber it "
                    f"to the end.")
    return pending, problems


def cmd_migrate(args: argparse.Namespace) -> int:
    try:
        with connect() as conn:
            pending, problems = plan(conn)
            if problems:
                for p in problems:
                    log("error", p)
                return 1

            if not pending:
                log("info", f"0 pending migrations; {len(applied(conn))} already applied")
                emit({"applied": 0, "pending": 0})
                return 0

            log("info", f"{len(pending)} pending migration(s)")
            if args.dry_run:
                for f in pending:
                    log("info", f"would apply {f.name}")
                emit({"pending": [f.name for f in pending], "applied": 0})
                return 0

            for f in pending:
                sql = f.read_text(encoding="utf-8")
                started = time.monotonic()
                # Explicit commit rather than `conn.transaction()`. Reading the
                # ledger above already opened the implicit transaction, which
                # would make `transaction()` a nested savepoint: it would release
                # cleanly, commit nothing, and close() would roll the whole run
                # back while every line above reported success. That bug is
                # exactly the class this repository refuses to ship, so the
                # commit is spelled out.
                try:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        ms = int((time.monotonic() - started) * 1000)
                        # Same transaction as the DDL, so a file cannot be
                        # recorded as applied unless it fully applied.
                        cur.execute("""
                            INSERT INTO meta.schema_migration
                                   (filename, checksum, duration_ms)
                            VALUES (%s, %s, %s)""",
                            (f.name, checksum(f), ms))
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    log("error", f"{f.name} failed and was rolled back:\n    {exc}")
                    return 1
                log("info", f"applied {f.name}", ms=ms)
                emit({"migration": f.name, "duration_ms": ms})

            log("info", f"applied {len(pending)} migration(s)")
            return 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    try:
        with connect() as conn:
            done = applied(conn)
            pending, problems = plan(conn)
            print(f"database        : {scalar(conn, 'SELECT current_database()')}")
            print(f"server          : {scalar(conn, 'SHOW server_version')}")
            print(f"migrations      : {len(done)} applied, {len(pending)} pending")
            if pending:
                for f in pending:
                    print(f"  pending       : {f.name}")
            for p in problems:
                log("error", p)

            print()
            print(f"{'extension':<22}{'installed':<12}{'available':<12}")
            for e in dicts(conn, """
                SELECT a.name,
                       COALESCE(x.extversion, '-') AS installed,
                       a.default_version           AS available
                  FROM pg_available_extensions a
                  LEFT JOIN pg_extension x ON x.extname = a.name
                 WHERE a.name IN ('postgis','pg_trgm','btree_gist','unaccent','ltree',
                                  'vector','h3','timescaledb','hypopg',
                                  'pg_stat_statements','pgrouting','postgis_raster')
                 ORDER BY a.name"""):
                print(f"{e['name']:<22}{e['installed']:<12}{e['available']:<12}")

            if _ledger_exists(conn):
                print()
                counts = dicts(conn, """
                    SELECT table_schema AS schema, count(*) AS tables
                      FROM information_schema.tables
                     WHERE table_type = 'BASE TABLE'
                       AND table_schema IN ('meta','source','ref','core','obs','geo',
                                            'content','derived','publication','mart',
                                            'search','staging_cwf')
                     GROUP BY 1 ORDER BY 1""")
                print(f"{'schema':<16}{'tables':>8}")
                for c in counts:
                    print(f"{c['schema']:<16}{c['tables']:>8}")
            return 1 if problems else 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1


MANAGED_SCHEMAS = ("api", "mart", "search", "publication", "derived", "staging_cwf",
                   "content", "geo", "obs", "core", "ref", "source", "meta")


def cmd_reset(args: argparse.Namespace) -> int:
    """Drop every managed schema. Destructive, and gated on saying so."""
    if not args.yes:
        log("error",
            "refusing to drop schemas without --yes.\n"
            "    This destroys every ingested observation, every curated entity "
            "mapping and every manual conflict decision in this database.\n"
            "    Curated state is the part that is NOT reproducible by re-running "
            "the pipeline — see docs/database/OPERATIONS.md on what to export first.")
        return 1
    try:
        with connect(autocommit=True) as conn, conn.cursor() as cur:
            for s in MANAGED_SCHEMAS:
                cur.execute(f'DROP SCHEMA IF EXISTS "{s}" CASCADE')
                log("info", f"dropped schema {s}")
        log("info", "reset complete; run `atlas-data db migrate` to rebuild")
        return 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1
