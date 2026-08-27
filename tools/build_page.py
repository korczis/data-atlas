#!/usr/bin/env python3
"""Sestaví jednosouborovou stránku: data + Tailwind/Flowbite CSS + Alpine.

Výstupem jsou dva soubory se shodným obsahem, lišící se jen obalem:

  dist/index.html            plný dokument — GitHub Pages i otevření z disku
  dist/artifact.html         fragment bez <html>/<head> pro Claude Artifacts

Vše je vloženo inline. Stránka nedělá jediný síťový požadavek, takže funguje
i offline a projde přísným CSP, které blokuje externí hosty.
"""
import csv, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
DIST = ROOT / "dist"


def read_csv(path):
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_data():
    catalog = [
        dict(cat=r["Kategorie"], name=r["Web"], dom=r["Doména"], desc=r["Popis"],
             src=r["Zdroj"], visits=int(r["Návštěvy"] or 0),
             last=r["Poslední návštěva"], url=r["URL"])
        for r in read_csv(ROOT / "data" / "catalog.csv")
    ]
    longlist = []
    for r in read_csv(ROOT / "data" / "longlist.csv"):
        bm, hi = int(r["V záložkách"] or 0), int(r["Z historie"] or 0)
        src = "+".join(x for x in (("bookmarks" if bm else ""),
                                   ("history" if hi else "")) if x)
        longlist.append(dict(dom=r["Doména"], visits=int(r["Návštěvy"] or 0),
                             urls=int(r["Unikátních URL"] or 0), src=src or "history",
                             last=r["Poslední návštěva"], title=r["Ukázkový titulek"],
                             url=r["Ukázková URL"]))

    # Stabilní klíče pro x-for. Bez nich Alpine při shodných klíčech (dvě položky
    # na stejné doméně) shodí celý render — ne jen tu jednu řádku.
    for i, r in enumerate(catalog):
        r["id"] = f"c{i}"
    for i, r in enumerate(longlist):
        r["id"] = f"l{i}"
    return catalog, longlist


def build_css():
    CACHE.mkdir(exist_ok=True)
    r = subprocess.run(
        ["npx", "tailwindcss", "-c", "src/tailwind.config.js",
         "-i", "src/input.css", "-o", ".cache/out.css", "--minify"],
        cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("tailwind build selhal")
    return (CACHE / "out.css").read_text(encoding="utf-8")


def main():
    catalog, longlist = load_data()
    data = json.dumps({"catalog": catalog, "longlist": longlist},
                      ensure_ascii=False, separators=(",", ":"))

    body = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
    body = body.replace("/*__JSON__*/", data)
    CACHE.mkdir(exist_ok=True)
    (CACHE / "page.src.html").write_text(body, encoding="utf-8")

    css = build_css()
    alpine = (ROOT / "node_modules" / "alpinejs" / "dist" / "cdn.min.js").read_text(encoding="utf-8")

    m = re.match(r"\s*(<title>.*?</title>)\s*", body, re.S)
    title, rest = m.group(1), body[m.end():]
    style = f"<style>{css}</style>\n"
    # Alpine se načítá až za tělem — atlas() musí být definované dřív, než
    # se Alpine nastartuje, jinak x-data spadne na nedefinovanou funkci.
    script = f"\n<script>{alpine}</script>\n"

    DIST.mkdir(exist_ok=True)
    (DIST / "artifact.html").write_text(title + "\n" + style + rest + script, encoding="utf-8")
    (DIST / "index.html").write_text(
        '<!doctype html>\n<html lang="cs">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="Katalog GIS, geodat a nástrojů pro prostorovou analytiku.">\n'
        + title + "\n" + style + "</head>\n<body>\n" + rest + script + "</body>\n</html>\n",
        encoding="utf-8")

    for f in ("index.html", "artifact.html"):
        print(f"  dist/{f:16s} {(DIST / f).stat().st_size / 1024:7.1f} KB")
    print(f"  katalog {len(catalog)} · long list {len(longlist)} · CSS {len(css)/1024:.1f} KB")


if __name__ == "__main__":
    main()
