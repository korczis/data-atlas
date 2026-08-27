/** Projde interakce, které stránka nabízí: hledání, filtry, řazení,
 *  přepnutí záložky a export do schránky. */
import { loadPage, loadData, checker } from './helpers.mjs';

const { window: w, document: d, state: s, errors, tick, tableRows, cardRows } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();
const inDataCount = catalog.filter(r => r['Zdroj'] !== 'reference').length;

check('výchozí pohled je katalog', tableRows() === catalog.length);
check('karty a tabulka jsou v souladu', cardRows() === tableRows(), `${cardRows()} karet / ${tableRows()} řádků`);

s.q = 'postgis'; await tick();
// Hledá se i v popisech, takže se trefí i položky, které PostGIS jen zmiňují.
const postgisHits = catalog.filter(r =>
  ['Web', 'Doména', 'Popis', 'Kategorie'].some(k => r[k].toLowerCase().includes('postgis'))).length;
check('hledání "postgis" projde i popisy', tableRows() === postgisHits,
      `${tableRows()} z ${postgisHits} očekávaných`);

s.q = 'katastr'; await tick();
check('hledání "katastr"', tableRows() >= 4, `${tableRows()} řádků`);

s.q = ''; s.cat = s.categories.find(c => c.name.includes('Routing')).name; await tick();
const routingCount = catalog.filter(r => r['Kategorie'].includes('Routing')).length;
check('filtr kategorie', tableRows() === routingCount,
      `${tableRows()} z ${routingCount} očekávaných`);

s.cat = ''; s.source = 'data'; await tick();
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

s.q = ''; s.view = 'catalog'; s.cat = s.categories.find(c => c.name.includes('Historické')).name; await tick();
s.copyCsv(); await tick();
const clip = w.__clip || '';
// Počet se bere z CSV — ručně zapsané číslo padne při první změně katalogu.
const expectedRows = catalog.filter(r => r['Kategorie'].includes('Historické')).length;
check('export filtrovaného výběru do schránky',
      clip.startsWith('"Kategorie"') && clip.split('\n').length === expectedRows + 1,
      `${clip.split('\n').length - 1} z ${expectedRows} očekávaných`);

// ── regresní test na past, která stála nejvíc času ─────────────────────────
// Alpine u výrazu vracejícího funkci tu funkci ZAVOLÁ. Callback uložený
// v datech a použitý v x-show se tak spouštěl při každém překreslení
// a mazal filtr. Test hlídá, že překreslení stav nemění.
s.reset(); s.view = 'catalog';
const someCat = catalog.find(r => r['Kategorie'].includes('Routing'))['Kategorie'];
s.cat = someCat;
await tick();
const afterSet = s.cat;
s.q = 'a'; await tick(); s.q = ''; await tick();   // vynuť několik překreslení
check('překreslení nemění nastavený filtr',
      s.cat === someCat && afterSet === someCat,
      `cat = ${JSON.stringify(s.cat).slice(0, 30)}`);

// ── stav ve URL ────────────────────────────────────────────────────────────
// history.replaceState nad about:blank neprojde, proto se ověřuje složený
// řetězec a zpětné načtení, ne skutečná adresa v prohlížeči.
s.reset(); s.cat = someCat; s.source = 'data'; await tick();
const written = new URLSearchParams(s.writeHash());
check('filtr se propíše do URL',
      written.get('cat') === someCat && written.get('src') === 'data',
      decodeURIComponent(written.toString()).slice(0, 52));

s.reset(); await tick();
s.readHash('#view=longlist&q=cuzk');
await tick();
check('stav se načte zpátky z URL',
      s.view === 'longlist' && s.q === 'cuzk', `view=${s.view} q=${s.q}`);
s.readHash('#cat=vymyšlená');
check('neplatná kategorie z URL se ignoruje', s.cat === '');

// ── členění po kategoriích ─────────────────────────────────────────────────
s.reset(); s.view = 'catalog'; s.sort = { key: 'ord', dir: 1 }; await tick();
check('bez filtru se katalog člení po kategoriích',
      s.sections.length === new Set(catalog.map(r => r['Kategorie'])).size,
      `${s.sections.length} sekcí`);
s.sortBy('visits'); await tick();
check('řazení podle návštěv členění vypne', s.sections.length === 1,
      `${s.sections.length} sekcí — jinak by globální pořadí rozbilo seskupení`);

// Hlavička a tělo tabulky se musí shodovat v počtu sloupců i po tom, co
// se sloupec Kategorie v seskupeném režimu skryje.
for (const [label, setup] of [['seskupeně', () => { s.reset(); s.sort = { key: 'ord', dir: 1 }; }],
                              ['plochý seznam', () => { s.sortBy('visits'); }]]) {
  setup(); await tick();
  const headers = d.querySelectorAll('table thead th').length;
  const row = d.querySelector('table tbody tr[data-row]');
  const visible = [...row.querySelectorAll('td')].filter(td => td.style.display !== 'none').length;
  check(`sloupce sedí (${label})`, headers === visible, `${headers} hlaviček / ${visible} buněk`);
}

check.report(errors);
