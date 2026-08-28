#!/usr/bin/env python3
"""Vygeneruje docs/CATALOG.md a docs/COVERAGE.md z data/catalog.csv.

Markdown je pro čtení v repu a pro grep; interaktivní verze žije na Pages.
Soubory se needitují ručně — přepíše je `just docs`.

CATALOG.md je úplný výpis v pořadí informační architektury (skupina → téma).
COVERAGE.md je matice země × rodina témat: ukazuje, kde katalog něco má a kde
zeje díra. Ručně udržovaná matice by zestárla při prvním přidaném zdroji,
takže se počítá z dat.
"""
import csv, collections, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Matice po jednotlivých tématech by měla 33 sloupců a nedala by se přečíst.
# Rodiny odpovídají otázkám, které si člověk klade při due diligence:
# „vidím pozemek?", „vidím firmu?", „vidím peníze?", „vidím riziko?".
FAMILIES = [
    ("Geo",       ["geoportal", "terrain", "basemaps", "remote-sensing"]),
    ("Katastr",   ["cadastre"]),
    ("Adresy",    ["addresses"]),
    ("Doprava",   ["transport"]),
    ("Prostředí", ["environment", "weather"]),
    ("Statistika", ["statistics"]),
    ("Open data", ["opendata"]),
    ("Sbírka",    ["gazette"]),
    ("Zakázky",   ["procurement"]),
    ("Výdaje",    ["spending"]),
    ("Firmy",     ["companies"]),
    ("Majitelé",  ["ownership"]),
    ("Závěrky",   ["filings"]),
    ("Insolvence", ["insolvency"]),
    ("Soudy",     ["courts"]),
    ("Regulace",  ["regulators"]),
    ("Nemovitosti", ["property"]),
    ("Riziko",    ["security", "cyber", "sanctions"]),
    ("Transp.",   ["transparency"]),
]


def anchor(text: str) -> str:
    keep = [c for c in text.lower() if c.isalnum() or c in " -"]
    return "".join(keep).strip().replace(" ", "-")


def load():
    with (ROOT / "data" / "catalog.csv").open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def catalog_md(rows) -> str:
    tree: dict[str, dict[str, list]] = collections.OrderedDict()
    for r in rows:
        tree.setdefault(r["Skupina"], collections.OrderedDict()) \
            .setdefault(r["Téma"], []).append(r)
    topics = collections.OrderedDict()
    for cats in tree.values():
        topics.update(cats)
    evidenced = sum(1 for r in rows if r["Zdroj"] != "reference")
    places = collections.Counter(r["Země"] for r in rows)

    out = [
        "<!-- Generováno `just docs` — needituj ručně. -->",
        "",
        "# Katalog",
        "",
        f"**{len(rows)}** položek v **{len(topics)}** tématech a **{len(places)}** zemích "
        f"a rozsazích — **{evidenced}** doložených v datech prohlížeče, "
        f"**{len(rows) - evidenced}** doplněných rešerší.",
        "",
        "Katalog má dvě nezávislé osy. **Téma** říká, o jaký druh zdroje jde "
        "(katastr, obchodní rejstřík, zakázky); **země** říká, kde platí. "
        "Filtr země je přesná shoda — celoevropské zdroje stojí pod `EU`, "
        "celosvětové pod `GLOBAL`, a needitují se sedmadvacetkrát.",
        "",
        "Sloupec **Přístup**: `open` volně, `search` jen vyhledávání, "
        "`registration` účet, `paid` zpoplatněno, `mixed` zdarma i placeně, "
        "`restricted` omezeno na oprávněný zájem.",
        "Sloupec **Data**: `bulk` hromadné stažení, `api` rozhraní, "
        "`ogc` mapové služby, `download` jednotlivé soubory, `search` jen dotaz, "
        "`sw` nástroj, ne datová sada.",
        "",
        "Sloupec **Zdroj**: `bookmarks` / `history` / `bookmarks+history` znamená, že položka",
        "je doložená v exportu prohlížeče; `reference` znamená doplněno rešerší.",
        "",
        "## Země",
        "",
    ]
    for name, n in sorted(places.items(), key=lambda kv: (-kv[1], kv[0])):
        code = next(r["Kód"] for r in rows if r["Země"] == name)
        out.append(f"- `{code}` {name} — {n}")
    out += ["", "## Témata", ""]
    for grp, cats in tree.items():
        total = sum(len(v) for v in cats.values())
        out.append(f"\n**{grp}** — {total}\n")
        for cat, items in cats.items():
            out.append(f"- [{cat}](#{anchor(cat)}) — {len(items)}")
    out.append("")

    for grp, cats in tree.items():
        out += ["", f"# {grp}", ""]
        for cat, items in cats.items():
            out += ["", f"## {cat}", "",
                    "| Země | Web | Doména | Popis | Přístup | Data | Zdroj |",
                    "|---|---|---|---|---|---|---|"]
            for r in items:
                desc = r["Popis"].replace("|", "\\|")
                out.append(f"| `{r['Kód']}` | [{r['Web']}]({r['URL']}) | `{r['Doména']}` | {desc} | "
                           f"{r['Přístup']} | {r['Data']} | {r['Zdroj']} |")
    out.append("")
    return "\n".join(out)


def coverage_md(rows) -> str:
    topics = json.loads((ROOT / "data" / "topics.json").read_text(encoding="utf-8"))
    countries = json.loads((ROOT / "data" / "countries.json").read_text(encoding="utf-8"))
    order = [c["code"] for c in countries["scopes"] + countries["countries"]]
    names = {c["code"]: c["name"] for c in countries["scopes"] + countries["countries"]}
    eu = {c["code"] for c in countries["countries"] if c.get("eu")}

    grid = collections.defaultdict(collections.Counter)
    for r in rows:
        grid[r["Kód"]][r["Téma ID"]] += 1
    present = [c for c in order if c in grid]

    out = [
        "<!-- Generováno `just docs` — needituj ručně. -->",
        "",
        "# Pokrytí",
        "",
        "Matice země × rodina témat. Číslo je počet zdrojů, prázdné pole znamená, "
        "že v katalogu k té rodině pro tu zemi nic není — buď to ještě nikdo "
        "nedohledal, nebo tam veřejně nic takového neexistuje. Poznámky "
        "k druhé možnosti patří do `docs/EU-EXPANSION-PLAN.md`.",
        "",
        "Sloupce sdružují příbuzná témata; úplné členění je v "
        "[`data/topics.json`](../data/topics.json).",
        "",
    ]
    head = "| Země | " + " | ".join(f for f, _ in FAMILIES) + " | Σ |"
    out += [head, "|" + "---|" * (len(FAMILIES) + 2)]
    for code in present:
        cells = []
        for _, ts in FAMILIES:
            n = sum(grid[code][t] for t in ts)
            cells.append(str(n) if n else "")
        total = sum(grid[code].values())
        out.append(f"| `{code}` {names[code]} | " + " | ".join(cells) + f" | **{total}** |")

    missing = sorted(eu - set(grid))
    out += ["", f"**Členských států v katalogu:** {len(eu & set(grid))} z 27."]
    if missing:
        out.append("**Bez jediného zdroje:** " + ", ".join(f"`{c}`" for c in missing) + ".")
    out += ["", "## Podle témat", "",
            "| Téma | Zdrojů | Zemí | Z toho úředních | S API nebo bulk |",
            "|---|--:|--:|--:|--:|"]
    for g in topics["groups"]:
        for t in g["topics"]:
            items = [r for r in rows if r["Téma ID"] == t["id"]]
            if not items:
                continue
            out.append(f"| {t['label']} | {len(items)} | {len({r['Kód'] for r in items})} | "
                       f"{sum(1 for r in items if r['Typ'] in ('official', 'regional', 'intl'))} | "
                       f"{sum(1 for r in items if r['Data'] in ('bulk', 'api', 'ogc'))} |")
    out += ["", "## Klasifikace", "",
            "| Přístup | Zdrojů |", "|---|--:|"]
    for k, n in collections.Counter(r["Přístup"] for r in rows).most_common():
        out.append(f"| `{k}` | {n} |")
    out += ["", "| Data | Zdrojů |", "|---|--:|"]
    for k, n in collections.Counter(r["Data"] for r in rows).most_common():
        out.append(f"| `{k}` | {n} |")
    out += ["", "| Vydavatel | Zdrojů |", "|---|--:|"]
    for k, n in collections.Counter(r["Typ"] for r in rows).most_common():
        out.append(f"| `{k}` | {n} |")
    out.append("")
    return "\n".join(out)


def main() -> None:
    rows = load()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "CATALOG.md").write_text(catalog_md(rows), encoding="utf-8")
    (docs / "COVERAGE.md").write_text(coverage_md(rows), encoding="utf-8")
    print(f"{len(rows)} položek → docs/CATALOG.md, docs/COVERAGE.md")


if __name__ == "__main__":
    main()
