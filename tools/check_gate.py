#!/usr/bin/env python3
"""Assert that `just check` is still the whole gate.

CI runs `just check` and nothing else, which is what keeps local and CI from
drifting apart — but it also means a checker left out of the `check` recipe now
runs nowhere at all, and passes by never being asked. That has already happened
once: `docs` was in CI and not in `check`, so a clean local run could still
break the build.

Two rules, both read out of the justfile:

  1. every recipe in the `test` group is a dependency of `check`, unless it is
     listed below with a reason;
  2. every script in tools/ and every suite in tests/ is invoked by some recipe;
  3. `check` still depends on the recipes that regenerate committed artefacts.

Rule 3 exists because CI asserts `git diff --exit-code data/catalog.csv docs/*.md`
*after* `just check`. That assertion only means anything while `check` actually
regenerates those files: drop `docs` from `check` and the diff finds nothing —
not because the docs are current, but because nothing rewrote them. Rule 1 does
not cover it, since `catalog`, `docs` and `build` are in the `build` group.

Rule 2 catches two things. A checker that was written, committed and never wired
up — a repository that looks better guarded than it is. And a tool that outlived
the architecture it was written for: `tools/apply_patch.py` edited a Python list
inside build_catalog.py long after the catalogue moved to data/sources/*.json,
and its docstring told any reader that the list was the source of truth. Nothing
ran it, so nothing said so.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUSTFILE = ROOT / "justfile"

# Recipes that belong to the test group but must stay out of `check`.
# Adding to this list is a decision; forgetting to add to `check` is an accident.
EXEMPT_FROM_CHECK = {
    "links": "goes out to the network; a clean-clone gate cannot depend on "
             "someone else's uptime",
    "shots": "renders screenshots for a human to look at; nothing to assert",
    "serve": "starts a web server and blocks",
}

# Modules that something else imports rather than a recipe running. Anything not
# listed here must be reachable through `just`, or it is dead: either nobody can
# run it the documented way, or it is code no longer connected to the build.
NOT_RUNNABLE = {
    "tests/helpers.mjs": "shared jsdom harness, imported by the suites",
    "tests/e2e/pages.mjs": "shared page list, imported by the specs",
}

# Recipes `check` must keep depending on for CI's generated-file diff to mean
# anything. Keyed to the paths CI compares, so the two move together.
REQUIRED_IN_CHECK = {
    "catalog": "regenerates data/catalog.csv, which CI then diffs",
    "docs": "regenerates docs/CATALOG.md and docs/COVERAGE.md, which CI then diffs",
    "build": "regenerates dist/, which every later check measures",
}

GROUP = re.compile(r"^\[group\('([^']+)'\)\]$")


def parse() -> tuple[dict[str, list[str]], dict[str, str], str]:
    """-> ({recipe: [dependencies]}, {recipe: group}, full text of every body)"""
    deps: dict[str, list[str]] = {}
    groups: dict[str, str] = {}
    bodies: list[str] = []
    pending_group = None

    for line in JUSTFILE.read_text(encoding="utf-8").splitlines():
        if line.startswith((" ", "\t")):
            # Strip shell comments: `# python3 tools/x.py once it works` must not
            # count as wiring the script up.
            code = re.split(r"(?:^|\s)#", line, maxsplit=1)[0]
            bodies.append(code)
            continue
        g = GROUP.match(line.strip())
        if g:
            pending_group = g.group(1)
            continue
        if line.startswith("[") or not line.strip() or line.startswith("#"):
            continue
        m = re.match(r"^([a-z0-9_][a-z0-9_-]*)((?:\s+[^:\n]*)?):(?!=)(.*)$", line)
        if not m:
            continue
        name = m.group(1)
        deps[name] = m.group(3).split()
        if pending_group:
            groups[name] = pending_group
        pending_group = None

    return deps, groups, "\n".join(bodies)


def main() -> int:
    deps, groups, bodies = parse()
    errors: list[str] = []

    if "check" not in deps:
        print("check_gate: no `check` recipe in the justfile", file=sys.stderr)
        return 1
    covered = set(deps["check"])

    for recipe, why in sorted(REQUIRED_IN_CHECK.items()):
        if recipe not in covered:
            errors.append(
                f"`check` no longer depends on `{recipe}` — it {why}. Without it "
                f"CI's `git diff --exit-code` passes because nothing regenerated "
                f"the file, not because it is current")

    for recipe, group in sorted(groups.items()):
        if group != "test" or recipe in covered or recipe in EXEMPT_FROM_CHECK:
            continue
        errors.append(
            f"`just {recipe}` is in the test group but not in `check` — add it to "
            f"the `check` recipe, or to EXEMPT_FROM_CHECK in {Path(__file__).name} "
            f"with the reason it must stay out")

    runnable = sorted(p.relative_to(ROOT).as_posix() for p in
                      list((ROOT / "tools").glob("*.py"))
                      + list((ROOT / "tests").glob("*.mjs"))
                      + list((ROOT / "tests" / "e2e").glob("*.mjs")))
    verified = 0
    for path in runnable:
        if path in NOT_RUNNABLE:
            continue
        # The e2e specs are collected by Playwright, not named in the justfile.
        if path.startswith("tests/e2e/") and path.endswith(".spec.mjs"):
            continue
        verified += 1
        if path not in bodies:
            errors.append(
                f"{path} is never invoked by any recipe — wire it into the "
                f"justfile, delete it, or add it to NOT_RUNNABLE in "
                f"{Path(__file__).name} with the reason something else imports it")

    for e in errors:
        print(f"  {e}", file=sys.stderr)
    if errors:
        return 1

    print(f"check_gate: `check` covers the test group · "
          f"{verified} scripts all reachable from the justfile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
