# Data Atlas

Katalog geodat, otevřených dat, veřejných registrů a OSINT/DD zdrojů Evropské unie —
katastr, doprava, statistika, obchodní rejstříky, skuteční majitelé, insolvence, zakázky,
soudy, regulace a rizika. Prohledávatelný, filtrovatelný, na jedné stránce.

**→ [korczis.github.io/data-atlas](https://korczis.github.io/data-atlas/)**

Projekt se jmenoval Geodata Atlas, dokud šlo o geodata. Dnes je většina katalogu
jinde — registry, insolvence, dohled, transparence — a název i adresa tomu
odpovídají. **Starý odkaz `korczis.github.io/geodata-atlas/` po přejmenování
vrací 404**; GitHub Pages přesměrování na novou cestu nedělá.

Klíč v `localStorage` zůstává `geodata-atlas-theme` schválně. Origin je
`korczis.github.io`, sdílený se všemi projekty na tom účtu, takže klíč je jen
jmenný prostor — a jeho přejmenování by každému návštěvníkovi tiše smazalo
uloženou volbu motivu.

### Náhledové obrázky

`just assets` generuje ikony i oba náhledy z **dat**, ne z ručně psaných čísel,
takže po přírůstku katalogu nelžou:

| Soubor | Rozměr | K čemu |
|---|---|---|
| `static/og-image.png` | 1200×630 | `og:image` a `twitter:image` — odkaz sdílený na sítích |
| `static/social-preview.png` | 1280×640 | **Social preview repozitáře** — nahrává se ručně v Settings → General → Social preview |

Náhled repozitáře nese matici pokrytí ve stejném barevném klíči jako stránka
(odstín = rodina tématu, sytost = počet zdrojů). Čísla v buňkách na něm
schválně nejsou: náhled se v odkazech zmenšuje a byla by z nich šmouha.

Jádro katalogu vzniklo z vlastních Chrome záložek a historie: co jsem za roky práce
s geodaty reálně používal. Zbytek je rešerše — všech 27 členských států, zdroj po zdroji,
s ověřenou adresou a popsaným způsobem přístupu.

## Co v tom je

Dvě nezávislé osy: **téma** říká, o jaký druh zdroje jde, **země** říká, kde platí.
Rejstřík firem je `companies` bez ohledu na to, jestli je český nebo maltský; Malta
je `MT` bez ohledu na to, jestli jde o katastr nebo o soudy.

| Skupina | Témata |
|---|---|
| Geodata | geoportály a NSDI, katastr a pozemkové knihy, adresy, ortofoto a výškopis, prostředí a geologie, doprava, remote sensing, globální referenční data |
| Veřejná data a správa | otevřená data, statistika, legislativa a věstníky, veřejné zakázky, rozpočty a dotace |
| Firmy a due diligence | obchodní rejstříky, skuteční majitelé, účetní závěrky, insolvence, soudy, regulace a licence, nemovitosti |
| Rizika a OSINT | sankce, kriminalita a IZS, kyberbezpečnost, počasí, transparentnost a volby, OSINT, archivy |
| Nástroje | gazetteery, mapové knihovny, spatial DB, routing, formáty |
| Učení | komunita a kurzy |

Celoevropské zdroje (TED, data.europa.eu, Eurostat, BRIS, VIES, EBA, ESMA…) stojí
pod rozsahem `EU` a needitují se sedmadvacetkrát; celosvětové pod `GLOBAL`.

Plný výpis je v [`docs/CATALOG.md`](docs/CATALOG.md), matice pokrytí
v [`docs/COVERAGE.md`](docs/COVERAGE.md), strojově čitelně v [`data/catalog.csv`](data/catalog.csv).
Jak přidat zemi nebo zdroj popisuje [`docs/EU-EXPANSION-PLAN.md`](docs/EU-EXPANSION-PLAN.md).

## Co katalog říká o přístupu

U každého zdroje stojí, **jestli se dovnitř dostaneš** a **co si odneseš** — jsou to dvě
různé věci a u registrů, kvůli kterým katalog vzniká, se pravidelně pletou.

- `open` · `registration` · `paid` · `mixed` · `restricted` — překážka v přístupu
- `bulk` · `api` · `ogc` · `download` · `search` · `none` — strojová dostupnost

**Veřejné vyhledávání není otevřená data.** Rejstřík, ve kterém si kdokoli najde firmu,
ale nedá se stáhnout, je `open` + `search`. Rozdíl mezi „vidím to v prohlížeči"
a „můžu s tím počítat" je přesně to, co u prověrky rozhoduje.

**Licence se nehádá.** Když ji nešlo zjistit rychle, není v katalogu.

## Zdroj a jeho meze

Sloupec **Zdroj** říká, odkud položka pochází:

- `bookmarks` / `history` / `bookmarks+history` — doloženo v exportu prohlížeče,
  včetně počtu návštěv a data poslední návštěvy
- `reference` — doplněno rešerší a ověřeno odkazem, ne návštěvou

**Chrome drží historii jen zhruba 90 dní.** Cokoli staršího v datech není,
takže nízký počet návštěv neznamená, že zdroj není používaný — jen že se do
okna nevešel.

Návštěvy se u odkazů s hlubší cestou počítají jen při skutečné shodě URL.
Bez toho by `github.com/…/awesome-geospatial` zdědil statistiku celého GitHubu
a tvářil se jako nejnavštěvovanější položka katalogu.

## Práce s repozitářem

```bash
just install     # npm závislosti
just catalog     # data/catalog.csv z data/sources/*.json
just build       # dist/index.html z data/catalog.csv
just check       # validace dat + build + lint + testy + responzivita + a11y
just links       # ověření odkazů (chodí po síti; --country AT, --topic companies, --changed)
just serve       # náhled na localhost:8000
just             # všechny recepty
```

### Datový řetěz

```
data/sources/<KÓD>.json  ─┐
data/topics.json          ├─→ tools/build_catalog.py ─→ data/catalog.csv ─→ stránka + docs
data/countries.json       │
data/provenance.csv      ─┘
                            tools/build_provenance.py ←─ .cache/raw.json   (jen lokálně)
```

**Zdrojem pravdy jsou `data/sources/*.json`** — jeden soubor na zemi nebo rozsah.
`data/catalog.csv`, `docs/CATALOG.md` i `docs/COVERAGE.md` se z nich generují.

Doložení z prohlížeče se počítá odděleně a committuje jako `data/provenance.csv`.
Veřejný build tedy projde i na čistém klonu bez cizího Chrome profilu — hlídá to
`tools/validate_sources.py`.

Build vyrábí tři věci:

- `dist/index.html` — stránka pro web. Veškeré CSS a JS je inline; zvenčí
  nestahuje nic, jen vedle sebe má ikony a manifest.
- `dist/artifact.html` — **jediný soběstačný soubor**, bez jakéhokoli odkazu
  na doprovodné soubory. Pro Claude Artifacts a pro poslání e-mailem.
- `dist/<kód>/` a `dist/zeme/` — stránka pro každou zemi a rozcestník mezi nimi
  (`tools/build_places.py`). Viz [Stránky zemí](#stránky-zemí).

Tailwind, Flowbite i Alpine.js jsou vloženy inline, takže obojí funguje z disku,
offline i pod přísným CSP.

Z Flowbite se bundluje jen to, co markup opravdu používá: plný `flowbite.min.js`
má 133 kB a nese accordion, carousel či datepicker, které tu nejsou — výřez
s jediným šuplíkem má 9 kB.

Hlídá to pět testových sad (`smoke` · `interact` · `meta` · `flowbite` ·
`places`), validace kurátorovaných dat, linter konvencí, měření responzivity
a audit přístupnosti přes axe-core — vše v `just check`. Responzivita i axe
běží nad oběma šablonami, ne jen nad hlavní stránkou.

### Rozvržení

Aplikační shell adaptovaný z Flowbite Pro Admin Dashboardu — horní lišta,
postranní panel, hlavní obsah a lepivá souhrnná lišta. Podrobnosti k licenci
jsou v [`NOTICE.md`](NOTICE.md).

V liště sedí **hledání** (nejpoužívanější prvek patří tam, kde neodscrolluje)
a **přepínač motivu se třemi stavy**: světlý → tmavý → podle systému. Volba se
ukládá a razí se ještě před vykreslením, aby při uložené tmavé neproblikla
světlá stránka. Pod záhlavím stránky stojí **čipy aktivních filtrů**, každý
maže jen svůj filtr; hlavička tabulky je lepivá.

Panel nese obě osy: **země** s vlastním filtrovacím polem (sedmadvacet států
plus nadnárodní rozsahy se do plochého seznamu nevejde) a **témata** seskupená
do šesti rodin. Počty se počítají křížem — při vybraném Rakousku ukazují témata
počty v Rakousku, při vybraném tématu ukazují země počty v tom tématu.
Filtr se propisuje do URL (`#country=DE&topic=companies`), takže výřez katalogu
jde poslat dál; v URL stojí stabilní identifikátor tématu, ne popisek.

Na prázdném katalogu se nahoře ukáže **úvodní rozcestník**: o co jde, počty
odvozené z dat a rychlé vstupy po zemích a tématech. Jakýkoli filtr ho schová,
takže sdílený odkaz jako `#country=DE&topic=companies` vede rovnou do dat —
rozcestník by překážel právě těm, kdo už vědí, co hledají.

Katalog se vykresluje **po dávkách** — všech 1050 položek naráz znamenalo na
telefonu 16 453 uzlů DOM a vteřiny prázdné, nereagující stránky. Doscrollování
načte další; počty i export do CSV přitom pracují s celým výběrem, ne s tím,
co je zrovna na obrazovce.

Mobile-first. Pod `md` se katalog vykresluje jako karty, výš jako tabulka
s řaditelnými sloupci. **Vykresluje se vždy jen ta větev, která je vidět** —
držet v DOM obě stálo u tisícovky položek zhruba vteřinu navíc a dvojnásobek
uzlů, z toho polovinu neviditelných.

Konvence Flowbite a Alpine popisuje [`docs/UI-RULES.md`](docs/UI-RULES.md)
a vynucuje `just lint` — nad **oběma** šablonami, `src/template.html`
i `src/country.html`. `just responsive` měří vodorovné přetečení v headless
Chrome na šířkách 320 – 1536 px, `just a11y` pouští axe-core ve čtyřech
scénářích (mobil i desktop × světlý i tmavý motiv); obojí se pouští zvlášť
i na stránce země (`--page place`).

### Stránky zemí

Vedle jedné aplikace stojí **stránka pro každou zemi** — `/at/`, `/de/`, `/cz/`
— a rozcestník `/zeme/`. Důvod je adresovatelnost: filtr hlavní stránky žije
v hashi, takže je pro vyhledávače neviditelný a odkaz „Rakousko" nemá vlastní
titulek ani popis. `/at/` má obojí, dá se sdílet a indexovat a nese jen data té
země — místo celého katalogu načte pár desítek položek.

Nejsou to kopie hlavní stránky. Ta zůstává soběstačná, se vším vloženým
dovnitř; stránky zemí naopak sdílejí `dist/assets/atlas.css` a
`dist/assets/atlas.js`, protože jednatřicet kopií stotřicetikilobajtového
runtime by byly čtyři megabajty duplikátu za nic. Cena je jeden požadavek
navíc, který se hned kešuje.

Šablona je `src/country.html` + `src/js/place.js`, generuje je
`tools/build_places.py`, hlídá `tests/places.mjs`. Vše — titulek, popis,
JSON-LD, počty i seznam témat — se odvozuje z `data/catalog.csv`
a číselníků; ručně se nepíše ani jedno číslo.

Tabulka má vlastní hledání, filtr tématu a přístupu a stránkování po padesáti
(vzory Table search / filter / pagination z Flowbite). Stav se propisuje do
URL (`#topic=companies&page=2`). Dávkování jako na hlavní stránce tu není:
u stovky položek je stránkování levnější i srozumitelnější.

### Přidání zdroje

Edituj `data/sources/<KÓD>.json`, pak `just validate`, `just links --changed`
a `just catalog docs build`. Schéma, číselníky a pravidla pro klasifikaci přístupu
jsou v [`docs/EU-EXPANSION-PLAN.md`](docs/EU-EXPANSION-PLAN.md).

### Ikony a OG karta

`static/` obsahuje vygenerované ikony, favicon, maskable ikonu a sociální kartu
1200×630. Zdroje jsou v `src/assets/` (`icon.svg`, `og.html`); přegeneruje je
`just assets` — potřebuje headless Chrome a ImageMagick. Výstupy jsou
committnuté, aby CI nemuselo nic renderovat.

Počty na kartě i v `<meta name="description">` se berou z `data/catalog.csv`.
Nikde se nepíšou ručně, takže nemůžou zestárnout.

### Přegenerování z prohlížeče

Vyžaduje Chrome profil na disku, běží jen lokálně a týká se **výhradně doložení
a long listu**, ne katalogu samotného:

```bash
just refresh     # extract → scan → longlist → sanitize → provenance → catalog → docs → build
just extract "~/Library/Application Support/Google/Chrome/Profile 1"
```

`tools/extract.py` čte `AccountBookmarks` (u přihlášeného účtu jsou záložky
tam, ne v `Bookmarks`) a kopii `History`, aby nenarazil na zámek Chromu.

## SEO a sdílení

Hlavička je kompletní: canonical, `robots`, Open Graph, Twitter card
`summary_large_image`, `theme-color` pro světlý i tmavý motiv, sada ikon,
web app manifest a strukturovaná data schema.org (`DataCatalog` + `WebSite`).
Build k tomu generuje `robots.txt`, `sitemap.xml`, `404.html` a `.nojekyll`.

Stránky zemí nesou vlastní canonical, Open Graph a `CollectionPage` s drobečky
a `ItemList`. Sitemapu proto **dopisuje až `tools/build_places.py`** — v tu
chvíli je teprve známý seznam stránek; kdyby zůstala ta z `build_page.py`,
měla by jedinou adresu a celý důvod, proč stránky zemí vznikly, by padl.

Sada `tests/meta.mjs` ověřuje každý tag i doprovodný soubor — chybějící
`og:image` se totiž jinak pozná až ve chvíli, kdy někdo odkaz nasdílí
a vypadne mu prázdná karta.

## Audit katalogu

Popisy i URL psal nejdřív jeden člověk z paměti. Katalog proto prošel
**multiagentním auditem**: sedm agentů po shlucích kategorií ověřovalo věcná
tvrzení a navrhovalo doplnění, každý shluk pak dostal skeptického oponenta
s výchozím postojem *reject* a povinností ověřit URL curlem.

Výsledek (patch-list je v [`docs/audit-patch-2026-08.json`](docs/audit-patch-2026-08.json)):
**141 → 218 položek, 44 oprav, 1 odebrání.**

Co audit našel a co by jinak zůstalo:

- **CIA World Factbook byl 4. 2. 2026 zrušen.** Odkaz vracel 200, ale mířil na
  rozlučkovou stránku bez dat — položka odstraněna, archiv v katalogu zůstává.
- Šest služeb se přestěhovalo (`developer.mapy.cz` → `.com`, `eagri.cz` →
  `mze.gov.cz`, `geoportal.cuzk.cz` → `.gov.cz`, …). Historické návštěvy pod
  starým jménem jsou pořád důkaz, že zdroj znáš, takže je drží
  `DOMAIN_ALIASES` v `tools/build_provenance.py`.
- Věcné chyby v popisech: `pgRouting` není součást PostGIS, `ESA WorldCover`
  existuje jen pro roky 2020 a 2021, `Planetary Computer` vypnul hostovaný
  JupyterHub, David Rumsey má 150 tisíc map a georeferencovaná je jen část.

Rozšíření na EU proběhlo stejnou logikou, jen bez agentů: **ověřit adresu →
napsat popis**, nikdy naopak. Ověřování cestou odhalilo, že
`www.ubo.nl` není nizozemský registr skutečných majitelů, ale strojírenská
firma pro betonárny, že INSPIRE geoportál Komise skončil a přesměrovává
na `data.europa.eu`, a že Amtsblatt zur Wiener Zeitung zanikl a nahradilo
ho `evi.gv.at`.

## Odkazy stárnou

Katalog odkazů, jehož odkazy nikdo neověřil, je pasivní lež — vypadá jako zdroj
informací a přitom část z něj nefunguje. `just links` proto projde všechny URL
a rozliší:

| Stav | Co znamená |
|---|---|
| `ok` | 2xx a cíl sedí |
| `přesměrování` | web se přestěhoval — stojí za pohled, ale často jde jen o jazykovou mutaci nebo session ID |
| `blokuje` | 403 na automat, v prohlížeči funguje (Cloudflare a spol.) |
| `certifikát` | TLS selže, přes `-k` obsah naskočí — vada webu, ne katalogu |
| `deklarováno` | zdroj má v datech `check: anti-bot`: server spojení po handshaku zahodí, přestože web žije. **Ověřuje se ručně** |
| `chyba` | opravdu nikam nevede |

Rozlišení není puntičkářství: první běh nahlásil osm chyb, ze kterých byly
**tři skutečné**. Zbytek byly bot ochrany, vypršelý certifikát a — hlavně —
selhání lokálního DNS. Checker proto překládá jména sám přes DoH, jinak by
výsledek závisel na tom, na jaké síti zrovna běží.

Rozšíření na EU do něj přidalo další tři poznatky: německé spolkové portály
odpovídají na HEAD kódem 400 a na tentýž GET vydají stránku; část portálů se
mezi `https` a `http` točí ve smyčce, kterou pět skoků neutáhne; a některé weby
spojení po TLS handshaku prostě zahodí, což od mrtvého odkazu automat nerozezná.

Kontrola není součástí `just check`, protože chodí po síti. Běží měsíčně
[vlastním workflow](.github/workflows/links.yml), který při nálezu založí issue.
Při rozpracované práci se zužuje: `just links --country AT`, `--topic companies`,
`--changed`.

## Soukromí

Datový řetěz pracuje s osobní historií prohlížení, takže je postavený tak,
aby ji nešlo zveřejnit omylem:

- `.cache/` je v `.gitignore` a **veškeré syrové výstupy končí tam** —
  `raw.json` i `longlist.raw.csv`
- do `data/longlist.csv` se dostane jen to, co projde `tools/sanitize.py`
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

## Co katalog není

Je to soupis **zdrojů a služeb**, ne databáze osob. Zdroj, který je za
přihlášením, za platbou nebo za oprávněným zájmem, se zapíše s uvedením
té překážky — neobchází se.

## Licence

Kód a nástroje: [MIT](LICENSE).

Katalog v `data/` je soupis veřejných odkazů s vlastními popisy — ber ho jako
CC0, s tím, že odkazované zdroje mají svoje vlastní licence a je potřeba se
řídit jimi.
