/** Odznaky u položky katalogu musí být na obou stránkách tytéž.
 *
 *  Byly dvě implementace a rozešly se: strojová dostupnost svítila na hlavní
 *  stránce modře a na stránkách zemí zeleně, odstíny se lišily (-50 proti -100)
 *  a slovník taky (`bulk` proti `hromadně`). Tenhle test hlídá výsledek, ne
 *  implementaci — kdyby někdo odznaky někde znovu opsal, projeví se to tady.
 */
import { test, expect } from '@playwright/test'

/** Třídy a texty odznaků na dané stránce, setříděné a odduplikované. */
async function badges(page, url) {
  await page.goto(url)
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  return page.evaluate(() => {
    const out = new Map()
    for (const el of document.querySelectorAll('span')) {
      const cls = el.className || ''
      if (!/\b(bg-emerald-|bg-amber-|bg-gray-100)\b/.test(cls)) continue
      if (!el.closest('[data-row], [data-card]')) continue
      const key = (el.textContent || '').trim()
      const sem = cls.split(/\s+/).filter(c => /emerald|amber|gray-100|gray-600|gray-700|gray-300/.test(c))
      out.set(key, sem.sort().join(' '))
    }
    return Object.fromEntries(out)
  })
}

test('odznaky vypadají stejně na hlavní stránce i na stránce země', async ({ page }) => {
  const main = await badges(page, '/')
  const country = await badges(page, '/cz/')

  const shared = Object.keys(main).filter(k => k in country)
  expect(shared.length, 'stránky nesdílejí ani jeden odznak — test by neměřil nic').toBeGreaterThan(2)

  const drift = shared.filter(k => main[k] !== country[k])
    .map(k => `${k}: index=${main[k]} · cz=${country[k]}`)
  expect(drift, 'tentýž odznak má na dvou stránkách jiné třídy').toEqual([])
})

test('barva odznaku nese stálý význam', async ({ page }) => {
  const main = await badges(page, '/')
  // Podlaha: nad prázdnou mapou se cyklus nespustí a test projde, aniž by
  // cokoli ověřil. Stejná stráž jako u testu o shodě mezi stránkami.
  expect(Object.keys(main).length, 'nenašel se ani jeden odznak').toBeGreaterThan(2)
  // emerald = data jdou ven strojově, amber = překážka v přístupu.
  const machine = ['hromadně', 'API', 'OGC služby', 'ke stažení']
  const barrier = ['registrace', 'placené', 'omezené', 'smíšené', 'vyhledávání']
  for (const [text, cls] of Object.entries(main)) {
    if (machine.includes(text)) expect(cls, text).toContain('emerald')
    if (barrier.includes(text)) expect(cls, text).toContain('amber')
  }
})

test('odznak nese význam i textem, ne jen barvou', async ({ page }) => {
  // Barva sama nesmí nést kritickou informaci — každý odznak má popisek.
  const main = await badges(page, '/')
  expect(Object.keys(main).length, 'nenašel se ani jeden odznak').toBeGreaterThan(2)
  expect(Object.keys(main).every(t => t.length > 0)).toBe(true)
})
