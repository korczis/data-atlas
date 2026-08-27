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
      d.querySelector('table tbody tr').textContent.includes('vomaste.cz'));

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

check.report(errors);
