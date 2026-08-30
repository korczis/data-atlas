/** Klávesnice a viditelnost fokusu.
 *
 *  Co tu **není**: kontrola, že se zaostřený prvek neschová pod lepivou lištou.
 *  Zkusil jsem ji a nedokázal jsem ji udělat falsifikovatelnou — prohlížeč
 *  prvek při zaostření doscrolluje tak velkoryse, že se vada neprojeví ani
 *  když se obsah pod lištu schválně zasune. Test, který projde ve zdravém
 *  i v rozbitém stavu, je horší než žádný: tvrdí, že něco hlídá.
 *  Překryv lepivých prvků měří `tools/check_responsive.py`, kde je na to
 *  scroll pod kontrolou.
 */
import { test, expect } from '@playwright/test'

test('zaostřený prvek má viditelný prstenec', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)

  // Měří se rozdíl proti nezaostřenému stavu, ne přítomnost třídy: outline
  // se dá přebít a `:focus-visible` v CSS ještě neznamená, že se vykreslí.
  const rings = await page.evaluate(() => {
    const out = []
    const els = [...document.querySelectorAll(
      'header button, header a[href], #main-content button, #main-content a[href]')]
      .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 })
      .slice(0, 12)
    for (const el of els) {
      const before = getComputedStyle(el).outlineWidth
      el.focus()
      const cs = getComputedStyle(el)
      const width = parseFloat(cs.outlineWidth) || 0
      const shadow = cs.boxShadow !== 'none'
      out.push({
        name: (el.getAttribute('aria-label') || el.textContent || el.tagName)
          .replace(/\s+/g, ' ').trim().slice(0, 34),
        ok: width > 0 || shadow, width, before,
      })
      el.blur()
    }
    return out
  })

  expect(rings.length, 'nebylo co změřit').toBeGreaterThan(5)
  const missing = rings.filter(r => !r.ok).map(r => r.name)
  expect(missing, 'zaostřený prvek bez viditelného prstence').toEqual([])
})

test('Escape a lomítko fungují podle nápovědy', async ({ page }) => {
  await page.goto('/#country=DE&topic=companies')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  // Stránka slibuje "/" v KBD nápovědě u hledání.
  await page.keyboard.press('/')
  await expect(page.locator('#search')).toBeFocused()
  // Escape ruší filtry — navěšené na @keydown.escape.window.
  await page.keyboard.press('Escape')
  await expect.poll(() => page.evaluate(() => location.hash)).toBe('')
})

test('do katalogu se dá dostat klávesnicí, aniž se projde celý panel',
  async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('[x-cloak]')).toHaveCount(0)
    // Panel má přes sto ovládacích prvků. Bez přeskočení by se uživatel
    // klávesnice k obsahu proklikával stovkou tabů.
    const skip = page.locator('a[href="#main-content"], a[href="#catalog"]').first()
    const hasSkip = await skip.count() > 0
    // Není-li přeskakovací odkaz, musí být obsah v pořadí PŘED panelem.
    const order = await page.evaluate(() => {
      const main = document.querySelector('#main-content')
      const aside = document.querySelector('aside')
      if (!main || !aside) return 'chybí'
      return (main.compareDocumentPosition(aside) & Node.DOCUMENT_POSITION_FOLLOWING)
        ? 'obsah před panelem' : 'panel před obsahem'
    })
    expect(hasSkip || order === 'obsah před panelem',
      `panel je v pořadí před obsahem (${order}) a chybí přeskakovací odkaz`).toBe(true)
  })
