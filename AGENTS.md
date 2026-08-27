# Pokyny pro AI agenty

Než sáhneš na `src/template.html`, přečti si **[`docs/UI-RULES.md`](docs/UI-RULES.md)**.
Je to závazná část, ne doporučení: vynucuje ji `tools/lint_ui.py` a CI.

## Než něco pošleš dál

```bash
just check      # build + lint + testy + kontrola responzivity
```

Samotné `just build` nestačí — projde i s rozbitou integrací Flowbite,
protože ta selhává tiše.

## Rozvržení projektu

| Cesta | Co v ní je |
|---|---|
| `data/*.csv` | Zdroj pravdy. Stránka se staví z něj. |
| `src/template.html` | Markup + Alpine komponenta. Platí pro něj `docs/UI-RULES.md`. |
| `src/assets/` | Zdroje ikon a OG karty (`just assets` je přerenderuje) |
| `tools/` | Datový řetěz a build |
| `tests/` | `smoke` · `interact` · `meta` · `flowbite` |
| `static/` | Vygenerované ikony a OG karta (committnuté) |
| `.cache/`, `dist/` | Gitignorované. **Nikdy necommituj.** |

## Co si pohlídat

- **Počty nikdy nepiš ručně.** `142`, `17`, `53` se odvozují z CSV — v popisu
  stránky, na OG kartě i v testech. Ručně opsané číslo zestárne při první změně.
- **Do `data/` jen přes `tools/sanitize.py`.** Syrový výstup obsahuje osobní
  historii prohlížení a interní hostnames. Hostnames vlastní sítě patří do
  `config/private-hosts.txt`, který je mimo repozitář.
- **Flowbite `data-*` nepatří do `x-for`.** Důvod je v `docs/UI-RULES.md`;
  selhává to tiše, bez chyby v konzoli.
- **URL v katalogu ověřuj, nevymýšlej.** `just links` je od toho. Zdrojem
  pravdy je `tools/build_catalog.py`, ne `data/catalog.csv` — ten se generuje.
- **Nespoléhej na jsdom u layoutu.** Umí DOM, ne rozvržení. Přetečení do strany
  odhalí jedině `just responsive`.

## Flowbite

Používáme open-source Flowbite 2.5 (MIT). Referenční markup komponent je
v [`llms.txt`](https://raw.githubusercontent.com/themesberg/flowbite/refs/heads/main/llms.txt)
a [`llms-full.txt`](https://raw.githubusercontent.com/themesberg/flowbite/refs/heads/main/llms-full.txt).
Komponenty opisuj odtamtud, ne z paměti — třídy se mezi verzemi mění.
