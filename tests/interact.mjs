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
check('hledání "postgis" projde i popisy', tableRows() === 3, `${tableRows()} řádků`);

s.q = 'katastr'; await tick();
check('hledání "katastr"', tableRows() >= 4, `${tableRows()} řádků`);

s.q = ''; s.cat = s.categories.find(c => c.includes('Routing')); await tick();
check('filtr kategorie', tableRows() === 6, `${tableRows()} řádků`);

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

s.q = ''; s.view = 'catalog'; s.cat = s.categories.find(c => c.includes('Historické')); await tick();
s.copyCsv(); await tick();
const clip = w.__clip || '';
check('export filtrovaného výběru do schránky',
      clip.startsWith('"Kategorie"') && clip.split('\n').length === 7,
      `${clip.split('\n').length - 1} datových řádků`);

check.report(errors);
