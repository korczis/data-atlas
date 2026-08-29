/** Seznam stránek se odvozuje z buildu, nepíše se rukou.
 *
 *  Ručně psaný seznam by při přidání země zůstal pozadu a test by tvrdil,
 *  že je pokryto všechno, přestože nová stránka nikdy neběžela. Čte se proto
 *  `dist/sitemap.xml`, což je zároveň to, co se říká vyhledávačům — když
 *  stránka chybí tam, chybí i v testu, a obojí je vada.
 */
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const DIST = path.join(ROOT, 'dist')

export function sitemapPaths() {
  const xml = path.join(DIST, 'sitemap.xml')
  if (!existsSync(xml)) throw new Error('chybí dist/sitemap.xml — spusť `just build`')
  const locs = [...readFileSync(xml, 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1])
  if (!locs.length) throw new Error('sitemapa je prázdná')
  // build_page.py sitemapu **zakládá** s jedinou adresou, plnou píše až
  // build_places.py. Po částečném buildu by se tedy testy tvářily, že
  // prošly, a nepodívaly se přitom na jedinou stránku země. Zelená od
  // brány, která nic neviděla, je horší než červená.
  if (locs.length < 2) {
    throw new Error(`sitemapa má ${locs.length} adresu — build je neúplný, `
      + 'spusť `just build` (build_places.py sitemapu přepisuje)')
  }
  // Z absolutní adresy zbude cesta, kterou lze servírovat lokálně.
  return locs.map(u => new URL(u).pathname.replace(/^\/[^/]+/, '') || '/')
}

/** Stránky zemí bez rozcestníku a bez hlavní stránky. */
export function countryPaths() {
  return sitemapPaths().filter(p => p !== '/' && p !== '/zeme/')
}

export { DIST, ROOT }
