#!/usr/bin/env python3
"""Ověří, že odkazy v katalogu někam vedou.

Katalog odkazů, jehož odkazy nikdo neověřil, je pasivní lež — vypadá jako
zdroj informací a přitom část z něj nefunguje. Velká část položek vznikla
ručně, tedy z paměti, což je přesně ten druh dat, který se ověřuje.

Nejdřív HEAD; servery, které ho odmítají (405/501, občas 403), se zkusí
ještě GETem s omezením na první kilobajty. Rozlišuje se:

  ok           2xx
  přesměrování cíl je jinde, než co je v katalogu (stojí za aktualizaci)
  blokuje      403 nebo 405 i po prostém GETu — ochrana proti robotům
               (AWS WAF vrací na výzvu „Human Verification\" právě 405),
               v prohlížeči web funguje
  certifikát   TLS selže, přes --insecure projde: vypršelý nebo špatný certifikát
  chyba        4xx/5xx nebo nedostupné

Rozlišení není puntičkářství. Bez něj checker nahlásí osm chyb, z nichž jsou
tři skutečné — a katalog se pak „opravuje" tam, kde je v pořádku.

DNS řeší checker sám přes DoH. Lokální resolver (Tailscale MagicDNS, firemní
VPN, blokátor reklam) umí selhat na doménách, které jsou globálně v pořádku,
a checker by pak hlásil mrtvé odkazy podle toho, na jaké síti zrovna běží.
"""
from __future__ import annotations

import argparse, csv, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog.csv"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
DOH = "https://cloudflare-dns.com/dns-query"


def probe(url: str, timeout: int, method: str = "HEAD",
          insecure: bool = False) -> tuple[int, str]:
    """Vrátí (http kód, konečná URL). Kód 0 znamená, že spojení nevyšlo."""
    cmd = ["curl", "-s", "-o", "/dev/null", "-L", "--max-redirs", "5",
           "--doh-url", DOH,
           "--connect-timeout", str(timeout), "--max-time", str(timeout * 2),
           "-A", UA, "-w", "%{http_code} %{url_effective}"]
    if insecure:
        cmd.append("-k")
    if method == "HEAD":
        cmd.append("-I")
    # Rozsahový požadavek (-r) si část serverů vyloží jako nepovolenou metodu
    # a odpoví 405, takže by fallback hlásil chybu tam, kde žádná není.
    # Tělo stejně zahazujeme do /dev/null.
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * 3)
    except subprocess.TimeoutExpired:
        return 0, url
    parts = r.stdout.strip().split(" ", 1)
    if len(parts) != 2 or not parts[0].isdigit():
        return 0, url
    return int(parts[0]), parts[1]


def canonical(url: str) -> str:
    """Porovnávací tvar — rozdíl jen ve schématu, www nebo lomítku není přesun."""
    s = urlsplit(url)
    host = s.netloc.lower().removeprefix("www.")
    return host + s.path.rstrip("/")


def classify(url: str, timeout: int) -> dict:
    code, final = probe(url, timeout)
    # Spousta serverů HEAD odmítá nebo na něj odpovídá jinak než na GET.
    # Mezi ně patří i 401: portály jako krz.ms.gov.pl na HEAD vrátí „neautorizováno"
    # a na GET tutéž stránku bez přihlášení normálně vydají.
    if code in (0, 401, 403, 405, 404, 501):
        code, final = probe(url, timeout, method="GET")

    if 200 <= code < 300:
        state = "ok" if canonical(final) == canonical(url) else "přesměrování"
    elif code in (403, 405):
        # Cloudflare, AWS WAF a spol. odmítají curl bez ohledu na User-Agent.
        # Po prostém GETu neznamená 405 chybějící stránku, ale odmítnutí klienta.
        state = "blokuje"
    elif code == 0:
        # Nespojilo se. Pokud to projde s -k, je vinen certifikát, ne server.
        alt, alt_final = probe(url, timeout, method="GET", insecure=True)
        state = "certifikát" if 200 <= alt <= 399 else "chyba"
        if state == "certifikát":
            code, final = alt, alt_final
    else:
        state = "chyba"
    return {"url": url, "code": code, "final": final, "state": state}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8, help="souběžných požadavků")
    ap.add_argument("--strict", action="store_true",
                    help="selhat i na přesměrováních, nejen na chybách")
    args = ap.parse_args()

    with CATALOG.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    targets = {r["URL"]: r["Web"] for r in rows}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda u: classify(u, args.timeout), targets))

    buckets: dict[str, list[dict]] = {k: [] for k in
                                      ("ok", "přesměrování", "blokuje", "certifikát", "chyba")}
    for r in results:
        buckets[r["state"]].append(r)

    print("  " + " · ".join(f"{len(v)} {k}" for k, v in buckets.items())
          + f"   (z {len(results)} odkazů)")

    for r in sorted(buckets["chyba"], key=lambda r: r["url"]):
        print(f"\n  ✗ {targets[r['url']]}  [{r['code'] or 'nedostupné'}]")
        print(f"      {r['url']}")
    for r in sorted(buckets["certifikát"], key=lambda r: r["url"]):
        print(f"\n  ⚠ {targets[r['url']]} — vadný TLS certifikát (obsah dostupný)")
        print(f"      {r['url']}")
    for r in sorted(buckets["přesměrování"], key=lambda r: r["url"]):
        print(f"\n  → {targets[r['url']]}")
        print(f"      z: {r['url']}")
        print(f"      na: {r['final']}")
    if buckets["blokuje"]:
        print("\n  Blokují automat, v prohlížeči fungují: "
              + ", ".join(targets[r["url"]] for r in buckets["blokuje"]))

    # Vadný certifikát je vada webu, ne katalogu — hlásí se, ale nesráží build.
    bad = len(buckets["chyba"]) + (len(buckets["přesměrování"]) if args.strict else 0)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
