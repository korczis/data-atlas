/** Skenuje se vygenerovaná stránka s už vloženými daty — Alpine výrazy v ní
 *  obsahují literální třídy (badge(), :class), které by jinak Tailwind ořezal. */
module.exports = {
  content: ['./.cache/page.src.html'],

  // Artefakt se vykresluje ve třech stavech motivu, ne dvou: explicitní volba
  // razí data-theme na :root, výchozí "system" nerazí nic a rozhoduje média.
  darkMode: ['variant', [
    '&:is(:root[data-theme="dark"] *)',
    '@media (prefers-color-scheme: dark) { &:is(:root:not([data-theme="light"]) *) }',
  ]],

  theme: {
    extend: {
      fontFamily: {
        sans: ['ui-sans-serif','system-ui','-apple-system','BlinkMacSystemFont','Segoe UI','Roboto','Helvetica Neue','Arial','sans-serif'],
        mono: ['ui-monospace','SFMono-Regular','Menlo','Consolas','Liberation Mono','monospace'],
      },
    },
  },
  plugins: [require('flowbite/plugin')],
}
