#!/usr/bin/env python3
"""Vyrobí syrový long list kandidátů z .cache/candidates.json.

Long list je to, co prošlo keyword filtrem nad historií prohlížeče, ale ne
kurací — je v něm šum a je v něm i soukromí. Zůstává proto v .cache/, která
je v .gitignore; do data/ ho pustí až `tools/sanitize.py`.

Dřív tenhle krok viselo na konci build_catalog.py. Katalog se ale mezitím
osamostatnil na committnutých datech a nemá důvod sahat na osobní historii —
long list je jediná část řetězu, která ji pořád potřebuje.
"""
import collections, csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"

# Domény, které v geo long listu nemají co dělat: přihlašování, sociální sítě,
# vývojářské nástroje a reklamní trackery. Filtr je hrubý schválně — jemné
# rozhodování dělá až sanitize.py, který má allowlist.
NOISE = re.compile(
    r"google\.com|accounts\.|signin|login|auth|aws\.amazon|slack|atlassian|microsoft|claude|"
    r"openai|chatgpt|facebook|linkedin|youtube|spotify|github|gitlab|bitbucket|docusign|"
    r"stripe|godaddy|localhost|ngrok|proton|icloud|apple|netflix|zoom|revolut|temu|ebay|"
    r"cloudflare|docker|tailscale|awstrack|twimg|licdn|fbcdn|afcdn|slack-edge|gemius|go2cloud",
    re.I)


def main() -> int:
    src = CACHE / "candidates.json"
    if not src.exists():
        print(f"  {src.relative_to(ROOT)} is missing — run `just extract` and `just scan` first")
        return 1
    cand = json.loads(src.read_text(encoding="utf-8"))
    with (CACHE / "longlist.raw.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Doména", "Návštěvy", "Unikátních URL", "V záložkách", "Z historie",
                    "Poslední návštěva", "Ukázkový titulek", "Ukázková URL"])
        n = 0
        for d, e in cand.items():
            if NOISE.search(d):
                continue
            t = collections.Counter(e["titles"]).most_common(1)
            w.writerow([d, e["visits"], len(e["urls"]), e["bm"], e["hist"], e["last"][:10],
                        t[0][0] if t else "", sorted(e["urls"])[0][:150]])
            n += 1
    print(f"long list: {n} candidates -> .cache/longlist.raw.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
