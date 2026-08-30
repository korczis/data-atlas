"""Every api view must execute, and its contract must be documented.

The `api` schema is the read contract: consumers select from it and never from
canonical or staging tables. A view that has been broken by a schema change
fails here rather than in whatever reads it next.

Three assertions per view — it runs, it returns rows, and it carries a COMMENT.

The middle one exists because the first two do not need any data to pass. This
file used to run `SELECT * ... LIMIT 5` and discard the result, so all 17 views
passed against a freshly migrated, completely empty database, and would have
passed just as cheerfully against a view whose joins had silently stopped
matching. A gate that goes green without looking at anything is worse than no
gate, because someone relies on it.

So: the suite refuses to run at all unless observations are loaded, and every
view must return at least one row unless it is named in EXPECTED_EMPTY with a
reason. A view that legitimately empties out is a one-line declaration; a view
that empties out by accident is a failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata.db import DatabaseUnavailable, connect, dicts, scalar

# Views that hold nothing on a healthy database, and why. Emptiness here is a
# stated expectation; anywhere else it is a defect.
EXPECTED_EMPTY = {
    "unresolved_entities": "every entity resolution in this corpus is accepted, "
                           "so the view of unresolved ones is correctly empty",
}

failures: list[str] = []
checks = 0


def main() -> int:
    global checks
    try:
        cm = connect()
        conn = cm.__enter__()
    except DatabaseUnavailable as exc:
        print(f"test_api_views: NOT RUN — {exc}", file=sys.stderr)
        return 1

    views = dicts(conn, """
        SELECT c.relname AS name, obj_description(c.oid) AS comment
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'api' AND c.relkind = 'v'
         ORDER BY c.relname""")

    if not views:
        print("test_api_views: NOT RUN — no api views found; run `just wh-migrate`",
              file=sys.stderr)
        cm.__exit__(None, None, None)
        return 1

    # Without data, "the view executes" is all this file can establish, and
    # reporting that as a pass is how a broken join reaches production.
    loaded = scalar(conn, "SELECT count(*) FROM obs.observation")
    if not loaded:
        print("test_api_views: NOT RUN — obs.observation is empty, so an empty "
              "view cannot be told from a broken one; run `just wh-load` first",
              file=sys.stderr)
        cm.__exit__(None, None, None)
        return 1

    for v in views:
        checks += 1
        with conn.cursor() as cur:
            try:
                # LIMIT 5 rather than count(*): this asserts the view executes
                # and its plan is valid, without the cost of a full scan over
                # every fact table on a populated database.
                cur.execute(f'SELECT * FROM api."{v["name"]}" LIMIT 5')
                rows = cur.fetchall()
            except Exception as exc:
                conn.rollback()
                failures.append(f"api.{v['name']} does not execute: "
                                f"{type(exc).__name__}: {exc}")
                continue

        checks += 1
        if not rows and v["name"] not in EXPECTED_EMPTY:
            failures.append(f"api.{v['name']} returns no rows on a loaded "
                            f"database — either its joins no longer match or it "
                            f"belongs in EXPECTED_EMPTY with a reason")
        elif rows and v["name"] in EXPECTED_EMPTY:
            failures.append(f"api.{v['name']} is declared EXPECTED_EMPTY "
                            f"({EXPECTED_EMPTY[v['name']]}) but returned rows — "
                            f"the declaration is now wrong")

        checks += 1
        comment = (v["comment"] or "").strip()
        if not comment:
            failures.append(f"api.{v['name']} has no COMMENT — an undocumented "
                            f"view is not a contract")
        elif "rain:" not in comment.lower():
            failures.append(f"api.{v['name']} has a COMMENT that does not state "
                            f"its grain")

    # One invariant with a knowable answer, so the suite is not purely
    # structural: api.entity is a projection of core.entity and must not lose or
    # invent one.
    checks += 1
    api_n = scalar(conn, "SELECT count(*) FROM api.entity")
    core_n = scalar(conn, "SELECT count(*) FROM core.entity")
    if api_n != core_n:
        failures.append(f"api.entity exposes {api_n} of {core_n} core.entity "
                        f"rows — the projection is dropping or duplicating")

    cm.__exit__(None, None, None)

    if failures:
        print(f"test_api_views: {len(failures)} of {checks} checks FAILED",
              file=sys.stderr)
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1
    print(f"test_api_views: {len(views)} views execute and document their grain "
          f"({checks} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
