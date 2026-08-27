/** Ověří, že se stránka nastartuje a vykreslí všechna data.
 *  Počty se berou z CSV, ne z hlavy. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPage, loadData, checker, remoteResources } from './helpers.mjs';

const DIST = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const { document: d, state, errors, tableRows, cardRows } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();

check('Alpine se načetl', !!state);
const flat = d.body.textContent.replace(/\s+/g, ' ');  // pozor na &nbsp; ve značce
check('značka v horní liště', flat.includes('Geodata Atlas'));
check('nadpis stránky', d.querySelector('h1')?.textContent.trim() === 'Kurátorovaný katalog');
check('tabulka vykreslila celý katalog', tableRows() === catalog.length, `${tableRows()} z ${catalog.length}`);
check('karty vykreslily totéž', cardRows() === catalog.length, `${cardRows()} karet`);

// Součet kategorií v panelu musí sedět na katalog — jinak některá chybí.
const sidebar = d.getElementById('sidebar');
const catCounts = [...sidebar.querySelectorAll('button[aria-pressed]')]
  .filter(b => b.querySelector('span:last-child'))
  .map(b => parseInt(b.querySelector('span:last-child').textContent, 10))
  .filter(Number.isFinite);
const cats = new Set(catalog.map(r => r['Kategorie']));
// první "Vše" nese celkový počet, zbytek jsou jednotlivé kategorie
const perCategory = catCounts.filter(n => n !== catalog.length);
check('součet kategorií v panelu sedí na katalog',
      perCategory.reduce((a, b) => a + b, 0) === catalog.length,
      `${perCategory.length} kategorií, součet ${perCategory.reduce((a, b) => a + b, 0)}`);
check('počet kategorií sedí', perCategory.length === cats.size, `${perCategory.length} z ${cats.size}`);

check('patička hlásí celkový počet', flat.includes(`z ${catalog.length}`));
check('long list je v panelu i ve spodní navigaci', flat.includes(String(longlist.length)));
check('x-cloak zrušen', d.querySelectorAll('[x-cloak]').length === 0);

for (const f of ['index.html', 'artifact.html']) {
  const found = remoteResources(fs.readFileSync(path.join(DIST, f), 'utf8'));
  check(`${f} nenačítá nic zvenčí`, found.length === 0, found.slice(0, 2).join(' '));
}
check('artifact.html je soběstačný',
      !/<(link|img|script)[^>]+(href|src)=/i.test(fs.readFileSync(path.join(DIST, 'artifact.html'), 'utf8')));

check.report(errors);
