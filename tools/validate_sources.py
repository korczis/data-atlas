#!/usr/bin/env python3
"""Ověří kurátorovaná data v data/sources/*.json dřív, než se z nich něco postaví.

Schéma hlídá už `build_catalog.py`, protože bez platných dat nemá co zapsat.
Tenhle skript přidává kontroly kvality, které build nezastaví, ale katalog
poškodí tiše: prázdný popis, popis „Oficiální web úřadu", datum ověření
z budoucnosti, dvě položky na tomtéž místě téhož webu.

Běží v `just check`, takže špatná data spadnou na stejném místě jako špatné UI.
"""
from __future__ import annotations

import ast, collections, datetime, json, re, sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_catalog import load_sources, load_taxonomy, domain  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Popis má odpovědět „proč to mám otevřít". Tyhle tvary neodpovídají nic.
EMPTY_PHRASES = re.compile(
    r"^(oficiální (web|stránk|portál)|webové stránky|domovská stránka|portál úřadu)\S*\s*\.?$",
    re.I)


def main() -> int:
    topic_meta, _, places, _ = load_taxonomy()
    sources = load_sources()
    today = datetime.date.today()

    errors, warnings = [], []
    seen_path = {}
    per_country_domain = collections.defaultdict(list)

    for s in sources:
        where = f"{s.get('country')}:{s.get('id')}"
        desc = (s.get("desc") or "").strip()
        if len(desc) < 40:
            errors.append(f'{where}: popis má {len(desc)} znaků — na „proč to otevřít“ to nestačí')
        if EMPTY_PHRASES.match(desc):
            errors.append(f"{where}: popis nic neříká — {desc!r}")
        if desc.endswith(("..", "…")):
            warnings.append(f"{where}: popis končí výpustkou")

        try:
            v = datetime.date.fromisoformat(s.get("verified", ""))
            if v > today:
                errors.append(f"{where}: datum ověření {v} je v budoucnosti")
            elif (today - v).days > 730:
                warnings.append(f"{where}: ověřeno naposledy {v}")
        except ValueError:
            errors.append(f"{where}: 'verified' není datum ve tvaru RRRR-MM-DD")

        u = urlsplit(s["url"])
        key = (u.hostname or "").lower().removeprefix("www.") + u.path.rstrip("/")
        if key in seen_path:
            errors.append(f"{where}: stejné místo jako {seen_path[key]} (liší se jen schéma nebo lomítko)")
        seen_path[key] = where
        per_country_domain[(s["country"], domain(s["url"]))].append((s["id"], u.path.rstrip("/")))

        if s.get("data") == "sw" and s.get("topic") not in (
                "maplibs", "spatialdb", "routing", "formats", "geocoding", "osint", "learning"):
            warnings.append(f"{where}: 'sw' u datového tématu '{s.get('topic')}' — je to opravdu nástroj?")

    # Jedna doména smí nést víc položek — geoportál, katastrální služba a katalog
    # WFS jsou tři různé věci na jednom webu. Podezřelé je něco jiného: mít
    # v katalogu kořen domény *a zároveň* několik jeho podstránek. To bývá
    # rozcestník rozepsaný na položky, které vedou k témuž.
    for (country, dom), items in per_country_domain.items():
        deep = [i for i, path in items if path]
        if any(not path for _, path in items) and len(deep) >= 4:
            warnings.append(f"{country}: {dom} má v katalogu kořen i {len(deep)} podstránek — "
                            "není to jeden rozcestník rozepsaný na položky? " + ", ".join(sorted(deep)[:5]))

    # Hledá se v kódu, ne v komentářích: docstring, který ten soubor jmenuje
    # a vysvětluje, proč se na něj nesahá, je v pořádku.
    private = ("raw.json", "candidates.json")
    for name in ("build_catalog.py", "build_page.py", "build_docs.py", "check_links.py"):
        tree = ast.parse((ROOT / "tools" / name).read_text(encoding="utf-8"))
        docstrings = {ast.get_docstring(n, clean=False) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
                continue
            if node.value in docstrings:
                continue
            for token in private:
                if token in node.value:
                    errors.append(
                        f"tools/{name}: sahá na {token} — veřejný build musí projít bez .cache/")

    for e in errors:
        print(f"  ✗ {e}")
    for w in warnings:
        print(f"  ⚠ {w}")
    print(f"validate_sources: {len(sources)} zdrojů · {len(errors)} chyb · {len(warnings)} varování")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
