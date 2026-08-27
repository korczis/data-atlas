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

Volá se to v `init()` přes `$nextTick`, tedy až Alpine dokreslí. Pořadí skriptů
v buildu je proto závazné: **tělo → Flowbite → Alpine**. Hlídá to
`tests/flowbite.mjs`, a to kliknutím, ne kontrolou přítomnosti atributu.

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

Sedmnáct kategorií v plochém seznamu je na 218 položek moc. Katalog má proto
dvě úrovně: **skupina → kategorie**, definované v `tools/build_catalog.py`
a nesené sloupcem `Skupina` v CSV.

| Skupina | Co v ní je |
|---|---|
| Data — svět | globální geodata, remote sensing, statistika, historické mapy |
| Data — Česko | katastr, doprava, open data, nemovitosti |
| Události a rizika | crime/IZS, OSINT, počasí |
| Nástroje | gazetteery, knihovny, spatial DB, routing, formáty |
| Učení | komunita a kurzy |

Z toho plyne zbytek:

- **CSV se zapisuje v pořadí IA**, ne podle toho, jak položky vznikaly.
  Stránka to pořadí drží ve sloupci `ord`; bez něj by se řadilo podle textu
  kategorie a `10. Spatial DB` by skončilo před `2. Globální geodata`.
- **Výsledky se člení po kategoriích** — 218 nerozlišených řádků se nedá
  procházet. Při hledání napříč katalogem je členění potřebnější než při
  procházení jedné kategorie.
- **Členění se vypne, když se řadí podle něčeho jiného než pořadí katalogu.**
  Seřadit podle návštěv a pak seskupit po kategoriích si odporuje: uživatel
  chce globální pořadí, ne nejnavštěvovanější v každé sekci. Proto je
  „Pořadí katalogu" první volbou v řazení — musí jít vrátit zpátky.
- **Sloupec Kategorie odpadá, když jsou řádky seskupené** — jinak opakuje
  hlavičku sekce na každém řádku. Hlídá to test, že hlavička a tělo tabulky
  mají stejný počet viditelných sloupců.
- **Filtr žije v URL** (`#cat=…&q=…&src=…`). Výřez katalogu se dá poslat dál.
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

- **Postranní panel** nese přepínání pohledu, filtr zdroje a všech 17 kategorií
  s počty. Pod `lg` je to Flowbite šuplík, od `lg` výš stojí napevno.
- `< md` — karty. Tabulka se šesti sloupci se na telefon nevejde a vodorovný
  scroll uvnitř řádku je horší než karta.
- `≥ md` — tabulka s řaditelnými sloupci.
- `< sm` — přepínání pohledu i spodní navigací.

Jedna past, na kterou upozornil až axe: Flowbite drží na panelu `aria-hidden`
z inicializace šuplíku **i na desktopu**, kde je panel trvale vidět. Odečítač
by ho pak přeskočil, přestože se do něj dá tabovat. Srovnává to
`syncSidebarAria()` podle breakpointu.

Obě varianty čtou týž `rows` getter. `tests/smoke.mjs` ověřuje, že karty
a tabulka vykreslí stejný počet položek — jinak by se dala jedna větev tiše
rozbít a druhá by to zakryla.
