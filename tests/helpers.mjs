import { JSDOM } from 'jsdom';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** Alpine při přerušeném x-transition odmítne vlastní promise značkou
 *  { isFromCancelledTransition: true } a zpracuje ji o mikrotask později.
 *  Node ji do té doby stihne prohlásit za unhandled a shodit celý běh —
 *  test pak spadne na chování, které v prohlížeči nikdo nepozná.
 *  Přeskakuje se přesně tahle značka; cokoli jiného musí testy vidět. */
const rejections = [];
process.on('unhandledRejection', reason => {
  if (reason && typeof reason === 'object' && reason.isFromCancelledTransition) return;
  rejections.push(String(reason?.message ?? reason));
});

/** Načte postavenou stránku do jsdom a vrátí okno, Alpine stav a zachycené chyby. */
export async function loadPage() {
  const html = fs.readFileSync(path.join(ROOT, 'dist', 'index.html'), 'utf8');
  const errors = [];
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    beforeParse(w) {
      w.addEventListener('error', e => errors.push(e.message));
      // jsdom nemá matchMedia ani clipboard; stránka obojí používá.
      //
      // Stránka se podle matchMedia rozhoduje, jestli vykreslit karty, nebo
      // tabulku. Konstantní `matches: false` by tedy znamenalo „nejužší telefon"
      // a testy by nikdy neviděly tabulku. Stub proto vyhodnocuje `min-width`
      // proti šířce okna jsdomu (výchozích 1024 px), tedy jako desktop.
      const viewport = 1024;
      w.matchMedia = q => {
        const m = /min-width:\s*(\d+)px/.exec(q);
        return { matches: m ? viewport >= Number(m[1]) : false, media: q,
                 addEventListener() {}, removeEventListener() {},
                 addListener() {}, removeListener() {} };
      };
      Object.defineProperty(w.navigator, 'clipboard', {
        value: { writeText: t => { w.__clip = t; return Promise.resolve(); } },
      });
    },
  });
  const { window } = dom;
  await new Promise(r => setTimeout(r, 1000));
  const state = window.Alpine ? window.Alpine.$data(window.document.querySelector('[x-data]')) : null;
  const d = window.document;
  errors.push(...rejections);
  return {
    window, document: d, state, errors,
    tick: () => new Promise(r => setTimeout(r, 250)),
    // Od přechodu na mobile-first je tabulka jen pro md: a výš; pod tím
    // se tentýž seznam vykresluje jako karty. Měříme obojí.
    // [data-row] odliší datové řádky od hlaviček sekcí.
    tableRows: () => d.querySelectorAll('table tbody tr[data-row]').length,
    cardRows: () => d.querySelectorAll('ul[role="list"] > li').length,
    // V DOM je vždy jen ta větev seznamu, která je na dané šířce vidět —
    // druhá se nevykresluje, aby se u tisícovky položek neplatilo dvakrát.
    // Testy si proto větev přepnou a změří ji zvlášť.
    withMobile: async (on, fn) => {
      const st = window.Alpine.$data(d.querySelector('[x-data]'));
      const before = st.mobile;
      st.mobile = on;
      await new Promise(r => setTimeout(r, 400));
      const out = fn();
      st.mobile = before;
      await new Promise(r => setTimeout(r, 400));
      return out;
    },
    tableSections: () => d.querySelectorAll('table tbody').length,
  };
}

/** Najde odkazy na zdroje, které by prohlížeč skutečně stahoval.
 *  Vědomě ignoruje canonical, og:url a JSON-LD: to jsou absolutní URL
 *  v metadatech, ne síťové požadavky. */
export function remoteResources(html) {
  const patterns = [
    /<script[^>]+\bsrc=["']https?:/gi,
    /<link[^>]+rel=["'](?:stylesheet|preload|prefetch|preconnect)["'][^>]*\bhref=["']https?:/gi,
    /<(?:img|iframe|video|audio|source|embed)[^>]+\bsrc=["']https?:/gi,
    /@import\s+(?:url\()?["']?https?:/gi,
    /url\(\s*["']?(?:https?:)?\/\//gi,
    /\bfetch\(\s*["']https?:/gi,
    /new\s+(?:XMLHttpRequest|WebSocket|EventSource)\b/gi,
  ];
  return patterns.flatMap(re => html.match(re) || []);
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
