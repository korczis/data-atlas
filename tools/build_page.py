#!/usr/bin/env python3
"""Sestaví jednosouborovou stránku: data + Tailwind/Flowbite CSS + Alpine.

Výstupem jsou dva soubory se shodným obsahem, lišící se jen obalem:

  dist/index.html            plný dokument — GitHub Pages i otevření z disku
  dist/artifact.html         fragment bez <html>/<head> pro Claude Artifacts

Vše je vloženo inline. Stránka nedělá jediný síťový požadavek, takže funguje
i offline a projde přísným CSP, které blokuje externí hosty.
"""
import csv, datetime, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
DIST = ROOT / "dist"
STATIC = ROOT / "static"

PKG = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
BASE = PKG["homepage"].rstrip("/") + "/"
AUTHOR = PKG["author"]

TITLE = "Geodata Atlas"

# Počty se nikdy nepíšou ručně — zestárnou při první změně katalogu.
def describe(items: int, topics: int, countries: int) -> str:
    return ("Katalog geodat, otevřených dat, veřejných registrů a OSINT/DD zdrojů pro Evropu — "
            "katastr, doprava, statistika, obchodní rejstříky, insolvence, zakázky a rizika. "
            f"{items} položek v {topics} tématech a {countries} zemích, "
            "prohledávatelných na jedné stránce.")


def og_alt(items: int, topics: int, countries: int) -> str:
    return (f"Geodata Atlas — katalog veřejných datových zdrojů, {items} položek "
            f"v {topics} tématech a {countries} zemích")


def read_csv(path):
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_data():
    """Řádky katalogu + číselníky témat a zemí.

    Číselníky se posílají zvlášť, ne na každém řádku: pořadí panelu má určovat
    taxonomie, ne to, co zrovna prošlo filtrem, a u tisícovky položek by se
    opakovaný název skupiny a země v JSONu sečetl do stovek kilobajtů.
    Vyhledávací řetězec se z týchž důvodů skládá až v prohlížeči při startu.
    """
    catalog = [
        dict(id=r["ID"], topic=r["Téma ID"], code=r["Kód"], name=r["Web"], dom=r["Doména"],
             desc=r["Popis"], kind=r["Typ"], access=r["Přístup"], data=r["Data"],
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
    # 'ord' drží pořadí informační architektury z CSV. Bez něj by se řadilo
    # podle textu tématu a '10. Spatial DB' by skončilo před '2. Globální'.
    for i, r in enumerate(catalog):
        r["ord"] = i
    for i, r in enumerate(longlist):
        r["id"] = f"l{i}"

    taxonomy = json.loads((ROOT / "data" / "topics.json").read_text(encoding="utf-8"))
    places = json.loads((ROOT / "data" / "countries.json").read_text(encoding="utf-8"))

    # Do panelu jdou jen země, které něco nesou — prázdná Malta by lhala
    # o pokrytí. Pořadí přebírá číselník, ne data.
    used = {r["code"] for r in catalog}
    place_list = [dict(code=c["code"], name=c["name"], scope=bool(c.get("scope")),
                       eu=bool(c.get("eu")))
                  for c in places["scopes"] + places["countries"] if c["code"] in used]
    used_topics = {r["topic"] for r in catalog}
    groups = [dict(label=g["label"],
                   topics=[dict(id=t["id"], label=t["label"]) for t in g["topics"]
                           if t["id"] in used_topics])
              for g in taxonomy["groups"]]
    groups = [g for g in groups if g["topics"]]
    return catalog, longlist, groups, place_list


def build_flowbite() -> str:
    """Zbundluje jen ty Flowbite komponenty, které markup skutečně používá.

    Plný UMD build má 133 kB a nese accordion, carousel, datepicker a další
    nepoužité věci. Výřez v src/js/flowbite-entry.js má 9 kB.
    """
    CACHE.mkdir(exist_ok=True)
    out = CACHE / "flowbite-min.js"
    r = subprocess.run(
        ["npx", "esbuild", "src/js/flowbite-entry.js", "--bundle", "--minify",
         "--format=iife", f"--outfile={out.relative_to(ROOT)}", "--log-level=warning"],
        cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("esbuild selhal")
    return out.read_text(encoding="utf-8")


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


def head_meta(description: str, alt: str) -> str:
    """Sada meta tagů pro dokumentovou variantu.

    Do artifact fragmentu se nevkládá: ten se vkládá do cizí <head>, takže
    by se vlastní meta tagy buď zahodily, nebo přepsaly hostitelské.
    """
    ld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "DataCatalog",
                "@id": BASE + "#catalog",
                "name": TITLE,
                "description": description,
                "url": BASE,
                "inLanguage": "cs",
                "keywords": ["GIS", "geodata", "geospatial", "open data", "veřejné registry",
                             "obchodní rejstřík", "due diligence", "OSINT", "EU",
                             "remote sensing", "PostGIS", "OpenStreetMap"],
                "license": "https://opensource.org/licenses/MIT",
                "creator": {"@type": "Person", "name": AUTHOR},
            },
            {
                "@type": "WebSite",
                "@id": BASE + "#website",
                "url": BASE,
                "name": TITLE,
                "description": description,
                "inLanguage": "cs",
                "about": {"@id": BASE + "#catalog"},
            },
        ],
    }
    og = BASE + "og-image.png"
    return f"""<meta name="description" content="{description}">
<link rel="canonical" href="{BASE}">
<meta name="author" content="{AUTHOR}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="referrer" content="strict-origin-when-cross-origin">

<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f9fafb" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#111827" media="(prefers-color-scheme: dark)">

<meta property="og:type" content="website">
<meta property="og:site_name" content="{TITLE}">
<meta property="og:locale" content="cs_CZ">
<meta property="og:url" content="{BASE}">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{og}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{alt}">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITLE}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{og}">
<meta name="twitter:image:alt" content="{alt}">

<link rel="icon" href="favicon.ico" sizes="48x48">
<link rel="icon" href="favicon.svg" type="image/svg+xml" sizes="any">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">

<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ":"))}</script>
"""


def write_site_files(description: str) -> None:
    """Doprovodné soubory webu: manifest, robots, sitemap, 404 a .nojekyll."""
    shutil.copytree(STATIC, DIST, dirs_exist_ok=True)

    (DIST / "site.webmanifest").write_text(json.dumps({
        "name": TITLE,
        "short_name": "Geodata",
        "description": description,
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "lang": "cs",
        "background_color": "#111827",
        "theme_color": "#1d4ed8",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (DIST / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n", encoding="utf-8")

    today = datetime.date.today().isoformat()
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url>\n    <loc>{BASE}</loc>\n    <lastmod>{today}</lastmod>\n"
        "    <changefreq>monthly</changefreq>\n    <priority>1.0</priority>\n  </url>\n"
        "</urlset>\n", encoding="utf-8")

    # GitHub Pages jinak protáhne výstup Jekyllem a zahodí soubory s podtržítkem
    (DIST / ".nojekyll").write_text("", encoding="utf-8")

    (DIST / "404.html").write_text(f"""<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stránka nenalezena — {TITLE}</title>
<meta name="robots" content="noindex">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<meta name="color-scheme" content="light dark">
<style>
  :root {{ --bg:#f9fafb; --fg:#111827; --muted:#6b7280; --accent:#1d4ed8; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#111827; --fg:#f3f4f6; --muted:#9ca3af; --accent:#60a5fa; }}
  }}
  body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:var(--bg); color:var(--fg); text-align:center; padding:24px;
         font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
  h1 {{ font-size:clamp(2rem,6vw,3rem); margin:0 0 .5rem; letter-spacing:-.02em; }}
  p {{ color:var(--muted); margin:0 0 1.75rem; font-size:1.05rem; }}
  a {{ color:var(--accent); font-weight:600; text-decoration:none; }}
  a:hover, a:focus-visible {{ text-decoration:underline; }}
</style>
</head>
<body>
  <main>
    <h1>404</h1>
    <p>Tahle stránka tu není.</p>
    <a href="./">Zpět na katalog</a>
  </main>
</body>
</html>
""", encoding="utf-8")


def main():
    catalog, longlist, groups, places = load_data()
    data = json.dumps({"catalog": catalog, "longlist": longlist,
                       "groups": groups, "places": places},
                      ensure_ascii=False, separators=(",", ":"))

    n_items = len(catalog)
    n_topics = len({r["topic"] for r in catalog})
    n_places = len(places)
    description = describe(n_items, n_topics, n_places)

    body = (ROOT / "src" / "template.html").read_text(encoding="utf-8")
    body = body.replace("/*__JSON__*/", data)
    CACHE.mkdir(exist_ok=True)
    (CACHE / "page.src.html").write_text(body, encoding="utf-8")

    css = build_css()
    alpine = (ROOT / "node_modules" / "alpinejs" / "dist" / "cdn.min.js").read_text(encoding="utf-8")
    flowbite = build_flowbite()

    m = re.match(r"\s*(<title>.*?</title>)\s*", body, re.S)
    title, rest = m.group(1), body[m.end():]
    style = f"<style>{css}</style>\n"
    # Pořadí je závazné:
    #   1. tělo — registruje posluchač alpine:init s Alpine.data('atlas')
    #   2. Flowbite — musí definovat initFlowbite() dřív, než ho init() zavolá
    #   3. Alpine — až on odpálí alpine:init a spustí komponentu
    script = f"\n<script>{flowbite}</script>\n<script>{alpine}</script>\n"

    DIST.mkdir(exist_ok=True)
    (DIST / "artifact.html").write_text(title + "\n" + style + rest + script, encoding="utf-8")
    (DIST / "index.html").write_text(
        '<!doctype html>\n<html lang="cs">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + title + "\n" + head_meta(description, og_alt(n_items, n_topics, n_places)) + style + "</head>\n<body>\n"
        + rest + script + "</body>\n</html>\n",
        encoding="utf-8")

    write_site_files(description)

    for f in ("index.html", "artifact.html"):
        print(f"  dist/{f:16s} {(DIST / f).stat().st_size / 1024:7.1f} KB")
    extras = sorted(f.name for f in DIST.iterdir() if f.name not in ("index.html", "artifact.html"))
    print(f"  + {len(extras)} doprovodných souborů: {', '.join(extras)}")
    print(f"  katalog {len(catalog)} · {n_topics} témat · {n_places} zemí · long list {len(longlist)} · "
          f"CSS {len(css)/1024:.1f} KB · Flowbite {len(flowbite)/1024:.1f} KB · Alpine {len(alpine)/1024:.1f} KB")


if __name__ == "__main__":
    main()
