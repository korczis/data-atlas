#!/usr/bin/env python3
"""Verify that the Markdown in this repository still describes this repository.

Three failure modes, all of them silent until someone follows the documentation
and it does not work:

  * a `just <recipe>` that no longer exists (renamed or deleted recipes),
  * a relative link pointing at a file that moved or was removed,
  * a repository path quoted in backticks that is not there any more.

Offline and deterministic, so it belongs in `just check`. Catalogue URLs are a
different problem and live in `tools/check_links.py`, which needs the network.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent

# Directories whose contents are committed, so a reference into them can be
# checked. dist/ and .cache/ are build outputs and absent on a clean clone;
# node_modules/ is not ours.
CHECKED_ROOTS = ("tools/", "tests/", "src/", "data/", "docs/", "config/",
                 "static/", ".github/")

# Only paths *into* a checked directory are verified. Bare root-level filenames
# are deliberately not: measured over the current docs, a rule matching them
# flagged `llms.txt` and `llms-full.txt` (Flowbite's, quoted from a URL),
# `raw.json` (shorthand for .cache/raw.json) and `robots.txt` (generated into
# dist/) — four false alarms against six real references. A gate that fails on
# correct prose gets worked around, so this one stays narrow. Markdown *links*
# to root files are still checked, by the LINK branch below.

# Placeholders and globs are prose, not paths: `data/sources/<CODE>.json`.
PLACEHOLDER = re.compile(r"[<>*?{}…]")

CODE_SPAN = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^```", re.M)
JUST_CALL = re.compile(r"\bjust\s+([a-z0-9-]+(?:\s+[a-z0-9-]+)*)")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$", re.M)
NOT_IN_SLUG = re.compile(r"[^\w\- ]", re.UNICODE)

# `just --list`, `just --dump`; and `just` with no recipe.
FLAGS = re.compile(r"^-")


def git_paths() -> set[str]:
    """Every path git would keep: tracked files plus new, non-ignored ones.

    Membership comes from git rather than the filesystem on purpose.
    `config/private-hosts.txt` and `dist/` exist on the maintainer's machine and
    on nobody else's, so a plain existence check would pass locally and fail on
    a clean clone — the exact drift this script exists to catch. Untracked but
    unignored files count, so a reference to a file added in the same change is
    not a false alarm.
    """
    out = subprocess.run(["git", "ls-files", "--cached", "--others",
                          "--exclude-standard"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    paths = set()
    for line in out.splitlines():
        if not line:
            continue
        paths.add(line)
        parent = PurePosixPath(line).parent
        while str(parent) != ".":
            paths.add(str(parent) + "/")
            paths.add(str(parent))
            parent = parent.parent
    return paths


def ignored(paths: list[str]) -> set[str]:
    """The subset of `paths` that .gitignore deliberately keeps out of the repo.

    Documentation is allowed — required, even — to name files that must never be
    committed, such as config/private-hosts.txt. Ignored is intentional absence;
    neither tracked nor ignored is a typo or a stale path.
    """
    if not paths:
        return set()
    out = subprocess.run(["git", "check-ignore", "--stdin"], cwd=ROOT,
                         input="\n".join(paths), capture_output=True, text=True)
    return {line for line in out.stdout.splitlines() if line}


def markdown_files(paths: set[str]) -> list[Path]:
    return sorted(ROOT / p for p in paths if p.endswith(".md"))


def justfile_recipe_mentions(known: set[str]) -> list[str]:
    """`just help` prints recipe names as plain echo text, so nothing checked
    them. Rename a recipe and the summary keeps advertising the old name with
    every gate green."""
    text = (ROOT / "justfile").read_text(encoding="utf-8")
    bad = []
    # Only the first word: in the justfile a help line is
    # `just install      install npm dependencies`, so the run-of-words form
    # used for Markdown would read the description as recipe names too.
    for word in re.findall(r"\bjust\s+(-{0,2}[a-z_][a-z0-9_-]*)", text):
        if FLAGS.match(word) or word in known:
            continue
        bad.append(f"justfile: `just {word}` is printed but is not a recipe")
    return bad


# A recipe header starts at column 0 and ends in `:`; `set x := ...` does not.
RECIPE = re.compile(r"^([a-z0-9_][a-z0-9_-]*)(?:\s+[^:\n]*)?:(?!=)", re.M)


def recipes() -> set[str]:
    """Read the recipe names out of the justfile itself.

    `just --dump` would be more authoritative, but CI has no reason to install
    the `just` binary to check Markdown, and a missing binary must not be the
    difference between a passing and a failing check.
    """
    return set(RECIPE.findall((ROOT / "justfile").read_text(encoding="utf-8")))


def anchors(text: str) -> set[str]:
    """Heading anchors the way GitHub builds them: lowercase, punctuation
    dropped, spaces to hyphens. Accented letters survive, so `## Stránky zemí`
    is reachable as `#stránky-zemí`."""
    out = set()
    # Fenced blocks first: a shell comment like `# Install deps` inside a ```bash
    # block otherwise parses as a heading, and a dead link to #install-deps then
    # passes. code_spans() already excludes prose for the same reason.
    prose = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    for raw in HEADING.findall(prose):
        # Strip inline formatting the heading text may carry.
        plain = re.sub(r"[`*_]", "", raw)
        out.add(NOT_IN_SLUG.sub("", plain).strip().lower().replace(" ", "-"))
    return out


def code_spans(text: str) -> list[str]:
    """Inline code plus fenced blocks. Prose is deliberately not searched:
    in English `just` is also an adverb."""
    spans = CODE_SPAN.findall(text)
    parts = FENCE.split(text)
    # Odd indices are inside a fence.
    for block in parts[1::2]:
        spans.extend(block.splitlines()[1:] if block.startswith(("bash", "sh"))
                     else block.splitlines())
    return spans


def main() -> int:
    known = recipes()
    in_git = git_paths()
    files = markdown_files(in_git)
    errors: list[str] = []
    unknown: list[tuple[str, str]] = []

    for path in files:
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        spans = code_spans(text)

        for span in spans:
            for call in JUST_CALL.findall(span):
                for word in call.split():
                    if FLAGS.match(word):
                        break
                    if word not in known:
                        errors.append(
                            f"{rel}: `just {word}` is not a recipe — "
                            f"see `just --list`")
                        break

            for token in span.split():
                # Diagrams draw with box characters right up against a path.
                token = token.strip("`,;:()\"'\u2500\u2502\u250c\u2510\u2514"
                                    "\u2518\u251c\u2524\u252c\u2534\u253c\u2192\u2190")
                token = token.rstrip(".")
                if PLACEHOLDER.search(token) or not token.startswith(CHECKED_ROOTS):
                    continue
                if token.rstrip("/") not in in_git and token not in in_git:
                    unknown.append((f"{rel}: `{token}` is neither in git nor "
                                    f"ignored — stale path?", token))

        for target in LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("#"):
                if target[1:] and target[1:] not in anchors(text):
                    errors.append(f"{rel}: link -> {target} matches no heading")
                continue
            file_part = target.split("#", 1)[0]
            if not file_part or PLACEHOLDER.search(file_part):
                continue
            resolved = (path.parent / file_part).resolve()
            try:
                as_posix = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                errors.append(f"{rel}: link -> {target} points outside the repository")
                continue
            if as_posix not in in_git and as_posix + "/" not in in_git:
                unknown.append((f"{rel}: link -> {target} is neither in git nor "
                                f"ignored — stale link?", as_posix))
                continue
            fragment = target.split("#", 1)[1] if "#" in target else ""
            if fragment and as_posix.endswith(".md"):
                if fragment not in anchors(resolved.read_text(encoding="utf-8")):
                    errors.append(f"{rel}: link -> {target} matches no heading in "
                                  f"{as_posix}")

    deliberate = ignored([token for _, token in unknown])
    errors.extend(msg for msg, token in unknown if token not in deliberate)

    errors.extend(justfile_recipe_mentions(known))

    for e in sorted(set(errors)):
        print(f"  {e}", file=sys.stderr)

    if errors:
        print(f"check_docs: {len(set(errors))} problem(s) across {len(files)} Markdown files",
              file=sys.stderr)
        return 1
    print(f"check_docs: {len(files)} Markdown files · recipes, links and paths all resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
