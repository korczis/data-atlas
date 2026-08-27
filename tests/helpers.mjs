import { JSDOM } from 'jsdom';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** Načte postavenou stránku do jsdom a vrátí okno, Alpine stav a zachycené chyby. */
export async function loadPage() {
  const html = fs.readFileSync(path.join(ROOT, 'dist', 'index.html'), 'utf8');
  const errors = [];
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(w) {
      w.addEventListener('error', e => errors.push(e.message));
      // jsdom nemá matchMedia ani clipboard; stránka obojí používá
      w.matchMedia = q => ({ matches: false, media: q, addEventListener() {},
                             removeEventListener() {}, addListener() {}, removeListener() {} });
      Object.defineProperty(w.navigator, 'clipboard', {
        value: { writeText: t => { w.__clip = t; return Promise.resolve(); } },
      });
    },
  });
  const { window } = dom;
  await new Promise(r => setTimeout(r, 1000));
  const state = window.Alpine ? window.Alpine.$data(window.document.querySelector('[x-data]')) : null;
  return { window, document: window.document, state, errors,
           tick: () => new Promise(r => setTimeout(r, 250)),
           rows: n => window.document.querySelectorAll('table')[n].querySelectorAll('tbody tr').length };
}

/** Přečte committnutá CSV, aby testy ověřovaly shodu stránky s daty,
 *  místo aby hlídaly ručně opsaná čísla, která zestárnou při každém rebuildu. */
export function loadData() {
  const parse = file => {
    const text = fs.readFileSync(path.join(ROOT, 'data', file), 'utf8').replace(/^\uFEFF/, '');
    const rows = [];
    let row = [], field = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
        else if (c === '"') quoted = false;
        else field += c;
      } else if (c === '"') quoted = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      else if (c !== '\r') field += c;
    }
    if (field || row.length) { row.push(field); rows.push(row); }
    const head = rows.shift();
    return rows.filter(r => r.length === head.length)
               .map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])));
  };
  return { catalog: parse('catalog.csv'), longlist: parse('longlist.csv') };
}

/** Minimální reportér — sbírá výsledky a na konci nastaví exit kód. */
export function checker() {
  const results = [];
  const check = (label, cond, detail = '') =>
    results.push({ label, cond: !!cond, detail }) && !!cond;
  check.report = extra => {
    for (const r of results) console.log(`${r.cond ? '✓' : '✗'} ${r.label}${r.detail ? ' — ' + r.detail : ''}`);
    if (extra?.length) console.log('\nJS chyby:', extra);
    const failed = results.filter(r => !r.cond).length;
    console.log(`\n${results.length - failed}/${results.length} prošlo`);
    process.exit(failed === 0 && !extra?.length ? 0 : 1);
  };
  return check;
}
