#!/usr/bin/env python3
"""Spočítá doložení kurátorovaných zdrojů z exportu prohlížeče do data/provenance.csv.

Tohle je jediný skript v řetězu, který sahá na .cache/raw.json — tedy na osobní
historii prohlížení. Běží jen lokálně a jen když ten export existuje; katalog,
dokumentace i stránka se staví bez něj z committnutých dat.

Zapisuje jen to, co už dnes stojí v data/catalog.csv (zdroj, počet návštěv,
počet URL, datum poslední návštěvy) — nic nového se tím nezveřejňuje.

Kořenová URL dostane statistiku celé domény, hlubší cesta jen záznamy, které na
ni skutečně sedí. Bez toho by github.com/…/awesome-geospatial zdědil statistiku
celého GitHubu a tvářil se jako nejnavštěvovanější položka katalogu.
"""
from __future__ import annotations

import collections, csv, json, sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
CACHE, DATA = ROOT / ".cache", ROOT / "data"

# Služby se stěhují. Návštěvy pod starým jménem jsou pořád důkaz, že zdroj znáš —
# sloupec Zdroj má říkat „tohle znáš", ne „tahle konkrétní doména je v exportu".
DOMAIN_ALIASES = {
    "developer.mapy.com": ["developer.mapy.cz"],
    "geoportal.cuzk.gov.cz": ["geoportal.cuzk.cz"],
    "mze.gov.cz": ["eagri.cz"],
    "dopravniinfo.gov.cz": ["dopravniinfo.cz"],
    "cgs.gov.cz": ["mapy.geology.cz"],
    "gis-aopkcr.opendata.arcgis.com": ["gis-aopk.opendata.arcgis.com"],
}


def norm(u: str) -> str:
    sp = urlsplit(u)
    h = (sp.hostname or "").lower()
    if h.startswith("www."):
        h = h[4:]
    return (h + sp.path).rstrip("/").lower()


def main() -> int:
    raw = CACHE / "raw.json"
    if not raw.exists():
        sys.stderr.write(
            f"  {raw.relative_to(ROOT)} chybí — doložení se přepočítat nedá.\n"
            "  Spusť `just extract` nad Chrome profilem; data/provenance.csv zůstává beze změny.\n")
        return 1

    rows = json.loads(raw.read_text(encoding="utf-8"))
    stat = collections.defaultdict(lambda: dict(v=0, last="", bm=0, hist=0, urls=set()))
    recorded = []
    for r in rows:
        d = r["domain"]
        if not d:
            continue
        s = stat[d]
        s["v"] += r["visits"]
        s["urls"].add(r["url"])
        s["bm" if r["source"] == "bookmark" else "hist"] += 1
        if r["last"] > s["last"]:
            s["last"] = r["last"]
        recorded.append((norm(r["url"]), r))

    def evidence(url: str):
        dom = (urlsplit(url).hostname or "").lower().removeprefix("www.")
        if not urlsplit(url).path.rstrip("/"):
            s = stat.get(dom)
            for alias in DOMAIN_ALIASES.get(dom, []):
                if s:
                    break
                s = stat.get(alias)
            if not s:
                return None
            parts = [x for x in (("bookmarks" if s["bm"] else ""),
                                 ("history" if s["hist"] else "")) if x]
            return ("+".join(parts), s["v"], len(s["urls"]), s["last"][:10])
        pref = norm(url)
        hits = [r for (n, r) in recorded if n == pref or n.startswith(pref + "/")]
        if not hits:
            return None
        parts = [x for x in (("bookmarks" if any(h["source"] == "bookmark" for h in hits) else ""),
                             ("history" if any(h["source"] == "history" for h in hits) else "")) if x]
        return ("+".join(parts), sum(h["visits"] for h in hits),
                len({h["url"] for h in hits}), max(h["last"] for h in hits)[:10])

    out = []
    for path in sorted((DATA / "sources").glob("*.json")):
        for s in json.loads(path.read_text(encoding="utf-8")):
            e = evidence(s["url"])
            if e:
                out.append([s["id"], s["url"], *e])
    out.sort()

    with (DATA / "provenance.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "url", "Zdroj", "Návštěvy", "Unikátních URL", "Poslední návštěva"])
        w.writerows(out)
    print(f"doložení: {len(out)} položek z {len(rows)} záznamů prohlížeče")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
