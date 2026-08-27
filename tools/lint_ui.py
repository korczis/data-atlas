#!/usr/bin/env python3
"""Vynucuje konvence Flowbite + Alpine.js nad src/template.html.

Pravidla vycházejí z oficiální dokumentace Flowbite (llms.txt) a z Alpine.js
docs; jejich slovní verze je v docs/UI-RULES.md. Tenhle skript je ta vynucovací
část — samotné pravidlo v dokumentu nikoho nezastaví.

Každé pravidlo tu je proto, že jeho porušení něco reálně rozbije. U každého je
napsáno co, aby se dalo posoudit, jestli pořád dává smysl.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "template.html"

problems: list[tuple[str, str]] = []


def tag(name: str) -> str:
    """Vzor otevíracího tagu, který snese '>' uvnitř hodnoty atributu.

    Naivní `<svg[^>]*>` se ukousne na `x-show="i > 0"` a pak nevidí atributy
    za ním — linter tak hlásil chybějící aria-hidden na značce, která ho má.
    Falešný poplach je horší než žádné pravidlo: naučí lidi výstup ignorovat.
    """
    return rf"""<{name}\b(?:[^>"']|"[^"]*"|'[^']*')*>"""


def fail(rule: str, detail: str) -> None:
    problems.append((rule, detail))


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def check(html: str) -> None:
    # Tělo bez <script> — pravidla o markupu nemají koukat do JS.
    markup = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)
    script = "\n".join(re.findall(r"<script\b.*?>(.*?)</script>", html, flags=re.S))

    # ── Flowbite: inicializace ────────────────────────────────────────────────
    # Flowbite váže chování na data atributy jediným skenem DOM. Cokoli
    # vykreslí Alpine až potom, zůstane mrtvé, pokud se nezavolá znovu.
    if "data-drawer-target" in markup or "data-dropdown-toggle" in markup \
            or "data-modal-target" in markup or "data-tooltip-target" in markup:
        if "initFlowbite" not in script:
            fail("flowbite/init",
                 "markup používá Flowbite data atributy, ale nikde se nevolá initFlowbite()")

    # Flowbite komponenta uvnitř x-for přežije jen do prvního přefiltrování:
    # Alpine uzel zahodí a nový už žádný Flowbite listener nemá.
    for m in re.finditer(tag("template") + r"(.*?)</template>", markup, re.S):
        if "x-for" not in m.group(0):
            continue
        if re.search(r"data-(drawer|dropdown|modal|tooltip|popover|accordion|tabs|collapse)-", m.group(1)):
            fail("flowbite/dynamic",
                 f"řádek {line_of(markup, m.start())}: Flowbite data atribut uvnitř x-for — "
                 "po přerenderování přestane fungovat")

    # ── Flowbite: RTL a logické vlastnosti ────────────────────────────────────
    # Flowbite 2.x jede na logických vlastnostech kvůli RTL režimu.
    directional = {
        r"\bml-\d": "ms-", r"\bmr-\d": "me-", r"\bpl-\d": "ps-", r"\bpr-\d": "pe-",
        r"\bleft-\d": "start-", r"\bright-\d": "end-",
        r"\btext-left\b": "text-start", r"\btext-right\b": "text-end",
    }
    for pattern, replacement in directional.items():
        for m in re.finditer(pattern, markup):
            fail("flowbite/rtl",
                 f"řádek {line_of(markup, m.start())}: '{m.group(0)}' — použij logickou "
                 f"variantu '{replacement}' (Flowbite RTL)")

    # ── Flowbite: tmavý režim ─────────────────────────────────────────────────
    # Barva bez dark: protějšku znamená černý text na černém pozadí.
    for m in re.finditer(r'class="([^"]*)"', markup):
        cls = m.group(1)
        if "dark:" in cls:
            continue
        for token in ("bg-white", "bg-gray-50", "bg-gray-100", "text-gray-900", "text-gray-500"):
            if re.search(rf"\b{token}\b", cls):
                fail("flowbite/dark",
                     f"řádek {line_of(markup, m.start())}: '{token}' bez dark: protějšku")
                break

    # ── Alpine: klíče v x-for ─────────────────────────────────────────────────
    # Duplicitní nebo chybějící :key neshodí jen jednu položku, ale celý seznam.
    for m in re.finditer(tag("template"), markup):
        if "x-for" not in m.group(0):
            continue
        if ":key" not in m.group(0):
            fail("alpine/key",
                 f"řádek {line_of(markup, m.start())}: x-for bez :key")

    # ── Alpine: x-cloak ───────────────────────────────────────────────────────
    # Bez něj problikne nevykreslená šablona, než Alpine nastartuje.
    root = re.search(tag("div"), markup)
    while root and "x-data=" not in root.group(0):
        root = re.search(tag("div"), markup[root.end():])
    if root and "x-cloak" not in root.group(0):
        fail("alpine/cloak", "kořenový x-data nemá x-cloak")
    if "[x-cloak]" not in html:
        fail("alpine/cloak", "chybí CSS pravidlo pro [x-cloak]")

    # ── Alpine: registrace komponenty ─────────────────────────────────────────
    # Alpine.data() drží logiku mimo globální jmenný prostor.
    if "x-data=" in markup and "Alpine.data(" not in script:
        fail("alpine/data",
             "komponenta není registrovaná přes Alpine.data() uvnitř alpine:init")

    # ── Alpine: debounce na vyhledávání ───────────────────────────────────────
    # Filtrování na každý stisk klávesy překresluje celý seznam.
    if re.search(r'type="search"', markup):
        m = re.search(r'type="search"[^>]*', markup)
        if m and "debounce" not in m.group(0):
            fail("alpine/debounce", "hledací input nemá x-model.debounce")

    # ── Přístupnost ───────────────────────────────────────────────────────────
    for m in re.finditer(tag("button") + r"(.*?)</button>", markup, re.S):
        open_tag, inner = m.group(0), m.group(1)
        # inner je obsah MEZI tagy, takže se v něm nehledá '>' — jen text
        # po odstranění vnořených elementů.
        text = re.sub(r"<[^>]*>", "", inner).strip()
        named = bool(text) or "aria-label" in open_tag or "x-text" in open_tag \
            or "x-text" in inner or "sr-only" in inner
        if not named:
            fail("a11y/button-name",
                 f"řádek {line_of(markup, m.start())}: tlačítko bez přístupného názvu")

    for m in re.finditer(tag("svg"), markup):
        if "aria-hidden" not in m.group(0) and "role=" not in m.group(0):
            fail("a11y/svg",
                 f"řádek {line_of(markup, m.start())}: dekorativní <svg> bez aria-hidden=\"true\"")

    for m in re.finditer(tag("input"), markup):
        ident_m = re.search(r'\bid="([^"]+)"', m.group(0))
        if not ident_m:
            continue
        ident = ident_m.group(1)
        if f'for="{ident}"' not in markup and "aria-label" not in m.group(0):
            fail("a11y/label", f"input #{ident} nemá <label for> ani aria-label")

    # Přepínač musí hlásit stav, jinak o něm odečítač neví.
    for m in re.finditer(tag("button"), markup):
        open_tag = m.group(0)
        if ":class=" in open_tag and re.search(r"@click=\"[a-zA-Z]+ ?=", open_tag):
            if "aria-pressed" not in open_tag and "aria-current" not in open_tag:
                fail("a11y/toggle-state",
                     f"řádek {line_of(markup, m.start())}: přepínač bez aria-pressed/aria-current")

    # ── Mobile-first ──────────────────────────────────────────────────────────
    # Pevná minimální šířka mimo vodorovný scroll roztáhne celou stránku.
    for m in re.finditer(r"min-w-\[[^\]]+\]", markup):
        window = markup[max(0, m.start() - 600):m.start()]
        if "overflow-x-auto" not in window:
            fail("responsive/min-width",
                 f"řádek {line_of(markup, m.start())}: '{m.group(0)}' bez overflow-x-auto předka")

    # Breakpointy se skládají odspodu nahoru; max-* je opačný směr.
    for m in re.finditer(r"\bmax-(sm|md|lg|xl):", markup):
        fail("responsive/mobile-first",
             f"řádek {line_of(markup, m.start())}: '{m.group(0)}' — piš mobile-first (min-width)")


def main() -> int:
    if not TEMPLATE.exists():
        raise SystemExit(f"chybí {TEMPLATE}")
    check(TEMPLATE.read_text(encoding="utf-8"))

    if not problems:
        print(f"lint_ui: {TEMPLATE.relative_to(ROOT)} — bez nálezů")
        return 0

    by_rule: dict[str, list[str]] = {}
    for rule, detail in problems:
        by_rule.setdefault(rule, []).append(detail)
    for rule, details in sorted(by_rule.items()):
        print(f"\n{rule} ({len(details)})")
        for d in details[:12]:
            print(f"  {d}")
        if len(details) > 12:
            print(f"  … a dalších {len(details) - 12}")
    print(f"\nlint_ui: {len(problems)} nálezů", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
