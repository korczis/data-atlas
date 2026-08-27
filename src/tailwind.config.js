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
      // Paleta 'primary' podle Flowbite Pro admin dashboardu, aby se dala
      // jeho třídová konvence (bg-primary-700, focus:ring-primary-300)
      // použít beze změny. Hodnoty odpovídají Tailwind blue.
      colors: {
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
