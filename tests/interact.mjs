/** Projde interakce, které stránka nabízí: hledání, filtry po zemi i tématu,
 *  řazení, přepnutí záložky a export do schránky. */
import { loadPage, loadData, checker } from './helpers.mjs';

const { window: w, document: d, state: s, errors, tick, tableRows, cardRows, withMobile } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();
const inDataCount = catalog.filter(r => r['Zdroj'] !== 'reference').length;

// Stejný vyhledávací řetězec, jaký si stránka skládá při startu. Kdyby se
// testovalo jen proti popisu, neodhalilo by se, že hledání přestalo brát
// v potaz zemi nebo téma.
const blob = r => [r['Web'], r['Doména'], r['Popis'], r['Téma'], r['Země'], r['Kód']]
  .join(' ').toLowerCase();

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

check.report(errors);
