#!/usr/bin/env python3
"""Vygeneruje docs/CATALOG.md z data/catalog.csv.

Markdown je pro čtení v repu a pro grep; interaktivní verze žije na Pages.
Soubor se needituje ručně — přepíše ho `just docs`.
"""
import csv, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def anchor(text: str) -> str:
    keep = [c for c in text.lower() if c.isalnum() or c in " -"]
    return "".join(keep).strip().replace(" ", "-")


def main() -> None:
    with (ROOT / "data" / "catalog.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    # Dvě úrovně: skupina → kategorie. Plochý seznam sedmnácti kategorií
    # je na 218 položek nepřehledný.
    tree: dict[str, dict[str, list]] = collections.OrderedDict()
    for r in rows:
        tree.setdefault(r["Skupina"], collections.OrderedDict()) \
            .setdefault(r["Kategorie"], []).append(r)
    groups = collections.OrderedDict()
    for cats in tree.values():
        groups.update(cats)
    evidenced = sum(1 for r in rows if r["Zdroj"] != "reference")

    out = [
        "<!-- Generováno `just docs` — needituj ručně. -->",
        "",
        "# Katalog",
        "",
        f"**{len(rows)}** položek v **{len(groups)}** kategoriích — "
        f"**{evidenced}** doložených v datech prohlížeče, "
        f"**{len(rows) - evidenced}** doplněných referenčně.",
        "",
        "Sloupec **Zdroj**: `bookmarks` / `history` / `bookmarks+history` znamená, že položka",
        "je doložená v exportu; `reference` znamená doplněno ručně.",
        "U odkazů s hlubší cestou se návštěvy počítají jen při skutečné shodě URL —",
        "statistika celé domény se na ně nepřenáší, aby `github.com` nedělal dojem,",
        "že jsi navštívil konkrétní repozitář.",
        "",
        "## Kategorie",
        "",
    ]
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
                    "| Web | Doména | Popis | Zdroj | Návštěv | Poslední |",
                    "|---|---|---|---|--:|---|"]
            for r in items:
                desc = r["Popis"].replace("|", "\\|")
                out.append(f"| [{r['Web']}]({r['URL']}) | `{r['Doména']}` | {desc} | "
                           f"{r['Zdroj']} | {r['Návštěvy'] or '–'} | {r['Poslední návštěva'] or '–'} |")
    out.append("")

    target = ROOT / "docs" / "CATALOG.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("\n".join(out), encoding="utf-8")
    print(f"{len(rows)} položek → {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
