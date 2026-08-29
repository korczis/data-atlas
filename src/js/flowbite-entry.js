/* Alpine ↔ Flowbite: jedna vrstva, která je spojuje po životním cyklu.
 *
 * Flowbite se běžně zapíná funkcemi `initDrawers()` / `initDropdowns()`, které
 * **jednou** projdou DOM a navěsí chování na `data-*` atributy. S Alpine to
 * nesedí: Alpine vykresluje až po startu a při každém přefiltrování uzly zahodí
 * a vyrobí nové. Cokoli vzniklo po tom jediném skenu je v DOM, vypadá správně
 * a nedělá nic — bez chyby v konzoli. Proto tu dřív platil zákaz Flowbite
 * `data-*` uvnitř `x-for`: nešlo to opravit, šlo se tomu jen vyhnout.
 *
 * Tenhle soubor to řeší místo obcházení. Flowbite má vedle scannerů i běžné
 * třídy (`Dropdown`, `Drawer`) s `destroy()`. Když se instance vyrábí v Alpine
 * direktivě, vzniká přesně tehdy, kdy Alpine uzel vytvoří, a `cleanup()` ji
 * zruší přesně tehdy, kdy ho zahodí. Tím zmizí obojí: mrtvé komponenty
 * i dvojité navěšení, po kterém si dvě instance vzájemně ruší `toggle()`
 * a šuplík nejde zavřít.
 *
 * Použití v markupu:
 *
 *     <button x-flowbite:dropdown="'sort-dropdown'">     — cíl podle id
 *     <button x-flowbite:drawer="'sidebar'">             — přepíná šuplík
 *
 * Žádné `initFlowbite()` se nevolá; není co skenovat.
 */
import Drawer from 'flowbite/lib/esm/components/drawer'
import Dropdown from 'flowbite/lib/esm/components/dropdown'

/** Šuplík je jeden na cíl, ale spouštěčů může být víc (lišta, patička).
 *  Instance se proto počítá odkazy a ruší se, až odejde poslední spouštěč —
 *  jinak by zavření jednoho tlačítka odpojilo i ostatní. */
const drawers = new Map()

function acquireDrawer(id, target) {
  let entry = drawers.get(id)
  if (!entry) {
    entry = { instance: new Drawer(target, {}, { id, override: true }), users: 0 }
    drawers.set(id, entry)
  }
  entry.users += 1
  return entry
}

function releaseDrawer(id) {
  const entry = drawers.get(id)
  if (!entry) return
  entry.users -= 1
  if (entry.users <= 0) {
    entry.instance.destroyAndRemoveInstance()
    drawers.delete(id)
  }
}

const BINDINGS = {
  /** Dropdown si spouštěč naváže sám — konstruktor dostane obojí. */
  dropdown(el, target, id) {
    const instance = new Dropdown(target, el, {}, { id, override: true })
    return () => instance.destroyAndRemoveInstance()
  },

  /** Drawer se váže na cíl, ne na spouštěč, takže klik se navěšuje ručně. */
  drawer(el, target, id) {
    const entry = acquireDrawer(id, target)
    const onClick = (ev) => { ev.preventDefault(); entry.instance.toggle() }
    el.addEventListener('click', onClick)
    return () => { el.removeEventListener('click', onClick); releaseDrawer(id) }
  },
}

document.addEventListener('alpine:init', () => {
  window.Alpine.directive('flowbite', (el, { value, expression }, { evaluate, cleanup }) => {
    const bind = BINDINGS[value]
    if (!bind) {
      console.error(`x-flowbite: neznámá komponenta ${value === undefined ? '(chybí)' : value}`)
      return
    }
    // Cíl smí přijít výrazem (`'sidebar'`) i z aria-controls, které tam kvůli
    // přístupnosti stejně patří. Dvě místa pro tutéž informaci by se rozešla.
    const id = expression ? evaluate(expression) : el.getAttribute('aria-controls')
    const target = id && document.getElementById(id)
    if (!target) {
      // Tiché selhání je přesně to, čemu se tady celou dobu vyhýbáme.
      console.error(`x-flowbite:${value} — cíl #${id} v dokumentu není`)
      return
    }
    const undo = bind(el, target, id)
    // Konstruktory Flowbite sahají cíli na atributy — Drawer mu nastaví
    // aria-hidden. Direktiva je potomek, takže běží až po init() komponenty
    // a přepsala by, co si komponenta nastavila. Místo hádání pořadí to
    // ohlásí: kdo na tom stojí, se přepočítá, až je vazba hotová.
    document.dispatchEvent(new CustomEvent('flowbite:bound', {
      detail: { component: value, id, target },
    }))
    cleanup(undo)
  })
})
