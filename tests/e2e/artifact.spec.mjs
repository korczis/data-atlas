/** `artifact.html` — soběstačná varianta pro Claude Artifacts a e-mail.
 *
 *  Je to týž markup vložený do cizí stránky, takže tady se hlídá přesně to,
 *  co se v ní liší: nesmí sahat ven a nesmí nabízet odkazy na stránky zemí,
 *  které vedle ní neexistují.
 */
import { test, expect } from '@playwright/test'

test('artefakt nesahá po síti', async ({ page }) => {
  const external = []
  page.on('request', r => {
    const u = r.url()
    if (!u.startsWith('http://127.0.0.1:8123') && !u.startsWith('data:')) external.push(u)
  })
  await page.goto('/artifact.html')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  expect(external).toEqual([])
})

test('artefakt vykreslí katalog', async ({ page }) => {
  await page.goto('/artifact.html')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  await expect(page.locator('[data-row]:visible, [data-card]:visible').first()).toBeVisible()
})

test('artefakt nenabízí odkazy na stránky zemí', async ({ page }) => {
  // Vedle artefaktu žádné stránky zemí nestojí; relativní `at/` by v cizím
  // dokumentu mířilo mimo. Řídí to window.__PAGES__.
  await page.goto('/artifact.html')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  expect(await page.evaluate(() => window.__PAGES__)).toBe(false)
  // Prvky v DOM zůstávají, skrývá je x-show — pro uživatele i pro odečítač
  // je `display:none` totéž jako by tam nebyly, a testovat počet uzlů místo
  // viditelnosti by měřilo implementaci, ne chování.
  await expect(page.locator('aside a[aria-label^="Otevřít stránku"]:visible')).toHaveCount(0)
  await expect(page.locator('a[href="zeme/"]:visible')).toHaveCount(0)
})

test('hlavní stránka je naopak nabízí', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  expect(await page.evaluate(() => window.__PAGES__)).toBe(true)
})
