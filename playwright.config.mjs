/** Playwright: prokliká hotové stránky v opravdovém prohlížeči.
 *
 *  Proč vedle jsdom testů: jsdom umí DOM, ne rozvržení ani skutečné události.
 *  Několikrát se v téhle kodbázi stalo, že jsdom test prošel a stránka byla
 *  přitom rozbitá — `x-show` se v něm chová jinak než v prohlížeči a klik
 *  přes `dispatchEvent` není totéž co klik uživatele. Tyhle testy jezdí
 *  v Chrome a klikají doopravdy.
 *
 *  Bere se **systémový Chrome** (`channel: 'chrome'`), ne stažený Chromium:
 *  je to týž prohlížeč, ve kterém měří `check_responsive.py`, `check_a11y.py`
 *  i `check_typography.py`, a ušetří to 150 MB v CI i na disku.
 *
 *  Servíruje se `dist/` přes HTTP, ne přes `file://`. Stránky zemí načítají
 *  sdílený runtime relativně a pod `file://` se chovají jinak než v ostrém
 *  provozu — testovat něco jiného, než co jede na webu, nemá smysl.
 */
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'line' : [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8123',
    trace: 'retain-on-failure',
    channel: 'chrome',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], channel: 'chrome',
                              viewport: { width: 1280, height: 900 } } },
    { name: 'mobil', use: { ...devices['Desktop Chrome'], channel: 'chrome',
                            viewport: { width: 390, height: 844 }, isMobile: false } },
  ],
  webServer: {
    command: 'python3 -m http.server 8123 --directory dist --bind 127.0.0.1',
    url: 'http://127.0.0.1:8123/',
    // Nikdy se needoptuje cizí server. `reuseExistingServer: true` převezme
    // *jakýkoli* proces na tom portu — i takový, který servíruje úplně jiný
    // adresář — a testy pak tiše měří cizí stránku. Stalo se to při dvou
    // souběžných sezeních nad týmž `dist/`, ale zasáhlo by to i vývojáře,
    // kterému na 8123 běží něco nesouvisejícího.
    //
    // S `false` Playwright na obsazeném portu spadne s hláškou o portu.
    // Chyba, které se dá věřit, je lepší než zelená, které se věřit nedá.
    reuseExistingServer: false,
    stdout: 'ignore',
    stderr: 'pipe',
  },
})
