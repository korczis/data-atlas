/** Ověří, že se stránka nastartuje a vykreslí všechna data.
 *  Počty se berou z CSV, ne z hlavy. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPage, loadData, checker, remoteResources } from './helpers.mjs';

const DIST = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const { document: d, state, errors, tableRows, cardRows, withMobile } = await loadPage();
const { catalog, longlist } = loadData();
const check = checker();

check('Alpine se načetl', !!state);
const flat = d.body.textContent.replace(/\s+/g, ' ');  // pozor na &nbsp; ve značce
check('značka v horní liště', flat.includes('Geodata Atlas'));
check('nadpis stránky', d.querySelector('h1')?.textContent.trim() === 'Kurátorovaný katalog');
check('tabulka vykreslila celý katalog', tableRows() === catalog.length, `${tableRows()} z ${catalog.length}`);
// Karty existují jen pod md:. Test si tu větev zapne, změří ji a vrátí zpátky.
const cards = await withMobile(true, cardRows);
check('karty vykreslily totéž', cards === catalog.length, `${cards} karet`);
check('vykresluje se jen jedna větev seznamu',
      await withMobile(true, tableRows) === 0 && cardRows() === 0,
      'pod md: není tabulka, nad md: nejsou karty');

// Součet v panelu musí sedět na katalog — jinak některé téma nebo země chybí.
// Země i téma se počítají křížem, takže bez filtru musí obě osy dát totéž číslo.
const sidebar = d.getElementById('sidebar');
const counts = sel => [...sidebar.querySelectorAll(sel)]
  .map(b => parseInt(b.querySelector('[data-count]').textContent, 10))
  .filter(Number.isFinite);

const topicCounts = counts('button[data-filter="topic"]');
const placeCounts = counts('button[data-filter="country"]');
const topics = new Set(catalog.map(r => r['Téma ID']));
const places = new Set(catalog.map(r => r['Kód']));

check('součet témat v panelu sedí na katalog',
      topicCounts.reduce((a, b) => a + b, 0) === catalog.length,
      `${topicCounts.length} témat, součet ${topicCounts.reduce((a, b) => a + b, 0)}`);
check('počet témat sedí', topicCounts.length === topics.size, `${topicCounts.length} z ${topics.size}`);
check('součet zemí v panelu sedí na katalog',
      placeCounts.reduce((a, b) => a + b, 0) === catalog.length,
      `${placeCounts.length} zemí, součet ${placeCounts.reduce((a, b) => a + b, 0)}`);
check('počet zemí sedí', placeCounts.length === places.size, `${placeCounts.length} z ${places.size}`);

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
