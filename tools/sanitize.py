#!/usr/bin/env python3
"""Vyčistí syrový long list do podoby, kterou lze zveřejnit.

Syrový výstup ze `scan.py` je výřez osobní historie prohlížení. Než se dostane
do veřejného repozitáře, musí z něj pryč tři skupiny:

  1. INFRASTRUKTURA — interní hostnames, privátní/VPN IP adresy, tunely.
     Zveřejnit je znamená vystavit topologii vlastní sítě.
  2. OSOBNÍ / CITLIVÉ — zdravotnictví, identita, datové schránky, bankovnictví.
  3. ŠUM — e-shopy, zpravodajství, zábava. S geodaty nemá nic společného;
     do katalogu se to dostalo jen kvůli širokému keyword filtru.

Skript je záměrně allowlist-first: co neprojde `RELEVANT`, vypadne. Je lepší
zahodit hraniční kandidáty než omylem publikovat něco osobního.
"""
import csv, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / ".cache" / "longlist.raw.csv"
OUT = ROOT / "data" / "longlist.csv"

# ── 1. infrastruktura ─────────────────────────────────────────────────────────
# Obecná, přenositelná pravidla. Konkrétní hostnames vlastní sítě sem NEPATŘÍ —
# committnuté pravidlo je stejný únik jako committnutá data. Ty patří do
# config/private-hosts.txt, který je v .gitignore.
INFRA = re.compile(r"""
      ^\d{1,3}(\.\d{1,3}){3}$        # jakákoli holá IP (včetně CGNAT 100.64/10)
    | ^\[?[0-9a-f]{0,4}:[0-9a-f:]+\]?$  # IPv6
    | ngrok | trycloudflare | loca\.lt   # veřejné tunely
    | ^localhost$
    | \.local$ | \.internal$ | \.lan$ | \.home\.arpa$
""", re.I | re.X)

PRIVATE_HOSTS = ROOT / "config" / "private-hosts.txt"


def private_host_pattern():
    """Načte site-specific denylist, pokud existuje.

    Jeden regex na řádek, `#` uvozuje komentář. Soubor je mimo repozitář
    záměrně: jsou v něm jména, která nemá smysl zveřejňovat.
    """
    if not PRIVATE_HOSTS.exists():
        return None
    pats = [ln.split("#", 1)[0].strip() for ln in
            PRIVATE_HOSTS.read_text(encoding="utf-8").splitlines()]
    pats = [p for p in pats if p]
    return re.compile("|".join(pats), re.I) if pats else None


# ── 2. osobní / citlivé ───────────────────────────────────────────────────────
SENSITIVE = re.compile(r"""
      erpid\.cz            # eRecept — zdravotnictví
    | mojedatovaschranka | datovaschranka
    | ceecr\.cz           # ověřování existence e-mailových schránek
    | identita\.gov\.cz | ^nia\. | bankid | ^oidc\. | eidasnode
    | ^login\.(kb|csob|rb)\.cz$
    | mediclinic | lekarna | drmax | aktin\.cz
""", re.I | re.X)

# ── 3. co si zaslouží zůstat ──────────────────────────────────────────────────
# Test běží VÝHRADNĚ nad doménou, nikoli nad titulkem stránky. Titulky jsou
# zrádné: české e-shopy inzerují "Doprava zdarma", což na `doprav` sedne stejně
# dobře jako Ředitelství silnic a dálnic. Doména je jediný spolehlivý signál.
RELEVANT = re.compile(r"""
      geo | \bgis\b | mapy?\. | maplibre   # \b jinak chytá "reGIStration", "loGIStic" | leaflet | carto | deck\.gl
    | openstreetmap | nominatim | naturalearth | geonames | factbook
    | cuzk | katastr | nahlizeni | ruian
    | dopravniinfo | mobilitydata | golemio | rsd\.cz | pid\.cz | md\.gov\.cz
    | hzscr | hasici | kr-stredocesky | sanfranciscopolice
    | meteo | in-pocasi | chmi
    | csu\.gov | census | eurostat
    | data\.gov | datahub | commoncrawl | openalex
    | hlidacstatu | smlouvy\.gov | ares\.gov | justice\.cz | northdata
    | osint | maltego | investigace | cia\.gov
    | postgres | postgis | duckdb | pgadmin
    | sigmajs | observablehq | sreality | flatzone | cbre
    | wikipedia | utoronto
    | progresus | vomaste | situacni-radar
""", re.I | re.X)


def main() -> int:
    if not RAW.exists():
        print(f"chybí {RAW} — spusť nejdřív `just catalog`", file=sys.stderr)
        return 1

    with RAW.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
        fields = rows[0].keys() if rows else []

    private = private_host_pattern()
    kept, dropped = [], {"infrastruktura": [], "citlivé": [], "šum": []}
    for r in rows:
        dom = r["Doména"]
        # citlivost se hledá i v titulku a URL, relevance výhradně v doméně
        hay = f"{dom} {r.get('Ukázkový titulek','')} {r.get('Ukázková URL','')}"
        if INFRA.search(dom) or (private and private.search(dom)):
            dropped["infrastruktura"].append(dom)
        elif SENSITIVE.search(hay):
            dropped["citlivé"].append(dom)
        elif not RELEVANT.search(dom):
            dropped["šum"].append(dom)
        else:
            kept.append(r)

    with OUT.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields))
        w.writeheader()
        w.writerows(kept)

    if private is None:
        print(f"pozn.: {PRIVATE_HOSTS.relative_to(ROOT)} neexistuje — "
              "filtrují se jen obecná infrastrukturní pravidla")
    print(f"long list: {len(rows)} → {len(kept)} zveřejnitelných")
    for label, doms in dropped.items():
        print(f"  vyřazeno ({label}): {len(doms)}")
        if label != "šum":
            for d in doms:
                print(f"      {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
