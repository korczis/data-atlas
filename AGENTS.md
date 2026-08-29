# Pokyny pro AI agenty

Než sáhneš na `src/template.html` nebo `src/country.html`, přečti si
**[`docs/UI-RULES.md`](docs/UI-RULES.md)**. Je to závazná část, ne doporučení:
vynucuje ji `tools/lint_ui.py` a CI, a to nad oběma šablonami.

Než přidáš zemi nebo zdroj do katalogu, přečti si
**[`docs/EU-EXPANSION-PLAN.md`](docs/EU-EXPANSION-PLAN.md)** — je tam schéma,
číselníky a pravidla pro klasifikaci přístupu.

## Než něco pošleš dál

```bash
just check      # validate + catalog + build + lint + testy + responzivita + a11y
```

Samotné `just build` nestačí — projde i s rozbitou integrací Flowbite,
protože ta selhává tiše.

## Rozvržení projektu

| Cesta | Co v ní je |
|---|---|
| `data/sources/*.json` | **Zdroj pravdy.** Kurátorované zdroje, jeden soubor na zemi nebo rozsah. |
| `data/topics.json`, `data/countries.json` | Číselníky témat a zemí; pořadí klíčů je pořadí v UI. |
| `data/provenance.csv` | Doložení z prohlížeče, klíčované `id`. Generuje `tools/build_provenance.py`. |
| `data/catalog.csv`, `data/longlist.csv` | **Generované.** Stránka a dokumentace se staví z nich. |
| `src/template.html` | Markup + Alpine komponenta hlavní stránky. Platí pro něj `docs/UI-RULES.md`. |
| `src/country.html`, `src/js/place.js` | Druhá šablona: stránka jedné země. Platí pro ni **týž** `docs/UI-RULES.md`. |
| `src/input.css` | Základ sdílený oběma šablonami — pozadí, `x-cloak`, fokus, redukovaný pohyb. |
| `src/assets/` | Zdroje ikon a OG karty (`just assets` je přerenderuje) |
| `tools/` | Datový řetěz a build |
| `tests/` | `smoke` · `interact` · `meta` · `flowbite` · `places` |
| `static/` | Vygenerované ikony a OG karta (committnuté) |
| `.cache/`, `dist/` | Gitignorované. **Nikdy necommituj.** |

## Co si pohlídat

- **Zdroj pravdy je `data/sources/*.json`, ne `data/catalog.csv`.** CSV,
  `docs/CATALOG.md` i `docs/COVERAGE.md` se generují — ruční úprava se ztratí
  při příštím `just catalog`.
- **Počty nikdy nepiš ručně.** Odvozují se z CSV — v popisu stránky, na OG kartě,
  v horní liště i v testech. Ručně opsané číslo zestárne při první změně.
- **Veřejný build nesmí sáhnout na `.cache/`.** Kurátorovaný katalog musí jít
  přegenerovat na čistém klonu bez cizího Chrome profilu; osobní export čte
  jedině `tools/build_provenance.py` a `tools/build_longlist.py`.
  Hlídá to `tools/validate_sources.py`.
- **Do `data/longlist.csv` jen přes `tools/sanitize.py`.** Syrový výstup obsahuje
  osobní historii prohlížení a interní hostnames. Hostnames vlastní sítě patří
  do `config/private-hosts.txt`, který je mimo repozitář.
- **Flowbite se váže direktivou `x-flowbite`, ne `data-*` atributy.** Instanci
  vyrábí `src/js/flowbite-entry.js` v okamžiku, kdy Alpine uzel vytvoří, a ruší
  ji, když ho zahodí. `data-*` atributy ani `initFlowbite()` do projektu
  nepatří — nic je neskenuje, takže by tiše nedělaly nic. Vynucuje to pravidlo
  `flowbite/binding`, důvod je v `docs/UI-RULES.md`.
- **Stránka není jen `index.html`.** Vedle ní stojí `dist/<kód>/` pro každou
  zemi a rozcestník `dist/zeme/`, které staví `tools/build_places.py` ze stejných
  dat. Sitemapu píše až on — `build_page.py` ji zakládá s jedinou adresou.
  Kdo přidá zemi, nemusí dělat nic navíc; kdo sáhne na runtime, musí myslet
  na to, že ho stránky zemí načítají jako sdílený soubor z `dist/assets/`.
- **URL v katalogu ověřuj, nevymýšlej.** `just links --changed` projde jen to,
  co jsi přidal; `just links` projde všechno.
- **Veřejné vyhledávání není otevřená data.** Klasifikace `access` a `data` má
  říkat pravdu o tom, co se z toho zdroje dá reálně dostat.
- **Nespoléhej na jsdom u layoutu.** Umí DOM, ne rozvržení. Přetečení do strany
  odhalí jedině `just responsive`.

## Flowbite

Používáme open-source Flowbite 2.5 (MIT). Referenční markup komponent je
v [`llms.txt`](https://raw.githubusercontent.com/themesberg/flowbite/refs/heads/main/llms.txt)
a [`llms-full.txt`](https://raw.githubusercontent.com/themesberg/flowbite/refs/heads/main/llms-full.txt).
Komponenty opisuj odtamtud, ne z paměti — třídy se mezi verzemi mění.
