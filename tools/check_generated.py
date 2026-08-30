#!/usr/bin/env python3
"""Say which generated files `just check` just rewrote, so they get committed.

`just check` regenerates the catalogue and the Markdown documentation on the way
past. That is deliberate — it means a local run cannot pass against stale
artefacts. The failure it leaves open is the next one: the files are correct on
disk, nobody commits them, and CI rejects the push for a mismatch that was
already fixed locally.

This is a notice, not a gate. Uncommitted generated output is the normal state
halfway through a change; it only becomes wrong at the moment of pushing, and
AGENTS.md makes committing it part of the definition of done.

The list of generated files is read from .gitattributes, so there is one place
that knows which files are generated rather than three that disagree.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ATTRS = ROOT / ".gitattributes"

# `path linguist-generated` is as valid to git as `=true`; matching only the
# latter would drop a file from this list without anyone noticing.
MARKED = re.compile(r"^(\S+)\s+.*\blinguist-generated(?:=(?:true|1))?(?:\s|$)")

# Generated, but not by this repository's build. Reporting it as "build output
# of just check" is false, and a notice that cries wolf gets ignored.
NOT_OUR_OUTPUT = {"package-lock.json": "npm writes it, not `just check`"}


def generated() -> list[str]:
    if not ATTRS.exists():
        return []
    return [m.group(1) for line in ATTRS.read_text(encoding="utf-8").splitlines()
            if (m := MARKED.match(line.strip()))
            and m.group(1) not in NOT_OUR_OUTPUT]


def main() -> int:
    paths = generated()
    if not paths:
        return 0

    out = subprocess.run(["git", "status", "--porcelain", "--"] + paths,
                         cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:          # not a git checkout; nothing to say
        return 0

    # `XY path`, but a rename is `R  old -> new` and a path with spaces is
    # quoted. Take what git actually points at.
    changed = []
    for line in out.stdout.splitlines():
        if not line:
            continue
        path = line[3:].split(" -> ")[-1].strip()
        changed.append(path.strip('"'))
    if not changed:
        print(f"check_generated: {len(paths)} generated files match the commit")
        return 0

    print()
    print("  These generated files changed and are not committed:")
    for path in changed:
        print(f"    {path}")
    print()
    print("  They are build output, not edits — commit them alongside the source")
    print("  change that produced them. CI regenerates and compares, so a push")
    print("  without them fails on a mismatch that is already fixed here.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
