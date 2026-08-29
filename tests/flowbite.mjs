/** Ověří integraci Flowbite s Alpine.
 *
 *  Tohle je nejkřehčí místo celé stránky: Flowbite váže chování jediným
 *  skenem DOM po načtení, kdežto Alpine vykresluje až po startu. Když se
 *  pořadí rozejde, komponenty jsou v DOM, vypadají správně a nedělají nic —
 *  bez jediné chyby v konzoli. Proto se to testuje kliknutím, ne přítomností. */
import { loadPage, checker } from './helpers.mjs';

const { window: w, document: d, state, errors, tick } = await loadPage();
const check = checker();

// Flowbite se neskenuje, váže ho direktiva x-flowbite po životním cyklu Alpine.
// Kdyby se initFlowbite vrátilo, znamenalo by to jednorázový sken vedle direktivy
// a dvojité navěšení: dvě instance si vzájemně vyruší toggle.
check('nesahá se na initFlowbite', typeof w.initFlowbite === 'undefined',
      typeof w.initFlowbite);
check('Flowbite eviduje instance', typeof w.FlowbiteInstances === 'object');
check('Alpine komponenta je registrovaná přes Alpine.data', !!state);
check('direktiva x-flowbite je registrovaná',
      !!w.Alpine && typeof w.Alpine.directive === 'function');

// ── šuplík s filtry ──────────────────────────────────────────────────────────
const sidebar = d.getElementById('sidebar');
const toggle = d.querySelector('[x-flowbite\\:drawer]');

check('postranní panel i jeho spouštěč existují', !!sidebar && !!toggle);
check('panel má aria-label', !!sidebar.getAttribute('aria-label'));
check('spouštěč má aria-controls', toggle.getAttribute('aria-controls') === 'sidebar');
check('panel startuje mimo plátno (pod lg:)', sidebar.className.includes('-translate-x-full'));
check('panel je od lg: napevno vidět', sidebar.className.includes('lg:translate-x-0'));

// Konstruktor Drawer nastaví cíli aria-hidden="true". Na desktopu je panel
// trvale vidět, takže by tím před odečítačem zmizel plný fokusovatelný obsah.
// Direktiva je potomek, takže běží až po init() komponenty — synchronizace
// aria proto musí přijít v $nextTick za ní.
check('panel není na desktopu schovaný před odečítačem',
      sidebar.getAttribute('aria-hidden') !== 'true',
      `aria-hidden=${sidebar.getAttribute('aria-hidden')}`);


toggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('kliknutí panel otevře', !sidebar.className.includes('-translate-x-full'));

toggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('další kliknutí panel zavře', sidebar.className.includes('-translate-x-full'));

// ── panel ovládá tentýž stav jako zbytek stránky ─────────────────────────────
check('panel nabízí kategorie i filtry',
      sidebar.querySelectorAll('button[aria-pressed]').length > 15,
      `${sidebar.querySelectorAll('button[aria-pressed]').length} přepínačů`);

state.source = 'reference';
await tick();
// Porovnává se popisek, ne celý textContent tlačítka: k popisku patří i počet
// a shoda na celý text by spadla při každém takovém doplnění — což je změna
// panelu, ne rozchod se stavem, který tenhle test hlídá.
check('panel odráží stav komponenty',
      [...sidebar.querySelectorAll('button[aria-pressed="true"]')]
        .some(b => (b.querySelector('span')?.textContent || b.textContent).trim() === 'Reference'));
state.source = '';
await tick();

// ── řadicí dropdown (Flowbite) ───────────────────────────────────────────────
const sortToggle = d.querySelector('[x-flowbite\\:dropdown]');
const sortMenu = d.getElementById('sort-dropdown');
check('řadicí dropdown existuje', !!sortToggle && !!sortMenu);
check('dropdown startuje skrytý', sortMenu.className.includes('hidden'));

sortToggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('kliknutí dropdown otevře', !sortMenu.className.includes('hidden'));

const visitsOption = [...sortMenu.querySelectorAll('button')]
  .find(b => b.textContent.includes('Návštěv'));
visitsOption.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('volba v dropdownu přeřadí tabulku', state.sort.key === 'visits',
      `řadí se dle '${state.sort.key}'`);

// ── spodní navigace a přepínání pohledu ──────────────────────────────────────
const bottomNav = d.querySelector('nav[aria-label="Přepnout pohled"]');
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

// ── instance přežije překreslení ────────────────────────────────────────────
// Tohle bylo se skenem DOM neproveditelné: Flowbite navěšoval jednou, takže
// cokoli Alpine vykreslil potom bylo mrtvé, a pravidlo flowbite/dynamic to
// muselo zakazovat. Direktiva váže instanci na životní cyklus uzlu, takže
// přefiltrování katalogu (které přerenderuje seznam) na dropdown nesmí sáhnout.
state.q = 'kataster';
await tick();
state.q = '';
await tick();

// Uzel se hledá znovu a výchozí stav se nepředpokládá: předchozí oddíl mohl
// menu nechat otevřené a test, který si stav domyslí, měří něco jiného.
const sortToggle2 = d.querySelector('[x-flowbite\\:dropdown]');
check('spouštěč dropdownu překreslení přežil', !!sortToggle2 && sortToggle2.isConnected);
if (!sortMenu.className.includes('hidden')) {
  sortToggle2.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await tick();
}
check('po překreslení je menu zavřené', sortMenu.className.includes('hidden'));
sortToggle2.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('dropdown se po překreslení otevře', !sortMenu.className.includes('hidden'));
sortToggle2.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await tick();
check('a zase zavře', sortMenu.className.includes('hidden'));

check.report(errors);
