/** Projde interakce, které stránka nabízí: hledání, filtry, řazení,
 *  přepnutí záložky a export do schránky. */
import { loadPage, loadData, checker } from './helpers.mjs';

const { window: w, document: d, state: s, errors, tick, rows } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();
const inDataCount = catalog.filter(r => r['Zdroj'] !== 'reference').length;

check('výchozí pohled je katalog', rows(0) === catalog.length && rows(1) === 0);

s.q = 'postgis'; await tick();
check('hledání "postgis" projde i popisy', rows(0) === 3, `${rows(0)} řádků`);

s.q = 'katastr'; await tick();
check('hledání "katastr"', rows(0) >= 4, `${rows(0)} řádků`);

s.q = ''; s.cat = s.categories.find(c => c.includes('Routing')); await tick();
check('filtr kategorie', rows(0) === 6, `${rows(0)} řádků`);

s.cat = ''; s.source = 'data'; await tick();
const inData = rows(0);
s.source = 'reference'; await tick();
const ref = rows(0);
check('filtr zdroje dělí katalog beze zbytku',
      inData === inDataCount && inData + ref === catalog.length,
      `${inData} v datech + ${ref} reference = ${catalog.length}`);

s.source = ''; s.sortBy('visits'); await tick();
check('řazení dle návštěv sestupně',
      d.querySelectorAll('table')[0].querySelector('tbody tr').textContent.includes('vomaste.cz'));

s.view = 'longlist'; await tick();
check('přepnutí na long list', rows(1) === longlist.length && rows(0) === 0, `${rows(1)} řádků`);

s.q = 'cuzk'; await tick();
const expected = longlist.filter(r => r['Doména'].includes('cuzk')).length;
check('hledání v long listu', rows(1) === expected, `${rows(1)} z ${expected} očekávaných`);

s.q = ''; s.view = 'catalog'; s.cat = s.categories.find(c => c.includes('Historické')); await tick();
s.copyCsv(); await tick();
const clip = w.__clip || '';
check('export filtrovaného výběru do schránky',
      clip.startsWith('"Kategorie"') && clip.split('\n').length === 7,
      `${clip.split('\n').length - 1} datových řádků`);

check.report(errors);
