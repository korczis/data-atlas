/** Odznaky u položky katalogu — jedna implementace pro obě stránky.
 *
 *  Byly dvě a rozešly se. Strojová dostupnost svítila na hlavní stránce
 *  modře (`primary`) a na stránkách zemí zeleně (`emerald`), odstíny se lišily
 *  (`-50` proti `-100`) a slovník taky (`bulk` proti `hromadně`). Tentýž odznak
 *  tedy znamenal totéž a vypadal jinak podle toho, kde se čtenář zrovna
 *  nacházel — což je přesně to, co barevná sémantika dělat nemá.
 *
 *  **Barva má stálý význam:**
 *
 *  | Barva | Znamená |
 *  |---|---|
 *  | `emerald` | data jdou ven strojově — API, OGC, hromadně, ke stažení |
 *  | `amber` | překážka v přístupu — registrace, poplatek, omezení |
 *  | `gray` | doplňující povaha zdroje — komerční, regionální |
 *
 *  `primary` se tu nepoužívá schválně: je to barva značky a vybraného stavu,
 *  a kdyby zároveň znamenala „má API", nedalo by se poznat, co je zvýrazněné
 *  a co je vlastnost.
 *
 *  Popisky se **nepíšou tady**. Berou se z číselníku, který cestuje v payloadu
 *  (`labels.data`, `labels.access`) a vzniká z `ACCESS`/`DATA_MODES`
 *  v `tools/build_catalog.py`, kde se zároveň validují povolené hodnoty.
 *  Hodnota a její název jsou totéž tvrzení a patří na jedno místo; tohle byla
 *  jejich třetí kopie.
 */

/** Hodnoty, které stojí za odznak. Zbytek je většina katalogu a psát ji na
 *  každý řádek je šum: „otevřený web bez API" nikomu nic neřekne. */
const MACHINE = ['bulk', 'api', 'ogc', 'download']
const BARRIER = ['registration', 'paid', 'restricted', 'mixed', 'search']
const KIND = { commercial: 'komerční', regional: 'regionální' }

const CLS = {
  machine: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  barrier: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  kind: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
}

/**
 * @param {object} row  řádek katalogu (`data`, `access`, `kind`)
 * @param {object} labels  `{ data: {...}, access: {...} }` z payloadu
 * @returns {{text: string, cls: string}[]}
 */
export function marks(row, labels) {
  const out = []
  const L = labels || {}
  if (MACHINE.includes(row.data)) {
    out.push({ text: (L.data || {})[row.data] || row.data, cls: CLS.machine })
  }
  if (BARRIER.includes(row.access)) {
    out.push({ text: (L.access || {})[row.access] || row.access, cls: CLS.barrier })
  }
  if (KIND[row.kind]) out.push({ text: KIND[row.kind], cls: CLS.kind })
  return out
}
