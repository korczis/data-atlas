#!/usr/bin/env python3
"""Aplikuje patch-list z auditu do tools/build_catalog.py.

Zdrojem pravdy pro katalog je seznam `C` v build_catalog.py, ne vygenerované
CSV. Ruční editace stovky řádků je práce pro stroj — a hlavně reprodukovatelná:
patch se dá projít, zamítnout po položkách a znovu spustit.

Vstup je JSON ve tvaru, který vrací workflow `geodata-atlas-audit`:

  {"additions":  [{"category","web","dom","url","popis"}, ...],
   "corrections":[{"dom","field","proposed"}, ...],
   "removals":   [{"dom","why"}, ...]}
"""
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "tools" / "build_catalog.py"

FIELD_INDEX = {"web": 1, "dom": 2, "popis": 3, "url": 4}


def entry_re(dom: str) -> re.Pattern:
    """Najde řádek položky podle domény ve třetím poli n-tice."""
    return re.compile(r'^\(("(?:[^"\\]|\\.)*",\s*){2}"' + re.escape(dom) + r'",.*\),$',
                      re.M)


def parse_entry(line: str) -> list[str]:
    return re.findall(r'"((?:[^"\\]|\\.)*)"', line)


def render(parts: list[str]) -> str:
    return "(" + ",".join(f'"{p}"' for p in parts) + "),"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("patch", type=Path, help="JSON s patch-listem")
    ap.add_argument("--dry-run", action="store_true", help="jen vypsat, nezapisovat")
    args = ap.parse_args()

    patch = json.loads(args.patch.read_text(encoding="utf-8"))
    src = BUILD.read_text(encoding="utf-8")
    applied, skipped = [], []

    # ── odebrání ─────────────────────────────────────────────────────────────
    for rem in patch.get("removals", []):
        m = entry_re(rem["dom"]).search(src)
        if not m:
            skipped.append(f"odebrání {rem['dom']}: položka nenalezena")
            continue
        src = src.replace(m.group(0) + "\n", "")
        applied.append(f"− {rem['dom']}  ({rem['why']})")

    # ── opravy ───────────────────────────────────────────────────────────────
    # Položka se v souboru hledá podle domény, takže přejmenování domény musí
    # jít až po ostatních opravách téže položky — jinak se pro ně klíč ztratí.
    corrections = sorted(patch.get("corrections", []),
                         key=lambda c: c["field"] == "dom")
    for cor in corrections:
        idx = FIELD_INDEX.get(cor["field"])
        if idx is None:
            skipped.append(f"oprava {cor['dom']}: neznámé pole {cor['field']}")
            continue
        m = entry_re(cor["dom"]).search(src)
        if not m:
            skipped.append(f"oprava {cor['dom']}: položka nenalezena")
            continue
        parts = parse_entry(m.group(0))
        if len(parts) != 5:
            skipped.append(f"oprava {cor['dom']}: nečekaný tvar n-tice")
            continue
        old = parts[idx]
        parts[idx] = cor["proposed"].replace('"', "'")
        src = src.replace(m.group(0), render(parts))
        applied.append(f"~ {cor['dom']} [{cor['field']}]\n    z:  {old[:88]}\n    na: {parts[idx][:88]}")

    # ── doplnění ─────────────────────────────────────────────────────────────
    # Vkládá se za poslední existující položku téže kategorie, aby zůstalo
    # seskupení podle kategorií, na kterém stojí generovaný markdown i UI.
    for add in patch.get("additions", []):
        if entry_re(add["dom"]).search(src):
            skipped.append(f"doplnění {add['dom']}: doména už v katalogu je")
            continue
        cat = add["category"]
        last = None
        for m in re.finditer(r'^\("' + re.escape(cat) + r'",.*\),$', src, re.M):
            last = m
        if last is None:
            skipped.append(f"doplnění {add['dom']}: kategorie '{cat}' nenalezena")
            continue
        line = render([cat, add["web"], add["dom"],
                       add["popis"].replace('"', "'"), add["url"]])
        src = src[:last.end()] + "\n" + line + src[last.end():]
        applied.append(f"+ {add['dom']}  →  {cat}")

    print(f"aplikováno {len(applied)}, přeskočeno {len(skipped)}\n")
    for a in applied:
        print("  " + a)
    if skipped:
        print("\n  přeskočeno:")
        for s in skipped:
            print("    " + s)

    if args.dry_run:
        print("\n(dry-run, nic se nezapsalo)")
    else:
        BUILD.write_text(src, encoding="utf-8")
        print(f"\nzapsáno do {BUILD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
