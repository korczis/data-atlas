#!/usr/bin/env python3
"""Vynucuje konvence Flowbite + Alpine.js nad šablonami v src/.

Pravidla vycházejí z oficiální dokumentace Flowbite (llms.txt) a z Alpine.js
docs; jejich slovní verze je v docs/UI-RULES.md. Tenhle skript je ta vynucovací
část — samotné pravidlo v dokumentu nikoho nezastaví.

Každé pravidlo tu je proto, že jeho porušení něco reálně rozbije. U každého je
napsáno co, aby se dalo posoudit, jestli pořád dává smysl.
"""
import re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Šablony, na které pravidla platí. Stránka země je druhá šablona se stejnými
# riziky — Flowbite dropdowny, x-for nad tabulkou, tmavý režim — takže prochází
# týmiž pravidly. Kdyby se hlídala jen hlavní stránka, brána by o půlce webu
# nevěděla.
#
# `scripts` je JS, který šablona nemá uvnitř sebe. Hlavní stránka nese Alpine
# komponentu v <script>, stránka země ji má v src/js/place.js a build ji
# připojuje až při generování. Bez toho by pravidla alpine/data a flowbite/init
# hlásila chybu na kódu, který existuje — jen leží ve vedlejším souboru.
#
# `closes` je markup, který za šablonu dopisuje build. src/country.html končí
# uvnitř <body>, protože </body></html> připojuje tools/build_places.py až za
# vloženými <script> tagy. Kontrola vyváženosti značek by jinak hlásila <body>,
# který se nikdy nezavírá — nález o skládání buildu, ne o šabloně.
TEMPLATES = (
    {"path": ROOT / "src" / "template.html", "scripts": (), "closes": ""},
    {"path": ROOT / "src" / "country.html",
     "scripts": (ROOT / "src" / "js" / "place.js",), "closes": "</body>"},
)

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


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


class Structure(HTMLParser):
    """Hlídá, že se blokové značky zavírají a ve správném pořadí.

    Vzniklo z chyby, která shodila celou stránku a **prošla všemi ostatními
    branami**: chybějící `</aside>` zanořilo `#main-content` do postranního
    panelu. V DOM byly všechny řádky, takže jsdom testy prošly; panel je pod
    `lg` mimo plátno, takže měření přetečení nic nenašlo; a axe nehlásil nic,
    protože obsah formálně existoval. V prohlížeči byla stránka prázdná.

    Prohlížeč nevyvážené značky tiše dorovná — proto to musí zachytit linter,
    ne test v DOM.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.problems: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.problems.append(f"řádek {self.getpos()[0]}: </{tag}> bez otevírací značky")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
            return
        # Zavírá se něco jiného, než co je navrchu — hledej, jestli je to
        # vůbec otevřené, a nahlas, co zůstalo nezavřené mezi tím.
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                unclosed = ", ".join(f"<{t}> z řádku {ln}" for t, ln in self.stack[i + 1:])
                self.problems.append(
                    f"řádek {self.getpos()[0]}: </{tag}> zavírá přes nezavřené {unclosed}")
                del self.stack[i:]
                return
        self.problems.append(f"řádek {self.getpos()[0]}: </{tag}> bez otevírací značky")


class MinWidth(HTMLParser):
    """Hlídá pevnou minimální šířku, kterou nemá co pohltit.

    Pohltit ji umí dvě věci: vodorovný scroll (obsah se odscrolluje) nebo
    zalomení (`flex-wrap` — prvek spadne na další řádek). Cokoli jiného tlačí
    do šířky dokumentu, a to na 320px znamená vodorovný scroll celé stránky.

    Ptá se na **předky**, ne na okno v textu. Původní verze koukala 600 znaků
    zpět a mýlila se oběma směry: u dlouhých Tailwind class stringů na rodiče
    nedosáhla a hlásila falešný nález, a naopak `overflow-x-auto` na pouhém
    *sourozenci* ji uspokojil.
    """

    ESCAPES = ("overflow-x-auto", "overflow-auto", "flex-wrap")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.problems: list[str] = []

    def _look(self, tag, attrs) -> str:
        cls = dict(attrs).get("class") or ""
        m = re.search(r"min-w-\[[^\]]+\]", cls)
        if m and not any(e in a for a in self.stack for e in self.ESCAPES):
            self.problems.append(
                f"řádek {self.getpos()[0]}: '{m.group(0)}' bez předka "
                "s overflow-x-auto ani flex-wrap")
        return cls

    def handle_starttag(self, tag, attrs):
        cls = self._look(tag, attrs)
        if tag not in VOID:
            self.stack.append(cls)

    def handle_startendtag(self, tag, attrs):
        self._look(tag, attrs)

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()


def check(html: str, extra_script: str = "") -> None:
    # Tělo bez <script> — pravidla o markupu nemají koukat do JS.
    markup = re.sub(r"<script\b.*?</script>", "", html, flags=re.S)
    script = "\n".join(re.findall(r"<script\b.*?>(.*?)</script>", html, flags=re.S))
    # Komponenta stránky země žije mimo šablonu; pro pravidla o JS je to
    # ale tentýž kód, protože build ho vkládá do téže stránky.
    script += "\n" + extra_script

    # ── Struktura: vyvážené značky ────────────────────────────────────────────
    structure = Structure()
    structure.feed(re.sub(r"<!--.*?-->", "", markup, flags=re.S))
    for problem in structure.problems:
        fail("html/structure", problem)
    for name, line in structure.stack:
        fail("html/structure", f"řádek {line}: <{name}> se nikdy nezavírá")

    # ── Flowbite: jak se váže na Alpine ───────────────────────────────────────
    # Flowbite umí dvojí: `data-*` atributy, které projde **jediný sken DOM**
    # při startu, a běžné třídy (Dropdown, Drawer) s destroy(). S Alpine sedí
    # jen to druhé — Alpine vykresluje až po startu a při přefiltrování uzly
    # zahodí a vyrobí nové, takže cokoli navěšeného skenem je pak mrtvé: je to
    # vidět, vypadá to správně a nedělá to nic, bez chyby v konzoli.
    #
    # Projekt proto váže Flowbite direktivou `x-flowbite` (src/js/flowbite-entry.js),
    # která instanci vyrobí v okamžiku, kdy Alpine uzel vytvoří, a zruší ji, když
    # ho zahodí. `data-*` atributy jsou tím pádem zakázané úplně — nic je neskenuje,
    # takže by tiše nedělaly nic.
    FLOWBITE_ATTRS = r"data-(drawer|dropdown|modal|tooltip|popover|accordion|tabs|collapse|dial|carousel)-[a-z-]+"
    for m in re.finditer(FLOWBITE_ATTRS, markup):
        fail("flowbite/binding",
             f"řádek {line_of(markup, m.start())}: '{m.group(0)}' — Flowbite se váže "
             "direktivou x-flowbite, tenhle atribut nikdo neskenuje a zůstane mrtvý")

    # Komentáře se odstraní: zmínka v poznámce („žádné initFlowbite()") není
    # volání a pravidlo, které pokárá vysvětlení sebe sama, naučí lidi výstup
    # ignorovat.
    code = re.sub(r"/\*.*?\*/", "", script, flags=re.S)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.M)
    if re.search(r"\binitFlowbite\b", code):
        fail("flowbite/binding",
             "volá se initFlowbite() — projekt Flowbite váže přes x-flowbite, "
             "jednorázový sken DOM by dvojitě navěsil to, co direktiva už vyrobila")

    # Direktiva musí mít podporovanou komponentu a existující cíl. Obojí je
    # staticky zjistitelné, dokud je cíl literál — a psát ho výrazem jen proto,
    # aby to linter neviděl, by bylo obcházení brány, ne řešení.
    SUPPORTED = {"dropdown", "drawer"}
    ids = set(re.findall(r'\bid="([^"]+)"', markup))
    for m in re.finditer(r'x-flowbite:([a-z-]*)="([^"]*)"', markup):
        comp, expr = m.group(1), m.group(2).strip()
        line = line_of(markup, m.start())
        if comp not in SUPPORTED:
            fail("flowbite/binding",
                 f"řádek {line}: x-flowbite:{comp or '(chybí)'} — podporované je "
                 + ", ".join(sorted(SUPPORTED)))
        literal = re.fullmatch(r"'([^']+)'", expr) or re.fullmatch(r'&#39;([^&]+)&#39;', expr)
        if literal and literal.group(1) not in ids:
            fail("flowbite/binding",
                 f"řádek {line}: x-flowbite:{comp} míří na #{literal.group(1)}, "
                 "který v šabloně není")

    # ── Odkazy do repozitáře musí vést na existující soubor ───────────────────
    # Šablona odkazuje na dokumentaci absolutní adresou na GitHub. Když se
    # soubor v repozitáři přejmenuje nebo rozdělí, odkaz v UI dál vede na
    # starý název a nikdo si toho nevšimne — kontrola Markdownu do HTML
    # nevidí. Zrovna se to stalo: „Schéma, číselníky a pravidla klasifikace"
    # mířilo na plán, ze kterého se schéma mezitím odstěhovalo.
    for m in re.finditer(r"blob/[^/]+/([A-Za-z0-9._/-]+\.(?:md|csv|json))", markup):
        target = ROOT / m.group(1)
        if not target.exists():
            fail("ui/repo-link",
                 f"řádek {line_of(markup, m.start())}: odkaz míří na {m.group(1)}, "
                 "který v repozitáři není")

    # ── Škála zaoblení je uzavřená ────────────────────────────────────────────
    # Tailwind nabízí šest stupňů, projekt používá čtyři: `rounded-sm` na
    # drobné čtverečky legendy, `rounded` na odznaky, `rounded-lg` na ovládací
    # prvky a karty, `rounded-full` na pilulky. Mezistupně nepřidávají význam,
    # jen rozdíl — týž odznak s počtem měl v hlavičce `rounded-md` a jinde
    # `rounded`, což je přesně ta tichá nekonzistence, kterou nikdo nenahlásí
    # a každý vidí.
    RADII_OK = {"rounded-sm", "rounded", "rounded-lg", "rounded-full"}
    for m in re.finditer(r"\brounded(?:-(?:sm|md|lg|xl|2xl|3xl|full|none))?\b", markup):
        if m.group(0) not in RADII_OK:
            fail("ui/radius",
                 f"řádek {line_of(markup, m.start())}: '{m.group(0)}' není ve škále — "
                 + ", ".join(sorted(RADII_OK)))

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
    # Kořen se hledá mezi **všemi** otevíracími značkami, ne jen mezi <div>:
    # stránka země má x-data na <body>. Dřív se tu navíc krájel `markup`
    # indexem z už uříznutého úseku, takže hledání skákalo mezi dvěma pozicemi
    # a u šablony bez <div x-data> se zacyklilo — linter se pověsil místo aby
    # něco nahlásil.
    any_tag = rf"""<([a-zA-Z][a-zA-Z0-9-]*)\b(?:[^>"']|"[^"]*"|'[^']*')*>"""
    root = next((m for m in re.finditer(any_tag, markup) if "x-data=" in m.group(0)), None)
    if "x-data=" in markup and root is None:
        fail("alpine/cloak", "x-data je v šabloně, ale nesedí na otevírací značce")
    if root and "x-cloak" not in root.group(0):
        fail("alpine/cloak", f"kořenový x-data (<{root.group(1)}>) nemá x-cloak")
    # Pravidlo smí být i ve sdíleném input.css — tam se přesunulo, když ho
    # začaly potřebovat i stránky zemí. Hlídá se, že existuje, ne kde leží.
    shared = (ROOT / "src" / "input.css")
    css_sources = html + (shared.read_text(encoding="utf-8") if shared.exists() else "")
    if "[x-cloak]" not in css_sources:
        fail("alpine/cloak",
             "chybí CSS pravidlo pro [x-cloak] v šabloně ani v src/input.css")

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
    widths = MinWidth()
    widths.feed(markup)
    for problem in widths.problems:
        fail("responsive/min-width", problem)

    # Breakpointy se skládají odspodu nahoru; max-* je opačný směr.
    for m in re.finditer(r"\bmax-(sm|md|lg|xl):", markup):
        fail("responsive/mobile-first",
             f"řádek {line_of(markup, m.start())}: '{m.group(0)}' — piš mobile-first (min-width)")


def report(path: Path) -> None:
    by_rule: dict[str, list[str]] = {}
    for rule, detail in problems:
        by_rule.setdefault(rule, []).append(detail)
    print(f"\n{path.relative_to(ROOT)}")
    for rule, details in sorted(by_rule.items()):
        print(f"  {rule} ({len(details)})")
        for d in details[:12]:
            print(f"    {d}")
        if len(details) > 12:
            print(f"    … a dalších {len(details) - 12}")


def main() -> int:
    global problems
    found = 0
    for tpl in TEMPLATES:
        path: Path = tpl["path"]
        if not path.exists():
            raise SystemExit(f"chybí {path}")
        problems = []
        extra = "\n".join(js.read_text(encoding="utf-8") for js in tpl["scripts"])
        check(path.read_text(encoding="utf-8") + tpl["closes"], extra)
        if problems:
            report(path)
            found += len(problems)
        else:
            print(f"lint_ui: {path.relative_to(ROOT)} — bez nálezů")

    if found:
        print(f"\nlint_ui: {found} nálezů", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
