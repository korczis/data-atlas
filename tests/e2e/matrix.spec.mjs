/** Matice pokrytí má popsané obě osy a součet.
 *
 *  Proč zvlášť a proč přes geometrii: mřížka se kreslí do <canvas>, takže
 *  popisky sloupců ani čísla součtu nejsou v DOM a `toBeVisible()` na ně
 *  nedosáhne. Do doby, než tohle vzniklo, měla matice popsané jen řádky —
 *  čtyřiatřicet sloupců bylo rozlišených pouhou barvou rodiny, což „Geodata"
 *  odliší od „Firmy", ale `geoportal` od `terrain` ne. Nahlásil to uživatel,
 *  ne brána, protože žádná brána se na to nedívala.
 *
 *  Měří se `mgeom`, kterou drawMatrix po každém vykreslení vystaví: výška
 *  hlavičky nad nulou znamená, že se popisky sloupců kreslily, a `sumX`
 *  nad nulou, že se kreslil sloupec součtu.
 */
import { test, expect } from '@playwright/test'

const geom = page => page.evaluate(() =>
  window.Alpine.$data(document.querySelector('[x-data]')).mgeom)

test('na šířce desktopu má matice popsané sloupce i součet', async ({ page, viewport }) => {
  if (viewport.width < 768) test.skip(true, 'úzké rozvržení popisky vynechává, to hlídá test níž')
  await page.goto('/#coverage')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  await expect.poll(async () => (await geom(page))?.head ?? 0).toBeGreaterThan(40)
  const g = await geom(page)
  expect(g.label, 'popisky řádků').toBeGreaterThan(0)
  expect(g.sumX, 'sloupec součtu').toBeGreaterThan(0)
  // Hlavička musí unést nejdelší popisek v číselníku, jinak se usekává —
  // a useknuté „Gazetteery a geokódová…" neodpoví na otázku, kvůli které
  // tam popisky jsou.
  const longest = await page.evaluate(() => {
    const s = window.Alpine.$data(document.querySelector('[x-data]'))
    const c = document.createElement('canvas').getContext('2d')
    c.font = '10px ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif'
    return Math.max(...s.matrixCols.map(x => c.measureText(x.label).width))
  })
  expect(g.head, 'hlavička unese i nejdelší popisek').toBeGreaterThanOrEqual(longest)
})

test('na úzké šířce se popisky ani součet nekreslí', async ({ page, viewport }) => {
  if (viewport.width >= 768) test.skip(true, 'tohle je tvrzení o mobilu')
  await page.goto('/#coverage')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  await expect.poll(async () => (await geom(page)) !== null).toBe(true)
  const g = await geom(page)
  // Pod hranicí čitelnosti je vynechání správná odpověď: dvojciferné číslo
  // přes sedmipixelový řádek je šmouha, ne informace, a prázdný pruh vpravo
  // by ubral šířku všem sloupcům bez protihodnoty.
  expect(g.head, 'popisky sloupců').toBe(0)
  expect(g.sumX, 'sloupec součtu').toBe(-1)
})
