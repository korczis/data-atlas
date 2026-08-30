/** Ověří vygenerované stránky zemí a rozcestník `zeme/`.
 *
 *  Stránky se generují, takže se netestuje jedna ručně napsaná, ale to, co
 *  o všech musí platit: každá země z katalogu má stránku, každá stránka nese
 *  jen svoje data, hlavičky odpovídají adrese a runtime se načítá relativně,
 *  aby to fungovalo i pod `file://`.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM, VirtualConsole } from 'jsdom';
import { remoteResources } from './helpers.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(ROOT, 'dist');

let pass = 0, fail = 0;
const check = (label, ok, note = '') => {
  if (ok) { pass++; console.log(`✓ ${label}${note ? ' — ' + note : ''}`); }
  else { fail++; console.log(`✗ ${label}${note ? ' — ' + note : ''}`); }
};

const csv = fs.readFileSync(path.join(ROOT, 'data', 'catalog.csv'), 'utf8');
const header = csv.split('\n')[0].replace(/^﻿/, '').split(',');
const codeCol = header.indexOf('Kód');
// Bez téhle stráže projdou dvě assertions nad nulou zemí: při přejmenování
// sloupce je index -1, `cells[-1]` je undefined, `counts` zůstane prázdné
// a „stránka existuje pro každou zemi" se splní triviálně.
if (codeCol < 0) {
  console.error(`sloupec 'Kód' v data/catalog.csv není — hlavička: ${header.join(', ')}`);
  process.exit(1);
}
const counts = new Map();
// Popisy obsahují čárky, ale sloupec Kód je vždycky dvou- až šestiznakový
// token bez uvozovek — na počty stačí a nemusí se sem tahat parser CSV.
for (const line of csv.split('\n').slice(1)) {
  if (!line.trim()) continue;
  const cells = line.match(/(".*?"|[^,]*)(,|$)/g).map(c => c.replace(/,$/, '').replace(/^"|"$/g, ''));
  const code = cells[codeCol];
  if (code) counts.set(code, (counts.get(code) || 0) + 1);
}

const slugs = [...counts.keys()].map(c => c.toLowerCase());

check('stránka existuje pro každou zemi v katalogu',
      slugs.every(s => fs.existsSync(path.join(DIST, s, 'index.html'))),
      `${slugs.length} zemí`);
check('rozcestník zeme/ existuje', fs.existsSync(path.join(DIST, 'zeme', 'index.html')));
// Ani stránky zemí nesmí sahat po síti. Tvrzení o tom existovalo, ale jen
// pro index.html a artifact.html — CDN skript v src/country.html by tedy
// neodhalilo nic, přestože je to týž zákaz a týž důvod: stránka musí jet
// z disku, offline a pod přísným CSP. Relativní `../assets/atlas.js` je
// v pořádku, remoteResources() hledá jen absolutní http(s).
{
  const offenders = [];
  for (const s of [...slugs, 'zeme']) {
    const f = path.join(DIST, s, 'index.html');
    if (!fs.existsSync(f)) continue;
    const found = remoteResources(fs.readFileSync(f, 'utf8'));
    if (found.length) offenders.push(`${s}: ${found[0]}`);
  }
  check('žádná stránka země nenačítá nic zvenčí', offenders.length === 0,
        offenders.length ? offenders.slice(0, 3).join(' · ') : `${slugs.length + 1} stránek`);
}

check('sdílený runtime existuje',
      fs.existsSync(path.join(DIST, 'assets', 'atlas.css'))
      && fs.existsSync(path.join(DIST, 'assets', 'atlas.js')));

// Sitemapa musí nést všechny stránky, jinak celý důvod, proč vznikly
// (viditelnost pro vyhledávače), padá.
const sitemap = fs.readFileSync(path.join(DIST, 'sitemap.xml'), 'utf8');
// Neúplný build se pozná dřív, než začnou padat jednotlivá tvrzení.
// build_page.py sitemapu zakládá s jedinou adresou a plnou píše až
// build_places.py, takže po částečném buildu tady spadnou dvě assertions
// s hláškou, ze které příčina není poznat. Radši jednou a jasně.
{
  const n = (sitemap.match(/<loc>/g) || []).length;
  if (n < 2) {
    console.error(`sitemapa má ${n} adresu — build je neúplný. `
      + 'Spusť `just build`: build_page.py ji zakládá, build_places.py přepisuje.');
    process.exit(1);
  }
}
check('sitemapa nese každou stránku země',
      slugs.every(s => sitemap.includes(`/${s}/</loc>`)),
      `${(sitemap.match(/<loc>/g) || []).length} adres`);
check('sitemapa nese rozcestník', sitemap.includes('/zeme/</loc>'));

// Detail jedné stránky — Česko má nejvíc položek, takže je nejtvrdší případ.
const html = fs.readFileSync(path.join(DIST, 'cz', 'index.html'), 'utf8');
check('stránka má vlastní title', /<title>Česko — Data Atlas<\/title>/.test(html));
check('stránka má canonical na svou adresu',
      html.includes('<link rel="canonical" href="https://korczis.github.io/data-atlas/cz/">'));
check('stránka má vlastní popis', /<meta name="description" content="\d+ ověřených/.test(html));
check('stránka je indexovatelná', html.includes('content="index,follow"'));
check('runtime se načítá relativně',
      html.includes('href="../assets/atlas.css"') && html.includes('src="../assets/atlas.js"'));
check('drobečková navigace vede zpět', html.includes('>Katalog</a>') && html.includes('>Země</a>'));

const ld = JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1]);
check('JSON-LD je CollectionPage s drobečky',
      ld['@type'] === 'CollectionPage' && ld.breadcrumb.itemListElement.length === 3);
check('JSON-LD hlásí správný počet položek',
      ld.mainEntity.numberOfItems === counts.get('CZ'), `${ld.mainEntity.numberOfItems}`);

// Payload musí nést **jen** tu zemi. Kdyby se do něj dostal celý katalog,
// stránka by vážila megabajt a celá úspora by zmizela.
const payload = JSON.parse(html.match(/window\.__PLACE__=(\{.*?\});<\/script>/s)[1]);
check('payload nese jen data té země',
      payload.rows.length === counts.get('CZ'), `${payload.rows.length} položek`);
check('payload nese předpočítané hledací pole',
      payload.rows.every(r => typeof r.s === 'string' && r.s === r.s.toLowerCase()));
check('payload nese taxonomii a popisky',
      payload.groups.length > 0 && Object.keys(payload.labels.topics).length > 0);

// Chování tabulky. Bez prohlížeče se netestuje vzhled, ale logika filtrů,
// řazení a stránkování — tedy to, co uživatel na stránce dělá.
// Chyby uvnitř stránky musí test shodit. Dřív se tu vkládal holý Alpine
// z node_modules s odůvodněním „testuje se komponenta, ne způsob doručení" —
// jenže magii `$marks` registruje až sdílený runtime, takže stránka při
// každém řádku házela `$marks is not defined`. Sto výjimek, a suita hlásila
// 37/37. Přesně ta zelená, které se nedá věřit: řádky se nevykreslily,
// odznaky nebyly, a nikdo se to nedozvěděl.
//
// Načítá se proto `dist/assets/atlas.js`, tedy to, co si stáhne prohlížeč.
// Způsob doručení *je* součást chování, když v sobě nese registrace.
const pageErrors = [];
const virtualConsole = new VirtualConsole();
virtualConsole.on('jsdomError', e => pageErrors.push(e.message || String(e)));
virtualConsole.on('error', (...a) => pageErrors.push(a.join(' ')));

const dom = new JSDOM(html, {
  runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole,
  beforeParse(w) {
    w.matchMedia = q => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} });
    w.HTMLCanvasElement.prototype.getContext = () => null;
  },
});
const runtime = path.join(DIST, 'assets', 'atlas.js');
dom.window.eval(fs.readFileSync(runtime, 'utf8'));
await new Promise(r => setTimeout(r, 500));

// Kontroluje se až tady, po dokončení prvního renderu: Alpine vyhodnocuje
// výrazy asynchronně a dřív by se stihla zachytit jen část.
check('stránka nevyhodila při vykreslení ani jednu chybu',
      pageErrors.length === 0,
      pageErrors.length ? `${pageErrors.length}× — první: ${pageErrors[0].split('\n')[0]}` : 'čistá');

const s = dom.window.Alpine
  ? dom.window.Alpine.$data(dom.window.document.querySelector('[x-data]')) : null;
check('komponenta nastartovala', !!s);
if (s) {
  check('výchozí výběr je celá země', s.filtered.length === payload.rows.length);
  const topic = s.topics[0];
  s.topic = topic.id;
  check('filtr tématu zúží výběr',
        s.filtered.length === topic.count && s.filtered.every(r => r.topic === topic.id),
        `${topic.label}: ${s.filtered.length}`);
  s.topic = '';
  s.q = 'katastr';
  check('hledání zabírá', s.filtered.length > 0 && s.filtered.length < payload.rows.length,
        `${s.filtered.length} položek`);
  s.q = '';
  check('výchozí řazení je podle názvu vzestupně',
        s.sort.key === 'name' && s.sort.dir === 1);
  const names = s.filtered.map(r => r.name);
  check('výchozí pořadí je opravdu abecední',
        names.every((n, i) => i === 0 || names[i - 1].localeCompare(n, 'cs') <= 0));
  s.sortBy('name');
  check('kliknutí na už seřazený sloupec obrátí směr', s.sort.dir === -1);
  const desc = s.filtered.map(r => r.name);
  check('obrácené pořadí je opravdu sestupné',
        desc.every((n, i) => i === 0 || desc[i - 1].localeCompare(n, 'cs') >= 0));
  s.sortBy('topic');
  check('jiný sloupec začíná vzestupně', s.sort.key === 'topic' && s.sort.dir === 1);
  s.sort = { key: 'name', dir: 1 };
  check('stránkuje se po padesáti', s.shown.length === Math.min(50, s.filtered.length));
  check('poslední stránka sedí na počet',
        s.lastPage === Math.max(1, Math.ceil(s.filtered.length / 50)));
  s.page = 2;
  check('druhá stránka navazuje', s.from === 50);
  s.page = 1;
  // Filtr žije v URL, aby šel výřez poslat dál; identifikátor tématu, ne popisek.
  s.topic = topic.id; s.page = 2;
  const hash = s.writeHash();
  check('URL nese téma i stránku', hash.includes('topic=' + topic.id) && hash.includes('page=2'));
  s.readHash('topic=' + topic.id + '&page=2');
  check('URL se přečte zpátky', s.topic === topic.id && s.page === 2);
  s.readHash('topic=neexistuje');
  check('neznámé téma z URL se zahodí', s.topic === '');
}

// ── vazby mezi tématy ──────────────────────────────────────────────────────
// Graf je kurátorovaný nad tématy, ne nad zdroji. Nabídnout téma, které
// v téhle zemi nic nenese, by byl slib, který se po kliknutí nenaplní.
s.topic = 'companies';
check('vazby se nabízejí jen k vybranému tématu', s.relatedTopics.length > 0,
      s.relatedTopics.map(r => r.id).join(' '));
check('každá nabídnutá vazba má v téhle zemi zdroje',
      s.relatedTopics.every(r => r.count > 0 && s.rows.some(row => row.topic === r.id)));
check('vazba nevede sama na sebe', !s.relatedTopics.some(r => r.id === 'companies'));
check('nadnárodní zdroje k tématu se hlásí počtem',
      Array.isArray(s.supraForTopic) && s.supraForTopic.every(x => x.count > 0),
      JSON.stringify(s.supraForTopic));
s.topic = '';
check('bez tématu se nenabízí nic', s.relatedTopics.length === 0 && !s.supraForTopic);

// ── co se opravdu vykreslilo ───────────────────────────────────────────────
// Až sem se testoval jen stav komponenty. Proto mohla stránka u každého řádku
// spadnout na `$marks is not defined` a suita to nezahlédla: do DOM se nikdo
// nepodíval. Stav bez výstupu není chování.
s.page = 1;
await new Promise(r => setTimeout(r, 100));
const doc = dom.window.document;
const rendered = doc.querySelectorAll('[data-row], [data-card]');
check('řádky se vykreslily do DOM', rendered.length > 0, `${rendered.length} uzlů`);

// Odznaky chodí přes magii `$marks`. Poznají se podle barvy, kterou nic
// jiného na řádku nepoužívá: `emerald` = data jdou ven strojově, `amber` =
// překážka v přístupu. Šedá se sem nepočítá, tu nosí i štítek tématu.
//
// Znění se ověřuje proti číselníku z payloadu, ne proti seznamu napsanému
// tady — jinak by test tvrdil, že se vykreslilo něco, čemu sám určil slova.
const vocabulary = new Set([...Object.values(payload.labels.data || {}),
                            ...Object.values(payload.labels.access || {})]);
const badges = [...doc.querySelectorAll('[data-row] span, [data-card] span')]
  .filter(el => /bg-(emerald|amber)-100/.test(el.className))
  .map(el => el.textContent.trim());
check('odznaky se vykreslily', badges.length > 0, `${badges.length}×`);
check('odznaky mluví číselníkem, ne vlastním slovníkem',
      badges.length > 0 && badges.every(t => vocabulary.has(t)),
      [...new Set(badges)].slice(0, 4).join(', '));

console.log(`\n${pass}/${pass + fail} prošlo`);
process.exit(fail ? 1 : 0);
