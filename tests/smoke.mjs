/** Ověří, že se stránka vůbec nastartuje: Alpine se načte, data se vykreslí,
 *  x-cloak zmizí a v konzoli není chyba. Počty se berou z CSV, ne z hlavy. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPage, loadData, checker, remoteResources } from './helpers.mjs';

const DIST = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');

const { document: d, state, errors, tableRows, cardRows } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();

const inData = catalog.filter(r => r['Zdroj'] !== 'reference').length;
const cats = new Set(catalog.map(r => r['Kategorie'])).size;

check('Alpine se načetl', !!state);
check('nadpis', d.querySelector('h1')?.textContent.trim().replace(/\s+/g, ' ') === 'Geodata Atlas');
check('tabulka vykreslila celý katalog', tableRows() === catalog.length, `${tableRows()} z ${catalog.length}`);
check('karty vykreslily totéž', cardRows() === catalog.length, `${cardRows()} karet`);
check('hlavička souhlasí s daty',
      [...d.querySelectorAll('dd')].map(e => e.textContent.trim()).join('|')
        === [catalog.length, inData, longlist.length, cats].join('|'));
check('x-cloak zrušen', d.querySelectorAll('[x-cloak]').length === 0);
// Stránka nesmí stahovat nic zvenčí — jinak přestane fungovat offline
// a rozbije se pod CSP, které blokuje cizí hosty.
for (const f of ['index.html', 'artifact.html']) {
  const found = remoteResources(fs.readFileSync(path.join(DIST, f), 'utf8'));
  check(`${f} nenačítá nic zvenčí`, found.length === 0, found.slice(0, 2).join(' '));
}
// Artefakt jde navíc jako jediný soubor: ani lokální doprovodné soubory.
check('artifact.html je soběstačný',
      !/<(link|img|script)[^>]+(href|src)=/i.test(fs.readFileSync(path.join(DIST, 'artifact.html'), 'utf8')));

check.report(errors);
