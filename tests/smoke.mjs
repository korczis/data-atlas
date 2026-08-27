/** Ověří, že se stránka vůbec nastartuje: Alpine se načte, data se vykreslí,
 *  x-cloak zmizí a v konzoli není chyba. Počty se berou z CSV, ne z hlavy. */
import { loadPage, loadData, checker } from './helpers.mjs';

const { document: d, state, errors, rows } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();

const inData = catalog.filter(r => r['Zdroj'] !== 'reference').length;
const cats = new Set(catalog.map(r => r['Kategorie'])).size;

check('Alpine se načetl', !!state);
check('nadpis', d.querySelector('h1')?.textContent.trim().replace(/\s+/g, ' ') === 'Geodata Atlas');
check('katalog vykreslen celý', rows(0) === catalog.length, `${rows(0)} z ${catalog.length}`);
check('hlavička souhlasí s daty',
      [...d.querySelectorAll('dd')].map(e => e.textContent.trim()).join('|')
        === [catalog.length, inData, longlist.length, cats].join('|'));
check('x-cloak zrušen', d.querySelectorAll('[x-cloak]').length === 0);
check('žádné externí zdroje',
      !/<(script|link)[^>]+(src|href)="https?:/.test(d.documentElement.outerHTML));

check.report(errors);
