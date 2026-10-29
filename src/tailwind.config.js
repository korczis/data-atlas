/** Skenuje se vygenerovaná stránka s už vloženými daty — Alpine výrazy v ní
 *  obsahují literální třídy (badge(), :class), které by jinak Tailwind ořezal.
 *
 *  Stránky zemí se generují až po buildu CSS, takže se jejich zdroje skenují
 *  přímo. Bez toho by z nich Tailwind ořízl každou třídu, kterou hlavní
 *  stránka nepoužívá — stránkování, dropdowny filtrů, mřížku témat — a
 *  vypadaly by rozsypaně, aniž by cokoli spadlo. */
module.exports = {
  // The last glob is the Flowbite components the bundle actually imports
  // (src/js/flowbite-entry.js), as Flowbite's install guide asks. Not all of
  // `node_modules/flowbite/**`: Flowbite 4 carries its own Tailwind in
  // `node_modules/flowbite/node_modules`, which would be scanned along with it.
  content: [
    './.cache/page.src.html', './src/country.html', './src/js/place.js',
    './node_modules/flowbite/lib/esm/components/{drawer,dropdown}/*.js',
  ],

  // Flowbite si tyhle třídy **přidává za běhu**, takže v markupu nejsou
  // a Tailwind je ořízne. Bez nich se šuplík otevře bez ztmavení a ťuknutí
  // vedle něj ho nezavře, protože backdrop bez `inset-0` má nulový rozměr
  // a žádné ťuknutí na něj nedosáhne.
  //
  // Držel je naživu `#sidebarBackdrop` — kus opsaného shellu, který sám nic
  // nedělal (`display: none`) a fungoval jako nechtěný safelist. Když jsem ho
  // jako mrtvý kód smazal, backdrop přestal existovat. Tady je to napsané
  // schválně, ať to příště nespadne na to, že někdo uklidí nepoužitý div.
  //
  // Seznam odpovídá `backdropClasses` a `_getPlacementClasses('left')`
  // v balíčku flowbite — při jeho aktualizaci ho zkontroluj.
  safelist: [
    'fixed', 'inset-0', 'z-30', 'bg-dark-backdrop/70',
    'transform-none', '-translate-x-full', 'overflow-hidden',
  ],

  // Scanning the drawer source above also finds the physical `left-0` that
  // Flowbite puts in the drawer's base placement. The panel is positioned with
  // logical `start-0` (flowbite/rtl), and a `left-0` rule would fight it in RTL;
  // tools/check_runtime_classes.py requires the rule to be absent
  // (UNSTYLED_BY_DESIGN), and tools/lint_ui.py already forbids it in markup.
  blocklist: ['left-0'],

  // Artefakt se vykresluje ve třech stavech motivu, ne dvou: explicitní volba
  // razí data-theme na :root, výchozí "system" nerazí nic a rozhoduje média.
  darkMode: ['variant', [
    '&:is(:root[data-theme="dark"] *)',
    '@media (prefers-color-scheme: dark) { &:is(:root:not([data-theme="light"]) *) }',
  ]],

  theme: {
    extend: {
      // Paleta 'primary' podle Flowbite Pro admin dashboardu, aby se dala
      // jeho třídová konvence (bg-primary-700, focus:ring-primary-300)
      // použít beze změny. Hodnoty odpovídají Tailwind blue.
      colors: {
        // Flowbite 4's drawer backdrop is `bg-dark-backdrop/70`. Its theme
        // defines the colour only for Tailwind 4 (`--color-dark-backdrop`, gray-950
        // in the default theme), so on Tailwind 3 it is declared here.
        'dark-backdrop': '#030712',
        primary: {
          50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd',
          400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8',
          800: '#1e40af', 900: '#1e3a8a',
        },
      },
      fontFamily: {
        sans: ['ui-sans-serif','system-ui','-apple-system','BlinkMacSystemFont','Segoe UI','Roboto','Helvetica Neue','Arial','sans-serif'],
        mono: ['ui-monospace','SFMono-Regular','Menlo','Consolas','Liberation Mono','monospace'],
      },
    },
  },
  plugins: [require('flowbite/plugin')],
}
