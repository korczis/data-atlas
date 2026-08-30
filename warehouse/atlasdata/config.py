"""Where things live, and how to reach the database.

Paths are derived from this file's location rather than from the working
directory, for the same reason `tools/build_catalog.py` does it: a recipe that
only works when you stand in the right directory is a recipe that breaks in CI.

The database URL is read from the environment. There is no default password and
no committed connection string; `warehouse/.env.example` documents the shape.
"""
from __future__ import annotations

import os
from pathlib import Path

# warehouse/atlasdata/config.py -> warehouse/ -> repository root
WAREHOUSE = Path(__file__).resolve().parent.parent
ROOT = WAREHOUSE.parent

MANIFESTS = WAREHOUSE / "manifests"
MIGRATIONS = WAREHOUSE / "migrations"
FIXTURES = WAREHOUSE / "fixtures"
REPORTS = WAREHOUSE / "reports"

# Raw artifacts are content-addressed and gitignored. See ADR-0003.
RAW = Path(os.environ.get("ATLAS_RAW_DIR") or (WAREHOUSE / "raw"))

DEFAULT_DATABASE_URL = "postgresql:///atlas_data"

# NOTE: the extraction ceilings that used to be declared here were never read
# by any parser — a documented guarantee that nothing enforced, which is worse
# than no guarantee at all. The real, enforced limits now live next to the code
# that applies them, in atlasdata/parsers/html_era.py and json_era.py, so a
# reader of either parser can see the ceiling it actually uses.


def database_url() -> str:
    """Connection string, from the environment.

    `DATABASE_URL` is the conventional name and is what compose files and hosted
    PostgreSQL both set; `ATLAS_DATABASE_URL` wins when both are present so this
    subsystem can point somewhere else without disturbing another tool that is
    already using DATABASE_URL in the same shell.
    """
    return (os.environ.get("ATLAS_DATABASE_URL")
            or os.environ.get("DATABASE_URL")
            or DEFAULT_DATABASE_URL)


def user_agent() -> str:
    """Identifies the client and says who to contact. Overridable, never absent.

    A crawler that does not say what it is gets blocked, and deserves to be.
    """
    return os.environ.get(
        "ATLAS_USER_AGENT",
        "data-atlas-warehouse/0.1 (+https://github.com/korczis/data-atlas)",
    )


def git_revision() -> str:
    """Short git revision of the working tree, or '' when unavailable.

    Lives here rather than in one pipeline stage because *every* stage has to
    record it. It previously existed only in `staging`, so every `load` run
    stored an empty string -- and since observations cite their load run, 100%
    of loaded values claimed a provenance chain whose commit was blank.
    """
    import subprocess
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=ROOT, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):   # pragma: no cover
        return ""
