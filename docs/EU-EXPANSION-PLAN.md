<!-- Pracovní dokument. Na rozdíl od CATALOG.md a COVERAGE.md se edituje ručně. -->

# Rozšíření na EU

Katalog vznikl jako soupis GIS a geodatových zdrojů s těžištěm v Česku a Polsku.
Cílem téhle práce je z něj udělat atlas **veřejných datových zdrojů všech
27 členských států** — geodata a katastr, otevřená data a statistika, obchodní
rejstříky, skuteční majitelé, insolvence, soudy, zakázky, regulace a rizikové
a OSINT zdroje.

Zůstává to katalog **zdrojů a služeb**. Není a nebude to databáze osob.

## Co se změnilo v architektuře

Původní model měl kategorie jako `3. ČR — katastr a geodata` a
`18. Polsko — katastr a geodata`. Země byla součástí kategorie, takže každá
další země znamenala tři až šest nových položek v postranním panelu.
Při 27 státech by to bylo přes sto kategorií a panel by přestal být k něčemu.

Nový model má **dvě nezávislé osy**:

| Osa | Kde je definovaná | K čemu je |
|---|---|---|
| **Téma** | [`data/topics.json`](../data/topics.json) — 33 témat v 6 skupinách | „O jaký druh zdroje jde" — katastr, obchodní rejstřík, zakázky |
| **Země** | [`data/countries.json`](../data/countries.json) — 27 států + `EU` a `GLOBAL` | „Kde to platí" |

Rejstřík firem je `companies` bez ohledu na to, jestli je český nebo maltský.
Malta je `MT` bez ohledu na to, jestli jde o katastr nebo o soudy.

Druhá změna je **reprodukovatelnost**. Kurátorovaný katalog byl dřív zapsaný
jako pythonní seznam uvnitř `tools/build_catalog.py`, který si hned při importu
načítal `.cache/raw.json` — osobní export Chromu. Na čistém klonu tedy nešlo
katalog přegenerovat vůbec. Dneska:

```
data/sources/<KÓD>.json  ─┐
data/topics.json          ├─→ tools/build_catalog.py ─→ data/catalog.csv ─→ stránka + docs
data/countries.json       │
data/provenance.csv      ─┘
                            tools/build_provenance.py ←─ .cache/raw.json   (jen lokálně)
```

Doložení z prohlížeče se počítá odděleně a committuje jako `data/provenance.csv`.
Neobsahuje nic, co by nebylo už dnes v `data/catalog.csv`. Že veřejný řetěz na
osobní data nesahá, hlídá `tools/validate_sources.py`.

## Jak přidat zdroj

1. Najdi soubor země: `data/sources/AT.json`. Neexistuje-li, založ ho polem `[]`
   a přidej zemi do `data/countries.json`, pokud tam ještě není.
2. Přidej objekt. Povinná pole:

   ```json
   {
     "id": "at-firmenbuch",
     "country": "AT",
     "topic": "companies",
     "name": "Firmenbuch",
     "url": "https://...",
     "desc": "Popis česky — odpovídá na otázku „proč to mám otevřít\"",
     "kind": "official",
     "access": "paid",
     "data": "search",
     "verified": "2026-08-28"
   }
   ```

   Nepovinná: `native` (původní název), `publisher`, `formats`, `license`,
   `lang`, `notes`, `tags`.
3. `just validate` — schéma, duplicity, kvalita popisu.
4. `just links --changed` — ověří jen to, co jsi přidal.
5. `just catalog docs build` a nakonec `just check`.

`data/catalog.csv`, `docs/CATALOG.md` ani `docs/COVERAGE.md` needituj —
generují se.

### Číselníky

`kind` — kdo to vydává:

| | |
|---|---|
| `official` | ústřední úřad, ministerstvo, soud, regulátor |
| `regional` | kraj, spolková země, region, město |
| `intl` | EU, OSN, mezivládní organizace |
| `research` | univerzita, výzkumný ústav |
| `ngo` | nezisková organizace, novinařina, open-source projekt |
| `commercial` | firma |

`access` — jak se dovnitř:

| | |
|---|---|
| `open` | volně, bez účtu |
| `registration` | vyžaduje účet, ale je zdarma |
| `paid` | zpoplatněno |
| `mixed` | část zdarma, část placená |
| `restricted` | omezeno na oprávněný zájem nebo na úřady |
| `unknown` | nezjištěno |

`data` — nejsilnější strojová dostupnost:

| | |
|---|---|
| `bulk` | celé datové sady ke stažení |
| `api` | programové rozhraní |
| `ogc` | mapové služby (WMS/WFS/WMTS/ATOM) |
| `download` | jednotlivé soubory |
| `search` | jen dotaz v prohlížeči |
| `sw` | nástroj nebo knihovna, ne datová sada |
| `none` | portál nebo dokument bez dat |
| `unknown` | nezjištěno |

**Veřejné vyhledávání není otevřená datová sada.** Rejstřík, ve kterém si
kdokoli najde firmu, je `access: open, data: search` — ne `bulk`. Rozdíl je
podstatný přesně u těch zdrojů, kvůli kterým katalog vzniká. Osy se nesmí
míchat: `access` říká, **jestli se dovnitř dostaneš**, `data` říká,
**co si odneseš**.

**Licenci nehádej.** Nejde-li zjistit rychle, nech `unknown`.

### Země, `EU` a `GLOBAL`

Filtr země je **přesná shoda**. Při vybraném Rakousku se celoevropské zdroje
nezobrazí; `EU` a `GLOBAL` jsou vlastní volby a v panelu stojí navrchu.

Je to vědomé rozhodnutí. Alternativa — přimíchávat celoevropské zdroje do každé
země — by znamenala, že u každého státu vidíš tytéž položky a nepoznáš, co má
ta země vlastního. Přesná shoda odpověď na otázku „co má Rakousko" nezkresluje.

TED, data.europa.eu, Eurostat ani BRIS se proto **nekopírují po zemích**.
Jsou jednou pod `EU`.

## Postup

Pro každou zemi:

```
BASELINE → REŠERŠE (i v místním jazyce) → TRIÁŽ → ZÁPIS → OVĚŘENÍ ODKAZŮ
        → BUILD + TESTY → REPORT → REVIZE PLÁNU → další země
```

Země je hotová, když je pro každou z těchto rodin buď zdroj v katalogu, nebo
poznámka, proč tam žádný není:

geoportál · katastr · adresy a územní členění · ortofoto/výškopis · životní
prostředí a rizika · doprava · statistika · otevřená data · sbírka zákonů
a věstník · veřejné zakázky · rozpočty a dotace · obchodní rejstřík · skuteční
majitelé · účetní závěrky · insolvence · soudy · finanční regulátor · CERT.

„Neexistuje", „je decentralizované", „je zpoplatněné" nebo „je jen pro oprávněný
zájem" jsou platné výsledky rešerše. Slabá náhražka jen proto, aby políčko
nebylo prázdné, není.

## Zvláštní pravidla

**Skuteční majitelé.** Po rozsudku Soudního dvora ve spojených věcech
C-37/20 a C-601/20 (22. 11. 2022) většina států veřejný přístup k registrům
skutečných majitelů zavřela; nový balíček AML (nařízení 2024/1624 a směrnice
2024/1640) ho vrací osobám s oprávněným zájmem s transpozicí do 10. 7. 2027.
Stav se tedy stát od státu liší a starší články lžou. **U každé země se ověřuje
znovu**, na stránce samotného registru.

**Katastr ≠ pozemková kniha ≠ ceny nemovitostí.** Geometrie parcel, popisná
data, vlastnická práva, zástavy, adresní registr, územní plán a databáze
realizovaných cen jsou různé věci a v různých státech je vede někdo jiný.
Mapa parcel bývá otevřená i tam, kde je vlastník neveřejný.

**Zakázka ≠ smlouva.** Portál s vyhlášeními neobsahuje plnění. Hledá se
zvlášť oznámení, zvlášť výsledek, zvlášť registr smluv nebo výdajů.

**Federace.** U Německa, Belgie, Rakouska, Španělska a Itálie se nejdřív hledá
národní federující katalog nebo harmonizované rozhraní; regionální zdroje se
přidávají, až když národní vrstva neexistuje. Šestnáct skoro stejných odkazů
na spolkové země katalog zhorší.

**Území mimo pevninu.** Grónsko, Faerské ostrovy, francouzská zámoří,
nizozemské Karibiky, autonomní oblasti Portugalska a Španělska mají jiný
právní i datový režim. Popisuje se jen to, co zdroj sám o svém pokrytí tvrdí.

## Co se nedělá

Obcházení autentizace, CAPTCHA, paywallů a rate limitů. Únikové databáze,
credential dumpy, doxxing. Hromadný sběr osobních údajů. Zdroj, který je za
přihlášením nebo za platbou, se **zkataloguje s uvedením překážky** — neobchází se.

## Stav

Legenda: ☐ nezačato · ◐ rozpracováno · ☑ hotovo · ⊘ blokováno

### Základ

- ☑ T00 Audit repozitáře
- ☑ T01 Baseline a regresní metriky (252 položek, 52 doložených — beze ztráty)
- ☑ T02 Datový model: `data/sources/*.json`, reprodukovatelný build
- ☑ T03 Taxonomie: 33 témat × země jako nezávislé osy
- ☑ T04 UI: filtr země, filtr tématu, křížové počty, stav v URL
- ☑ T05 Validace a cílená kontrola odkazů (`just validate`, `just links --country`)

### Země

- ☑ EU — celoevropské zdroje
- ☑ CZ · ☑ PL (audit a doplnění po zavedení nového modelu)
- ☑ AT · ☑ SK · ☑ DE · ☑ BE · ☑ NL · ☑ FR · ☑ ES · ☑ PT · ☑ IT · ☑ SI
- ☑ HR · ☑ HU · ☑ RO · ☑ BG · ☑ GR · ☑ CY · ☑ MT · ☑ IE · ☑ DK · ☑ SE
- ☑ FI · ☑ EE · ☑ LV · ☑ LT · ☑ LU

### Závěr

- ☑ Druhý průchod: doplnění systematických děr podle `docs/COVERAGE.md`
- ☑ Konsolidace duplicit napříč zeměmi
- ☑ Audit popisů a klasifikace přístupu
- ☑ Přeověření tvrzení o skutečných majitelích
- ☑ Úplná kontrola odkazů
- ☑ Regrese UI, dokumentace, závěrečná zpráva

## Reporty po zemích

Průběžně sem přibývají krátké zprávy: co přibylo, co se opravilo, co se nenašlo
a proč, a co z toho plyne pro další země.

---

### EU — celoevropské zdroje · HOTOVO

- Zdrojů před: 10 · přidáno: 44 · upraveno: 6 · zamítnuto jako duplicita: 0
- Úředních a mezivládních: 44 · komerčních: 0
- S API nebo hromadnými daty: 30
- Kromě toho do `GLOBAL` přibyly GLEIF, OpenCorporates a Espacenet, do `GB` Companies House —
  jsou to nadnárodní nebo mimoevropské zdroje, které pod `EU` nepatří.

**Pokryté rodiny:** otevřená data, statistika (Eurostat, ECB, agri), právo (EUR-Lex, N-Lex),
zakázky (TED + API, Funding & Tenders), veřejné peníze (FTS, Kohesio, CohesionData, CORDIS),
firmy (BRIS, VIES, e-Justice rozcestník, EUIPO), regulace (EBA, ESMA, EIOPA, ECB, ETS, RASFF),
soudy (InfoCuria), transparentnost (rejstřík lobbistů, EP, Rada), sankce, kyber (CERT-EU, EUVD,
CSIRTs Network), doprava (ENTSO-E, ERADIS), prostředí a rizika (EEA, EFFIS, EFAS, EDO, EGMS,
Copernicus Marine, průmyslové emise, ESDAC).

**Zjištěná omezení přístupu**

- **INSPIRE geoportál skončil.** `inspire-geoportal.ec.europa.eu` vrací trvalé přesměrování
  na `data.europa.eu`; samostatný evropský INSPIRE katalog už neexistuje a geoprostorové
  vyhledávání je součástí hlavního portálu. Položka `eu-eu-data-portal` to říká.
- **Sankční seznam ve strojovém tvaru je za tokenem.** Služba FSF
  (`webgate.ec.europa.eu/fsd/fsf`) vrací automatu 401 a token vydává Komise na žádost.
  V katalogu proto stojí rozcestník Komise s `access: restricted` a odkaz na OpenSanctions,
  které týž seznam vydávají volně.
- **EFAS, ESDAC, Copernicus Marine a ENTSO-E vyžadují účet** (zdarma), mapová aplikace
  bývá veřejná. Klasifikováno jako `registration`.
- **Anti-bot ochranu** mají `data.europa.eu`, `kohesio.ec.europa.eu`, `curia.europa.eu`,
  `euipo.europa.eu` a `worldwide.espacenet.com` — v prohlížeči fungují. Popisy to zmiňují
  tam, kde by to člověk mohl považovat za nefunkční odkaz.

**Zamítnuto:** samostatné položky pro insolvenční a pozemkové rejstříky na e-Justice
(jsou pod jedním rozcestníkem), Copernicus jako celek (rozcestník nad službami, které
už v katalogu jsou), ACER a Eurojust (bez datové hodnoty pro tenhle katalog).

**Kontroly:** `just validate` (0 chyb), `just links --country EU` — 52 ok, 2 přesměrování,
0 chyb. **Výsledek: PASS.**

**Revize plánu**

1. Model dvou os drží. Čtyřicet čtyři zdrojů se rozprostřelo do 17 témat, aniž by bylo
   potřeba zavádět nové.
2. Přibyla potřeba, kterou původní plán neměl: **rozlišit token od registrace**. Enum
   `access` to zvládá (`restricted` × `registration`), ale u zemí bude potřeba to psát
   důsledně, ne od oka.
3. Tři témata zůstala po EU průchodu prázdná napříč katalogem: `filings`, `courts` je
   jen s jednou položkou a `gazette` má dvě. Jsou to přesně ta, kde nese obsah národní
   úroveň — v CZ a PL průchodu se musí doplnit.
4. `validate_sources.py` dostalo přesnější pravidlo na rozcestník rozepsaný na podstránky;
   původní počítalo položky na doménu a u `ec.europa.eu` hlásilo planý poplach.

---

### CZ — Česko · HOTOVO

- Zdrojů před: 66 · přidáno: 28 · upraveno: 3 · zamítnuto jako duplicita: 1
- Úředních a regionálních: 23 · komerčních: 1 · nezisk/výzkum: 4
- S API nebo hromadnými daty: 12

**Doplněné rodiny** (před průchodem prázdné): legislativa a věstníky (e-Sbírka, Zákony pro lidi,
Sbírka právních předpisů ÚSC), soudy (NS, NSS, NALUS, InfoSoud), účetní závěrky (Sbírka listin),
regulace (ČNB JERRS, ERÚ, ČTÚ, SÚKL, ÚOHS), kyberbezpečnost (NÚKIB, CSIRT.CZ),
transparentnost (Volby.cz, ÚDHPSH), veřejné peníze (data MF, DotaceEU, CityVizor, NKÚ),
zakázky (Věstník veřejných zakázek), exekuce (CEE).

**Zjištěná omezení přístupu**

- **Evidence skutečných majitelů je od 17. 12. 2025 neveřejná.** Ministerstvo spravedlnosti
  zrušilo částečný výpis dostupný bez přihlášení; dnes se dostane k údajům jen evidující osoba
  přes datovou schránku, orgány veřejné moci a povinné osoby podle AML zákona na žádost.
  Položka je překlasifikovaná na `access: restricted` a popis to říká i s datem.
- **Centrální evidence exekucí je zpoplatněná** za každý dotaz — a insolvenční rejstřík
  exekuce nezachytí, takže se u prověrky dělá obojí.
- **Sbírka listin je zdarma, ale neúplná** — část firem zákonnou povinnost zakládat účetní
  závěrky neplní. Popis to uvádí, aby se z prázdné sbírky nedělal závěr o neexistenci firmy.

**Opravené a zastaralé odkazy**

- Systematický přesun české státní správy na `*.gov.cz`: `vdp.cuzk.cz` → `vdp.cuzk.gov.cz`
  (opraveno), a mimo katalog se týkal i `ctu.cz`, `volby.cz`, `mzp.cz`, `uzsvm.cz`, `upv.cz`,
  `policie.cz`, `e-sbirka.cz` a `hzscr.cz` — nové položky rovnou míří na cílové adresy.
- `cedr.mfcr.cz` (Centrální evidence dotací) **neodpovídá**; data jsou dnes na
  `data.mf.gov.cz`. Do katalogu šel funkční nástupce.
- Věstník veřejných zakázek se přestěhoval na `vvz.nipez.cz`.
- ČTÚ: adresa konkrétní evidence se mění s ročníkem všeobecného oprávnění, proto míří
  položka na rozcestník `ctu.gov.cz/databaze`, který přežije.

**Nenalezeno / vynecháno:** ISOH (informační systém odpadového hospodářství) vrací 503;
statistické ročenky HZS jsou jen v archivní části webu bez stabilní adresy.

**Kontroly:** `just validate` (0 chyb), `just links --country CZ` — 77 ok, 15 přesměrování,
1 vadný certifikát (HZS Vysočina, vada webu), 0 chyb. **Výsledek: PASS.**

**Revize plánu**

1. Většina přesměrování jsou vstupní cesty aplikace (`or.justice.cz/` → `/ias/ui/rejstrik`),
   ne stěhování. Prohlubovat je nemá smysl a u položek s doložením z prohlížeče by to navíc
   utnulo vazbu na `data/provenance.csv`. Pravidlo pro další země: **opravovat jen skutečné
   přesuny domény**, ne vstupní přesměrování aplikace.
2. Kontrolní seznam rodin z plánu se osvědčil — bez něj by chyběly soudy a věstníky, tedy
   přesně to, co původní geodatový katalog neměl.
3. Doména typu `*.gov.xx` se v členských státech mění hromadně (ČR přešla na `gov.cz`).
   U dalších zemí je proto lepší ověřovat kandidáty dřív, než se sepíší popisy.

---

### PL — Polsko · HOTOVO

- Zdrojů před: 34 · přidáno: 24 · odebráno: 1 · upraveno: 1
- Úředních: 21 · komerčních: 1 · nezisk: 0
- S API nebo hromadnými daty: 8

**Doplněné rodiny:** legislativa (Dziennik Ustaw, Monitor Polski, ISAP), soudy (obecné soudy,
SN, NSA/CBOSA, Ústavní tribunál), účetní závěrky (Repozytorium Dokumentów Finansowych, MSiG,
iMSiG), regulace (KNF, UOKiK, URE, UKE), kyberbezpečnost (CERT Polska, CSIRT GOV),
bezpečnost (statistiky policie, RCB), transparentnost (PKW, wybory.gov.pl),
veřejné peníze (Mapa Dotacji UE, Rejestr Umów), zakázky (UZP).

**Odebráno:** `pl-geoportal-prehled-datovych-sad` — rozcestník na datové sady geoportálu,
který jen opakuje to, co katalog nese po jednotlivých registrech (PRNG, RCN, wykaz usług).
Upozornil na něj `just validate`.

**Zjištěná omezení přístupu**

- **CBOSA (`orzeczenia.nsa.gov.pl`) neodpovídá mimo prohlížeč.** TLS spojení naváže s platným
  certifikátem, HTTP požadavek pak nezodpoví — a to ani přes syrový `openssl s_client`.
  Databáze zjevně žije, ověřit ji odsud nešlo, takže položka míří na web soudu, který do ní
  vede, a popis to říká. **Vymyslet URL, kterou nejde ověřit, není možnost.**
- **CRBR (skuteční majitelé) zůstává veřejný a bezplatný** — Polsko je v tomhle výjimka;
  výpis se dostane podle NIP bez přihlášení. Ověřeno na registru samotném.
- **Repozytorium Dokumentów Finansowych je zdarma** a účetní závěrky vydává bez registrace,
  na rozdíl od části členských států, kde jsou listiny zpoplatněné.

**Kontroly:** `just validate` (0 chyb, 0 varování), `just links --country PL` — 55 ok,
1 přesměrování, 1 blokuje (rejestr.io, anti-bot), 0 chyb. **Výsledek: PASS.**

---

## Revize po kalibraci na CZ a PL

Dvě země, které katalog znal nejlépe, prošly novým modelem bez potřeby měnit taxonomii —
33 témat pokrylo všechno, co se našlo, a všech 33 je teď obsazených. Z kalibrace plyne
pro zbývajících 25 států tohle:

1. **Pořadí práce je ověřit → napsat, ne napsat → ověřit.** U ČR se ukázalo, že celá státní
   správa přešla na `*.gov.cz`; u Polska že se e-KRS složil do `prs.ms.gov.pl`. Kdyby se
   popisy psaly z paměti a ověřovaly až potom, přepisovala by se polovina.
2. **Kontrolní seznam rodin je nosný.** Bez něj by CZ i PL zůstaly bez soudů, věstníků,
   účetních závěrek a regulátorů — tedy bez poloviny toho, kvůli čemu se katalog rozšiřuje.
3. **Rozlišovat přesměrování aplikace od stěhování.** Opravovat se má jen druhé; první je
   kosmetika a u položek s doložením z prohlížeče by prohloubení URL zbytečně utnulo vazbu
   na `data/provenance.csv`.
4. **Skuteční majitelé se stát od státu liší radikálně** — Česko registr v prosinci 2025
   zavřelo, Polsko ho má dál veřejný a zdarma. Potvrzuje to, že se to musí ověřovat
   u každé země zvlášť, na registru samotném.
5. **Nedostupný zdroj se nepíše.** CBOSA se ověřit nedalo, takže položka míří na ověřitelný
   vstup a popis stav pojmenovává. Totéž pravidlo platí pro zbytek průchodu.
6. `validate_sources.py` dostalo mírnější práh na „rozcestník rozepsaný na podstránky"
   (kořen + 4 podstránky místo 3): národní geoportál běžně nese tři různé registry
   a hlásit to jako podezření by bylo planým poplachem.

---

### AT — Rakousko · HOTOVO

- Zdrojů před: 0 · přidáno: 32 · úředních 28, komerční 1 (ANKÖ), neziskové 3
- S API nebo hromadnými daty: 9

**Pokryté rodiny:** katastr (BEV) i pozemková kniha (Grundbuch) zvlášť, geoportál a INSPIRE
katalog, geologie, hydrologie, prostředí, doprava (NAP + ASFINAG), otevřená data, statistika,
právo (RIS, EVI), firmy (Firmenbuch, WKO), skuteční majitelé, insolvence, dražby nemovitostí,
soudy (OGH, VwGH, VfGH), regulace (FMA, OeNB), veřejné peníze, transparentnost (parlament,
lobbistický registr), kyber, kriminalita, zakázky.

**Zjištěná omezení přístupu**

- **WiEReG je od listopadu 2022 neveřejný** — po rozsudku Soudního dvora zůstal přístup jen
  povinným osobám podle AML a žadatelům s doloženým oprávněným zájmem, za poplatek.
  Od 10. 7. 2027 ho nahrazuje WiEReG 2027.
- **Firmenbuch i Grundbuch jsou zpoplatněné za dotaz.** Rakousko nemá bezplatnou obdobu ARESu;
  jako bezplatná první kontrola slouží databáze členů Hospodářské komory (členství je povinné).
- **Rakousko nemá bezplatný státní věstník zakázek.** Podlimitní zakázky se soustřeďují na
  komerční platformě ANKÖ / Auftrag.at; nadlimitní jsou v TED.
- **`ris.bka.gv.at` odmítá automatické klienty (503).** Položka proto míří na oficiální
  otevřené API `data.bka.gv.at/ris/api/v2.6/` nad týmiž daty. `www.fma.gv.at` a `www.bev.gv.at`
  vracejí 403, v prohlížeči fungují.

**Zaniklé zdroje, které se nabízely**

- **Amtsblatt zur Wiener Zeitung skončil** (tištěné vydání zrušeno v roce 2023); úřední
  vyhlášky převzala platforma **EVI** (`evi.gv.at`). `wienerzeitung.at/amtsblatt/` vrací 410.
- **Geologische Bundesanstalt se v roce 2023 sloučila do GeoSphere Austria**; `geologie.ac.at`
  neodpovídá, geologické mapy jsou na `gis.geosphere.at`. Totéž platí pro ZAMG → GeoSphere.

**Federální struktura:** devět zemských geoportálů se do katalogu nepřidávalo. Rakousko má
národní federující katalog `geometadatensuche.inspire.gv.at`, přes který jsou zemské vrstvy
dosažitelné — regionální duplikáty by katalog jen nafoukly.

**Kontroly:** `just links --country AT` — 29 ok, 2 přesměrování (vstupní cesty aplikace),
1 blokuje (FMA), 0 chyb. **Výsledek: PASS.**

---

### SK — Slovensko · HOTOVO

- Zdrojů před: 0 · přidáno: 30 · úředních 27, komerční 1 (FinStat), neziskové 2
- S API nebo hromadnými daty: 12

**Pokryté rodiny:** katastr (ZBGIS, ESKN), geoportál (GKÚ), geologie, počasí a hydrologie,
prostředí a EIA, doprava, otevřená data, statistika (DATAcube), právo (Slov-Lex), věstník,
firmy (ORSR, RPO), účetní závěrky, skuteční majitelé (RPVS), insolvence, soudy, regulace (NBS),
zakázky (ÚVO, CRZ), veřejné peníze, kyber, volby.

**Zjištěná omezení a zvláštnosti**

- **Slovensko je v katastru otevřenější než sousedé.** ZBGIS ukazuje vlastníka parcely zdarma
  a bez přihlášení; v Rakousku i Německu je to placené nebo vázané na oprávněný zájem.
- **RPVS není obecný registr skutečných majitelů.** Veřejný a bezplatný je jen u partnerů
  veřejného sektora — tedy u těch, kdo berou peníze od státu. Obecná evidence konečných
  užívateľov výhod v obchodním rejstříku veřejná není. Popis to rozlišuje.
- **Register účtovných závierok vydává výkazy zdarma a strukturovaně**, včetně hromadného
  výdeje — to je proti většině členských států nadstandard.
- `registeruz.sk` a `finstat.sk` vracejí automatu 403, v prohlížeči fungují.

**Opravené odkazy:** `geoportal.sk` dnes vede na `gku.sk` (a varianta s `www` má vadný
certifikát), `upv.gov.sk` neodpovídá a úřad má doménu `indprop.gov.sk`, `data.gov.sk`
přesměrovává na `data.slovensko.sk`.

**Vylepšení kontroly odkazů:** `data.slovensko.sk` se na HEAD točí ve smyčce mezi `https`
a `http` a checker ho hlásil jako mrtvý. Přidalo se proto opakování GETem i po vyčerpání
skoků v přesměrování a limit skoků se zvedl z pěti na deset — prohlížeč jich povoluje dvacet.
Oprava zároveň uklidila dvě planá přesměrování v `EU`.

**Kontroly:** `just links --country SK` — 28 ok, 0 přesměrování, 2 blokují, 0 chyb.
**Výsledek: PASS.**

---

### DE — Německo · HOTOVO

- Zdrojů před: 0 · přidáno: 39 · úředních 38, neziskový 1 (openJur)
- S API nebo hromadnými daty: 17

**Federální struktura — jak se řešila.** Německo nemá celostátní katastr ani celostátní
sbírku zemského práva; obojí vedou spolkové země. Šestnáct skoro stejných zemských odkazů
by katalog nafouklo, aniž by odpovědělo na otázku „kde to najdu". Do katalogu proto šla
**národní federující vrstva**: `Geoportal.de` (vyhledávání napříč zeměmi včetně katastrálních
služeb ALKIS), **AdV** (kdo katastr v které zemi vede a podle jakého datového modelu)
a **BORIS-D** (celoněmecká mapa směrných hodnot pozemků). Zemské zdroje nepřibyly žádné;
decentralizace je pojmenovaná v popisech, ne zamlčená.

**Zjištěná omezení přístupu**

- **Transparenzregister je od listopadu 2022 neveřejný.** Nahlédnutí je podmíněné doloženým
  oprávněným zájmem, podává se žádost přes web registru a je zpoplatněné — prostý výpis
  1,65 €, ověřený 20,80 €; veřejnost navíc dostává jen omezený rozsah údajů.
- **Wettbewerbsregister je zavřený úplně.** Dotaz na registr firem vyloučených ze zakázek
  smí podat jen zadavatel; pro prověrku dodavatele je nepoužitelný a katalog to říká.
- **Handelsregister je naopak od srpna 2022 zdarma**, včetně stahování listin — dřív se
  platilo za každý výpis. To je proti Rakousku zásadní rozdíl.
- **Insolvenzbekanntmachungen mají krátkou retenci** — zveřejnění mizí šest měsíců
  po skončení řízení, takže starší úpadky se nedohledají.
- **Účetní závěrky jsou v Bundesanzeigeru, ne v Unternehmensregisteru.** Ten je jen jednotným
  vstupem a často se za samostatný rejstřík zaměňuje; popisy to rozlišují.

**Nedostupné:** `www.bgr.bund.de` a `evergabe-online.de` vyžadují cookie kontrolu a automatu
neodpovídají — u BGR proto katalog míří na `geoviewer.bgr.de` a `produktcenter.bgr.de`,
u zakázek na centrální `oeffentlichevergabe.de`, který má navíc otevřené API.
`subventionsdatenbank.de` a `basisregister.adv-online.de` neodpovídají vůbec.

**Vylepšení kontroly odkazů:** německé spolkové portály (`bkg.bund.de`, `bafin.de`,
`bsi.bund.de`, `zensus2022.de`) odpovídají na HEAD kódem 400 a na tentýž GET vydají stránku.
Checker proto opakuje GETem i po 400 — bez toho by hlásil sedm mrtvých odkazů, které
v prohlížeči fungují.

**Kontroly:** `just links --country DE` — 37 ok, 2 přesměrování (vstupní cesty aplikace),
0 chyb. **Výsledek: PASS.**

---

### BE — Belgie · HOTOVO

- Zdrojů před: 0 · přidáno: 28 · federálních 20, regionálních 4, komerční 1
- S API nebo hromadnými daty: 10

**Federální × regionální rozdělení — jak se řešilo.** Belgie je jediný stát, kde regionální
zdroje **musely** do katalogu: geodata vedou Flandry, Valonsko a Brusel odděleně, v odlišných
datových modelech, a společná belgická vrstva pro ně neexistuje. Federální `geo.be` je katalog
metadat nad nimi, ne datový zdroj. Přidaly se proto všechny tři regionální geoportály
(Geopunt, Géoportail de la Wallonie, BruGIS) a katalog to v popisech pojmenovává.
Federální zůstává katastrální plán (CadGIS pod finanční správou), registr podniků,
věstník, justice a dohled.

**Zjištěná omezení přístupu**

- **UBO-register je od listopadu 2022 zavřený veřejnosti** po rozsudku Soudního dvora;
  vidí do něj povinné osoby podle AML a žadatelé s oprávněným zájmem.
- **CadGIS ukazuje parcely zdarma, ale vlastníka ani katastrální příjem ne** — ty vidí
  jen přihlášený vlastník přes MyMinfin.
- **Belgie nemá samostatný veřejný insolvenční rejstřík.** Úpadky se vyhlašují v Moniteur
  belge; spisový systém RegSol je pro věřitele a správce, ne pro veřejnost.
- **Statutární orgány a stanovy nejsou v registru podniků, ale ve věstníku.** KBO/BCE nese
  identifikaci, sídlo a NACE činnosti; kdo firmu zastupuje, se hledá v Moniteur belge.
  To je proti českému nebo slovenskému rejstříku podstatný rozdíl a popisy to říkají.
- **Účetní závěrky jsou naopak nadstandard** — centrála Národní banky vydává výkazy prakticky
  všech belgických společností strukturovaně a zdarma.
- `ccb.belgium.be` a `stat.policefederale.be` vracejí automatu 403, v prohlížeči fungují;
  `bnb.be` má vadný certifikát, funkční doména je `nbb.be`.

**Kontroly:** `just links --country BE` — 25 ok, 1 přesměrování, 2 blokují, 0 chyb.
**Výsledek: PASS.**

---

### NL — Nizozemsko · HOTOVO

- Zdrojů před: 0 · přidáno: 29 · všechny úřední · s API nebo hromadnými daty: 18

**Základní registry se nesloučily do jedné položky.** Nizozemsko má oddělené základní
registrace a katalog je drží zvlášť, protože se liší přístupem i obsahem: **PDOK** rozdává
geometrii zdarma, **BAG Viewer** ukazuje rok výstavby, plochu a účel užívání každé budovy,
ale **BRK** (vlastnická práva) je u Kadasteru zpoplatněné za dotaz. Sloučit je do „Kadaster"
by zamlčelo právě ten rozdíl, na kterém při prověrce záleží.

**Zjištěná omezení přístupu**

- **UBO-register je od listopadu 2022 pozastavený** a znovu neotevřený; vidí do něj orgány,
  FIU a povinné instituce podle zákona Wwft.
- **KVK Handelsregister je hybrid:** vyhledání firmy zdarma, výpis, orgány a dokumenty
  zpoplatněné, API placené. Není to obdoba německého Handelsregisteru, který je od roku
  2022 zdarma — popis to rozlišuje.
- **Insolventieregister maže záznamy šest měsíců po skončení řízení**, stejně jako německý.
- `knmi.nl`, `dnb.nl` a `politie.nl` vracejí automatu 403; u všech tří míří katalog
  na datovou variantu (`dataplatform.knmi.nl`, `dnb.nl/en/`, `data.politie.nl`).

**Zamítnutý kandidát:** `www.ubo.nl` **není** nizozemský registr skutečných majitelů, ale
soukromá strojírenská firma pro betonárny. Ověření odhalilo doménu, která by se podle názvu
do katalogu dostala jako oficiální registr. Doklad k pravidlu „URL ověřuj, nevymýšlej".

**Kontroly:** `just links --country NL` — 26 ok, 2 přesměrování, 1 blokuje, 0 chyb.
**Výsledek: PASS.**

---

### FR — Francie · HOTOVO

- Zdrojů před: 0 · přidáno: 35 · úředních 34, komerční 1 (Pappers)
- S API nebo hromadnými daty: 22 — nejvyšší podíl ze všech dosud zpracovaných států

**Co Francii odlišuje.** Tři věci, které jinde v EU veřejné nejsou:

- **DVF — realizované ceny nemovitostních transakcí.** Každý prodej za posledních pět let
  s cenou, plochou a parcelou, na mapě i ke stažení. Většina států má jen nabídkové ceny
  nebo znalecké směrné hodnoty.
- **HATVP — majetková a zájmová přiznání politiků** plus registr lobbistů s klienty
  a rozpočty, jako otevřená data.
- **Otevřený IGN.** Od roku 2021 vydává národní zeměměřický institut prakticky všechna data
  pod otevřenou licencí — BD TOPO, ortofota, výškopis.

**Zjištěná omezení přístupu**

- **Vlastníci parcel veřejní nejsou.** Katastrální geometrie je otevřená a hromadně ke stažení,
  ale vlastníka vede daňová správa a ukáže ho jen samotnému vlastníkovi. Ceny transakcí
  jsou přitom veřejné — rozdíl, který stojí za zapamatování.
- **Francie nemá samostatný insolvenční rejstřík.** Úpadky a likvidace se vyhlašují v BODACC,
  který je ale jako otevřená data ke stažení.
- **RNE u INPI vyžaduje bezplatnou registraci** pro hromadné stahování; část firem si smí
  účetní závěrku utajit.
- Anti-bot ochranu (403) mají `legifrance.gouv.fr`, `data.inpi.fr`, `infogreffe.fr`,
  `pappers.fr` a `interieur.gouv.fr` — v prohlížeči fungují.

**Přesměrování:** deset odkazů končí na jazykové cestě (`/fr`) nebo vstupní stránce aplikace.
Podle pravidla z kalibrace se neopravují — nejde o stěhování.

**Kontroly:** `just links --country FR` — 20 ok, 10 přesměrování, 5 blokuje, 0 chyb.
**Výsledek: PASS.**

---

### ES — Španělsko · HOTOVO

- Zdrojů před: 0 · přidáno: 27 · všechny úřední · s API nebo hromadnými daty: 15

**Decentralizace:** geodata drží z velké části autonomní společenství. Do katalogu šla
národní federující vrstva **IDEE** a národní produkce **IGN/CNIG**; regionální geoportály
se nepřidávaly. Baskicko a Navarra vedou **vlastní katastr** mimo státní Catastro —
popis to říká, aby se z prázdného výsledku nedělal závěr o neexistenci parcely.

**Zjištěná omezení přístupu**

- **Obchodní i nemovitostní rejstřík jsou zpoplatněné za výpis** (Registradores, Registro
  Mercantil). Bezplatná obdoba francouzského Annuaire des Entreprises ve Španělsku není.
  Bezplatnou cestou ke změnám ve firmě je **BORME** — obchodní věstník, který vychází denně
  a je i strojově čitelný.
- **Catastro dává nemovitostní údaje zdarma, ale ne jméno vlastníka** — to je chráněný údaj
  vydávaný při doloženém oprávněném zájmu.
- **Španělsko nemá bezplatný insolvenční rejstřík.** Úpadky se vyhlašují v BOE; Registro
  Público Concursal má omezený rozsah.
- **BDNS je naopak nadstandard** — každá vyplacená veřejná podpora s příjemcem a částkou,
  ze všech úrovní správy, ke stažení.
- `contrataciondelestado.es` má vadný řetěz certifikátů (vada webu, obsah dostupný);
  `tribunalconstitucional.es`, `interior.gob.es` a `ccn-cert.cni.es` vracejí automatu 403.

**Kontroly:** `just links --country ES` — 19 ok, 4 přesměrování, 3 blokují, 1 certifikát,
0 chyb. **Výsledek: PASS.**

---

### PT — Portugalsko · HOTOVO

- Zdrojů před: 0 · přidáno: 28, z toho 1 zase odebrán · úředních 26, neziskový 1 (PORDATA)
- S API nebo hromadnými daty: 11

**Zvláštnost, kterou má jen Portugalsko: chybějící katastr.** Na severu a ve vnitrozemí
hranice pozemků nikdy zaměřeny nebyly a plošný katastr neexistuje. Program **BUPi** je
dobrovolná evidence, kterou to má postupně napravit. Do katalogu šel právě proto — vysvětluje,
proč portugalské parcely v mapě chybí, což by jinak vypadalo jako vada zdroje.

**Zjištěná omezení přístupu**

- **Výpisy z obchodního i nemovitostního rejstříku (IRN) jsou zpoplatněné**; bezplatné
  vyhledávání firem Portugalsko nemá. Bezplatnou cestou ke změnám ve firmě jsou
  **Publicações do Ministério da Justiça**, kde vycházejí i insolvenční oznámení.
- **RCBE (skuteční majitelé) byl po rozsudku Soudního dvora omezen** na orgány, povinné
  osoby a oprávněný zájem.
- **BASE je nadstandard** — nese uzavřené smlouvy včetně hodnoty, ne jen vyhlášení,
  protože zveřejnění je podmínkou účinnosti smlouvy.
- `bportugal.pt`, `snirh.apambiente.pt` a `parlamento.pt` vracejí automatu 403,
  v prohlížeči fungují.

**Odebráno po ověření:** **CNCS** (národní centrum kybernetické bezpečnosti) odmítá
automatické klienty smyčkou 307 na všech testovaných adresách — ověřit se nedal, takže
v katalogu nezůstal. Kyberbezpečnost za Portugalsko pokrývá **CERT.PT**, který funguje.

**Kontroly:** `just links --country PT` — 17 ok, 7 přesměrování, 1 blokuje, 0 chyb.
**Výsledek: PASS.**

---

### IT — Itálie · HOTOVO

- Zdrojů před: 0 · přidáno: 31 · úředních 30, komerční 1 (Terna)
- S API nebo hromadnými daty: 15

**Decentralizace:** geodata drží z velké části regiony. Do katalogu šla národní federující
vrstva (`geodati.gov.it` / RNDT) a celostátní produkce (geoportál MASE, katastrální mapa
daňové správy, IGM); regionální geoportály se nepřidávaly. **Autonomní provincie Trento
a Bolzano vedou vlastní katastr** mimo státní — popis to říká.

**Zjištěná omezení přístupu**

- **Registro Imprese je placené za každý dokument.** Základní vyhledání je zdarma, výpis
  i účetní závěrka nikoli; objednává se přes Telemaco na předplacený účet. Bezplatná cesta
  k italským firemním výkazům neexistuje — proti Německu (Bundesanzeiger zdarma) nebo
  Belgii (centrála NBB zdarma) je to zásadní rozdíl.
- **Katastrální mapa je veřejná a má WMS, vlastníci jsou placení.** Zdarma jsou naopak
  **statistiky trhu OMI** se čtvrtletními cenami za m² po zónách.
- **Dati ANAC jsou nadstandard** — každá zakázka s identifikátorem CIG, vítězem, hodnotou
  a plněním, hromadně ke stažení. Co do granularity nejúplnější databáze zakázek v EU.
- `consob.it` a `cortecostituzionale.it` mají bot management (Radware), automatické klienty
  občas odmítnou. `soldipubblici.gov.it` je v době ověřování v údržbě — do katalogu nešel.

**Kontroly:** `just links --country IT` — 24 ok, 7 přesměrování, 0 chyb. **Výsledek: PASS.**

---

### SI — Slovinsko · HOTOVO

- Zdrojů před: 0 · přidáno: 21 · všechny úřední · s API nebo hromadnými daty: 8

**Erar je unikát.** Sleduje **každou transakci slovinského veřejného sektoru** — kdo komu
kdy kolik zaplatil, od ministerstev po obce, dohledatelné z obou stran a propojené
s obchodním rejstříkem. Provozuje ho protikorupční komise. Obdobu tomu nemá žádný
jiný členský stát; nejblíž je český Registr smluv, ten ale nese smlouvy, ne platby.

**AJPES sdružuje to, co jinde leží u pěti institucí** — obchodní rejstřík, účetní závěrky
zdarma, insolvence, registr transakčních účtů a statistiky na jednom místě.

**Nedostupné / omezené:** `si-cert.si` (národní CERT) neodpovídá automatickým klientům
ani po opakovaném ověření — do katalogu nešel a kyberbezpečnost tak u Slovinska zůstává
nepokrytá; k doplnění v druhém průchodu. `us-rs.si`, `a-tvp.si` a `volitve.dvk-rs.si`
vracejí 403, v prohlížeči fungují.

**Kontroly:** součástí běhu `just links --country SI --country HR` — 0 chyb. **PASS.**

---

### HR — Chorvatsko · HOTOVO

- Zdrojů před: 0 · přidáno: 18 · úředních 17, komerční 1 (Zakon.hr)
- S API nebo hromadnými daty: 6

**Chorvatsko je v korporátních datech otevřenější, než se čeká.** Soudní rejstřík vydává
**strukturovaná data přes otevřené API zdarma** — to v EU umí málokterý rejstřík. Účetní
závěrky u FINA jsou rovněž bezplatné a databáze je díky povinnosti odevzdávat výkazy úplná.
A **výpis z pozemkové knihy s vlastníky a břemeny je online a zdarma** (OSS), zatímco
v Rakousku, Itálii nebo Španělsku se za totéž platí.

**Zvláštnost:** katastr a pozemková kniha jsou v Chorvatsku **dva oddělené systémy**
(geodetická správa × soudy), které program Uređena zemlja propojuje. Popisy to rozlišují.

**Nedostupné:** `dhmz.hr` neodpovídá, funkční doména meteorologického ústavu je `meteo.hr`;
`sudovi.pravosudje.hr` neodpovídá, judikatura obecných soudů se tak u Chorvatska nedoplnila —
k dořešení v druhém průchodu.

**Kontroly:** 30 ok, 7 přesměrování, 2 blokují, 0 chyb (společný běh SI+HR). **PASS.**

---

### HU — Maďarsko · HOTOVO (s doloženými dírami)

- Zdrojů před: 0 · přidáno: 24 · všechny úřední · s API nebo hromadnými daty: 4

**E-beszámoló je nejcennější maďarský zdroj** — účetní závěrky všech firem zdarma, včetně
příloh a auditorských zpráv, s povinným ukládáním, takže je databáze prakticky úplná.
Naopak **pozemková kniha i úplný výpis z obchodního rejstříku jsou zpoplatněné**; bezplatný
veřejný náhled na vlastníka nemovitosti Maďarsko nemá.

**Nedostupné z našeho ověřování** (spojení odmítnuto i přes nezávislý fetch, nejspíš filtrace
mimo Maďarsko): `njt.hu` (Nemzeti Jogszabálytár — konsolidované právo), `data.gov.hu`,
`map.gov.hu`, `mbfsz.gov.hu` (geologická služba). Do katalogu nešly. Náhradou:
legislativu pokrývá **Magyar Közlöny** (věstník, funguje), katalog dat **Közadatkereső**.
**Geologie u Maďarska zůstává nepokrytá** — k dořešení v druhém průchodu.

`e-epites.hu` má vadný řetěz certifikátů (vada webu, obsah dostupný).

**Kontroly:** společný běh HU+RO — 0 chyb. **Výsledek: PASS.**

---

### RO — Rumunsko · HOTOVO (s doloženými dírami)

- Zdrojů před: 0 · přidáno: 20 · všechny úřední · s API nebo hromadnými daty: 6

**Dvě bezplatné náhrady za placený rejstřík.** ONRC (obchodní rejstřík) je zpoplatněný
a jeho portál mimo Rumunsko neodpovídá. Zdarma jsou ale **ANAF** (ověření plátce DPH
podle CUI přes veřejné API) a **Ministerul Finanțelor** (databáze účetních výkazů firem
podle CUI: obrat, zisk, zaměstnanci). Kombinace obojího nahradí základní prověrku
rumunské protistrany bez placení.

**Portal.just.ro je nadstandard** — stav řízení, termíny a účastníci podle jména strany
u všech soudů zdarma; takový rozsah dohledatelnosti má v EU málokdo.

**Nedostupné z našeho ověřování:** `geoportal.ancpi.ro`, `legislatie.just.ro`,
`portal.onrc.ro`, `insse.ro` (503), `anpm.ro`, `ccr.ro` (503), `scj.ro`, `cert.ro`.
Náhradou: statistiku pokrývá **TEMPO Online** (funguje, ale jen přes HTTP na portu 8077 —
popis to říká), legislativu **Monitorul Oficial**, kyberbezpečnost **DNSC** (nástupce CERT-RO).
**Ústavní a Nejvyšší kasační soud u Rumunska nepokryty** — k dořešení v druhém průchodu.

**Kontroly:** 32 ok, 10 přesměrování, 1 blokuje, 1 certifikát, 0 chyb. **Výsledek: PARTIAL** —
země je zpracovaná, ale se dvěma doloženými dírami.

---

### BG — Bulharsko · HOTOVO

- Zdrojů před: 0 · přidáno: 23 · úředních 22, komerční 1 (Lex.bg)
- S API nebo hromadnými daty: 5

**Bulharský obchodní rejstřík patří k nejotevřenějším v EU** — společnosti, orgány, společníci
**i uložené listiny včetně účetních závěrek jsou zdarma, bez registrace, a má API**.
Zatímco v Rakousku, Itálii, Maďarsku nebo Řecku se za výpis platí.

**Zvláštnost:** katastrální mapa (АГКК) a **vlastnická práva (imotenský registr u Registrové
agentury) jsou dva oddělené systémy**; výpisy z druhého jsou zpoplatněné. Popisy to rozlišují.

**Nedostupné:** `legalacts.justice.bg` (databáze právních aktů justice) vrací chybovou stránku;
legislativu pokrývá **Държавен вестник** a komerční **Lex.bg**. Anti-bot 403 mají
`data.egov.bg`, `lex.bg` a `cik.bg` — v prohlížeči fungují.

**Kontroly:** společný běh BG+GR — 0 chyb. **Výsledek: PASS.**

---

### GR — Řecko · HOTOVO

- Zdrojů před: 0 · přidáno: 16 · všechny úřední · s API nebo hromadnými daty: 3

**Διαύγεια (Diavgeia) je právně nejsilnější transparenční nástroj v EU:** každé rozhodnutí
řecké veřejné správy s výdajovým dopadem — jmenování, zakázka, dotace, platba — **musí být
zveřejněno, jinak není platné**. A má otevřené API. Žádný jiný členský stát nespojuje
zveřejnění s platností aktu takto plošně.

**Zvláštnost:** Řecko dokončovalo **první plošný katastr** teprve v posledních letech;
do té doby fungovaly hypotéční knihy (υποθηκοφυλακεία). Popis to říká, aby se z chybějící
parcely nedělal závěr o vadě zdroje.

**Nedostupné z našeho ověřování:** `geodata.gov.gr` (národní geoportál otevřených geodat)
a `hcmc.gr` (Komise pro kapitálový trh) neodpovídají. **Geoportál a dohled nad kapitálovým
trhem u Řecka nepokryty** — k dořešení v druhém průchodu; kapitálový trh částečně pokrývá
evropský registr ESMA.

**Anti-bot 403** má většina řeckých vládních domén (`gov.gr`, `ktimatologio.gr`,
`bankofgreece.gr`, `hellenicparliament.gr`, `astynomia.gr`, `gsis.gr`) — v prohlížeči fungují,
popisy to u každé uvádějí.

**Kontroly:** 25 ok, 5 přesměrování, 9 blokuje, 0 chyb. **Výsledek: PARTIAL** — dvě doložené díry.

---

### CY — Kypr · HOTOVO

- Zdrojů před: 0 · přidáno: 13 · úředních 12, neziskový 1 (CyLaw) · s API/bulk: 1

**Územní upřesnění je v popisech závazné.** Katastr i statistika Kyperské republiky
popisují **jen území pod její kontrolou**; na severu ostrova se acquis neuplatňuje.
Popisy to říkají, aby se z chybějícího záznamu nedělal závěr o neexistenci nemovitosti.

**Kypr je v korporátních datech otevřenější, než napovídá pověst:** obchodní rejstřík
DRCOR vydává **akcionáře zdarma ve výpisu**. Registr skutečných majitelů je naopak
po rozsudku Soudního dvora uzavřený.

**Nedostupné:** `dls.moi.gov.cy` (funkční je `portal.dls.moi.gov.cy`),
`digitalsecurityauthority.cy` — **kyberbezpečnost u Kypru nepokryta**, k dořešení
v druhém průchodu.

**Kontroly:** společný běh CY+MT+IE — 0 chyb. **Výsledek: PARTIAL** (jedna doložená díra).

---

### MT — Malta · HOTOVO

- Zdrojů před: 0 · přidáno: 12 · všechny úřední · s API/bulk: 1

**Malta nemá plošný katastr** srovnatelný s kontinentálními — evidence pozemkových práv
stojí na registraci listin, ne parcel. Praktickou náhradou pro otázku „co se na pozemku smí"
je mapová aplikace **Planning Authority** se stavebními povoleními a územními plány.

**MFSA je pro prověrky zásadní** — Malta hostí velké množství přeshraničně působících
fondů a poskytovatelů služeb a jednotný registr je veřejný.

**Nedostupné:** `geoportal.mt` (národní geoportál), `met.gov.mt` (meteorologická služba),
`csirt.gov.mt`. **Geoportál, počasí a kyberbezpečnost u Malty nepokryty** — k dořešení
v druhém průchodu. Většina maltských vládních domén má anti-bot 403.

**Výsledek: PARTIAL** (tři doložené díry).

---

### IE — Irsko · HOTOVO

- Zdrojů před: 0 · přidáno: 16 · všechny úřední · s API nebo hromadnými daty: 7

**Property Price Register je spolu s francouzským DVF jediný svého druhu v EU** —
realizované ceny **všech** prodejů rezidenčních nemovitostí od roku 2010 s adresou
a datem, ke stažení jako CSV.

**Lobbying.ie hlásí konkrétní kontakty**, ne jen roční rozpočet jako většina evropských
registrů: kdo koho lobboval, u koho a v jaké věci, čtvrtletně a ke stažení.

**Zjištěná omezení přístupu**

- **RBO je od listopadu 2022 zavřený**, omezení promítnuto do irského práva v červnu 2023.
  Automaticky se přihlásí jen irské povinné osoby; ostatní musí prokázat, že vyšetřují
  praní peněz nebo financování terorismu.
- **CRO vydává dokumenty a účetní závěrky za poplatek** (jednotky eur za dokument).
- **Irsko nemá samostatný insolvenční rejstřík** — agenda je u soudní služby a ISI.
- **Eircode (adresní kódy) jsou licencované** mimo otevřená data GeoHive.

**Výsledek: PASS.**

---

### DK — Dánsko · HOTOVO

- Zdrojů před: 0 · přidáno: 21 · úředních 20, neziskový 1 (Opendata.dk)
- S API nebo hromadnými daty: 14

**CVR je nejotevřenější firemní registr v EU** — společnosti, vedení, **skuteční majitelé,
historie změn i účetní závěrky zdarma, bez registrace a s hromadným výdejem**. Dánsko je
jediný členský stát, kde jsou skuteční majitelé i po rozsudku Soudního dvora nadále
plošně veřejní jako součást firemního registru.

**BBR** dává ke každé budově rok výstavby, plochu, materiál a vytápění veřejně a zdarma;
**OIS** to spojuje s katastrem, oceněním a realizovanými cenami na jednu adresu.

**Územní upřesnění:** Grónsko a Faerské ostrovy **nejsou součástí EU** a mají vlastní
správu i datové systémy. Dánské zdroje v katalogu se týkají vlastního Dánska; do katalogu
se grónské ani faerské registry nepřidávaly, protože by pod kódem `DK` tvrdily nepravdu
o rozsahu.

**Nedostupné:** `politi.dk` (statistiky kriminality) — **kriminalita u Dánska nepokryta**,
k dořešení v druhém průchodu. `cfcs.dk` se přestěhoval na `samsik.dk`.

**Výsledek: PARTIAL** (jedna doložená díra).

---

### SE — Švédsko · HOTOVO

- Zdrojů před: 0 · přidáno: 18 · úředních 17, neziskový 1 (Lagen.nu)
- S API nebo hromadnými daty: 9

**Otevřenost švédské správy neznamená otevřená data.** Zásada veřejnosti dokumentů
(offentlighetsprincipen) dává právo na přístup ke spisu **na žádost**, ale online se
plošně nezveřejňuje — soudní rozhodnutí ani rejstříkové listiny. Bolagsverket vydává
výpisy a dokumenty **za poplatek**, přestože jsou základní údaje zdarma. Popisy to
rozlišují, aby se z „nejotevřenější správy v Evropě" nevyvozovalo víc, než platí.

**Co je naopak výborné:** **Brå** (kriminální statistika s dlouhými řadami a API),
**Finansinspektionen** (registr licencí ke stažení **plus veřejný registr insider
transakcí** v kótovaných společnostech) a **SMHI** (otevřené API bez klíče).

**Švédsko nemá jeden státní věstník zakázek** — vyhlášení běží přes komerční databáze,
nadlimitní přes TED.

**Nevyřešeno:** `bolagsverket.se` při závěrečném ověřování neodpovědělo, přestože při
průzkumu vracelo 200 — prověří se v úplném auditu odkazů.

**Výsledek: PASS.**

---

### FI — Finsko · HOTOVO

- Zdrojů před: 0 · přidáno: 13 · všechny úřední · s API nebo hromadnými daty: 8

**Finsko otevřelo geodata už v roce 2012** a meteorologická data patří k nejlépe
zpřístupněným v Evropě (WFS/OGC, bez klíče). **YTJ** dává identifikaci, obor a daňovou
registraci všech finských firem zdarma a s API.

**Ale:** **výpisy z pozemkové knihy s vlastníkem a účetní závěrky jsou zpoplatněné**
(Virre, za dokument). Bezplatná cesta k finským firemním výkazům neexistuje.

`finlex.fi` a `oikeus.fi` vracejí automatu 403, v prohlížeči fungují.

**Výsledek: PASS.**

---

## Druhý průchod: systematické díry

Po prvním průchodu všemi 27 státy ukázala matice v `docs/COVERAGE.md` díry, které
nebyly vidět zemi po zemi, protože se opakovaly napříč. Druhý průchod je zavřel:

| Rodina | Chybělo u | Doplněno |
|---|---|---|
| Doprava | 17 států | Národní přístupové body k dopravním datům podle nařízení 2017/1926 plus silniční správy |
| Skuteční majitelé | 16 států | Registry s **ověřeným aktuálním stavem přístupu** u každého zvlášť |
| Insolvence | 19 států | Registry, kde existují; kde ne, je to pojmenované u věstníku nebo rejstříku |
| Veřejné peníze | 13 států | Rozpočtové a dotační portály, státní pokladny |
| Účetní závěrky | 10 států | Výdejní kanály včetně toho, kolik stojí |
| Prostředí, počasí, kyber, bezpečnost, soudy | 4–10 států každá | Národní agentury a CERTy |

### Co druhý průchod zjistil o skutečných majitelích

Rozsudek Soudního dvora z 22. 11. 2022 (spojené věci C-37/20 a C-601/20 —
**lucemburský případ**) zavřel plošný veřejný přístup ve většině států.
Ověřením k srpnu 2026 vyšlo:

- **Veřejné a bezplatné zůstaly tři členské státy: Estonsko, Lotyšsko a Polsko.**
  Lotyšsko údaje vydává dokonce jako otevřená data.
- **Dánsko** zavedlo řízení o oprávněném zájmu, které vyřizuje zhruba do dvanácti dnů —
  proti ostatním rychle a s jasnými pravidly.
- **Bulharsko** má údaje formálně ve veřejném rejstříku, ale přístup vyžaduje bulharskou
  elektronickou identitu, což ho pro zahraniční žadatele prakticky uzavírá.
- **Česko zavřelo registr až 17. 12. 2025**, tedy tři roky po rozsudku.
- **Itálie** registr spustila v roce 2023 a od té doby se o něj vedou správní spory;
  popis to říká a doporučuje ověřit stav před použitím.
- **Slovensko** má zvláštní režim: veřejný a bezplatný je jen **RPVS** u partnerů
  veřejného sektora, obecná evidence veřejná není.

Kdyby se tahle tvrzení opsala ze starších článků, byla by polovina z nich chybná.

### Konsolidace duplicit

- **e-Certis** byl zapsaný pod `IT`, přestože je to celoevropský nástroj — přesunut pod `EU`.
- **LVĢMC** mělo dvě položky na tomtéž webu s prakticky stejným popisem — rozděleno
  na environmentální a meteorologickou sekci.
- **Tribunal Constitucional** figuroval dvakrát pod stejným názvem (PT, ES) — názvy
  doplněny o zemi, aby se v seznamu nepletly.
- Enum `access` obsahoval hodnotu `search`, která říkala totéž co `data: search`.
  Odstraněna: `access` odpovídá na „dostanu se dovnitř", `data` na „co si odnesu",
  a míchat je znamená lhát právě u registrů, kvůli kterým katalog vzniká.

---

## Výkon při tisícovce položek

Katalog vyrostl z 252 na 1014 položek, tedy čtyřnásobek. Měření v headless Chrome
(medián pěti běhů, srovnání téže stránky s plným katalogem a s deseti položkami):

| | cena za ~1000 řádků |
|---|---|
| před úpravou | **961 ms** |
| po úpravě | **240 ms** |

Dvě změny, obě vyvolané měřením, ne odhadem:

1. **Vykresluje se jen viditelná větev seznamu.** Karty (`< md`) a tabulka (`≥ md`)
   byly v DOM obě naráz, přestože je vidět vždycky jen jedna. `x-if` řízený
   `matchMedia` na breakpointu md to půlí.
2. **`initFlowbite()` se volá hned, ne v `$nextTick`.** Předtím byl šuplík s filtry
   mrtvý po celou dobu, než Alpine dokreslil seznam — při tisícovce položek přes
   vteřinu. Na to přišel test, který při 1014 položkách začal padat; při 252
   to bylo pod rozlišovací schopnost.

Stránka má 637 kB (z toho 447 kB data) a zůstává jednosouborová, bez síťových
požadavků a bez serveru.

---

## Zbývající známá omezení

Tohle **nejsou** nápady na budoucí práci, ale místa, kde katalog vědomě nemá pokrytí
a je to doložené:

| Co | Kde | Proč |
|---|---|---|
| Geoportál | GR, MT, RO | `geodata.gov.gr` a `geoportal.mt` neodpovídají, `geoportal.ancpi.ro` **neexistuje ani v DNS** |
| Kyberbezpečnost | CY, GR, MT | `digitalsecurityauthority.cy`, `ncsa.gov.gr` a `csirt.gov.mt` neodpovídají |
| Judikatura správních soudů | RO | `orzeczenia`-obdoba `scj.ro` a `ccr.ro` neodpovídají (503) |
| Geologie | HU | `mbfsz.gov.hu` neodpovídá; agenda přešla pod dozorový úřad bez veřejného portálu |
| Insolvenční rejstřík | GR, MT, RO, SI | Samostatný veřejný rejstřík neexistuje — úpadky jsou ve věstníku nebo v obchodním rejstříku, což popisy říkají |
| Výškopis jako samostatná položka | 16 států | Není to samostatná služba: u většiny států je výškopis součástí geoportálu nebo katastru, které v katalogu jsou. Kde má vlastní produktovou stránku (NL, ES, FR, IT, SI, SE, FI, DK, LV, HR, CZ), je v katalogu zvlášť |
| Ceny nemovitostních transakcí | 17 států | Veřejně neexistují. Plošně je mají jen **FR** (DVF), **IE** (Property Price Register), **DK** (OIS) a částečně **PL** (RCN) a **IT** (OMI, jen agregovaně po zónách) |

Kromě toho: **CBOSA** (polská judikatura správních soudů), **Bolagsverket** (švédský
rejstřík) a **CNCS** (portugalská kyberbezpečnost) odmítají automatické klienty tak,
že se od mrtvého odkazu nedají odlišit měřením. CBOSA a CNCS proto v katalogu
nejsou pod vlastní adresou; Bolagsverket ano, ale s deklarací `check: anti-bot`,
protože při první rešerši prokazatelně odpovídal.


---

## Doplnění adresních registrů (CY, GR, HU, MT, RO)

Adresy se ukázaly jako nejslabší místo katalogu — původně šest zemí ze sedmadvaceti,
protože jsem si do plánu napsal, že „adresy jsou u většiny států součástí geoportálu".
Nebyla to pravda. Po dvou průchodech je to **27 z 27**, poslední pětice si vyžádala
rešerši zvlášť, protože žádná z nich nemá adresní registr tam, kde by ho člověk čekal:

| Stát | Co se našlo | Jak to je |
|---|---|---|
| **CY** | DLS e-Services / INSPIRE prohlížečka | Kypr celostátní adresní registr nemá; podle metadat úřadu **adresní data pokrývají asi 4 % území** |
| **GR** | data.gov.gr — data Hellenic Cadastre | Řecko jednotný registr nemá, pojmenování ulic je v gesci obcí; ulice a čísla vycházejí tak, jak je nahlásili vlastníci při zakládání katastru |
| **HU** | Helységnévtár (KSH) | Územní číselník obcí a jejich částí. Adresy na úrovni ulic vede **KCR, což je úřední evidence bez veřejného vyhledávání** |
| **MT** | MaltaPost Postcode Finder | Státní adresní registr Malta nemá; vyhledávač PSČ je de facto referenční zdroj |
| **RO** | SIRUTA (otevřená data) | Územní číselník krajů, obcí a vesnic. **RENNS existuje na papíře, ale jeho ohlašovaná adresa `renns.ancpi.ro` neexistuje ani v DNS** |

**Dvě pasti, které ověřování odhalilo.** `kcr.hu` vypadá jako maďarský Központi
Címregiszter, ale je to certifikát mediální firmy Lapcom Zrt. — druhý případ po
`www.ubo.nl` (nizozemská „registr skutečných majitelů" = strojírna pro betonárny),
kdy by se podle názvu domény do katalogu dostalo něco úplně jiného.
A `renns.ancpi.ro`, `geoportal.ancpi.ro` i `ran.mai.gov.ro` vracejí **NXDOMAIN** —
nejde o filtrování ze zahraničí, ty hostitele prostě nikdo neprovozuje, přestože
je odborné články i obecní weby dál uvádějí.
