<!-- Pracovní dokument. Na rozdíl od CATALOG.md a COVERAGE.md se edituje ručně. -->

# Datový model

Závazná část katalogu: schéma zdroje, číselníky a pravidla klasifikace. Kdo
přidává nebo mění cokoli v `data/sources/*.json`, řídí se tímhle dokumentem.
Vynucuje ho dvojice nástrojů, obojí uvnitř `just check`: schéma a duplicity
`tools/build_catalog.py` (`just catalog`), kvalitu popisu, data ověření,
doložené absence a symetrii vazeb `tools/validate_sources.py` (`just validate`).
Pořadí je opačné, než se čeká: `validate` běží první, ale neplatné schéma
zastaví až `catalog`.

Průběh rozšíření na EU — postup po zemích, stav a zprávy — je vedle
v [`EU-EXPANSION-PLAN.md`](EU-EXPANSION-PLAN.md). Tenhle dokument je pravidlo,
ten druhý je záznam práce.

## Co se změnilo v architektuře

Původní model měl kategorie jako `3. ČR — katastr a geodata` a
`18. Polsko — katastr a geodata`. Země byla součástí kategorie, takže každá
další země znamenala tři až šest nových položek v postranním panelu.
Při 27 státech by to bylo přes sto kategorií a panel by přestal být k něčemu.

Nový model má **dvě nezávislé osy**:

| Osa | Kde je definovaná | K čemu je |
|---|---|---|
| **Téma** | [`data/topics.json`](../data/topics.json) — témata seskupená do rodin | „O jaký druh zdroje jde" — katastr, obchodní rejstřík, zakázky |
| **Země** | [`data/countries.json`](../data/countries.json) — státy a nadnárodní rozsahy | „Kde to platí" |

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

   Nepovinná — a je poctivé říct, co s nimi dnes je: `check` čte
   `tools/check_links.py` (viz níž). `native` (původní název) nese 25 záznamů,
   ale `tools/build_catalog.py` píše pevných osmnáct sloupců a `native` mezi
   nimi není — do `data/catalog.csv` ani na stránku se tedy nedostane.
   `publisher`, `formats`, `license`, `lang`, `notes` a `tags` nemá ani jeden
   záznam a nečte je nic. Jména nepovinných polí se nevalidují, takže překlep
   (`licence`, `tag`) projde a tiše zmizí.

   `check: "anti-bot"` je jediná povolená hodnota `check` a zapisuje se jen
   tehdy, když server zahodí spojení automatu, přestože web v prohlížeči žije.
   `tools/check_links.py` takový zdroj nevyhodnotí jako chybu, ale vypíše ho
   zvlášť do sekce „Declared anti-bot" **k ručnímu ověření** — jinak by
   se nepoznalo, že takový web skutečně zemřel. Nepoužívej ho na obyčejné 403;
   ty checker rozliší sám.
3. `just validate` — kvalita popisu, datum ověření, kolize adres. Schéma
   a duplicitní `id`/URL hlásí až `just catalog`.
4. `just links --changed` — ověří jen to, co jsi přidal (chodí po síti).
5. `just check` — přegeneruje katalog i dokumentaci a projde všemi kontrolami.
6. Commitni zdroj **spolu** s přegenerovaným `data/catalog.csv`,
   `docs/CATALOG.md` a `docs/COVERAGE.md`. Konec `just check` vypíše, čeho se to
   týká; CI porovnává committnutý stav s tím, co si samo vygeneruje.

`data/catalog.csv`, `docs/CATALOG.md` ani `docs/COVERAGE.md` needituj ručně —
generují se.

### Co se kontroluje

Rozdělené podle toho, co tě zastaví. **Chyba** zastaví build, **varování** ne.

| Kontrola | Kde | |
|---|---|---|
| Povinná pole, `id` a `url` unikátní v celém katalogu | `build_catalog.py` | chyba |
| `topic`, `country`, `kind`, `access`, `data`, `check` z číselníků | `build_catalog.py` | chyba |
| URL musí být absolutní (`http://` nebo `https://`) | `build_catalog.py` | chyba |
| `country` se musí rovnat názvu souboru | `build_catalog.py` | chyba |
| `desc` aspoň **40 znaků** | `validate_sources.py` | chyba |
| `desc` nesmí být prázdná fráze („oficiální web", „domovská stránka") | `validate_sources.py` | chyba |
| `verified` ve tvaru `RRRR-MM-DD` a ne z budoucnosti (den tolerance na časové pásmo) | `validate_sources.py` | chyba |
| Dvě položky na tomtéž místě — shodný host + cesta + dotaz, i když se liší schéma nebo koncové lomítko | `validate_sources.py` | chyba |
| `verified` starší dvou let | `validate_sources.py` | varování |
| `desc` končí výpustkou | `validate_sources.py` | varování |
| `data: sw` u tématu, které není nástrojové | `validate_sources.py` | varování |
| Jedna doména jako kořen **a** čtyři a víc podstránek v téže zemi | `validate_sources.py` | varování |

Nejčastější náraz je čtyřicetiznaková podlaha popisu. Není to formalita: popis
má odpovědět „proč to mám otevřít", a na to se do kratší věty vejde jen název
úřadu, který už stojí ve sloupci vedle.

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

**Licenci nehádej.** Nejde-li zjistit rychle, pole `license` prostě vynech —
v katalogu ho dnes nemá ani jeden záznam a nic ho nečte.

### Země, `EU` a `GLOBAL`

Filtr země je **přesná shoda**. Při vybraném Rakousku se celoevropské zdroje
nezobrazí; `EU` a `GLOBAL` jsou vlastní volby a v panelu stojí navrchu.

Je to vědomé rozhodnutí. Alternativa — přimíchávat celoevropské zdroje do každé
země — by znamenala, že u každého státu vidíš tytéž položky a nepoznáš, co má
ta země vlastního. Přesná shoda odpověď na otázku „co má Rakousko" nezkresluje.

TED, data.europa.eu, Eurostat ani BRIS se proto **nekopírují po zemích**.
Jsou jednou pod `EU`.

### Soubory číselníků

Tři ručně editované soubory vedle `data/sources/`. U `topics.json` a
`gaps.json` nejsou pravidla níž doporučení — `tools/validate_sources.py` je
vynucuje, takže `just validate` spadne dřív, než se z nich něco postaví.
U `countries.json` **nevynucuje nic**: chybný tvar položky se projeví až tím,
že se stránka postaví divně. Piš ho pozorně.

**[`data/topics.json`](../data/topics.json)** — `groups[]` (`id`, `label`,
`topics[]`), téma `{ "id", "label", "scope", "related" }`:

| Pole | Co znamená |
|---|---|
| `scope` | `national` = téma, které dává smysl u jednotlivého státu · `supra` = existuje jen nadnárodně. Testuje se na rovnost `supra`, takže překlep v `national` projde — piš ho přesně |
| `related` | Příbuzná témata, na která UI odkazuje křížem |

`related` je **vztah, ne odkaz**, a vynucuje se symetricky: je-li `B`
v `related` tématu `A`, musí být `A` v `related` tématu `B`. Jednosměrná vazba
by se při čtení z druhé strany tiše ztratila. Téma nesmí být příbuzné samo se
sebou a nesmí odkazovat na téma, které v souboru není.

**[`data/countries.json`](../data/countries.json)** — `scopes[]` a `countries[]`.
Stát je `{ "code", "name", "eu", "acc" }`, nadnárodní rozsah tentýž tvar
s `"scope": true` místo `eu`. `eu: true` označuje členský stát;
`acc` je 4. pád názvu pro nadpisy stránek zemí („Otevřít **Rakousko**" vedle
„Otevřít **Belgii**"). Chybí-li `acc`, použije se nominativ — neobratné, ale
nic to nerozbije. **Pořadí položek v poli je pořadí v UI.**

**[`data/gaps.json`](../data/gaps.json)** — doložené absence, položka
`{ "country", "topic", "reason" }`. Je to tvrzení „ověřili jsme, že tam nic
není", které stránka odliší šrafováním od prázdné buňky, na kterou se nikdo
nedíval. Zapisuje se jen doložená absence; nedoložená prázdná buňka je díra
a patří do ní zdroj, ne záznam sem. Validace vyžaduje, aby:

- téma i země existovaly ve svých číselnících,
- téma bylo `scope: national` — u nadnárodního tématu není prázdno absence,
- buňka **neměla** v katalogu zdroj (jinak by matice šrafovala místo, kde zdroj je),
- buňka byla v souboru jen jednou,
- `reason` byl vypsaný — validace odmítne kratší než 20 znaků. Délku pozná
  stroj, smysl ne: napiš, **proč** zdroj neexistuje, ne že neexistuje.

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

