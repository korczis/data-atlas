"""Database connection and small query helpers.

Thin on purpose. There is no ORM here and no query builder: the authoritative
DDL is SQL in `warehouse/migrations/`, readable and reviewable as SQL, and the
canonicalisation steps are set-based statements rather than Python loops over
rows. ADR-0010.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from . import config


class DatabaseUnavailable(RuntimeError):
    """Raised with something actionable, never a bare driver traceback."""


def _driver():
    try:
        import psycopg
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise DatabaseUnavailable(
            "psycopg 3 is not installed. From the repository root:\n"
            "    just db-install      (or: uv pip install --python $(which python3) 'psycopg[binary]>=3.2')"
        ) from exc
    return psycopg


@contextmanager
def connect(*, autocommit: bool = False, url: str | None = None) -> Iterator[Any]:
    psycopg = _driver()
    dsn = url or config.database_url()
    try:
        conn = psycopg.connect(dsn, autocommit=autocommit)
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable(
            f"cannot connect to {_redact(dsn)}\n"
            f"    {exc}\n"
            f"    Set ATLAS_DATABASE_URL or DATABASE_URL, and check the server is "
            f"running. warehouse/.env.example documents the shape."
        ) from exc
    try:
        yield conn
    finally:
        conn.close()


def _redact(dsn: str) -> str:
    """Never echo a password, not even in an error the user asked for.

    Three DSN forms are valid for libpq and all three can carry a secret, so all
    three are handled. An earlier version covered only the first, which meant a
    keyword/value DSN printed its password in clear text on any connection
    failure — and a failed connection is exactly when this string is logged.

        postgresql://user:secret@host/db      URI with inline credentials
        postgresql://host/db?password=secret  URI with the password as a param
        host=localhost password=secret ...    keyword/value form
    """
    import re

    # keyword/value form, anywhere in the string
    out = re.sub(r"(?i)\b(password|passfile)\s*=\s*('[^']*'|\S+)", r"\1=***", dsn)
    # password as a URI query parameter
    out = re.sub(r"(?i)([?&]password=)[^&\s]*", r"\1***", out)

    # inline URI credentials
    if "://" in out and "@" in out:
        scheme, _, rest = out.partition("://")
        creds, _, host = rest.rpartition("@")
        if ":" in creds:
            user, _, _pw = creds.partition(":")
            creds = f"{user}:***"
        out = f"{scheme}://{creds}@{host}"
    return out


def scalar(conn: Any, sql: str, params: tuple = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def rows(conn: Any, sql: str, params: tuple = ()) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def dicts(conn: Any, sql: str, params: tuple = ()) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def extension_available(conn: Any, name: str) -> bool:
    return bool(scalar(conn,
                       "SELECT 1 FROM pg_available_extensions WHERE name = %s", (name,)))


def extension_installed(conn: Any, name: str) -> bool:
    return bool(scalar(conn, "SELECT 1 FROM pg_extension WHERE extname = %s", (name,)))
