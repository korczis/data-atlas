/* Minimální výřez Flowbite.
 *
 * Plný `flowbite.min.js` má 133 kB a nese accordion, carousel, datepicker,
 * modal, tabs a další věci, které tahle stránka nepoužívá — jediná Flowbite
 * komponenta v markupu je šuplík s filtry. Bundlujeme proto jen jeho.
 *
 * `initFlowbite` zůstává pod stejným jménem, protože šablona ho volá v init()
 * a docs/UI-RULES.md na něj odkazuje. Až přibude další Flowbite komponenta,
 * přidá se sem její initXxx — a lint_ui.py na to upozorní, protože kontroluje
 * dvojici "data atribut v markupu ↔ volání initFlowbite".
 */
import { initDrawers } from 'flowbite/lib/esm/components/drawer'

window.initFlowbite = () => {
  initDrawers()
}
