#!/usr/bin/env python3
"""Verify that classes Flowbite adds **at runtime** have a rule in the CSS.

Grew out of a defect that passed everything else. Flowbite does not put the
drawer backdrop in the markup - it builds it from JavaScript with
`bg-gray-900/50 dark:bg-gray-900/80 fixed inset-0 z-30`. Tailwind scans the
source, never sees those classes there and purges them. The backdrop then
appears in the DOM with the right `class` but, without `inset-0`, **zero
size**: the drawer opens without dimming and tapping beside it does not close
it. A check for "the element exists" passes, because the element exists.

They were kept alive by `#sidebarBackdrop`, a piece of copied application shell
that did nothing itself (`display: none`) and acted as an accidental safelist.
When it was cleaned up as dead code, the backdrop stopped existing.

So the script does two things:

1. **Extracts from the bundle** every class it can add at runtime - from the
   `*Classes` options, from `classList.add/remove` literals and from the drawer
   placement table. If a Flowbite upgrade renames one or adds another, the list
   diverges from the baseline and the script says so. Without that, the safelist
   would drift away from the library in silence.
2. **Checks in the CSS** the ones this page actually needs. The rest (drawer
   placements we do not use) must not be in the CSS - safelisting them would
   pull them into the build for nothing.

Exits non-zero when a needed class is missing from the CSS, or when the bundle
can add a class the baseline does not know about.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"

# What Flowbite in this version can add at runtime. The baseline is compared
# against the bundle, so an upgrade that adds something here fails and asks for
# a decision.
BASELINE = {
    # the drawer's backdropClasses
    "bg-gray-900/50", "dark:bg-gray-900/80", "fixed", "inset-0", "z-30",
    # classList.add/remove with a literal
    "transition-transform", "overflow-hidden", "hidden", "block",
    # _getPlacementClasses - every placement, including ones we do not use
    "top-0", "left-0", "right-0", "bottom-0", "transform-none",
    "-translate-y-full", "translate-x-full", "translate-y-full", "-translate-x-full",
}

# The subset this page actually needs: the left drawer (the default placement)
# and its backdrop. `hidden`/`block` belong to the dropdown.
NEEDED = {
    "bg-gray-900/50", "dark:bg-gray-900/80", "fixed", "inset-0", "z-30",
    "transition-transform", "overflow-hidden", "hidden", "block",
    "top-0", "transform-none", "-translate-x-full",
}

# Classes Flowbite stamps that we **deliberately do not style**. Without this
# category the script would push towards safelisting everything the library
# adds, turning a silent gap into a silent extra rule.
UNSTYLED_BY_DESIGN = {
    "left-0": "Flowbite gives the drawer a physical `left-0` as part of `base`. "
              "The panel positions itself with logical `start-0` (the flowbite/rtl "
              "rule), so in LTR `left-0` would only duplicate it and in RTL it "
              "would fight `start-0` and pull the panel the wrong way. The rule "
              "is therefore meant to be absent from the CSS.",
}

# Placements the markup does not use. Keeping them safelisted means pulling
# rules into the CSS that will never style anything.
UNUSED = BASELINE - NEEDED - set(UNSTYLED_BY_DESIGN)


def injectable(page: str) -> set[str]:
    """Classes the bundle can add at runtime."""
    out: set[str] = set()
    for _, value in re.findall(r'([a-zA-Z]*[Cc]lasses)\s*:\s*"([^"]{2,200})"', page):
        out.update(value.split())
    out.update(re.findall(r'classList\.(?:add|remove)\("([^"]{1,60})"\)', page))
    start = page.find("prototype._getPlacementClasses")
    if start != -1:
        table = page[start:start + 1500]
        out.update(re.findall(r'"(-?[a-z][a-z0-9-]*-(?:0|full))"', table))
        out.update(re.findall(r'"(transform-none)"', table))
    return out


def styled(css: str, cls: str) -> bool:
    """Does the class have a CSS rule? Escaped the Tailwind way: `:` `/` `.` backslashed."""
    escaped = cls.replace("\\", "\\\\")
    for ch in (":", "/", "."):
        escaped = escaped.replace(ch, "\\" + ch)
    return f".{escaped}" in css


def main() -> int:
    if not PAGE.exists():
        raise SystemExit("missing dist/index.html - run `just build` first")
    page = PAGE.read_text(encoding="utf-8")

    # Hledá se jen ve <style>, ne v celém souboru. Minifikovaný JS obsahuje
    # řetězce jako `.block` a uspokojil by tvrzení „třída má pravidlo", aniž
    # by ji cokoli stylovalo. A když blok stylů chybí, prázdný výsledek by
    # znamenal „nic není ostylované" a hledání v prázdnu by prošlo stejně
    # dobře jako hledání v celém souboru — proto se rovnou padá.
    css = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", page, re.S))
    if not css.strip():
        raise SystemExit("no <style> block in dist/index.html - there is nothing "
                         "to check the runtime classes against")

    problems: list[str] = []

    found = injectable(page)
    drift = found - BASELINE
    if drift:
        problems.append(
            "the bundle can add runtime classes the baseline does not know about: "
            + ", ".join(sorted(drift))
            + " - decide whether the page needs them and add them to "
              "BASELINE (and if so NEEDED plus the safelist in src/tailwind.config.js)")
    gone = BASELINE - found
    if gone:
        problems.append(
            "the baseline knows classes the bundle no longer adds: " + ", ".join(sorted(gone))
            + " - drop them after the Flowbite upgrade so the safelist stops holding a dead rule")

    for cls, why in sorted(UNSTYLED_BY_DESIGN.items()):
        if styled(css, cls):
            problems.append(f"`{cls}` has a CSS rule but should not - {why}")

    missing = sorted(c for c in NEEDED if not styled(css, c))
    if missing:
        problems.append(
            "the CSS is missing rules for classes Flowbite adds at runtime: "
            + ", ".join(missing)
            + " - Tailwind purged them because they are not in the markup; add them to "
              "`safelist` v src/tailwind.config.js")

    print(f"  bundle adds {len(found)} classes at runtime · page needs "
          f"{len(NEEDED)} · deliberately unstyled {len(UNSTYLED_BY_DESIGN)} · "
          f"unused placements {len(UNUSED)}")
    for p in problems:
        print(f"  ✗ {p}", file=sys.stderr)
    if problems:
        print("\nFlowbite runtime classes do not line up", file=sys.stderr)
        return 1
    print("\nevery Flowbite runtime class has a CSS rule")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
