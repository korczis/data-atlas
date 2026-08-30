"""Refreshing the dimensional projection.

The mart is materialised views over the canonical model, so "building" it is a
refresh. There is no load script and no second copy of the transformation logic:
the view definition in `migrations/0012_mart.sql` is the only place the mapping
from canonical to dimensional exists. ADR-0001.

Refresh order matters: dimensions before facts, so a fact refreshed against a
stale dimension cannot briefly reference a key that is not there yet.
"""
from __future__ import annotations

import argparse
import time

from .db import DatabaseUnavailable, connect, scalar
from .logging import emit, log

# Dimensions first, then facts. Within each group the order is irrelevant.
REFRESH_ORDER = (
    "mart.dim_entity",
    "mart.dim_metric",
    "mart.dim_release",
    "mart.dim_period",
    "mart.fact_observation",
    "mart.fact_composition",
    "mart.fact_bilateral",
)


def refresh(conn, *, concurrently: bool = False) -> list[dict]:
    results = []
    for view in REFRESH_ORDER:
        started = time.monotonic()
        with conn.cursor() as cur:
            # CONCURRENTLY needs a unique index (every view here has one) and
            # cannot run inside a transaction block, so it is only offered
            # explicitly. On a first build the view is empty and CONCURRENTLY
            # would fail, which is why it is not the default.
            keyword = "CONCURRENTLY " if concurrently else ""
            cur.execute(f"REFRESH MATERIALIZED VIEW {keyword}{view}")
        conn.commit()
        rows = scalar(conn, f"SELECT count(*) FROM {view}")
        ms = int((time.monotonic() - started) * 1000)
        results.append({"view": view, "rows": rows, "duration_ms": ms})
        log("info", f"refreshed {view}", rows=f"{rows:,}", ms=ms)
    return results


def cmd_build(args: argparse.Namespace) -> int:
    try:
        with connect(autocommit=args.concurrently) as conn:
            results = refresh(conn, concurrently=args.concurrently)
            total = sum(r["rows"] for r in results)
            log("info", f"mart rebuilt: {len(results)} relations, {total:,} rows")
            for r in results:
                emit(r)
            return 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """ANALYZE the database so the planner has real statistics.

    Worth its own command because every EXPLAIN in the performance suite is
    meaningless against tables the planner has never looked at, and a bulk load
    leaves statistics stale. ANALYZE takes a table or nothing -- there is no
    per-schema form -- so this runs the database-wide version once.
    """
    try:
        with connect(autocommit=True) as conn, conn.cursor() as cur:
            started = time.monotonic()
            cur.execute("ANALYZE")
            ms = int((time.monotonic() - started) * 1000)
        log("info", "ANALYZE complete", ms=ms)
        emit({"analyze_ms": ms})
        return 0
    except DatabaseUnavailable as exc:
        log("error", str(exc))
        return 1
