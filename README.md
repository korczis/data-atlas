# Geodata Atlas

Katalog GIS a geodatových zdrojů — datasety, katastr, doprava, remote sensing,
prostorové databáze a analytika. Prohledávatelný, filtrovatelný, na jedné stránce.

**→ [korczis.github.io/geodata-atlas](https://korczis.github.io/geodata-atlas/)**

Katalog vznikl z vlastních Chrome záložek a historie: co jsem za roky práce
s geodaty reálně používal, doplněné o zdroje, které do obrázku patří, i když
je zrovna nemám v historii.

## Co v tom je

142 položek v 17 kategoriích:

| | |
|---|---|
| Gazetteery a geokódování | Nominatim, GeoNames, Pelias, RÚIAN/VDP, OpenAddresses |
| Globální geodata | Natural Earth, GADM, geoBoundaries, Overture, TIGER/Line, Geofabrik |
| ČR — katastr a geodata | ČÚZK (KN, geoportál, ZABAGED, DMR), ArcČR, DIBAVOD, LPIS, ČGS |
| ČR — doprava a mobilita | Golemio, ŘSD, NDIC/dopravniinfo, PID |
| Crime, IZS, bezpečnost | SFPD dashboard, data.police.uk, portály HZS, ACLED, GDELT |
| Remote sensing | Copernicus, EarthExplorer, NASA Earthdata, OpenTopography, STAC |
| Statistika a demografie | ČSÚ, Eurostat GISCO, WorldPop, GHSL |
| Historické mapy | David Rumsey, Old Maps Online, Mapire, archiv ČÚZK |
| Mapové knihovny a basemapy | MapLibre, Leaflet, deck.gl, OpenLayers, Protomaps, PMTiles |
| Spatial DB a analytika | PostGIS, GDAL, QGIS, GeoPandas, DuckDB spatial, Sedona, H3 |
| Routing | OSRM, Valhalla, GraphHopper, pgRouting, OSMnx |
| Formáty a standardy | GeoParquet, COG, FlatGeobuf, EPSG.io, OGC API, STAC |

Plný výpis je v [`docs/CATALOG.md`](docs/CATALOG.md), strojově čitelný
v [`data/catalog.csv`](data/catalog.csv).

## Zdroj a jeho meze

Sloupec **Zdroj** říká, odkud položka pochází:

- `bookmarks` / `history` / `bookmarks+history` — doloženo v exportu prohlížeče,
  včetně počtu návštěv a data poslední návštěvy
- `reference` — doplněno ručně, protože do katalogu patří

**Chrome drží historii jen zhruba 90 dní.** Cokoli staršího v datech není,
takže nízký počet návštěv neznamená, že zdroj není používaný — jen že se do
okna nevešel.

Návštěvy se u odkazů s hlubší cestou počítají jen při skutečné shodě URL.
Bez toho by `github.com/…/awesome-geospatial` zdědil statistiku celého GitHubu
a tvářil se jako nejnavštěvovanější položka katalogu.

## Práce s repozitářem

```bash
just install     # npm závislosti
just build       # dist/index.html z data/*.csv
just check       # build + lint + testy + responzivita
just serve       # náhled na localhost:8000
just             # všechny recepty
```

Build vyrábí dvě varianty téhož:

- `dist/index.html` — stránka pro web. Veškeré CSS a JS je inline; zvenčí
  nestahuje nic, jen vedle sebe má ikony a manifest.
- `dist/artifact.html` — **jediný soběstačný soubor**, bez jakéhokoli odkazu
  na doprovodné soubory. Pro Claude Artifacts a pro poslání e-mailem.

Tailwind, Flowbite i Alpine.js jsou vloženy inline, takže obojí funguje z disku,
offline i pod přísným CSP. Hlídá to 83 testů ve čtyřech sadách
(`smoke` · `interact` · `meta` · `flowbite`), linter konvencí a měření
responzivity v headless Chrome.

### Rozvržení

Mobile-first. Pod `md` se katalog vykresluje jako karty, výš jako tabulka
s řaditelnými sloupci — tabulka o šesti sloupcích se na telefon nevejde.
Pohled se pod `sm` přepíná spodní navigací, výš záložkami; filtry jsou pod `lg`
v šuplíku, výš rozbalené v liště. Obě větve čtou týž getter a testy ověřují,
že vykreslí stejný počet položek.

Konvence Flowbite a Alpine popisuje [`docs/UI-RULES.md`](docs/UI-RULES.md)
a vynucuje `just lint`. `just responsive` měří vodorovné přetečení v headless
Chrome na šířkách 320 – 1536 px.

### Přidání položky

Edituj `data/catalog.csv`, pak `just build docs`. Sloupce `Zdroj`, `Návštěvy`
a `Poslední návštěva` nech u ručně přidaných prázdné — patří datovému řetězu.

### Ikony a OG karta

`static/` obsahuje vygenerované ikony, favicon, maskable ikonu a sociální kartu
1200×630. Zdroje jsou v `src/assets/` (`icon.svg`, `og.html`); přegeneruje je
`just assets` — potřebuje headless Chrome a ImageMagick. Výstupy jsou
committnuté, aby CI nemuselo nic renderovat.

Počty na kartě i v `<meta name="description">` se berou z `data/catalog.csv`.
Nikde se nepíšou ručně, takže nemůžou zestárnout.

### Přegenerování z prohlížeče

Vyžaduje Chrome profil na disku, běží jen lokálně:

```bash
just refresh     # extract → scan → catalog → sanitize → docs → build
just extract "~/Library/Application Support/Google/Chrome/Profile 1"
```

`tools/extract.py` čte `AccountBookmarks` (u přihlášeného účtu jsou záložky
tam, ne v `Bookmarks`) a kopii `History`, aby nenarazil na zámek Chromu.

## SEO a sdílení

Hlavička je kompletní: canonical, `robots`, Open Graph, Twitter card
`summary_large_image`, `theme-color` pro světlý i tmavý motiv, sada ikon,
web app manifest a strukturovaná data schema.org (`DataCatalog` + `WebSite`).
Build k tomu generuje `robots.txt`, `sitemap.xml`, `404.html` a `.nojekyll`.

Sada `tests/meta.mjs` ověřuje každý tag i doprovodný soubor — chybějící
`og:image` se totiž jinak pozná až ve chvíli, kdy někdo odkaz nasdílí
a vypadne mu prázdná karta.

## Soukromí

Datový řetěz pracuje s osobní historií prohlížení, takže je postavený tak,
aby ji nešlo zveřejnit omylem:

- `.cache/` je v `.gitignore` a **veškeré syrové výstupy končí tam** —
  `raw.json` i `longlist.raw.csv`
- do `data/` se dostane jen to, co projde `tools/sanitize.py`
- sanitizer je allowlist-first: vyhazuje interní hostnames, privátní a VPN
  adresy, tunely, zdravotnické a identitní služby, a všechno, co netrefí
  téma geo/data. Z 192 kandidátů projde 53.
- test relevance běží **jen nad doménou**, ne nad titulkem stránky — české
  e-shopy inzerují „Doprava zdarma", což na `doprav` sedne stejně dobře
  jako Ředitelství silnic a dálnic
- hostnames vlastní sítě patří do `config/private-hosts.txt`, který je také
  v `.gitignore`. Committnuté pravidlo `^orin\.` je stejný únik jako
  committnutý hostname, proto v `tools/sanitize.py` zůstávají jen obecné
  vzory (holé IP, tunely, `.local`). Šablona je
  [`config/private-hosts.example.txt`](config/private-hosts.example.txt)

Před každým zveřejněním stojí za to projet `python3 tools/sanitize.py` a
podívat se, co vyhodilo.

## Licence

Kód a nástroje: [MIT](LICENSE).

Katalog v `data/` je soupis veřejných odkazů s vlastními popisy — ber ho jako
CC0, s tím, že odkazované zdroje mají svoje vlastní licence a je potřeba se
řídit jimi.
