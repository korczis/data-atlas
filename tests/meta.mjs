/** Ověří hlavičku dokumentové varianty a doprovodné soubory webu.
 *  Meta tagy se snadno rozbijí tiše — chybějící og:image se pozná až
 *  ve chvíli, kdy někdo odkaz nasdílí a vypadne mu prázdná karta. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadData, checker } from './helpers.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DIST = path.join(ROOT, 'dist');
const html = fs.readFileSync(path.join(DIST, 'index.html'), 'utf8');
const head = html.slice(0, html.indexOf('</head>'));
const { catalog } = loadData();
const check = checker();
const has = re => re.test(head);

check('lang na <html>', /<html lang="cs">/.test(html));
check('charset je první', head.indexOf('<meta charset="utf-8">') < 60);
check('viewport', has(/name="viewport"[^>]*width=device-width/));
check('title', /<title>Geodata Atlas<\/title>/.test(head));
check('description', has(/name="description" content="[^"]{80,}"/));
check('canonical', has(/rel="canonical" href="https:\/\/korczis\.github\.io\/geodata-atlas\/"/));
check('robots', has(/name="robots"[^>]*max-image-preview:large/));
check('author', has(/name="author"/));
check('color-scheme', has(/name="color-scheme" content="light dark"/));
check('theme-color pro oba motivy',
      (head.match(/name="theme-color"/g) || []).length === 2 && has(/prefers-color-scheme: dark/));

for (const t of ['og:type', 'og:site_name', 'og:locale', 'og:url', 'og:title',
                 'og:description', 'og:image', 'og:image:width', 'og:image:height', 'og:image:alt'])
  check(t, has(new RegExp(`property="${t}"`)));

for (const t of ['twitter:card', 'twitter:title', 'twitter:description',
                 'twitter:image', 'twitter:image:alt'])
  check(t, has(new RegExp(`name="${t}"`)));

check('twitter:card je summary_large_image', has(/name="twitter:card" content="summary_large_image"/));
check('ikony: ico, svg, apple-touch', has(/href="favicon\.ico"/) && has(/href="favicon\.svg"/) && has(/rel="apple-touch-icon"/));
check('manifest', has(/rel="manifest"/));

// strukturovaná data musí být platný JSON, ne jen přítomný tag
const ld = head.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
let parsed = null;
try { parsed = JSON.parse(ld[1]); } catch { /* zůstane null */ }
check('JSON-LD je platný JSON', !!parsed);
check('JSON-LD popisuje DataCatalog',
      parsed?.['@graph']?.some(n => n['@type'] === 'DataCatalog'));

// popis nesmí obsahovat ručně opsané počty, které nesedí s daty
const cats = new Set(catalog.map(r => r['Kategorie'])).size;
check('popis odpovídá skutečným počtům',
      head.includes(`${catalog.length} položek v ${cats} kategoriích`),
      `${catalog.length} položek / ${cats} kategorií`);

for (const f of ['robots.txt', 'sitemap.xml', 'site.webmanifest', '404.html', '.nojekyll',
                 'favicon.ico', 'favicon.svg', 'apple-touch-icon.png',
                 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'og-image.png'])
  check(`dist/${f}`, fs.existsSync(path.join(DIST, f)));

check('sitemap odkazuje na kanonickou URL',
      fs.readFileSync(path.join(DIST, 'sitemap.xml'), 'utf8').includes('https://korczis.github.io/geodata-atlas/'));
check('robots.txt odkazuje na sitemapu',
      fs.readFileSync(path.join(DIST, 'robots.txt'), 'utf8').includes('sitemap.xml'));
check('manifest je platný JSON s maskable ikonou', (() => {
  try {
    const m = JSON.parse(fs.readFileSync(path.join(DIST, 'site.webmanifest'), 'utf8'));
    return m.icons?.some(i => i.purpose === 'maskable');
  } catch { return false; }
})());
check('404 je noindex', fs.readFileSync(path.join(DIST, '404.html'), 'utf8').includes('name="robots" content="noindex"'));

check.report([]);
