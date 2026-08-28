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

Bez argumentů projde celý katalog. Při rozšiřování po zemích je to zbytečné —
kontrolovat sedm set odkazů kvůli dvaceti novým je drahé a výsledek se utopí
v šumu. Proto se dá výběr zúžit:

  --country AT        jen jedna země nebo rozsah (jde uvést víckrát)
  --topic companies   jen jedno téma
  --id cz-ares        konkrétní zdroj
  --changed           jen to, co se v data/sources/ liší proti gitu
  --url-file f.txt    URL po jedné na řádek

Měsíční workflow zůstává bez argumentů: zúžený běh je nástroj na rozpracovanou
práci, ne náhrada úplné kontroly.
"""
from __future__ import annotations

import argparse, csv, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog.csv"
SOURCES = ROOT / "data" / "sources"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
DOH = "https://cloudflare-dns.com/dns-query"


def probe(url: str, timeout: int, method: str = "HEAD",
          insecure: bool = False) -> tuple[int, str]:
    """Vrátí (http kód, konečná URL). Kód 0 znamená, že spojení nevyšlo."""
    # Deset skoků, ne pět: část portálů se přepíná mezi https a http nebo mezi
    # jazykovými mutacemi a v pěti skocích se neusadí. Prohlížeč jich povoluje
    # dvacet, takže na pěti selhávaly odkazy, které člověku fungují.
    cmd = ["curl", "-s", "-o", "/dev/null", "-L", "--max-redirs", "10",
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


def declared_antibot() -> set[str]:
    """URL, u kterých kurátor doložil, že server odmítá automatické klienty.

    Část serverů nevrací 403, ale spojení po TLS handshaku prostě zahodí —
    checker to vidí jako mrtvý odkaz, přestože web v prohlížeči běží. Bez téhle
    deklarace by měsíční kontrola každý měsíc hlásila totéž a naučila by lidi
    výstup ignorovat.

    Deklarace se nemaskuje do „ok": výsledek se hlásí zvlášť, aby šlo poznat,
    že se u té položky spoléhá na tvrzení kurátora, ne na měření.
    """
    out = set()
    for path in SOURCES.glob("*.json"):
        for s in json.loads(path.read_text(encoding="utf-8")):
            if s.get("check") == "anti-bot":
                out.add(s["url"])
    return out


def canonical(url: str) -> str:
    """Porovnávací tvar — rozdíl jen ve schématu, www nebo lomítku není přesun."""
    s = urlsplit(url)
    host = s.netloc.lower().removeprefix("www.")
    return host + s.path.rstrip("/")


def classify(url: str, timeout: int, antibot: frozenset[str] = frozenset()) -> dict:
    code, final = probe(url, timeout)
    # Spousta serverů HEAD odmítá nebo na něj odpovídá jinak než na GET.
    # Mezi ně patří i 401: portály jako krz.ms.gov.pl na HEAD vrátí „neautorizováno"
    # a na GET tutéž stránku bez přihlášení normálně vydají. A 400: německé
    # spolkové portály (bkg.bund.de, bafin.de, bsi.bund.de) odpovídají na HEAD
    # „chybný požadavek" a na tentýž GET vydají stránku.
    #
    # Zbylé 3xx po vyčerpání skoků znamená smyčku v přesměrování. Část portálů
    # (data.slovensko.sk) se v ní točí jen na HEAD a na GET se usadí, takže
    # se to zkusí znovu, než se odkaz prohlásí za mrtvý.
    if code in (0, 400, 401, 403, 405, 404, 501) or 300 <= code < 400:
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
    if state == "chyba" and url in antibot:
        state = "deklarováno"
    return {"url": url, "code": code, "final": final, "state": state}


def changed_urls() -> set[str]:
    """URL, které se v data/sources/ liší proti poslednímu commitu.

    Bere nové i změněné položky. Když git není k dispozici (tarball, CI bez
    historie), vrátí prázdno a volající to pozná podle nulového výběru.
    """
    try:
        head = subprocess.run(["git", "show", "HEAD:data/sources"], cwd=ROOT,
                              capture_output=True, text=True)
        names = head.stdout.split() if head.returncode == 0 else []
        before = set()
        for n in names:
            blob = subprocess.run(["git", "show", f"HEAD:data/sources/{n}"], cwd=ROOT,
                                  capture_output=True, text=True)
            if blob.returncode == 0:
                before |= {s["url"] for s in json.loads(blob.stdout)}
    except (OSError, json.JSONDecodeError):
        return set()
    now = set()
    for path in SOURCES.glob("*.json"):
        now |= {s["url"] for s in json.loads(path.read_text(encoding="utf-8"))}
    return now - before


def select(args) -> dict[str, str]:
    """URL → jméno položky, zúžené podle argumentů."""
    with CATALOG.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    if args.url_file:
        wanted = {u.strip() for u in Path(args.url_file).read_text(encoding="utf-8").splitlines()
                  if u.strip() and not u.startswith("#")}
        known = {r["URL"]: r["Web"] for r in rows}
        return {u: known.get(u, u) for u in wanted}

    if args.changed:
        urls = changed_urls()
        return {r["URL"]: r["Web"] for r in rows if r["URL"] in urls}

    if args.country:
        codes = {c.upper() for c in args.country}
        rows = [r for r in rows if r["Kód"] in codes]
    if args.topic:
        topics = set(args.topic)
        rows = [r for r in rows if r["Téma ID"] in topics]
    if args.id:
        ids = set(args.id)
        rows = [r for r in rows if r["ID"] in ids]
    return {r["URL"]: r["Web"] for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--workers", type=int, default=8, help="souběžných požadavků")
    ap.add_argument("--strict", action="store_true",
                    help="selhat i na přesměrováních, nejen na chybách")
    ap.add_argument("--country", action="append", metavar="KÓD",
                    help="jen tato země nebo rozsah (lze uvést víckrát)")
    ap.add_argument("--topic", action="append", metavar="ID", help="jen toto téma")
    ap.add_argument("--id", action="append", metavar="ID", help="jen tento zdroj")
    ap.add_argument("--changed", action="store_true",
                    help="jen URL přidané nebo změněné proti gitu")
    ap.add_argument("--url-file", metavar="SOUBOR", help="URL po jedné na řádek")
    args = ap.parse_args()

    targets = select(args)
    if not targets:
        print("  nic k ověření (výběr je prázdný)")
        return 0

    antibot = frozenset(declared_antibot())
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda u: classify(u, args.timeout, antibot), targets))

    buckets: dict[str, list[dict]] = {k: [] for k in
                                      ("ok", "přesměrování", "blokuje", "certifikát",
                                       "deklarováno", "chyba")}
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
    # Vypisuje se zvlášť, protože tady se nespoléhá na měření, ale na tvrzení
    # kurátora v datech. Když takový web opravdu zemře, pozná se to jen tak,
    # že si toho někdo při čtení téhle sekce všimne.
    if buckets["deklarováno"]:
        print("\n  Deklarované jako anti-bot (`check: anti-bot` ve zdrojích) — "
              "ověřuj ručně, checker se sem nedostane:")
        for r in sorted(buckets["deklarováno"], key=lambda r: r["url"]):
            print(f"      {targets[r['url']]} — {r['url']}")

    # Vadný certifikát je vada webu, ne katalogu — hlásí se, ale nesráží build.
    bad = len(buckets["chyba"]) + (len(buckets["přesměrování"]) if args.strict else 0)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
