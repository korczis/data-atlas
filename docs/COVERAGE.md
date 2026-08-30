<!-- Generováno `just docs` — needituj ručně. -->

# Pokrytí

Matice země × rodina témat. Číslo je počet zdrojů, prázdné pole znamená, že v katalogu k té rodině pro tu zemi nic není — buď to ještě nikdo nedohledal, nebo tam veřejně nic takového neexistuje. Ověřená druhá možnost se zapisuje do [`data/gaps.json`](../data/gaps.json); tady ji nese `·`, na stránce šrafování.

`·` znamená, že doložená je **každá** položka za tou buňkou. Sloupec sdružující víc témat ho proto dostane až tehdy, když je doložený celý — jedna doložená absence ve čtyřtématovém sloupci se schová do prázdna. Prázdná buňka tedy znamená „díra, nebo zčásti doložená díra“; přesné rozlišení po tématech je na stránce a v [`data/gaps.json`](../data/gaps.json).

Sloupce sdružují příbuzná témata; úplné členění je v [`data/topics.json`](../data/topics.json). Poslední sloupec `Ostatní` nese témata, která do žádné rodiny nespadla (nástroje, formáty, OSINT, archivy), takže Σ je vždy součet viditelných buněk.

| Země | Geo | Katastr | Adresy | Doprava | Prostředí | Statistika | Open data | Sbírka | Zakázky | Výdaje | Firmy | Majitelé | Závěrky | Insolvence | Soudy | Regulace | Nemovitosti | Riziko | Transp. | Ostatní | Σ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `EU` Evropská unie | 5 |  |  | 2 | 10 | 5 | 2 | 2 | 4 | 5 | 4 |  |  |  | 1 | 6 |  | 6 | 3 | 3 | **58** |
| `GLOBAL` Celosvětové | 16 |  | 1 | 2 | 5 | 7 |  |  |  |  | 2 |  |  |  |  |  |  | 5 |  | 92 | **130** |
| `AT` Rakousko | 3 | 2 | 1 | 2 | 4 | 2 | 1 | 2 | 1 | 4 | 2 | 1 | 1 | 1 | 3 | 8 | 1 | 2 | 2 | 4 | **47** |
| `BE` Belgie | 6 | 1 | 1 | 1 | 2 | 1 | 2 | 1 | 1 | 3 | 2 | 1 | 1 | 1 | 4 | 8 | 1 | 2 | 2 | 3 | **44** |
| `BG` Bulharsko | 2 | 3 | 1 | 1 | 3 | 1 | 1 | 2 | 2 | 3 | 1 | 1 | 1 | 1 | 4 | 9 |  | 2 | 1 | 3 | **42** |
| `HR` Chorvatsko | 2 | 2 | 1 | 2 | 3 | 2 | 1 | 2 | 1 | 2 | 2 | 1 | 1 | 1 | 2 | 7 | 1 | 2 | 1 | 3 | **39** |
| `CY` Kypr | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 3 | 1 | 1 | · | 1 | 2 | 9 | 1 | 1 | 1 | 2 | **33** |
| `CZ` Česko | 7 | 5 | 2 | 12 | 10 | 3 | 1 | 3 | 3 | 6 | 4 | 1 | 1 | 2 | 4 | 10 | 8 | 7 | 3 | 9 | **101** |
| `DK` Dánsko | 3 | 1 | 1 | 2 | 3 | 2 | 1 | 2 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 9 | 2 | 2 | 1 | 3 | **41** |
| `EE` Estonsko | 2 | 1 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 3 | 8 | 1 | 2 | 1 | 3 | **37** |
| `FI` Finsko | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 4 | 2 | 1 | 1 | 1 | 1 | 7 | 1 | 2 | 1 | 4 | **37** |
| `FR` Francie | 4 | 2 | 1 | 1 | 4 | 3 | 1 | 2 | 2 | 3 | 3 | 1 | 2 | 1 | 3 | 10 | 1 | 3 | 1 | 3 | **51** |
| `DE` Německo | 4 | 1 | 1 | 2 | 5 | 4 | 1 | 2 | 1 | 3 | 1 | 1 | 1 | 1 | 3 | 9 | 1 | 3 | 3 | 3 | **50** |
| `GR` Řecko |  | 1 | 1 | 1 | 2 | 1 | 2 | 2 | 1 | 2 | 2 | 1 | 1 | · | 1 | 8 | 1 | 1 | 2 | 3 | **33** |
| `HU` Maďarsko | 2 | 2 | 1 | 2 | 4 | 1 | 1 | 1 | 2 | 3 | 1 | 1 | 1 | 1 | 4 | 8 | 1 | 3 | 1 | 3 | **43** |
| `IE` Irsko | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 8 | 1 | 2 | 1 | 3 | **35** |
| `IT` Itálie | 4 | 2 | 1 | 2 | 3 | 2 | 1 | 2 | 2 | 4 | 1 | 1 | 1 | · | 3 | 9 | 1 | 2 | 3 | 2 | **46** |
| `LV` Lotyšsko | 2 | 2 | 1 | 1 | 2 | 2 | 1 | 2 | 1 | 3 | 2 | 1 | 1 | 1 | 2 | 6 | 1 | 2 | 1 | 3 | **37** |
| `LT` Litva | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 2 | 8 | 1 | 2 | 1 | 3 | **35** |
| `LU` Lucembursko | 2 | 1 | 1 | 2 | 2 | 1 | 2 | 1 | 1 | 3 | 1 | 1 | 1 | 1 | 1 | 7 | 1 | 2 | 1 | 3 | **35** |
| `MT` Malta | 1 | 1 | 1 | 1 | 2 | 1 | 2 | 1 | 1 | 3 | 1 | 1 | 1 | · | 1 | 8 | 1 | 1 | 1 | 3 | **32** |
| `NL` Nizozemsko | 3 | 1 | 1 | 2 | 3 | 2 | 2 | 2 | 1 | 4 | 1 | 1 | 1 | 1 | 2 | 7 | 1 | 2 | 2 | 3 | **42** |
| `PL` Polsko | 7 | 3 | 2 | 5 | 5 | 3 | 1 | 3 | 2 | 3 | 5 | 1 | 3 | 1 | 4 | 8 | 1 | 4 | 2 | 3 | **66** |
| `PT` Portugalsko | 3 | 1 | 1 | 1 | 4 | 2 | 1 | 1 | 1 | 3 | 2 | 1 | 1 | 1 | 2 | 9 | 1 | 2 | 2 | 3 | **42** |
| `RO` Rumunsko |  | 1 | 1 | 1 | 2 | 2 | 1 | 1 | 1 | 2 | 2 | 1 | 1 | · | 3 | 7 |  | 3 | 1 | 2 | **32** |
| `SK` Slovensko | 2 | 2 | 1 | 1 | 4 | 2 | 1 | 1 | 2 | 3 | 3 | 1 | 2 | 1 | 2 | 8 | 1 | 2 | 1 | 3 | **43** |
| `SI` Slovinsko | 2 | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 2 | 3 | 1 | 1 | 1 | 1 | 3 | 9 | 1 | 2 | 1 | 3 | **40** |
| `ES` Španělsko | 4 | 1 | 1 | 2 | 4 | 1 | 1 | 1 | 1 | 3 | 2 | 1 | 1 | 1 | 3 | 7 | 1 | 3 | 1 | 3 | **42** |
| `SE` Švédsko | 2 | 1 | 1 | 2 | 2 | 1 | 1 | 2 | 1 | 3 | 2 | 1 | 1 | 1 | 1 | 9 | 1 | 2 | 1 | 3 | **38** |
| `GB` Spojené království |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |  | 1 |  | 1 | **3** |
| `US` Spojené státy | 5 |  |  |  | 1 |  | 2 |  |  |  |  |  |  |  |  |  |  | 1 |  | 4 | **13** |

**Členských států v katalogu:** 27 z 27.

## Podle témat

| Téma | Zdrojů | Zemí | Z toho úředních | S API nebo bulk |
|---|--:|--:|--:|--:|
| Geoportály a NSDI | 43 | 24 | 42 | 37 |
| Katastr a pozemkové knihy | 42 | 27 | 42 | 26 |
| Adresy a územní členění | 30 | 28 | 26 | 22 |
| Ortofoto, výškopis, topografie | 26 | 26 | 25 | 15 |
| Životní prostředí, geologie, rizika | 64 | 29 | 61 | 35 |
| Doprava a infrastruktura | 57 | 29 | 52 | 36 |
| Remote sensing / rastr | 15 | 3 | 7 | 14 |
| Globální referenční geodata | 17 | 8 | 8 | 15 |
| Otevřená data | 37 | 29 | 36 | 31 |
| Statistika a demografie | 59 | 29 | 54 | 46 |
| Legislativa a věstníky | 45 | 28 | 41 | 21 |
| Veřejné zakázky | 40 | 28 | 39 | 18 |
| Rozpočty, dotace, výdaje | 90 | 28 | 87 | 29 |
| Obchodní rejstříky | 55 | 30 | 46 | 28 |
| Skuteční majitelé | 27 | 27 | 27 | 3 |
| Účetní závěrky a listiny | 30 | 26 | 29 | 9 |
| Insolvence a exekuce | 24 | 23 | 24 | 2 |
| Soudy a judikatura | 66 | 28 | 63 | 4 |
| Průmyslové vlastnictví | 33 | 29 | 33 | 4 |
| Regulace a licencované subjekty | 226 | 28 | 226 | 45 |
| Nemovitosti a trh | 33 | 25 | 28 | 17 |
| Sankce a compliance | 3 | 2 | 2 | 2 |
| Kriminalita, IZS, bezpečnost | 41 | 31 | 37 | 11 |
| Kyberbezpečnost a CERT | 32 | 25 | 30 | 10 |
| Počasí a klima | 37 | 30 | 32 | 26 |
| Transparentnost, volby, lobbing | 42 | 28 | 41 | 31 |
| OSINT a investigace | 10 | 2 | 0 | 5 |
| Archivy a historické zdroje | 61 | 30 | 54 | 15 |
| Gazetteery a geokódování | 10 | 3 | 1 | 9 |
| Mapové knihovny a basemapy | 15 | 1 | 0 | 5 |
| Spatial DB a analytika | 23 | 1 | 0 | 0 |
| Routing a síťová analýza | 11 | 1 | 0 | 2 |
| Formáty, projekce, standardy | 13 | 1 | 0 | 2 |
| Učení a komunita | 10 | 1 | 0 | 1 |

## Klasifikace

| Přístup | Zdrojů |
|---|--:|
| `open` | 1218 |
| `mixed` | 63 |
| `registration` | 39 |
| `restricted` | 25 |
| `paid` | 22 |

| Data | Zdrojů |
|---|--:|
| `search` | 424 |
| `api` | 277 |
| `bulk` | 217 |
| `none` | 164 |
| `download` | 157 |
| `ogc` | 82 |
| `sw` | 46 |

| Vydavatel | Zdrojů |
|---|--:|
| `official` | 1112 |
| `ngo` | 105 |
| `intl` | 64 |
| `commercial` | 46 |
| `research` | 23 |
| `regional` | 17 |
