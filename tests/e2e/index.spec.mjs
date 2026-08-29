/** Hlavní stránka: katalog jako jedna aplikace.
 *
 *  Testuje se klikáním, ne přítomností atributu. Tahle kodbáze má
 *  zdokumentovanou historii vad, které přítomnost markupu prošly a přesto
 *  nefungovaly — Flowbite navěšený jediným skenem DOM, `scrollTo` na prvku,
 *  který se nescrolluje, odkaz schovaný za `opacity-0`.
 */
import { test, expect } from '@playwright/test'

/** Řádek katalogu bez ohledu na větev rozvržení: pod md karty, výš tabulka.
 *  Počítají se jen viditelné — obě větve mohou být v DOM zároveň. */
const rows = (page) => page.locator('[data-row]:visible, [data-card]:visible')

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  // Alpine musí naběhnout, jinak měříme prázdnou šablonu.
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
})

test('stránka naběhne a vykreslí katalog', async ({ page }) => {
  await expect(page).toHaveTitle(/Data Atlas/)
  await expect(page.getByRole('heading', { level: 2, name: /Ověřené veřejné datové zdroje/ })).toBeVisible()
  await expect(rows(page).first()).toBeVisible()
})

test('statistika hlásí čísla odvozená z katalogu', async ({ page }) => {
  // Počet zdrojů v horní liště a v dlaždici musí souhlasit — obojí se odvozuje
  // z týchž dat, takže rozpor by znamenal, že jedno místo počítá po svém.
  const badge = (await page.locator('header').getByText(/\d+\s*zdrojů/).first().innerText()).match(/\d+/)[0]
  const tile = await page.locator('dl').getByText(/^\d+$/).first().innerText()
  expect(Number(tile)).toBe(Number(badge))
})

test('hledání zúží výběr a jde zrušit', async ({ page }) => {
  const before = await rows(page).count()
  await page.locator('#search').fill('kataster')
  await expect.poll(() => rows(page).count()).toBeLessThan(before)
  await page.locator('#search').fill('')
  await expect.poll(() => rows(page).count()).toBe(before)
})

test('značka vede zpět na nefiltrovaný katalog', async ({ page }) => {
  await page.goto('/#country=DE&topic=companies')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  const brand = page.locator('header a[aria-label^="Data Atlas"]')
  await expect(brand).toBeVisible()
  await brand.click()
  await expect.poll(() => page.evaluate(() => location.hash)).toBe('')
  // Rozcestník se vrátí, jakmile filtr padne.
  await expect(page.locator('#coverage')).toBeVisible()
})

test('„Procházet katalog" opravdu posune na výpis', async ({ page }) => {
  const y0 = await page.evaluate(() => window.scrollY)
  await page.getByRole('button', { name: /Procházet katalog/ }).click()
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(y0 + 100)
  const top = await page.locator('#catalog').evaluate(el => Math.abs(el.getBoundingClientRect().top))
  expect(top).toBeLessThan(120)
})

test('„Matice pokrytí" skočí na matici i při aktivním filtru', async ({ page }) => {
  await page.goto('/#country=DE')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  // Cílí se na kotvu, ne na název: „Matice pokrytí" nese i odkaz do
  // dokumentace na GitHubu a hledat podle popisku by trefilo jiný cíl.
  await page.locator('a[href="#coverage"]:visible').first().click()
  const fig = page.locator('#coverage')
  await expect(fig).toBeVisible()
  await expect.poll(() => fig.evaluate(el => Math.abs(el.getBoundingClientRect().top)))
    .toBeLessThan(140)
})

test('Flowbite dropdown řazení funguje i po překreslení seznamu', async ({ page }) => {
  // Dřív nemožné: Flowbite se vázal jediným skenem DOM, takže cokoli Alpine
  // vykreslil potom bylo mrtvé. Direktiva x-flowbite to váže po životním cyklu.
  await page.locator('#search').fill('kataster')
  await page.locator('#search').fill('')
  const trigger = page.locator('[x-flowbite\\:dropdown]')
  const menu = page.locator('#sort-dropdown')
  await trigger.click()
  await expect(menu).toBeVisible()
  await trigger.click()
  await expect(menu).toBeHidden()
})

test('skupiny témat v panelu jdou sbalit a rozbalit', async ({ page, viewport }) => {
  if (viewport.width < 1024) test.skip(true, 'panel je pod lg: šuplík, má vlastní test')
  const head = page.locator('aside h3 button').first()
  const list = page.locator('#topic-group-0')
  await expect(list).toBeVisible()
  await expect(head).toHaveAttribute('aria-expanded', 'true')
  await head.click()
  await expect(list).toBeHidden()
  await expect(head).toHaveAttribute('aria-expanded', 'false')
  await head.click()
  await expect(list).toBeVisible()
})

test('odkaz na stránku země je v panelu vidět a vede tam', async ({ page, viewport }) => {
  if (viewport.width < 1024) test.skip(true, 'panel je pod lg: šuplík')
  // Vada, kterou tenhle test hlídá: šipky byly opacity-0 do group-hover,
  // takže na dotykovém zařízení nešly vidět ani použít.
  const arrow = page.locator('aside a[aria-label^="Otevřít stránku"]').first()
  await expect(arrow).toBeVisible()
  await arrow.click()
  await expect(page).toHaveURL(/\/[a-z]{2,6}\/$/)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
})

test('mobilní šuplík se otevře a zavře', async ({ page, viewport }) => {
  if (viewport.width >= 1024) test.skip(true, 'nad lg: je panel trvale vidět')
  const sidebar = page.locator('#sidebar')
  const toggle = page.locator('[x-flowbite\\:drawer]')
  await expect(toggle).toBeVisible()
  await toggle.click()
  await expect(sidebar).not.toHaveClass(/-translate-x-full/)
  await toggle.click()
  await expect(sidebar).toHaveClass(/-translate-x-full/)
})

test('stránka nikam nepřeteče do strany', async ({ page }) => {
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)
})

test('nic nepadá do konzole', async ({ page }) => {
  const bad = []
  page.on('pageerror', e => bad.push(String(e)))
  page.on('console', m => { if (m.type() === 'error') bad.push(m.text()) })
  await page.goto('/')
  await expect(page.locator('[x-cloak]')).toHaveCount(0)
  await page.locator('#search').fill('kataster')
  await page.waitForTimeout(300)
  // ResizeObserver loop je neškodné varování prohlížeče, ne chyba stránky.
  expect(bad.filter(t => !/ResizeObserver/.test(t))).toEqual([])
})
