/** Ověří integraci Flowbite s Alpine.
 *
 *  Tohle je nejkřehčí místo celé stránky: Flowbite váže chování jediným
 *  skenem DOM po načtení, kdežto Alpine vykresluje až po startu. Když se
 *  pořadí rozejde, komponenty jsou v DOM, vypadají správně a nedělají nic —
 *  bez jediné chyby v konzoli. Proto se to testuje kliknutím, ne přítomností. */
import { loadPage, checker } from './helpers.mjs';

const { window: w, document: d, state, errors, tick } = await loadPage();
const check = checker();

check('Flowbite se načetl', typeof w.initFlowbite === 'function');
check('Flowbite eviduje instance', typeof w.FlowbiteInstances === 'object');
check('Alpine komponenta je registrovaná přes Alpine.data', !!state);

// ── šuplík s filtry ──────────────────────────────────────────────────────────
const drawer = d.getElementById('filters');
const open = d.querySelector('[data-drawer-show="filters"]');
const close = d.querySelector('[data-drawer-hide="filters"]');

check('šuplík i jeho spouštěč existují', !!drawer && !!open && !!close);
check('šuplík startuje mimo plátno', drawer.className.includes('translate-x-full'));
check('spouštěč má aria-controls', open.getAttribute('aria-controls') === 'filters');
check('šuplík má aria-labelledby',
      !!d.getElementById(drawer.getAttribute('aria-labelledby')));

open.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('kliknutí šuplík otevře', !drawer.className.includes('translate-x-full'));

close.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('zavírací tlačítko šuplík zavře', drawer.className.includes('translate-x-full'));

// ── filtry v šuplíku ovládají tentýž stav jako na desktopu ───────────────────
const drawerSourceBtns = drawer.querySelectorAll('button[aria-pressed]');
check('šuplík nabízí filtry', drawerSourceBtns.length > 3, `${drawerSourceBtns.length} přepínačů`);

state.source = 'reference';
await tick();
const pressed = [...drawer.querySelectorAll('button[aria-pressed="true"]')]
  .some(b => b.textContent.trim() === 'Reference');
check('šuplík odráží stav komponenty', pressed);

// ── spodní navigace a přepínání pohledu ──────────────────────────────────────
const bottomNav = d.querySelector('nav[aria-label]');
check('spodní navigace existuje', !!bottomNav);
check('spodní navigace je jen pro mobil', bottomNav.className.includes('sm:hidden'));

// ── toast ────────────────────────────────────────────────────────────────────
state.flash('test');
await tick();
const toast = [...d.querySelectorAll('[role="status"]')]
  .find(e => e.textContent.includes('test'));
check('toast se zobrazí a hlásí se jako status', !!toast);
check('toast je aria-live', toast?.getAttribute('aria-live') === 'polite');

// ── klávesová zkratka slíbená v KBD nápovědě ─────────────────────────────────
check('KBD nápověda pro "/" je v markupu', /<kbd[^>]*>\s*\/\s*<\/kbd>/.test(d.body.innerHTML));
const root = d.querySelector('[x-data]');
check('"/" je opravdu navěšené', root.outerHTML.includes('keydown.slash.window'));

check.report(errors);
