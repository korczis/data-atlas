# Použité komponenty třetích stran

## Flowbite (open source)

Stránka staví na [Flowbite](https://flowbite.com/) 2.5 pod licencí MIT.
Bundluje se jen výřez, který markup skutečně používá — viz `src/js/flowbite-entry.js`.

Z open-source dokumentace (šuplík, dropdown, navbar, tabulka, toast a vzor
přepínače motivu) je markup **adaptovaný**, ne opsaný: přepínač má tři stavy
místo dvou a razí `data-theme` místo třídy `.dark`, protože artefakt se
vykresluje i ve stavu „podle systému".

## Vlajky zemí

Sprite `src/assets/flags.png` je poskládaný z [korczis/flags](https://github.com/korczis/flags),
kde jsou vlajky převzaté z [Wikimedia Commons](https://commons.wikimedia.org/)
a označené jako **public domain** — národní vlajky ve většině jurisdikcí
autorskoprávní ochraně nepodléhají.

Rozsahy `EU` a `GLOBAL` vlajku **nemají** a nesou textový odznak. Není to
jen estetika: nejsou to země a filtr země je přesná shoda, takže ten rozdíl
má být vidět. U emblému Evropské unie navíc platí pravidla užití, která se
sem netahají.

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
