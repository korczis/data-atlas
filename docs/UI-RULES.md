# Pravidla pro UI

Konvence pro `src/template.html`. Vynucuje je `tools/lint_ui.py` (`just lint`),
takže co je tady napsané, to CI kontroluje — pravidlo bez vynucení nikoho nezastaví.

Zdroje: [Flowbite `llms.txt`](https://raw.githubusercontent.com/themesberg/flowbite/refs/heads/main/llms.txt),
[Flowbite JavaScript](https://flowbite.com/docs/getting-started/javascript/),
[Flowbite RTL](https://flowbite.com/docs/customize/rtl/),
[Alpine.js docs](https://alpinejs.dev/).

## Flowbite × Alpine: kde to praská

Tohle je nejkřehčí místo celé stránky a stojí za to mu rozumět, než se v šabloně
začne škrtat.

Flowbite váže chování na `data-*` atributy **jediným skenem DOM**. Alpine
vykresluje obsah až po svém startu. Když se to pořadí rozejde, komponenta je
v DOM, vypadá správně a **nedělá nic** — bez chyby v konzoli.

Z toho plynou dvě pravidla:

| Pravidlo | Proč |
|---|---|
| `flowbite/init` — kdo použije Flowbite `data-*`, musí volat `initFlowbite()` | Bez toho se sken nespustí nad tím, co vykreslil Alpine |
| `flowbite/dynamic` — žádné Flowbite `data-*` uvnitř `<template x-for>` | Alpine uzly při přefiltrování zahodí; nové už žádný listener nemají a znovu-init na každý překreslení je drahý |

Pořadí skriptů v buildu je závazné: **tělo → Flowbite → Alpine**. Hlídá to
`tests/flowbite.mjs`, a to kliknutím, ne kontrolou přítomnosti atributu.

### `initFlowbite()` se volá jednou, a hned

Volalo se to původně v `$nextTick`, tedy až Alpine dokreslí seznam. Při dvou stech
položkách to bylo neviditelné; při tisícovce je to **vteřina, po kterou je šuplík
s filtry mrtvý** — na telefonu na něj klikneš a nic se nestane.

Čekat na Alpine přitom není proč: pravidlo `flowbite/dynamic` zakazuje Flowbite
`data-*` uvnitř `x-for`, takže **všechny interaktivní Flowbite komponenty jsou
ve statickém markupu** a v DOM jsou od parsování.

A zavolat to „pro jistotu" dvakrát je horší než pozdě: Flowbite navěsí posluchač
znovu, dvě instance si `toggle()` vzájemně vyruší a šuplík pak nejde zavřít
vůbec. Narazili jsme na to při pokusu nechat obě volání vedle sebe.

Praktický důsledek: interaktivní Flowbite komponenty patří do **statického**
markupu (šuplík, spodní navigace, toast). Seznam položek si řídí Alpine sám.

## Flowbite

| Pravidlo | Proč |
|---|---|
| `flowbite/rtl` — logické vlastnosti: `ms-`/`me-`/`ps-`/`pe-`/`start-`/`end-`/`text-start`/`text-end` | Flowbite 2.x je postavené na RTL režimu; `ml-`/`left-` ho rozbíjí |
| `flowbite/dark` — každá barva má `dark:` protějšek | Jinak vznikne černý text na černém pozadí; stránka jede v obou motivech |

Tmavý režim je nastavený jako `darkMode: ['variant', …]` v `src/tailwind.config.js`,
protože artefakt se vykresluje ve **třech** stavech, ne dvou: explicitní volba razí
`data-theme` na `:root`, výchozí „system" nerazí nic a rozhoduje media query.

## Alpine

### Past, která stála nejvíc času

**Alpine u výrazu, který vrátí funkci, tu funkci zavolá.** Je to záměr — aby
šlo psát `x-text="metoda"` místo `x-text="metoda()"`. Důsledek je ale ošklivý:
callback uložený v datech a použitý ve výrazu se spustí při **každém
překreslení**.

Drobečky původně nesly `action: () => { this.cat = '' }` a šablona měla
`x-show="crumb.action"`. Každý render tím mazal filtr, který uživatel právě
nastavil. Tvářilo se to jako rozbitá reaktivita: hodnota se přiřadila, po pár
milisekundách zmizela a v `$watch` dorazilo `"" → ""`.

Pravidlo: **v datech používaných ve výrazech nikdy neukládej funkce.**
Drobeček nese cíl skoku jako řetězec, kliknutí obsluhuje `goTo(crumb.to)`.
Hlídá to test *„překreslení nemění nastavený filtr"*.

| Pravidlo | Proč |
|---|---|
| `alpine/data` — komponenta registrovaná přes `Alpine.data()` v `alpine:init` | Drží logiku mimo globální jmenný prostor |
| `alpine/key` — každý `x-for` má `:key` | Duplicitní klíč neshodí jednu položku, ale **celý seznam** — narazili jsme na to s dvěma položkami na stejné URL |
| `alpine/cloak` — `x-cloak` na kořeni + CSS pravidlo | Jinak problikne nevykreslená šablona |
| `alpine/debounce` — hledání má `x-model.debounce` | Filtrování na každý stisk překresluje celý seznam |

## Přístupnost

| Pravidlo | Proč |
|---|---|
| `a11y/button-name` | Tlačítko bez textu, `x-text`, `aria-label` nebo `sr-only` je pro odečítač prázdné |
| `a11y/svg` | Dekorativní `<svg>` bez `aria-hidden="true"` se předčítá jako šum |
| `a11y/label` | Každý `input` má `<label for>` nebo `aria-label` |
| `a11y/toggle-state` | Přepínač musí hlásit stav přes `aria-pressed`/`aria-current` |

ARIA se nepoužívá na efekt: záložky **nemají** `role="tablist"`, protože
neimplementujeme obsluhu šipkami, kterou ta role slibuje. Nedodržený ARIA
kontrakt je horší než žádný.

## Informační architektura

Katalog má **dvě nezávislé osy**: *téma* (o jaký druh zdroje jde) a *země*
(kde platí). Kdyby byla země součástí kategorie — jako dřív, kdy existovaly
kategorie „ČR — katastr" a „Polsko — katastr" — znamenal by každý další stát
tři až šest nových položek v panelu a při sedmadvaceti státech by jich byly stovky.

Témata a jejich skupiny jsou v [`data/topics.json`](../data/topics.json), země
v [`data/countries.json`](../data/countries.json); pořadí klíčů v obou souborech
je pořadí v UI.

**Filtr země je přesná shoda.** Při vybraném Rakousku se celoevropské zdroje
nezobrazí; `EU` a `GLOBAL` jsou vlastní volby a v panelu stojí navrchu.
Alternativa — přimíchávat celoevropské zdroje do každé země — by znamenala,
že u každého státu vidíš tytéž položky a nepoznáš, co má ta země vlastního.

**Počty v panelu se počítají křížem:** při vybrané zemi ukazují témata počty
v té zemi, při vybraném tématu ukazují země počty v tom tématu. Absolutní součty
by u sedmadvaceti států říkaly „něco tu je" místo „tady je toho kolik". Hledání
a filtr zdroje se do počtů schválně nepromítají — poskakovaly by při každém
stisku klávesy.

**Křížení se ale nesmí promítnout do *délky* seznamů.** Původně se položky
s nulovým počtem ze seznamu vyhazovaly: po výběru tématu spadl seznam zemí
z jednatřiceti na třiadvacet a na zbylé země se nedalo přepnout — uživatel
zůstal v pasti a vypadalo to, že se z katalogu ztratila data. Nula se proto
ukáže jako nula, položka zůstane klikatelná a jen zešedne. Výjimka je textový
filtr nad zeměmi: ten seznam zúžit smí, protože o to uživatel výslovně požádal.

**Odznaky u „Všechny země" a „Všechna témata" počítají v rámci druhé osy**, ne
celý katalog — mají odpovídat tomu, co se po kliknutí skutečně stane. Se zvoleným
tématem `companies` ukáže „Všechny země" šedesát, ne tisíc.

Hlídají to testy *„výběr tématu nezkrátí seznam zemí"*, *„výběr země nezkrátí
seznam témat"* a *„odznak … počítá v rámci …"*.

**Seznam zemí má vlastní filtrovací pole.** Sedmadvacet států plus nadnárodní
rozsahy se do plochého seznamu v panelu nevejde; skládací strom je na telefonu
horší než hledání.

Z toho plyne zbytek:

- **CSV se zapisuje v pořadí IA** (skupina → téma → země), ne podle toho, jak
  položky vznikaly. Stránka to pořadí drží ve sloupci `ord`, a porovnává ho
  **číselně**: přes `String().localeCompare` by položka 100 skončila před 99
  a výchozí „Pořadí katalogu" by bylo od dvou set položek rozházené.
- **Výsledky se člení po tématech** — tisíc nerozlišených řádků se nedá
  procházet. Při hledání napříč katalogem je členění potřebnější než při
  procházení jednoho tématu; při vybrané zemi je to hlavní způsob, jak se
  v jejích zdrojích vyznat.
- **Členění se vypne, když se řadí podle něčeho jiného než pořadí katalogu.**
  Seřadit podle návštěv a pak seskupit po tématech si odporuje: uživatel
  chce globální pořadí, ne nejnavštěvovanější v každé sekci. Proto je
  „Pořadí katalogu" první volbou v řazení — musí jít vrátit zpátky.
- **Sloupec Téma odpadá, když jsou řádky seskupené** — jinak opakuje
  hlavičku sekce na každém řádku. Hlídá to test, že hlavička a tělo tabulky
  mají stejný počet viditelných sloupců.
- **Filtr žije v URL** (`#country=…&topic=…&q=…&src=…`). Výřez katalogu se dá
  poslat dál. V URL stojí **identifikátor** tématu, ne jeho popisek: popisky se
  přepisují („Katastr" → „Katastr a pozemkové knihy") a odkaz poslaný před rokem
  by po takové úpravě tiše přestal filtrovat.
  Zápis je v `try` — pod `file://` a v sandboxu `replaceState` vyhodí výjimku,
  a ta by uvnitř `$watch` shodila reaktivitu celé stránky.

## Mobile-first

| Pravidlo | Proč |
|---|---|
| `responsive/mobile-first` — žádné `max-*:` varianty | Breakpointy se skládají odspodu nahoru |
| `responsive/min-width` — `min-w-[…]` jen uvnitř `overflow-x-auto` | Jinak roztáhne celou stránku do strany |

Linter tu ale nestačí — konvence nezaručí layout. Skutečné přetečení měří
`tools/check_responsive.py` (`just responsive`): pustí stránku v headless Chrome
na šířkách 320 – 1536 px a porovná `scrollWidth` s viewportem. Stránka se vkládá
do **iframu** přesné šířky, protože Chrome na macOS neumí okno užší než ~500 px
a `--window-size=320` se tiše klampne — test by pak měřil něco jiného, než tvrdí.

Rozdělení rolí: **linter** hlídá konvence ve zdroji, **sonda** hlídá výsledek
v prohlížeči. Ani jedno nenahradí to druhé.

## Audit přístupnosti

`just a11y` pouští **axe-core** nad postavenou stránkou ve čtyřech scénářích:
mobil i desktop × světlý i tmavý motiv. Selhává od závažnosti `serious` výš.

Proč v prohlížeči a ne v jsdom: jsdom nepočítá layout ani barvy, takže pravidlo
`color-contrast` v něm skončí jako „incomplete" a projde i stránka, na které
není nic vidět. A proč oba motivy: kontrast se mezi nimi liší — první běh našel
selhání jen v tmavém režimu a jiné jen ve světlém.

Dva nálezy z prvního běhu stojí za zapamatování:

- **`aria-hidden-focus` na šuplíku.** Posunout ho mimo plátno přes
  `translate-x-full` nestačí — obsah zůstane fokusovatelný a odečítač do něj
  vleze. Řeší to `#filters[aria-hidden="true"] { visibility: hidden }`,
  navázané na atribut, který razí Flowbite.
- **Kontrast těsně pod hranicí.** `gray-500` na `gray-100` dává 4,4:1 při
  požadovaných 4,5:1. Okem nerozeznatelné, měřením ano.

## Rozvržení

Aplikační shell podle Flowbite Pro Admin Dashboardu (viz [`NOTICE.md`](../NOTICE.md)):
horní lišta, postranní panel, hlavní obsah, lepivá souhrnná lišta.

- **Postranní panel** nese přepínání pohledu, filtr zdroje, seznam zemí
  s vlastním hledáním a témata seskupená po rodinách, obojí s počty.
  Pod `lg` je to Flowbite šuplík, od `lg` výš stojí napevno.
- `< md` — karty. Tabulka se šesti sloupci se na telefon nevejde a vodorovný
  scroll uvnitř řádku je horší než karta.
- `≥ md` — tabulka s řaditelnými sloupci.
- `< sm` — přepínání pohledu i spodní navigací.
- **Země, strojová dostupnost a překážka v přístupu jsou odznaky, ne sloupce.**
  Tabulka už má šest sloupců a tři další by ji na tabletu rozbily; odznaky
  se vejdou do buňky s názvem a popisem.

Jedna past, na kterou upozornil až axe: Flowbite drží na panelu `aria-hidden`
z inicializace šuplíku **i na desktopu**, kde je panel trvale vidět. Odečítač
by ho pak přeskočil, přestože se do něj dá tabovat. Srovnává to
`syncSidebarAria()` podle breakpointu.

### Vykresluje se jen ta větev, která je vidět

Karty a tabulka čtou týž `rows` getter, ale v DOM je vždycky jen jedna z nich:
`<template x-if="mobile">` kolem karet, `x-if="!mobile"` kolem tabulky.
Příznak nastavuje `matchMedia` na breakpointu **md (768 px)** — musí odpovídat
třídám `md:hidden` / `hidden md:block` v markupu, jinak by vznikla šířka,
na které není vidět ani jedna větev. Ty třídy proto zůstávají jako pojistka.

Důvod je měřený: držet v DOM obě větve stálo u tisícovky položek zhruba
**vteřinu navíc** (961 ms → 240 ms po změně, medián pěti běhů headless Chrome)
a dvojnásobek uzlů, z toho polovinu neviditelných.

`tests/smoke.mjs` proto větev přepne, změří ji zvlášť a ověří, že obě vykreslí
stejný počet položek — jinak by se dala jedna tiše rozbít a druhá by to zakryla.
Stub `matchMedia` v `tests/helpers.mjs` vyhodnocuje `min-width` proti šířce
1024 px; konstantní `matches: false` by znamenalo „nejužší telefon" a testy
by tabulku nikdy neviděly.
