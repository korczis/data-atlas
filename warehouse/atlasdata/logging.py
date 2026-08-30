"""Structured, deterministic logging.

Two rules, both learned from the checkers on the catalogue side of this
repository: a run that did nothing must not look like a run that succeeded, and
output that goes into a report must not carry timestamps that change between
identical runs.

`log` writes human-readable lines to stderr. `emit` writes machine-readable
JSON lines to stdout when --json is on, so a caller can pipe results without
parsing prose.
"""
from __future__ import annotations

import json
import sys
from typing import Any

_LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}
_state = {"level": 20, "json": False}


def configure(*, level: str = "info", json_output: bool = False) -> None:
    _state["level"] = _LEVELS[level]
    _state["json"] = json_output


def json_mode() -> bool:
    return bool(_state["json"])


def log(level: str, message: str, **fields: Any) -> None:
    """Human-readable progress on stderr, so stdout stays pipeable."""
    if _LEVELS[level] < _state["level"]:
        return
    extra = " ".join(f"{k}={v}" for k, v in fields.items())
    prefix = {"debug": "  ", "info": "  ", "warn": "! ", "error": "✗ "}[level]
    print(f"{prefix}{message}{(' ' + extra) if extra else ''}", file=sys.stderr, flush=True)


def emit(payload: dict[str, Any]) -> None:
    """One JSON object per line on stdout, only in --json mode."""
    if _state["json"]:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
