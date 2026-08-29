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

### Tailwind ořízne to, co Flowbite přidává za běhu

Flowbite si část tříd nevkládá do markupu, ale **přidává je z JavaScriptu**:
backdrop šuplíku vzniká za běhu s `bg-gray-900/50 dark:bg-gray-900/80 fixed
inset-0 z-30`, přepnutí polohy razí `transform-none` a `-translate-x-full`.
Tailwind skenuje zdroj, tyhle třídy v něm nevidí a ořízne je.

Výsledek je zákeřný, protože **v DOM všechno vypadá správně**: backdrop se
vytvoří, má správný `class`, jen bez `inset-0` má nulový rozměr. Šuplík se pak
otevře bez ztmavení a ťuknutí vedle něj ho nezavře — posluchač na něm visí, ale
nulová plocha žádné ťuknutí nezachytí. Kontrola „backdrop existuje" projde.

Drží je proto `safelist` v [`src/tailwind.config.js`](../src/tailwind.config.js)
a hlídá `tools/check_runtime_classes.py` (`just lint`). Ten si třídy **vytáhne
přímo z balíčku** — z voleb `*Classes`, z literálů v `classList.add/remove`
a z tabulky poloh šuplíku — a porovná je se třemi seznamy:

| Seznam | Význam |
|---|---|
| `NEEDED` | musí mít v CSS pravidlo, jinak komponenta tiše nefunguje |
| `UNSTYLED_BY_DESIGN` | pravidlo mít **nesmí**, s uvedeným důvodem |
| zbytek | polohy šuplíku, které markup nepoužívá — safelist by je tahal zbytečně |

Ta prostřední kategorie je tam schválně. Flowbite přidává šuplíku fyzické
`left-0`; panel si polohu řeší logickým `start-0` (pravidlo `flowbite/rtl`),
takže v LTR by `left-0` jen zdvojilo totéž a v RTL by táhlo panel na špatnou
stranu. Bez té kategorie by brána nutila safelistovat všechno, co knihovna
razí, a tichá mezera by se změnila v tiché pravidlo navíc.

Když upgrade Flowbite některou třídu přejmenuje nebo přidá novou, seznam se
rozejde s balíčkem a brána si vyžádá rozhodnutí. Bez toho by se safelist
s knihovnou tiše rozešel.

Jak se to našlo: v šabloně byl `#sidebarBackdrop`, kus opsaného aplikačního
shellu, který sám nic nedělal (`display: none`) a Flowbite ho nepoužíval.
Jenže **fungoval jako nechtěný safelist** — držel `inset-0` a `bg-gray-900/50`
naživu. Když jsem ho uklidil jako mrtvý kód, backdrop přestal existovat.
Odsud pravidlo: třídu, kterou razí knihovna za běhu, drží safelist, ne náhodný
kus markupu.

### Vrstvení šuplíku

`hlavička z-50 > panel z-40 > backdrop Flowbite z-30 > obsah`.

Backdrop má `z-30` natvrdo v knihovně a připojuje se na konec `<body>`. Kdyby
měl panel taky `z-30`, prohraje pořadím v DOM: menu se otevře **pod** ztmavením
a každé ťuknutí do něj spadne na backdrop, jehož obsluha šuplík zavře. Na
telefonu to vypadá přesně tak, že boční menu nefunguje. `z-40` na panelu je
i vzor z [Flowbite drawer navigation](https://flowbite.com/docs/components/drawer/).

Obě vady spolu souvisí a jedna maskovala druhou: dokud byl backdrop nulový,
neměl se s panelem o co přetahovat, takže kolize `z-30` nebyla vidět. Proto
`check_responsive.py` pod 1024 px měří obojí — že je panel po otevření
klikatelný, že backdrop **kryje celou plochu**, leží nad obsahem vedle šuplíku,
a že ťuknutí do něj šuplík zavře. Ověřeno vrácením každé vady zvlášť.


| Pravidlo | Proč |
|---|---|
| `flowbite/rtl` — logické vlastnosti: `ms-`/`me-`/`ps-`/`pe-`/`start-`/`end-`/`text-start`/`text-end` | Flowbite 2.x je postavené na RTL režimu; `ml-`/`left-` ho rozbíjí |
| `flowbite/dark` — každá barva má `dark:` protějšek | Jinak vznikne černý text na černém pozadí; stránka jede v obou motivech |

Tmavý režim je nastavený jako `darkMode: ['variant', …]` v `src/tailwind.config.js`,
protože artefakt se vykresluje ve **třech** stavech, ne dvou: explicitní volba razí
`data-theme` na `:root`, výchozí „system" nerazí nic a rozhoduje media query.

### Přepínač motivu má tři stavy

Flowbite ve svých dokumentech přepíná třídu `.dark` mezi dvěma stavy. Tady to
nejde: „podle systému" je **volba, ne absence volby**, a stránka se v ní chová
jinak než v obou explicitních — proto `data-theme` a cyklus
světlý → tmavý → podle systému. Návrat na systém musí atribut **odstranit**,
ne nastavit na prázdno, jinak přestane platit media query.

Volba se ukládá do `localStorage` a razí se na `:root` **inline skriptem
v hlavičce, ještě před vykreslením** — jinak by při uložené volbě „tmavý"
problikla světlá stránka. Zápis i čtení jsou v `try`: v přísném sandboxu
`localStorage` vůbec neexistuje (přesně jako v jsdomu, kde běží testy)
a výjimka by shodila start komponenty. Hlídá to test
*„motiv jde přepnout i bez localStorage"*.

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
| `html/structure` — blokové značky se musí zavírat, a ve správném pořadí | Prohlížeč nevyvážený markup tiše dorovná; jednou chybějící `</aside>` zanořilo celý obsah do panelu |

### Prázdná stránka se nepozná měřením přetečení

Jedna chybějící `</aside>` zanořila `#main-content` do postranního panelu.
Ten je pod `lg` mimo plátno, takže **stránka byla prázdná** — a přitom:

- **jsdom testy prošly**: v DOM bylo všech 1050 řádků, jen je nebylo vidět;
- **měření přetečení prošlo**: nic neteklo do strany, všechno se vešlo do `w-64`;
- **axe neohlásil nic**: obsah formálně existoval.

Z toho plynou dvě pravidla. Za prvé, strukturu markupu hlídá **linter**
(`html/structure`), protože prohlížeč nevyvážené značky tiše dorovná a v DOM
už je chyba neviditelná. Za druhé, `check_responsive.py` měří i to, že
**hlavní obsah má nenulovou plochu, není zanořený v panelu a je vidět aspoň
jedna položka** — měřit rozvržení znamená měřit i to, že obsah něco zabírá,
ne jen že nic nepřetéká.

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

**Referenční markup Flowbite kontrast negarantuje.** Hlavička tabulky má
v jejich dokumentaci `dark:text-gray-400` na `dark:bg-gray-700`, což dává
zhruba 3,5:1 a axe to hlásí jako `serious`. Opsat vzor tedy nestačí —
vyhrává vlastní brána, ne předloha.

Tři nálezy stojí za zapamatování:

- **`aria-hidden-focus` na šuplíku.** Posunout ho mimo plátno přes
  `translate-x-full` nestačí — obsah zůstane fokusovatelný a odečítač do něj
  vleze. Řeší to `#filters[aria-hidden="true"] { visibility: hidden }`,
  navázané na atribut, který razí Flowbite.
- **Kontrast těsně pod hranicí.** `gray-500` na `gray-100` dává 4,4:1 při
  požadovaných 4,5:1. Okem nerozeznatelné, měřením ano.
- **Hlavička tabulky opsaná z Flowbite** propadla v tmavém motivu; opraveno
  na `dark:text-gray-300`.

### Měření nestačí — je potřeba se podívat

Dvě vady prošly úplně vším a odhalil je až pohled na stránku:

- chybějící `</aside>` zanořila obsah do panelu a **stránka byla prázdná**,
  přestože v DOM byly všechny řádky;
- lepivá hlavička tabulky (`sticky top-16`, vlastní vynález, ne vzor
  z Flowbite) **překryla záhlaví sekce a první řádek** — uvnitř
  `overflow-x-auto` se z obalu stane scroll kontejner a `top` se počítá
  od něj.

`check_responsive.py` dnes obojí chytí (plocha obsahu, zanoření v panelu,
vnitřní přetečení tabulky) a k tomu **překryv při scrollu 0**.

Ten poslední stojí za vysvětlení, protože intuice vede opačně. Lepivý prvek
do prvního scrollu drží svou přirozenou pozici, takže tam **nemá co překrývat**.
Když překrývá, znamená to, že se jeho lepivý kontext počítá od něčeho jiného,
než člověk čeká — přesně to udělala `sticky top-16` na hlavičce tabulky uvnitř
`overflow-x-auto`: obal se stal scroll kontejnerem a hlavička skončila 4 rem
pod *jeho* horní hranou, tedy přes záhlaví sekce a první řádek.

Po odscrollování se naopak překrývat **má** — lepivé nadpisy sekcí v kartách
fungují právě tak. Kdyby se měřilo po scrollu, hlásila by sonda je, a ne tu
skutečnou vadu. Pro nové vady toho druhu je tu `just shots`:
vyrenderuje stránku ve čtyřech šířkách do `.cache/shots/`. **Po každém zásahu
do rozvržení se na ty obrázky podívej** — je to levnější než vymýšlet metriku
na každý způsob, jak se dá layout rozbít.

## Rozvržení

Aplikační shell podle Flowbite Pro Admin Dashboardu (viz [`NOTICE.md`](../NOTICE.md)):
horní lišta, postranní panel, hlavní obsah, lepivá souhrnná lišta.

- **Horní lišta** nese značku, **hledání** a přepínač motivu. Hledání je
  nejpoužívanější ovládací prvek, takže patří do lišty, která zůstává na očích,
  ne do záhlaví stránky, které odscrolluje.
- **Postranní panel** nese přepínání pohledu, filtr zdroje, seznam zemí
  s vlastním hledáním a témata seskupená po rodinách, obojí s počty, a v patičce
  odkazy na plný výpis, matici pokrytí a zdrojová data.
  Pod `lg` je to Flowbite šuplík, od `lg` výš stojí napevno.
- **Čipy aktivních filtrů** v záhlaví stránky. Filtr je jinak vidět jen v panelu,
  který se scrolluje zvlášť; každý čip maže **jen svůj** filtr. Druh filtru nesou
  jako řetězec, nikdy jako callback — viz past s `x-show="crumb.action"` výš.
- **Úvodní rozcestník** se ukazuje jen v nultém stavu (`isLanding`): katalog,
  žádné hledání, žádná země, téma ani filtr zdroje. Jakýkoli filtr ho schová,
  aby sdílený odkaz vedl rovnou do dat. Hlídá to pět testů.
- **Tabulka má tři sloupce, ne šest.** Zdroj, Návštěv a Poslední braly 370 px
  a jsou prázdné u 998 z 1050 položek; při 768 px se kvůli nim tabulka
  scrollovala do strany. Doložení z prohlížeče je odznak u popisu, a jen tam,
  kde vůbec je.
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

### Katalog se vykresluje po dávkách

Vykreslit všech 1050 položek naráz znamenalo na mobilní šířce **16 453 uzlů DOM**
a ~200 ms jen na renderu — na desktopovém CPU. Na telefonu je to násobek a po
tu dobu je stránka **prázdná a nereagující**, protože `x-cloak` drží obsah
schovaný, dokud Alpine nedokreslí.

Renderuje se proto po dávkách (`limit`, výchozí `STEP = 60`); doscrollování
načte další přes `IntersectionObserver`, tlačítko zůstává pro klávesnici a pro
prohlížeče bez observeru.

  uzlů DOM   16 453 → 1 631
  render       196 ms → 7 ms   (390 px, medián 5 běhů headless Chrome)

Dvě věci, na kterých to stojí:

- **`filtered` zůstává úplné.** Dávkuje se až `sections`. Počty v panelu,
  souhrn i export do CSV proto pracují s celým výběrem, ne s tím, co je zrovna
  na obrazovce. Hlídá to test *„CSV exportuje celý výběr, ne jen vykreslenou
  dávku"*.
- **Změna filtru vrací `limit` na `STEP`.** Bez toho by po zúžení výběru zůstal
  vykreslený zbytek předchozího, širšího výsledku.

Souhrnná lišta říká pravdu o obojím: dokud je co načítat, hlásí
„Vykresleno 60 z 1050 odpovídajících", potom „Zobrazeno 1050 z 1050".

### Matice pokrytí je `<canvas>`, ne mřížka tlačítek

Rozcestník ukazuje celý katalog naráz: řádek země, sloupec téma, sytost počet
zdrojů. Buněk je tolik, kolik má katalog položek — jako DOM by stály přesně to,
co dávkování vykreslování ušetřilo, tedy přes tisíc uzlů na místě, kde uživatel
zatím nic nefiltruje. Kreslí se proto do jednoho `<canvas>`u.

Cena je klávesnice: do canvasu se tabovat nedá. Proto **nenese `role="grid"`** —
ta role slibuje obsluhu šipkami, kterou neimplementujeme, a nedodržený ARIA
kontrakt je horší než žádný. Nese `role="img"` s `aria-label`, který shrnuje
rozměr matice a kolik témat je kompletních. K témuž filtru vedou tři cesty
běžnými tlačítky: panel, čipy „Nebo rovnou zemí" a cesty podle otázky.

Dvě věci, na které se přišlo až pohledem na obrázek:

- **Popisek řádku se pod jedenáct pixelů výšky buňky nekreslí.** Na telefonu
  vyjde buňka na osm pixelů a desetibodové kódy se slily do šedé kaše přes data.
  Nečitelný popisek není informace navíc, jen šum — gutter tam připadne buňkám.
- **Gutter musí unést nejdelší kód v číselníku.** `GLOBAL` na šest znaků
  podtekl pod první sloupec, protože byl gutter dimenzovaný na dvoupísmenné
  kódy zemí.

Odstín nese rodinu tématu, ne jednotlivé téma — šest rodin je tolik odstínů,
kolik jde od sebe rozeznat. Díky tomu je díra vidět jako světlé místo **uvnitř**
barevného pruhu, kdežto prázdné bloky vpravo (nástroje, učení) dírou nejsou:
ta témata nejsou národní agenda a svítí jen v řádcích `EU` a `GLOBAL`. Text pod
maticí to říká, protože samotný obrázek to rozlišit neumí.

### Rozcestník má i osu, kterou katalog nemá

Katalog je dvouosý — téma a země. Rešerše se ale po ose nevede, vede se po
otázce: *kdo tu firmu vlastní*, *je v problémech*, *čí je ten pozemek*,
*kolik bere z veřejných peněz*. Každá cesta je pořadí témat, ve kterém na ni
jde odpovědět, a každý krok nastaví filtr. Je to jediné místo, kde má stránka
názor na to, v jakém pořadí se zdroje používají; do dat ten názor nepatří,
protože pro každou otázku je jiný.

Počty u kroků se počítají z katalogu, ne z hlavy. Krok, jehož téma v datech
není, ze seznamu vypadne — cesta tak nikdy nenabídne prázdno.

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
