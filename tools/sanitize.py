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
import argparse, csv, re, sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

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
    | ^intranet\. | \.intranet\. | ^intra\.   # vnitřní weby organizací
""", re.I | re.X)

# ── ukázkové sloupce ──────────────────────────────────────────────────────────
# `Ukázkový titulek` a `Ukázková URL` se z historie kopírovaly doslova. Doména
# projde allowlistem, tyhle dva sloupce ale neprocházely ničím — a nesly přesně
# to, co po člověku v historii zůstane: `?_ga=` s trvalým identifikátorem
# prohlížeče, `ico=` konkrétní prověřované firmy, id parcely v katastru,
# kampaňový token z e-mailu, adresu vlastního API účtu, stránky přihlášení
# a registrace. Přes `tools/build_page.py` se to vkládalo do `dist/index.html`
# i do artefaktu, tedy na veřejný web, kde se v tom dalo fulltextově hledat.
#
# Ukázka má říct „takhle na té doméně vypadá stránka", ne „tohle jsem tam
# dělal". Dotaz tu první informaci nikdy nenese a tu druhou skoro vždy, takže
# padá celý; cesta do účtu padá s ní a bere s sebou i titulek, aby nezůstal
# popis stránky bez adresy.
ACCOUNT_PATH = re.compile(
    r"/(account|ucet|login|prihlaseni|signin|auth|register|registrace|zadost"
    r"|zadosti|identity|profile|profil|admin|dashboard)", re.I)

# Titulek prozradí účet i tam, kde cesta mlčí: `/zadostdp` je neprůhledné,
# ale „Žádosti - prihlaseni" ne.
ACCOUNT_TITLE = re.compile(
    r"přihlá|prihla|odhlá|login|sign in|registrace|register|můj účet|my account",
    re.I)


def scrub_sample(row: dict) -> dict:
    url = (row.get("Ukázková URL") or "").strip()
    if not url:
        return row
    parts = urlsplit(url)
    if ACCOUNT_PATH.search(parts.path) or ACCOUNT_TITLE.search(row.get("Ukázkový titulek") or ""):
        row["Ukázková URL"] = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
        row["Ukázkový titulek"] = ""
    else:
        row["Ukázková URL"] = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, "", ""))
    return row


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
    # Vlastní veřejné projekty autora katalogu. Stojí tu schválně: bez nich by
    # allowlist tyhle domény zahodil jako šum, přestože jsou to geo/OSINT
    # projekty a v katalogu mají kurátorovaný záznam. Ověřeno 2026-08-30, že
    # všechny tři odpovídají veřejně HTTP 200 — nejde tedy o hostnames vlastní
    # sítě, na které míří zákaz o šedesát řádků výš. Ten platí pro denylist:
    # tam konkrétní jméno prozrazuje topologii a patří do config/private-hosts.txt.
    # Tady konkrétní jméno jen říká „tohle propusť", což nic neprozrazuje.
    | progresus | vomaste | situacni-radar
""", re.I | re.X)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    # Bez denylistu se dřív pokračovalo s poznámkou. Na cizím stroji tím tiše
    # platily jen obecné vzory, a co pouštěl committnutý allowlist, prošlo do
    # zveřejněného long listu. Mlčky publikovat je horší než nespustit se.
    ap.add_argument("--no-private-hosts", action="store_true",
                    help="run without config/private-hosts.txt (generic rules only)")
    args = ap.parse_args()

    if not RAW.exists():
        print(f"{RAW.relative_to(ROOT)} is missing — run `just extract`, "
              f"`just scan` and `just longlist` first", file=sys.stderr)
        return 1

    with RAW.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
        fields = rows[0].keys() if rows else []

    private = private_host_pattern()
    if private is None and not args.no_private_hosts:
        print(f"{PRIVATE_HOSTS.relative_to(ROOT)} is missing — the site-specific "
              f"denylist would not apply and internal hostnames could reach "
              f"data/longlist.csv.\n"
              f"  Copy config/private-hosts.example.txt to it, or pass "
              f"--no-private-hosts to run with the generic rules only.",
              file=sys.stderr)
        return 1
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
        w.writerows(scrub_sample(r) for r in kept)

    if private is None:
        print(f"pozn.: běží bez {PRIVATE_HOSTS.relative_to(ROOT)} "
              "(--no-private-hosts) — filtrují se jen obecná pravidla")
    print(f"long list: {len(rows)} → {len(kept)} zveřejnitelných")
    for label, doms in dropped.items():
        print(f"  vyřazeno ({label}): {len(doms)}")
        if label != "šum":
            for d in doms:
                print(f"      {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
