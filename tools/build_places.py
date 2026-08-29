#!/usr/bin/env python3
"""Postaví stránku pro každou zemi a rozcestník `zeme/`.

Proč vlastní stránky a ne jen filtr v jedné aplikaci: filtr žije v hashi,
takže je pro vyhledávače neviditelný a odkaz „Rakousko" nemá vlastní titulek
ani popis. Stránka na `/at/` má obojí, dá se sdílet a indexovat a nese jen
data té země — místo 1347 položek jich načte kolem padesáti.

**Nejsou to kopie hlavní stránky.** Ta zůstává soběstačná, se vším vloženým
dovnitř. Stránky zemí naopak sdílejí `assets/atlas.css` a `assets/atlas.js`:
třiatřicet kopií stotřicetikilobajtového runtime by byly čtyři megabajty
duplikátu za nic. Cena je jeden požadavek navíc, který se hned kešuje.

Vše se generuje z `data/catalog.csv`, `data/topics.json` a
`data/countries.json` — počty, seznamy ani skloňování se nikde nepíšou rukou.
"""
from __future__ import annotations

import base64, csv, datetime, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT / "tools"))

PKG = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
BASE = PKG["homepage"].rstrip("/") + "/"
REPO = PKG["repository"]["url"].replace(".git", "") if isinstance(PKG.get("repository"), dict) \
    else "https://github.com/korczis/data-atlas"
TITLE = "Data Atlas"

# Popisky přístupu a formy dat jsou v build_catalog.py vedle validace hodnot.
from build_catalog import ACCESS, DATA_MODES as DATA  # noqa: E402


def slug(code: str) -> str:
    return code.lower()


def rows_for(catalog: list[dict], code: str) -> list[dict]:
    out = []
    for r in catalog:
        if r["code"] != code:
            continue
        row = {"id": r["id"], "name": r["name"], "domain": r["dom"], "url": r["url"],
               "desc": r["desc"], "topic": r["topic"], "access": r["access"],
               "data": r["data"], "ord": r["ord"]}
        # Předpočítané hledací pole: skládat ho v prohlížeči při každém stisku
        # klávesy je zbytečná práce, a v datech je to jeden řetězec navíc.
        row["s"] = " ".join([r["name"], r["dom"], r["desc"]]).lower()
        out.append(row)
    return out


def head(title: str, desc: str, canonical: str, depth: int, jsonld: dict) -> str:
    up = "../" * depth
    return (
        '<!doctype html>\n<html lang="cs">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n"
        f'<meta name="description" content="{desc}">\n'
        f'<link rel="canonical" href="{canonical}">\n'
        '<meta name="robots" content="index,follow">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:site_name" content="{TITLE}">\n'
        '<meta property="og:locale" content="cs_CZ">\n'
        f'<meta property="og:url" content="{canonical}">\n'
        f'<meta property="og:title" content="{title}">\n'
        f'<meta property="og:description" content="{desc}">\n'
        f'<meta property="og:image" content="{BASE}og-image.png">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<link rel="icon" href="{up}favicon.svg" type="image/svg+xml">\n'
        f'<link rel="apple-touch-icon" href="{up}apple-touch-icon.png">\n'
        f'<link rel="stylesheet" href="{up}assets/atlas.css">\n'
        f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False, separators=(",", ":"))}</script>\n'
        # Motiv se razí ještě před vykreslením, jinak při uložené volbě
        # „tmavý" problikne světlá stránka.
        "<script>try{var t=localStorage.getItem('geodata-atlas-theme');"
        "if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t);}"
        "catch(e){}</script>\n"
        "</head>\n")


def flag_span(place: dict, meta: dict) -> str:
    """Vlajka ve větší velikosti než v panelu: sprite je jeden, mění se měřítko.

    `meta` je celý obsah flags.json, ne jen mapa posunů — sáhnout do něj přímo
    znamená, že se pro každou zemi najde `False` a všechny dostanou hvězdičku.
    """
    offsets = meta["offsets"]
    if place["scope"] or place["code"] not in offsets:
        return ('<span class="rounded bg-gray-100 px-2 py-1 font-mono text-xs font-semibold '
                'text-gray-700 dark:bg-gray-700 dark:text-gray-300" aria-hidden="true">'
                + ("EU" if place["code"] == "EU" else "★") + "</span>")
    return (f'<span class="flag" aria-hidden="true" style="width:36px;height:26px;'
            f'background-size:{meta["width"] * 1.8:.0f}px 26px;'
            f'background-position-x:{offsets[place["code"]] * 1.8:.0f}px"></span>')


def build(catalog, groups, places, offsets) -> int:
    place_js = (SRC / "js" / "place.js").read_text(encoding="utf-8")
    tpl = (SRC / "country.html").read_text(encoding="utf-8")
    labels = {"topics": {t["id"]: t["label"] for g in groups for t in g["topics"]},
              "access": ACCESS, "data": DATA}
    # Kolik k tématu nese EU a GLOBAL. Posílá se jen počet, ne řádky: stránka
    # země je o té zemi, ale zamlčet, že k témuž tématu existuje celoevropský
    # zdroj, by z ní udělalo slepou uličku. Kliknutí vede do hlavního katalogu,
    # takže se nic neduplikuje — 188 nadnárodních řádků krát 31 stránek by byl
    # megabajt navíc za informaci, která se vejde do čísla.
    supra = {}
    for r in catalog:
        if r["code"] in ("EU", "GLOBAL"):
            key = r["topic"]
            supra.setdefault(key, {"eu": 0, "global": 0})
            supra[key]["eu" if r["code"] == "EU" else "global"] += 1

    written = []
    for place in places:
        code = place["code"]
        rows = rows_for(catalog, code)
        if not rows:
            continue
        # Skloňování přichází z data/countries.json, ne z tabulky v tomhle
        # souboru: název země patří do číselníku jednou, ne dvakrát.
        nom, acc = place["name"], place.get("acc") or place["name"]
        n_topics = len({r["topic"] for r in rows})
        desc = (f"{len(rows)} ověřených veřejných datových zdrojů pro {acc} "
                f"v {n_topics} tématech — katastr, registry, otevřená data, "
                f"insolvence, zakázky a dohled. U každého je uvedeno, "
                f"jestli je přístupný a co z něj jde získat.")
        canonical = f"{BASE}{slug(code)}/"
        jsonld = {
            "@context": "https://schema.org", "@type": "CollectionPage",
            "@id": canonical + "#page", "name": f"{nom} — {TITLE}",
            "description": desc, "url": canonical, "inLanguage": "cs",
            "isPartOf": {"@type": "WebSite", "@id": BASE + "#website", "name": TITLE, "url": BASE},
            "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Katalog", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "Země", "item": BASE + "zeme/"},
                {"@type": "ListItem", "position": 3, "name": nom, "item": canonical}]},
            "mainEntity": {"@type": "ItemList", "numberOfItems": len(rows),
                           "itemListElement": [
                               {"@type": "ListItem", "position": i + 1,
                                "url": r["url"], "name": r["name"]}
                               for i, r in enumerate(rows[:50])]},
        }
        body = (tpl.replace("{{ROOT}}", "../").replace("{{NAME}}", nom)
                   .replace("{{NAME_LOC}}", nom).replace("{{NAME_ACC}}", acc)
                   .replace("{{CODE}}", code).replace("{{REPO}}", REPO)
                   .replace("{{FLAG}}", flag_span(place, offsets))
                   .replace("{{INTRO}}", desc))
        payload = json.dumps({"rows": rows, "groups": groups, "labels": labels,
                              "supra": supra},
                             ensure_ascii=False, separators=(",", ":"))
        out = DIST / slug(code)
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(
            head(f"{nom} — {TITLE}", desc, canonical, 1, jsonld)
            + body
            + f'\n<script>window.__PLACE__={payload};</script>\n'
            + f'<script>{place_js}</script>\n'
            + '<script src="../assets/atlas.js"></script>\n</body>\n</html>\n',
            encoding="utf-8")
        written.append((code, len(rows), (out / "index.html").stat().st_size))
    return written


def build_index(places, catalog, offsets) -> None:
    """Rozcestník `zeme/` — jediné místo, kde jsou všechny stránky pohromadě."""
    counts = {}
    for r in catalog:
        counts[r["code"]] = counts.get(r["code"], 0) + 1
    listed = [p for p in places if counts.get(p["code"])]
    canonical = BASE + "zeme/"
    desc = (f"Přehled {len(listed)} zemí a nadnárodních rozsahů v katalogu "
            "Data Atlas. Každá má vlastní stránku se seznamem ověřených "
            "veřejných datových zdrojů.")
    jsonld = {"@context": "https://schema.org", "@type": "CollectionPage",
              "@id": canonical + "#page", "name": f"Země — {TITLE}",
              "description": desc, "url": canonical, "inLanguage": "cs",
              "isPartOf": {"@type": "WebSite", "@id": BASE + "#website",
                           "name": TITLE, "url": BASE}}
    cards = []
    for p in sorted(listed, key=lambda p: (not p["scope"], p["name"])):
        nom = p["name"]
        cards.append(
            f'<li><a href="../{slug(p["code"])}/" class="flex items-center gap-3 rounded-lg '
            'border border-gray-200 p-4 hover:border-primary-500 hover:bg-gray-50 '
            'dark:border-gray-700 dark:hover:border-primary-500 dark:hover:bg-gray-700/40">'
            + flag_span(p, offsets)
            + f'<span class="min-w-0 flex-1"><span class="block truncate font-medium '
              f'text-gray-900 dark:text-white">{nom}</span>'
              f'<span class="block font-mono text-xs text-gray-500 dark:text-gray-400">{p["code"]}</span></span>'
            + f'<span class="shrink-0 tabular-nums text-sm text-gray-600 dark:text-gray-300">{counts[p["code"]]}</span>'
            "</a></li>")
    body = f"""<body class="font-sans antialiased text-gray-900 dark:text-gray-100">
<header class="sticky top-0 z-40 w-full border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
  <div class="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:px-6">
    <a href="../" aria-label="Data Atlas — katalog"
       class="flex shrink-0 items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
      <img src="../favicon.svg" alt="" width="28" height="28" class="h-7 w-7">
      <span class="hidden whitespace-nowrap sm:inline">Data&nbsp;Atlas</span>
    </a>
    <nav aria-label="Drobečková navigace" class="min-w-0 flex-1">
      <ol class="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400">
        <li><a href="../" class="hover:underline">Katalog</a></li>
        <li aria-hidden="true">/</li>
        <li class="font-medium text-gray-900 dark:text-white">Země</li>
      </ol>
    </nav>
  </div>
</header>
<main class="mx-auto max-w-6xl px-4 py-8 sm:px-6">
  <h1 class="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-white sm:text-4xl">Země</h1>
  <p class="mt-3 max-w-3xl text-base leading-relaxed text-gray-600 dark:text-gray-300">{desc}</p>
  <ul class="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
    {''.join(cards)}
  </ul>
</main>
</body>
</html>
"""
    out = DIST / "zeme"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(
        head(f"Země — {TITLE}", desc, canonical, 1, jsonld) + body, encoding="utf-8")


def write_sitemap(written) -> None:
    """Sitemapu píše až tenhle krok, protože až tady je známý seznam stránek.

    `build_page.py` ji zakládá s jedním záznamem; kdyby zůstala jeho,
    vyhledávače by o stránkách zemí nevěděly a celý důvod, proč vznikly,
    by padl.
    """
    today = datetime.date.today().isoformat()
    urls = [(BASE, "1.0"), (BASE + "zeme/", "0.8")]
    urls += [(f"{BASE}{slug(code)}/", "0.7") for code, _, _ in written]
    body = "".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>monthly</changefreq>\n    <priority>{prio}</priority>\n  </url>\n"
        for loc, prio in urls)
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body + "</urlset>\n", encoding="utf-8")


def main() -> int:
    import build_page

    catalog, longlist, groups, places, _gaps = build_page.load_data()
    offsets = json.loads((SRC / "assets" / "flags.json").read_text(encoding="utf-8"))

    # Sdílený runtime. Stránky zemí ho načtou jako soubor; index.html si ho
    # dál vkládá dovnitř a zůstává soběstačný.
    assets = DIST / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "atlas.css").write_text(build_page.build_css() + build_page.flag_css(),
                                      encoding="utf-8")
    alpine = (ROOT / "node_modules" / "alpinejs" / "dist" / "cdn.min.js").read_text(encoding="utf-8")
    # Pořadí je závazné: Flowbite musí definovat initFlowbite() dřív, než ho
    # zavolá init() komponenty, a Alpine se pouští až nakonec.
    (assets / "atlas.js").write_text(build_page.build_flowbite() + "\n" + alpine,
                                     encoding="utf-8")

    written = build(catalog, groups, places, offsets)
    build_index(places, catalog, offsets)
    write_sitemap(written)

    total = sum(size for _, _, size in written)
    print(f"  stránky zemí: {len(written)} · celkem {total / 1024:.0f} KB · "
          f"největší {max(size for _, _, size in written) / 1024:.0f} KB")
    print(f"  sdílený runtime: atlas.css {(assets / 'atlas.css').stat().st_size / 1024:.0f} KB"
          f" · atlas.js {(assets / 'atlas.js').stat().st_size / 1024:.0f} KB")
    print(f"  sitemapa: {len(written) + 2} adres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
