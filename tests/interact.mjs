/** Projde interakce, které stránka nabízí: hledání, filtry po zemi i tématu,
 *  řazení, přepnutí záložky a export do schránky. */
import { loadPage, loadData, checker } from './helpers.mjs';

const { window: w, document: d, state: s, errors, tick, tableRows, cardRows, withMobile, renderAll } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();
const inDataCount = catalog.filter(r => r['Zdroj'] !== 'reference').length;

// Stejný vyhledávací řetězec, jaký si stránka skládá při startu. Kdyby se
// testovalo jen proti popisu, neodhalilo by se, že hledání přestalo brát
// v potaz zemi nebo téma.
const blob = r => [r['Web'], r['Doména'], r['Popis'], r['Téma'], r['Země'], r['Kód']]
  .join(' ').toLowerCase();

// ── dávkování ──────────────────────────────────────────────────────────────
// Testuje se dřív, než ho zbytek souboru vypne: katalog se vykresluje po
// dávkách, protože všech 1050 položek naráz znamenalo na mobilu 16 453 uzlů
// DOM a vteřiny prázdné, nereagující stránky.
check('vykresluje se jen první dávka', tableRows() === s.STEP, `${tableRows()} řádků`);
check('souhrn přizná, že je vykreslená jen část', s.hasMore && s.shown === s.STEP);
s.loadMore(); await tick();
check('další dávka přibude', tableRows() === 2 * s.STEP, `${tableRows()} řádků`);
s.q = 'kataster'; await tick();
check('změna filtru začíná znovu od první dávky', s.limit === s.STEP);
s.q = ''; await tick();
// Export bere celý výběr, ne jen vykreslenou dávku.
s.reset(); s.topic = 'companies'; await tick();
s.copyCsv(); await tick();
const exportRows = (w.__clip || '').split('\n').length - 1;
check('CSV exportuje celý výběr, ne jen vykreslenou dávku',
      exportRows === catalog.filter(r => r['Téma ID'] === 'companies').length,
      `${exportRows} řádků`);
s.reset();

// Zbytek souboru ověřuje filtrování, ne dávkování — ať vidí celý výběr.
await renderAll();

check('výchozí pohled je katalog', tableRows() === catalog.length);
const cardsAll = await withMobile(true, cardRows);
check('karty a tabulka jsou v souladu', cardsAll === tableRows(), `${cardsAll} karet / ${tableRows()} řádků`);

s.q = 'postgis'; await tick();
const postgisHits = catalog.filter(r => blob(r).includes('postgis')).length;
check('hledání "postgis" projde i popisy', tableRows() === postgisHits,
      `${tableRows()} z ${postgisHits} očekávaných`);

s.q = 'katastr'; await tick();
check('hledání "katastr"', tableRows() >= 4, `${tableRows()} řádků`);

// Země musí jít najít jménem i kódem — jinak je dvouznakový kód v odznaku
// dekorace, na kterou se nedá zeptat.
s.q = 'polsko'; await tick();
const plByName = catalog.filter(r => blob(r).includes('polsko')).length;
check('hledání podle názvu země', tableRows() === plByName, `${tableRows()} z ${plByName}`);

// ── osa téma ────────────────────────────────────────────────────────────────
s.q = ''; s.topic = 'routing'; await tick();
const routingCount = catalog.filter(r => r['Téma ID'] === 'routing').length;
check('filtr tématu', tableRows() === routingCount, `${tableRows()} z ${routingCount} očekávaných`);

// ── osa země ────────────────────────────────────────────────────────────────
s.topic = ''; s.country = 'CZ'; await tick();
const czCount = catalog.filter(r => r['Kód'] === 'CZ').length;
check('filtr země', tableRows() === czCount, `${tableRows()} z ${czCount} očekávaných`);

// Filtr země je přesná shoda: celoevropské zdroje se pod členským státem
// nezobrazují. Je to vědomá volba — jinak by 27 zemí táhlo tytéž položky
// dokola a nešlo by odlišit, co je národní. EU a Svět jsou vlastní rozsahy.
const euCount = catalog.filter(r => r['Kód'] === 'EU').length;
check('celoevropské zdroje nespadnou pod členský stát',
      tableRows() === czCount && euCount > 0 &&
      catalog.filter(r => r['Kód'] === 'CZ').every(r => r['Kód'] !== 'EU'));
s.country = 'EU'; await tick();
check('rozsah EU je vlastní volba', tableRows() === euCount, `${tableRows()} z ${euCount}`);

// ── obě osy naráz ───────────────────────────────────────────────────────────
s.country = 'PL'; s.topic = 'companies'; await tick();
const plCompanies = catalog.filter(r => r['Kód'] === 'PL' && r['Téma ID'] === 'companies').length;
check('země × téma se kombinují', tableRows() === plCompanies,
      `${tableRows()} z ${plCompanies} očekávaných`);

// Počty v panelu se počítají křížem — jinak by u vybrané země ukazovaly,
// kolik je toho v celém katalogu, a to je při 27 zemích k ničemu.
s.topic = ''; s.country = 'PL'; await tick();
check('počty témat respektují vybranou zemi',
      s.topicCounts.get('companies') === plCompanies,
      `companies v PL = ${s.topicCounts.get('companies')}`);
s.country = ''; s.topic = 'companies'; await tick();
check('počty zemí respektují vybrané téma',
      s.placeCounts.get('PL') === plCompanies,
      `PL v companies = ${s.placeCounts.get('PL')}`);

// ── panel nesmí položky schovávat ──────────────────────────────────────────
// Křížové počty se dřív promítaly i do *délky* seznamů: po výběru tématu
// zmizely země, které v něm nic nemají, takže se na ně nedalo přepnout —
// a vypadalo to, že se z katalogu ztratila data.
const allPlaces = new Set(catalog.map(r => r['Kód'])).size;
const allTopics = new Set(catalog.map(r => r['Téma ID'])).size;
const sidebarCounts = sel => [...d.getElementById('sidebar').querySelectorAll(sel)]
  .map(b => parseInt(b.querySelector('[data-count]').textContent, 10));

s.reset(); s.topic = 'addresses'; await tick();
check('výběr tématu nezkrátí seznam zemí',
      sidebarCounts('button[data-filter="country"]').length === allPlaces,
      `${sidebarCounts('button[data-filter="country"]').length} z ${allPlaces}`);
s.reset(); s.country = 'MT'; await tick();
check('výběr země nezkrátí seznam témat',
      sidebarCounts('button[data-filter="topic"]').length === allTopics,
      `${sidebarCounts('button[data-filter="topic"]').length} z ${allTopics}`);
check('prázdná kombinace se v panelu ukáže jako nula, ne zmizením',
      sidebarCounts('button[data-filter="topic"]').includes(0));

// Textový filtr nad zeměmi seznam zkrátit smí — o to uživatel výslovně požádal.
s.reset(); s.cq = 'pol'; await tick();
check('textový filtr zemí seznam zúží',
      s.countryList.length < allPlaces && s.countryList.every(p =>
        (p.name + p.code).toLowerCase().includes('pol')),
      `${s.countryList.length} zemí`);
s.cq = '';

// ── panel musí říct, že počty jsou křížené ────────────────────────────────
// Uživatel čte počty u zemí, ale filtr tématu je jinde v odscrollovaném panelu.
// Bez téhle hlášky vypadalo „Rakousko 2" jako celý katalog místo počtu
// obchodních rejstříků.
// jsdom nepočítá layout, takže offsetParent je vždycky null — skryté prvky
// se poznají podle toho, co na ně napsal x-show.
const banner = () => [...d.getElementById('sidebar').querySelectorAll('p')]
  .filter(e => e.style.display !== 'none')
  .map(e => e.textContent.replace(/\s+/g, ' ').trim())
  .filter(t => t.startsWith('počty jen'));

s.reset(); await tick();
check('bez filtru se o křížení nemluví', banner().length === 0);
s.topic = 'companies'; await tick();
check('vybrané téma je vidět u seznamu zemí',
      banner().some(t => t.includes('Obchodní rejstříky')), banner()[0] || '—');
s.reset(); s.country = 'CZ'; await tick();
check('vybraná země je vidět u seznamu témat',
      banner().some(t => t.includes('Česko')), banner()[0] || '—');

// ── odznaky u „Vše" musí odpovídat tomu, co se po kliknutí stane ───────────
s.reset(); s.topic = 'companies'; await tick();
const companiesTotal = catalog.filter(r => r['Téma ID'] === 'companies').length;
check('odznak „Všechny země" počítá v rámci vybraného tématu',
      s.allCountriesCount === companiesTotal, `${s.allCountriesCount} z ${companiesTotal}`);
s.reset(); s.country = 'MT'; await tick();
const mtTotal = catalog.filter(r => r['Kód'] === 'MT').length;
check('odznak „Všechna témata" počítá v rámci vybrané země',
      s.allTopicsCount === mtTotal, `${s.allTopicsCount} z ${mtTotal}`);
s.reset(); await tick();
check('bez filtru oba odznaky ukazují celý katalog',
      s.allCountriesCount === catalog.length && s.allTopicsCount === catalog.length);

// ── zdroj ───────────────────────────────────────────────────────────────────
s.reset(); s.source = 'data'; await tick();
const inData = tableRows();
s.source = 'reference'; await tick();
const ref = tableRows();
check('filtr zdroje dělí katalog beze zbytku',
      inData === inDataCount && inData + ref === catalog.length,
      `${inData} v datech + ${ref} reference = ${catalog.length}`);

s.source = ''; s.sortBy('visits'); await tick();
check('řazení dle návštěv sestupně',
      // [data-row] přeskočí hlavičku sekce, která v DOM zůstává i skrytá
      d.querySelector('table tbody tr[data-row]').textContent.includes('vomaste.cz'));

s.view = 'longlist'; await tick();
check('přepnutí na long list', tableRows() === longlist.length, `${tableRows()} řádků`);

s.q = 'cuzk'; await tick();
const expected = longlist.filter(r => r['Doména'].includes('cuzk')).length;
check('hledání v long listu', tableRows() === expected, `${tableRows()} z ${expected} očekávaných`);

// ── export ──────────────────────────────────────────────────────────────────
s.q = ''; s.view = 'catalog'; s.topic = 'archives'; await tick();
s.copyCsv(); await tick();
const clip = w.__clip || '';
// Počet se bere z CSV — ručně zapsané číslo padne při první změně katalogu.
const expectedRows = catalog.filter(r => r['Téma ID'] === 'archives').length;
check('export filtrovaného výběru do schránky',
      clip.startsWith('"Země"') && clip.split('\n').length === expectedRows + 1,
      `${clip.split('\n').length - 1} z ${expectedRows} očekávaných`);
check('export nese obě osy i klasifikaci přístupu',
      ['"Země"', '"Téma"', '"Přístup"', '"Data"'].every(c => clip.split('\n')[0].includes(c)));

// ── regresní test na past, která stála nejvíc času ─────────────────────────
// Alpine u výrazu vracejícího funkci tu funkci ZAVOLÁ. Callback uložený
// v datech a použitý v x-show se tak spouštěl při každém překreslení
// a mazal filtr. Test hlídá, že překreslení stav nemění.
s.reset(); s.view = 'catalog';
s.topic = 'routing'; s.country = 'GLOBAL';
await tick();
const afterSet = s.topic;
s.q = 'a'; await tick(); s.q = ''; await tick();   // vynuť několik překreslení
check('překreslení nemění nastavený filtr',
      s.topic === 'routing' && s.country === 'GLOBAL' && afterSet === 'routing',
      `topic=${s.topic} country=${s.country}`);

// ── stav ve URL ────────────────────────────────────────────────────────────
// history.replaceState nad about:blank neprojde, proto se ověřuje složený
// řetězec a zpětné načtení, ne skutečná adresa v prohlížeči.
s.reset(); s.topic = 'cadastre'; s.country = 'PL'; s.source = 'data'; await tick();
const written = new URLSearchParams(s.writeHash());
check('filtr se propíše do URL',
      written.get('topic') === 'cadastre' && written.get('country') === 'PL'
      && written.get('src') === 'data',
      decodeURIComponent(written.toString()).slice(0, 60));

s.reset(); await tick();
s.readHash('#view=longlist&q=cuzk');
await tick();
check('stav se načte zpátky z URL',
      s.view === 'longlist' && s.q === 'cuzk', `view=${s.view} q=${s.q}`);
s.readHash('#topic=vymyšlené&country=XX');
check('neplatné téma i země z URL se ignorují', s.topic === '' && s.country === '');
// V URL stojí identifikátor tématu, ne popisek. Popisky se přepisují a odkaz
// poslaný před rokem by po takové úpravě tiše přestal filtrovat.
s.readHash('#topic=companies');
check('v URL je stabilní identifikátor tématu, ne popisek', s.topic === 'companies');

// ── členění po tématech ────────────────────────────────────────────────────
s.reset(); s.view = 'catalog'; s.sort = { key: 'ord', dir: 1 }; await tick();
check('bez filtru se katalog člení po tématech',
      s.sections.length === new Set(catalog.map(r => r['Téma ID'])).size,
      `${s.sections.length} sekcí`);
s.country = 'CZ'; await tick();
check('vybraná země se pořád člení po tématech',
      s.sections.length === new Set(catalog.filter(r => r['Kód'] === 'CZ').map(r => r['Téma ID'])).size,
      `${s.sections.length} sekcí`);
s.country = ''; s.sortBy('visits'); await tick();
check('řazení podle návštěv členění vypne', s.sections.length === 1,
      `${s.sections.length} sekcí — jinak by globální pořadí rozbilo seskupení`);

// Hlavička a tělo tabulky se musí shodovat v počtu sloupců i po tom, co
// se sloupec Téma v seskupeném režimu skryje.
for (const [label, setup] of [['seskupeně', () => { s.reset(); s.sort = { key: 'ord', dir: 1 }; }],
                              ['plochý seznam', () => { s.sortBy('visits'); }]]) {
  setup(); await tick();
  const headers = d.querySelectorAll('table thead th').length;
  const row = d.querySelector('table tbody tr[data-row]');
  const visible = [...row.querySelectorAll('td')].filter(td => td.style.display !== 'none').length;
  check(`sloupce sedí (${label})`, headers === visible, `${headers} hlaviček / ${visible} buněk`);
}

// ── přepínač motivu ────────────────────────────────────────────────────────
// Tři stavy, ne dva: „podle systému" je volba, ne absence volby, a artefakt
// se v ní vykresluje jinak než v obou explicitních.
const root = d.documentElement;
s.theme = 'system'; root.removeAttribute('data-theme');
s.cycleTheme(); await tick();
check('motiv: systém → světlý', s.theme === 'light' && root.getAttribute('data-theme') === 'light');
s.cycleTheme(); await tick();
check('motiv: světlý → tmavý', s.theme === 'dark' && root.getAttribute('data-theme') === 'dark');
s.cycleTheme(); await tick();
check('motiv: tmavý → zpět na systém',
      s.theme === 'system' && root.getAttribute('data-theme') === null,
      'systémový stav nesmí razit data-theme, jinak přestane platit media query');
// jsdom bez `url` nemá localStorage — a přesně tak se chová i artefakt
// v přísném sandboxu. Přepínání proto musí fungovat i bez něj; kde úložiště
// je, musí se volba uložit.
const store = (() => { try { return w.localStorage; } catch (e) { return null; } })();
s.cycleTheme(); await tick();
check('motiv jde přepnout i bez localStorage',
      s.theme === 'light' && root.getAttribute('data-theme') === 'light',
      store ? 'úložiště je k dispozici' : 'úložiště chybí, jako v sandboxu');
if (store) {
  check('explicitní volba se uloží', store.getItem('geodata-atlas-theme') === 'light');
  s.theme = 'dark'; s.cycleTheme();
  check('návrat na systém volbu smaže', store.getItem('geodata-atlas-theme') === null);
}

// ── čipy aktivních filtrů ─────────────────────────────────────────────────
s.reset(); s.country = 'DE'; s.topic = 'companies'; s.q = 'register'; s.source = 'reference';
await tick();
check('každý aktivní filtr má vlastní čip',
      s.filterChips.map(c => c.kind).sort().join() === 'country,q,source,topic',
      s.filterChips.map(c => c.label).join(' · '));
s.clearFilter('country'); await tick();
check('čip maže jen svůj filtr',
      s.country === '' && s.topic === 'companies' && s.q === 'register' && s.source === 'reference');
s.reset(); await tick();
check('bez filtru nejsou čipy', s.filterChips.length === 0);

// ── úvodní rozcestník ──────────────────────────────────────────────────────
// Hero smí být jen v nultém stavu. Kdo přijde přes sdílený odkaz, musí
// přistát rovnou v datech — jinak by rozcestník překážel právě těm, kdo už
// vědí, co hledají.
s.reset(); await tick();
// Filtr zdroje je provenience z prohlížeče a v long listu nemá co filtrovat.
// Odkaz #view=longlist&src=reference vracel prázdnou stránku bez vysvětlení.
{
  s.view = 'longlist'; s.source = 'reference';
  check('long list se filtrem zdroje nevyprázdní',
        s.filtered.length === s.longlist.length, `${s.filtered.length} z ${s.longlist.length}`);
  s.readHash('view=longlist&src=reference');
  check('odkaz s src v long listu se normalizuje', s.source === '');
  s.view = 'longlist'; s.source = 'reference';
  check('src se do URL long listu nezapíše', !s.writeHash().includes('src='));
  s.view = 'catalog'; s.source = 'reference';
  check('v katalogu filtr zdroje pořád platí',
        s.filtered.length > 0 && s.filtered.every(r => r.src === 'reference'),
        `${s.filtered.length} referencí`);
  s.source = '';
}

// Vlajky: každá země musí mít posun ve spritu a žádný rozsah ho mít nesmí.
// Chybějící posun by dal `background-position-x: undefined` a vykreslil
// první vlajku ze spritu u špatné země — tiše a pro všechny stejně.
{
  const countries = s.places.filter(p => !p.scope);
  const scopes = s.places.filter(p => p.scope);
  check('každá země má posun ve spritu',
        countries.length > 0 && countries.every(p => typeof p.fx === 'number'),
        `${countries.length} zemí`);
  check('posuny jsou různé', new Set(countries.map(p => p.fx)).size === countries.length);
  check('rozsahy vlajku nemají', scopes.every(p => p.fx === undefined));
  check('rychlé vstupy nesou posun i pro rozsahy',
        s.topCountries.every(c => c.fx === undefined || typeof c.fx === 'number'));
}

check('hero se ukazuje na prázdném katalogu', s.isLanding);

// Rozcestník: matice a cesty podle otázky. Canvas se v jsdomu nevykreslí,
// takže se testuje to, co se vykreslit dá — čísla, ze kterých kreslí.
check('matice má řádek pro každý stát a rozsah',
      s.matrixRows.length === s.places.filter(p => p.eu || p.scope).length,
      `${s.matrixRows.length} řádků`);
check('matice má sloupec pro každé téma',
      s.matrixCols.length === s.taxonomy.reduce((a, g) => a + g.topics.length, 0),
      `${s.matrixCols.length} sloupců`);
check('součet buněk matice je celý katalog',
      [...s.matrixCounts.values()].reduce((a, b) => a + b, 0) === s.catalog.length);
check('každá rodina témat má vlastní odstín',
      new Set(s.matrixLegend.map(g => g.swatch)).size === s.taxonomy.length);
check('popis matice pro odečítač nese rozměr i souhrn',
      /\d+ zemí a rozsahů krát \d+ témat/.test(s.matrixLabel) &&
      s.matrixLabel.includes(String(s.matrixFull)));
// Číslo v textu pod maticí musí sedět na data, ne na to, co bylo pravda
// v den, kdy se věta psala.
{
  const eu = s.places.filter(p => p.eu).map(p => p.code);
  const full = s.matrixCols.filter(c => eu.every(k => s.matrixCounts.get(k + ' ' + c.id))).length;
  check('počet kompletních témat se počítá z dat', s.matrixFull === full, `${full}`);
}
check('cesty podle otázky nenabízejí prázdný krok',
      s.paths.every(p => p.steps.length > 0 && p.steps.every(st => st.count > 0)));
check('krok cesty nastaví existující téma',
      s.paths.every(p => p.steps.every(st =>
        s.catalog.some(r => r.topic === st.id))));

for (const [label, set] of [['hledání', () => { s.q = 'kataster'; }],
                            ['zemi', () => { s.country = 'DE'; }],
                            ['tématu', () => { s.topic = 'companies'; }],
                            ['filtru zdroje', () => { s.source = 'data'; }]]) {
  s.reset(); set(); await tick();
  check(`hero mizí při ${label}`, !s.isLanding);
}
s.reset(); s.view = 'longlist'; await tick();
check('hero mizí na long listu', !s.isLanding);
s.reset(); await tick();
check('rychlé vstupy nesou počty z dat',
      s.topCountries.length > 0 && s.topTopics.length > 0
      && s.topCountries[0].count >= s.topCountries[s.topCountries.length - 1].count,
      `${s.topCountries.length} zemí, ${s.topTopics.length} témat`);
check('největší země v rozcestníku sedí na katalog',
      s.topCountries[0].count === Math.max(...[...s.placeCounts.values()]));

check.report(errors);
