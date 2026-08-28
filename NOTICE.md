# Použité komponenty třetích stran

## Flowbite (open source)

Stránka staví na [Flowbite](https://flowbite.com/) 2.5 pod licencí MIT.
Bundluje se jen výřez, který markup skutečně používá — viz `src/js/flowbite-entry.js`.

Z open-source dokumentace (šuplík, dropdown, navbar, tabulka, toast a vzor
přepínače motivu) je markup **adaptovaný**, ne opsaný: přepínač má tři stavy
místo dvou a razí `data-theme` místo třídy `.dark`, protože artefakt se
vykresluje i ve stavu „podle systému".

## Flowbite Pro

Rozvržení aplikace (horní lišta + postranní panel + hlavní obsah), záhlaví
stránky s nástrojovou lištou, vzhled tabulky a lepivá souhrnná lišta jsou
**adaptované** z Flowbite Pro Admin Dashboard (HTML), který vlastní autor
repozitáře pod [EULA Flowbite](https://flowbite.com/license/).

Co to v praxi znamená pro tenhle repozitář:

- **Adaptujeme vzory** do vlastní šablony s vlastním obsahem. To licence
  pro open-source projekty připouští — hlavním účelem repozitáře není
  redistribuce Flowbite Pro.
- **Nekopírujeme sem soubory Flowbite Pro.** Žádný `vendor/` adresář, žádné
  celé stránky z balíku. Vytvářet veřejný repozitář Pro elementů licence
  výslovně zakazuje.

Kdo chce stejné bloky použít, potřebuje vlastní licenci Flowbite Pro.
Paleta `primary` v `src/tailwind.config.js` odpovídá hodnotám z jejich
konfigurace (shodné s Tailwind blue) — barvy jako takové licenci nepodléhají.
