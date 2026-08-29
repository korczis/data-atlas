#!/usr/bin/env python3
"""Ověří, že třídy, které Flowbite přidává **až za běhu**, mají v CSS pravidlo.

Vzniklo z vady, která prošla vším ostatním. Flowbite si backdrop šuplíku
nedává do markupu — staví ho z JavaScriptu s
`bg-gray-900/50 dark:bg-gray-900/80 fixed inset-0 z-30`. Tailwind skenuje
zdroj, tyhle třídy v něm nevidí a ořízne je. Backdrop pak v DOM vznikne,
má správný `class`, ale bez `inset-0` má **nulový rozměr**: šuplík se otevře
bez ztmavení a ťuknutí vedle něj ho nezavře. Kontrola „element existuje"
projde, protože element existuje.

Držel je naživu `#sidebarBackdrop`, kus opsaného aplikačního shellu, který
sám nic nedělal (`display: none`) a fungoval jako nechtěný safelist. Když se
uklidil jako mrtvý kód, backdrop přestal existovat.

Skript proto dělá dvě věci:

1. **Vytáhne z balíčku** všechny třídy, které umí za běhu přidat — z voleb
   `*Classes`, z literálů v `classList.add/remove` a z tabulky poloh šuplíku.
   Když upgrade Flowbite některou přejmenuje nebo přidá novou, seznam se
   rozejde s baseline a skript to ohlásí. Bez toho by se safelist tiše
   rozešel s knihovnou.
2. **Ověří v CSS** ty z nich, které tahle stránka opravdu potřebuje. Ostatní
   (polohy šuplíku, které nepoužíváme) být v CSS nemají — safelist by je
   tahal do buildu zbytečně.

Vrací nenulový kód, když některá potřebná třída v CSS chybí nebo když balíček
umí přidat třídu, o které baseline neví.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "dist" / "index.html"

# Co Flowbite v téhle verzi umí za běhu přidat. Baseline se porovnává proti
# balíčku, takže upgrade, který sem něco přidá, spadne a vyžádá si rozhodnutí.
BASELINE = {
    # backdropClasses šuplíku
    "bg-gray-900/50", "dark:bg-gray-900/80", "fixed", "inset-0", "z-30",
    # classList.add/remove s literálem
    "transition-transform", "overflow-hidden", "hidden", "block",
    # _getPlacementClasses — všechny polohy, i ty, které nepoužíváme
    "top-0", "left-0", "right-0", "bottom-0", "transform-none",
    "-translate-y-full", "translate-x-full", "translate-y-full", "-translate-x-full",
}

# Podmnožina, kterou tahle stránka opravdu potřebuje: šuplík vlevo (výchozí
# poloha) a jeho backdrop. `hidden`/`block` patří dropdownu.
NEEDED = {
    "bg-gray-900/50", "dark:bg-gray-900/80", "fixed", "inset-0", "z-30",
    "transition-transform", "overflow-hidden", "hidden", "block",
    "top-0", "transform-none", "-translate-x-full",
}

# Třídy, které Flowbite razí a my je **schválně nestylujeme**. Bez téhle
# kategorie by skript nutil safelistovat všechno, co knihovna přidá, a tichá
# mezera by se změnila v tiché pravidlo navíc.
UNSTYLED_BY_DESIGN = {
    "left-0": "Flowbite přidává šuplíku fyzické `left-0` jako součást `base`. "
              "Panel si polohu řeší logickým `start-0` (pravidlo flowbite/rtl), "
              "takže v LTR by `left-0` jen zdvojilo totéž a v RTL by proti "
              "`start-0` táhlo panel na špatnou stranu. Pravidlo v CSS proto "
              "chybět má.",
}

# Polohy, které markup nepoužívá. Držet je v safelistu znamená tahat do CSS
# pravidla, která nikdy nic neobarví.
UNUSED = BASELINE - NEEDED - set(UNSTYLED_BY_DESIGN)


def injectable(page: str) -> set[str]:
    """Třídy, které balíček umí přidat za běhu."""
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
    """Má třída v CSS pravidlo? Escapuje se jako Tailwind: `:` `/` `.` s lomítkem."""
    escaped = cls.replace("\\", "\\\\")
    for ch in (":", "/", "."):
        escaped = escaped.replace(ch, "\\" + ch)
    return f".{escaped}" in css


def main() -> int:
    if not PAGE.exists():
        raise SystemExit("chybí dist/index.html — spusť nejdřív `just build`")
    page = PAGE.read_text(encoding="utf-8")

    problems: list[str] = []

    found = injectable(page)
    drift = found - BASELINE
    if drift:
        problems.append(
            "balíček umí za běhu přidat třídy, o kterých baseline neví: "
            + ", ".join(sorted(drift))
            + " — rozhodni, jestli je stránka potřebuje, a doplň je do "
              "BASELINE (a případně NEEDED + safelistu v src/tailwind.config.js)")
    gone = BASELINE - found
    if gone:
        problems.append(
            "baseline zná třídy, které už balíček nepřidává: " + ", ".join(sorted(gone))
            + " — po upgradu Flowbite je vyřaď, ať safelist nedrží mrtvé pravidlo")

    for cls, why in sorted(UNSTYLED_BY_DESIGN.items()):
        if styled(page, cls):
            problems.append(f"`{cls}` má v CSS pravidlo, ale mít nemá — {why}")

    missing = sorted(c for c in NEEDED if not styled(page, c))
    if missing:
        problems.append(
            "v CSS chybí pravidlo pro třídy, které Flowbite přidává za běhu: "
            + ", ".join(missing)
            + " — Tailwind je ořízl, protože v markupu nejsou; doplň je do "
              "`safelist` v src/tailwind.config.js")

    print(f"  balíček přidává za běhu {len(found)} tříd · stránka potřebuje "
          f"{len(NEEDED)} · schválně nestylované {len(UNSTYLED_BY_DESIGN)} · "
          f"nepoužité polohy {len(UNUSED)}")
    for p in problems:
        print(f"  ✗ {p}", file=sys.stderr)
    if problems:
        print("\nběhové třídy Flowbite nesedí", file=sys.stderr)
        return 1
    print("\nvšechny běhové třídy Flowbite mají v CSS pravidlo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
