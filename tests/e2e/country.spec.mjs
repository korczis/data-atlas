/** Stránky zemí a rozcestník `zeme/`.
 *
 *  Seznam se bere ze sitemapy, ne z ručního výčtu — přidaná země se tak
 *  otestuje sama, místo aby test tvrdil, že je pokryto všechno.
 */
import { test, expect } from '@playwright/test'
import { countryPaths } from './pages.mjs'

const paths = countryPaths()

test('rozcestník zemí vede na existující stránky', async ({ page }) => {
  await page.goto('/zeme/')
  await expect(page.getByRole('heading', { level: 1, name: 'Země' })).toBeVisible()
  const links = page.locator('main a[href]')
  const count = await links.count()
  expect(count).toBe(paths.length)
  // Namátkou první tři: rozcestník, který odkazuje do prázdna, je horší
  // než rozcestník, který chybí.
  for (const i of [0, 1, 2]) {
    const href = await links.nth(i).getAttribute('href')
    const res = await page.request.get(new URL(href, page.url()).toString())
    expect(res.status(), href).toBe(200)
  }
})

test('každá stránka země se načte a vykreslí data', async ({ page }) => {
  test.setTimeout(120_000)
  const broken = []
  for (const p of paths) {
    const res = await page.goto(p)
    if (!res || res.status() !== 200) { broken.push(`${p}: HTTP ${res && res.status()}`); continue }
    const h1 = await page.getByRole('heading', { level: 1 }).first().innerText().catch(() => '')
    const n = await page.locator('[data-row]:visible, [data-card]:visible').count()
    if (!h1.trim()) broken.push(`${p}: chybí nadpis`)
    if (n === 0) broken.push(`${p}: nevykreslil se ani jeden řádek`)
  }
  expect(broken, `${paths.length} stránek`).toEqual([])
})

test.describe('Česko jako zástupce', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/cz/')
    await expect(page.locator('[x-cloak]')).toHaveCount(0)
  })

  test('drobečky vedou zpět do katalogu', async ({ page }) => {
    await expect(page.getByRole('navigation', { name: 'Drobečková navigace' })).toBeVisible()
    await page.getByRole('link', { name: 'Katalog', exact: true }).click()
    await expect(page).toHaveURL(/\/$/)
  })

  test('filtr tématu zúží tabulku', async ({ page }) => {
    const before = await page.locator('[data-row]:visible, [data-card]:visible').count()
    await page.locator('#topicFilterButton').click()
    await expect(page.locator('#topicFilter')).toBeVisible()
    await page.locator('#topicFilter button').nth(1).click()
    await expect.poll(() => page.locator('[data-row]:visible, [data-card]:visible').count()).toBeLessThan(before)
  })

  test('vazby mezi tématy nabídnou další krok', async ({ page }) => {
    await page.goto('/cz/#topic=companies')
    await expect(page.locator('[x-cloak]')).toHaveCount(0)
    const strip = page.locator('[x-show*="relatedTopics.length || supraForTopic"]')
    await expect(strip).toBeVisible()
    // Nabídnuté téma musí něco nést, jinak je to slib, co se nenaplní.
    const chip = strip.locator('button').first()
    await expect(chip).toBeVisible()
    await chip.click()
    await expect.poll(() => page.locator('[data-row]:visible, [data-card]:visible').count()).toBeGreaterThan(0)
  })

  test('nadnárodní zdroje odkazují zpět do katalogu', async ({ page }) => {
    await page.goto('/cz/#topic=companies')
    await expect(page.locator('[x-cloak]')).toHaveCount(0)
    const link = page.locator('a[href*="country=EU"]').first()
    await expect(link).toBeVisible()
    await expect(link).toHaveAttribute('href', /#country=EU&topic=companies/)
  })

  test('stránkování chodí tam i zpět', async ({ page }) => {
    const next = page.getByRole('button', { name: 'Další' })
    const prev = page.getByRole('button', { name: 'Předchozí' })
    await expect(prev).toBeDisabled()
    await next.click()
    await expect.poll(() => page.evaluate(() => location.hash)).toContain('page=2')
    await prev.click()
    await expect.poll(() => page.evaluate(() => location.hash)).not.toContain('page=2')
  })

  test('řazení kliknutím na hlavičku', async ({ page, viewport }) => {
    if (viewport.width < 768) test.skip(true, 'pod md se místo tabulky vykreslují karty')
    const first = () => page.locator('[data-row] a').first().innerText()
    const before = await first()
    await page.locator('thead button').first().click()
    await expect.poll(async () => await first()).not.toBe(before)
  })

  test('přepínač motivu přepne motiv', async ({ page }) => {
    const root = page.locator('html')
    const before = await root.getAttribute('data-theme')
    await page.locator('button[aria-label^="Motiv"]').click()
    await expect.poll(() => root.getAttribute('data-theme')).not.toBe(before)
  })

  test('stránka nikam nepřeteče do strany', async ({ page }) => {
    const overflow = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(0)
  })
})
