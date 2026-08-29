#!/usr/bin/env python3
"""Složí data/catalog.csv z kurátorovaných zdrojů v data/sources/*.json.

Model má dvě nezávislé osy: **země** a **téma**. Rejstřík firem je `companies`
bez ohledu na to, jestli je český nebo maltský, a Malta je `MT` bez ohledu na
to, jestli jde o katastr nebo o soudy. Kdyby země byla součástí kategorie,
skončil by katalog u 27 zemí na stovkách položek v postranním panelu.

Vstupy — všechny committnuté, takže build projde i na čistém klonu:

  data/sources/<KÓD>.json   kurátorované zdroje, jeden soubor na zemi/rozsah
  data/topics.json          témata a jejich skupiny (pořadí = pořadí v UI)
  data/countries.json       země a nadnárodní rozsahy
  data/provenance.csv       doložení z prohlížeče (id → návštěvy, poslední)

Doložení z prohlížeče vzniká odděleně v `tools/build_provenance.py`, který jako
jediný sahá na .cache/raw.json. Dřív ho počítal tenhle skript přímo při importu,
takže katalog nešlo přegenerovat bez cizího Chrome profilu — a to je u zdroje
pravdy, který má být reprodukovatelný, vada.
"""
from __future__ import annotations

import csv, json, sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

KINDS = {"official", "regional", "intl", "research", "ngo", "commercial"}
# Číselník hodnot i s popisky. Mapa, ne množina: platné hodnoty a jejich český
# název jsou totéž tvrzení a patří na jedno místo. Dokud byly popisky zvlášť
# v build_places.py, byly hodnoty definované dvakrát a mohly se rozejít —
# validace by to nepoznala, protože kontroluje jen klíče.
ACCESS = {"open": "otevřené", "registration": "registrace", "paid": "placené",
          "mixed": "smíšené", "restricted": "omezené", "unknown": "neuvedeno"}
DATA_MODES = {"bulk": "hromadně", "api": "API", "ogc": "OGC služby",
              "download": "ke stažení", "search": "vyhledávání", "sw": "software",
              "none": "bez dat", "unknown": "neuvedeno"}
REQUIRED = ("id", "country", "topic", "name", "url", "desc", "kind", "access", "data", "verified")
# Nepovinné pole "check": "anti-bot" říká, že server odmítá automatické klienty,
# přestože v prohlížeči funguje. Čte ho tools/check_links.py.
CHECK_MODES = {"anti-bot"}


def domain(url: str) -> str:
    """Doména se odvozuje z URL, nepíše se zvlášť — dvě místa pravdy se rozejdou."""
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def load_taxonomy():
    topics = json.loads((DATA / "topics.json").read_text(encoding="utf-8"))
    countries = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    topic_meta, topic_order = {}, {}
    for gi, g in enumerate(topics["groups"]):
        for ti, t in enumerate(g["topics"]):
            # 'scope' jde dál, ne jen label: na něm stojí rozdíl mezi dírou
            # a prázdnem, které tam patří. Kdyby se tu zahodilo, musel by ho
            # každý konzument uhodnout znovu.
            topic_meta[t["id"]] = {"label": t["label"], "group": g["label"],
                                   "scope": t.get("scope", "national")}
            topic_order[t["id"]] = (gi, ti)
    places, place_order = {}, {}
    for i, c in enumerate(countries["scopes"] + countries["countries"]):
        places[c["code"]] = c["name"]
        place_order[c["code"]] = i
    return topic_meta, topic_order, places, place_order


def load_sources() -> list[dict]:
    out = []
    for path in sorted((DATA / "sources").glob("*.json")):
        items = json.loads(path.read_text(encoding="utf-8"))
        for it in items:
            it["_file"] = path.name
        out += items
    return out


def load_provenance() -> dict[str, dict]:
    path = DATA / "provenance.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig") as fh:
        return {r["id"]: r for r in csv.DictReader(fh)}


def main() -> int:
    topic_meta, topic_order, places, place_order = load_taxonomy()
    sources = load_sources()
    prov = load_provenance()

    problems = []
    seen_ids, seen_urls = {}, {}
    for s in sources:
        where = f"{s.get('_file')}:{s.get('id', '?')}"
        for f in REQUIRED:
            if not s.get(f):
                problems.append(f"{where}: chybí pole '{f}'")
        if s.get("id") in seen_ids:
            problems.append(f"{where}: duplicitní id (už v {seen_ids[s['id']]})")
        seen_ids[s.get("id")] = where
        if s.get("url") in seen_urls:
            problems.append(f"{where}: duplicitní URL (už v {seen_urls[s['url']]})")
        seen_urls[s.get("url")] = where
        if s.get("topic") not in topic_meta:
            problems.append(f"{where}: neznámé téma '{s.get('topic')}'")
        if s.get("country") not in places:
            problems.append(f"{where}: neznámá země '{s.get('country')}'")
        if s.get("kind") not in KINDS:
            problems.append(f"{where}: neznámý typ '{s.get('kind')}'")
        if s.get("access") not in ACCESS:
            problems.append(f"{where}: neznámý přístup '{s.get('access')}'")
        if s.get("data") not in DATA_MODES:
            problems.append(f"{where}: neznámý režim dat '{s.get('data')}'")
        if s.get("check") is not None and s["check"] not in CHECK_MODES:
            problems.append(f"{where}: neznámá hodnota 'check' — {s['check']!r}")
        if not str(s.get("url", "")).startswith("https://") and \
           not str(s.get("url", "")).startswith("http://"):
            problems.append(f"{where}: URL není absolutní")
        if s.get("_file", "").removesuffix(".json") != s.get("country"):
            problems.append(f"{where}: položka je v souboru jiné země")
    if problems:
        for p in problems[:40]:
            sys.stderr.write("  ✗ " + p + "\n")
        sys.stderr.write(f"{len(problems)} problémů ve zdrojích\n")
        return 1

    # Pořadí katalogu: skupina → téma → země → pořadí v souboru. Sloupec `ord`
    # na stránce z něj vzniká a nese výchozí řazení „Pořadí katalogu".
    idx = {id(s): i for i, s in enumerate(sources)}
    sources.sort(key=lambda s: (*topic_order[s["topic"]], place_order[s["country"]], idx[id(s)]))

    drift = []
    rows = []
    for s in sources:
        p = prov.get(s["id"])
        if p and p["url"] != s["url"]:
            drift.append(f"{s['id']}: doložení je k {p['url']}, položka míří na {s['url']}")
            p = None
        rows.append([
            topic_meta[s["topic"]]["group"], topic_meta[s["topic"]]["label"], s["topic"],
            places[s["country"]], s["country"],
            s["name"], domain(s["url"]), s["desc"],
            s["kind"], s["access"], s["data"],
            p["Zdroj"] if p else "reference",
            p["Návštěvy"] if p else "", p["Unikátních URL"] if p else "",
            p["Poslední návštěva"] if p else "",
            s["url"], s["id"], s.get("verified", ""),
        ])

    DATA.mkdir(exist_ok=True)
    with (DATA / "catalog.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["Skupina", "Téma", "Téma ID", "Země", "Kód", "Web", "Doména", "Popis",
                    "Typ", "Přístup", "Data", "Zdroj", "Návštěvy", "Unikátních URL",
                    "Poslední návštěva", "URL", "ID", "Ověřeno"])
        w.writerows(rows)

    evidenced = sum(1 for r in rows if r[11] != "reference")
    countries = {r[4] for r in rows}
    print(f"katalog: {len(rows)} položek · {len({r[1] for r in rows})} témat · "
          f"{len(countries)} zemí a rozsahů · {evidenced} doložených z prohlížeče")
    for d in drift:
        sys.stderr.write(f"  ⚠ doložení se rozešlo s URL — {d}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
