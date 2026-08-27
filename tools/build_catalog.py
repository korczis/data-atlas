# -*- coding: utf-8 -*-
import json, csv, collections, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE, DATA = ROOT / ".cache", ROOT / "data"
rows = json.load(open(CACHE / "raw.json", encoding="utf-8"))

stat=collections.defaultdict(lambda: dict(v=0,last='',bm=0,hist=0,urls=set()))
for r in rows:
    d=r['domain']
    if not d: continue
    s=stat[d]; s['v']+=r['visits']; s['urls'].add(r['url'])
    if r['source']=='bookmark': s['bm']+=1
    else: s['hist']+=1
    if r['last']>s['last']: s['last']=r['last']

from urllib.parse import urlsplit

# Služby se stěhují. Když se doména přejmenuje, návštěvy pod starým jménem
# jsou pořád důkaz, že jsi ten zdroj používal — sloupec Zdroj má říkat
# "tohle znáš", ne "tahle konkrétní doména je v exportu".
DOMAIN_ALIASES = {
    "developer.mapy.com": ["developer.mapy.cz"],
    "geoportal.cuzk.gov.cz": ["geoportal.cuzk.cz"],
    "mze.gov.cz": ["eagri.cz"],
    "dopravniinfo.gov.cz": ["dopravniinfo.cz"],
    "cgs.gov.cz": ["mapy.geology.cz"],
    "gis-aopkcr.opendata.arcgis.com": ["gis-aopk.opendata.arcgis.com"],
}


def _norm(u):
    """kanonizuj URL pro porovnání prefixu: bez schématu, bez www, bez trailing /"""
    sp = urlsplit(u)
    h = (sp.hostname or '').lower()
    if h.startswith('www.'): h = h[4:]
    return (h + sp.path).rstrip('/').lower()

# všechny zaznamenané URL s jejich metrikami, pro prefix matching
recorded = []
for r in rows:
    if r['domain']:
        recorded.append((_norm(r['url']), r))

def evidence(entry_url, dom):
    """Vrať (zdroj, navstevy, pocet_url, posledni).

    Kořenová URL  -> statistiky celé domény.
    Hlubší cesta  -> jen záznamy, jejichž URL na tuto cestu skutečně sedí.
                     Bez shody = položka je čistě referenční, žádná čísla.
    """
    path = urlsplit(entry_url).path.rstrip('/')
    if not path:                                   # kořen domény
        s = stat.get(dom)
        for alias in DOMAIN_ALIASES.get(dom, []):  # zdroj se mohl přestěhovat
            if s: break
            s = stat.get(alias)
        if not s: return ('reference', '', '', '')
        p = [x for x in (('bookmarks' if s['bm'] else ''),
                         ('history' if s['hist'] else '')) if x]
        return ('+'.join(p) or 'reference', s['v'], len(s['urls']), s['last'][:10])

    pref = _norm(entry_url)
    hits = [r for (n, r) in recorded if n == pref or n.startswith(pref + '/')]
    if not hits:
        return ('reference', '', '', '')
    p = [x for x in (('bookmarks' if any(h['source'] == 'bookmark' for h in hits) else ''),
                     ('history' if any(h['source'] == 'history' for h in hits) else '')) if x]
    return ('+'.join(p), sum(h['visits'] for h in hits),
            len({h['url'] for h in hits}), max(h['last'] for h in hits)[:10])

# (kategorie, nazev, domena, popis, url)
C=[
# ═══ 1. GAZETTEERY, GEOKÓDOVÁNÍ, ADRESY ═══
("1. Gazetteer / geokódování","Nominatim","nominatim.org","OSM geocoder — forward/reverse, self-hosted i veřejný. Import, admin, maintenance docs máš v záložkách Geo & Maps","https://nominatim.org/"),
("1. Gazetteer / geokódování","GeoNames","geonames.org","Globální gazetteer pod CC-BY 4.0 — 12M unikátních objektů a 25M jmen (z toho 4,8M sídel a 16M alternate names), admin hierarchie ADM1-4 a populace; dumpy zdarma (allCountries.zip)","https://www.geonames.org/"),
("1. Gazetteer / geokódování","Pelias","pelias.io","Modulární OSS geocoder (OSM + WOF + OpenAddresses + Geonames), Elasticsearch backend","https://pelias.io/"),
("1. Gazetteer / geokódování","Who's on First","whosonfirst.org","Gazetteer admin i POI entit se stabilními ID a hierarchií, podklad Pelias","https://whosonfirst.org/"),
("1. Gazetteer / geokódování","OpenAddresses","openaddresses.io","Agregované otevřené adresní body globálně — živý pipeline na batch.openaddresses.io vydává týdenní kolekce po zemích a regionech v line-delimited GeoJSON, starý CSV výstup na results.openaddresses.io je zamrzlý archiv z 10/2021","https://openaddresses.io/"),
("1. Gazetteer / geokódování","RÚIAN / VDP ČÚZK","vdp.cuzk.cz","Autoritativní CZ registr adres a územní identifikace — výměnný formát, adresní body, definiční body parcel","https://vdp.cuzk.cz/"),
("1. Gazetteer / geokódování","Mapy.com REST API","developer.mapy.com","CZ geokódování, suggest, routing, dlaždice. Máš tam aktivní projekt s consumption trackingem","https://developer.mapy.com/"),
("1. Gazetteer / geokódování","Photon","photon.komoot.io","Rychlý OSM geocoder s type-ahead, snadný self-hosting","https://photon.komoot.io/"),
("1. Gazetteer / geokódování","OpenCage Geocoding API","opencagedata.com","Hostované geokódovací API nad OSM a dalšími otevřenými geokodéry — forward i reverse, u výsledku časová zóna, Wikidata ID, NUTS a FIPS kódy, výsledky lze ukládat; free trial 2 500 dotazů/den, dál placené tarify","https://opencagedata.com/"),
("1. Gazetteer / geokódování","NGA GEOnet Names Server (GNS)","geonames.nga.mil","Gazetteer NGA a US Board on Geographic Names pro toponyma mimo USA — schválené tvary jmen, varianty, historické i nelatinkové zápisy, souřadnice a admin zařazení; country files ke stažení bez licenčních omezení","https://geonames.nga.mil/"),
("1. Gazetteer / geokódování","Wikidata","wikidata.org","Otevřená znalostní báze — místa nesou souřadnici (P625), stabilní QID a křížové odkazy na GeoNames a OSM, rekonciliace toponym přes SPARQL endpoint","https://www.wikidata.org/"),
("1. Gazetteer / geokódování","World Historical Gazetteer","whgazetteer.org","Historický gazetteer (v3.2, University of Pittsburgh) — přes 2,2 mil. míst propojených napříč epochami a jazyky, rekonciliace proti GeoNames a Wikidata, API i stahování datasetů","https://whgazetteer.org/"),

# ═══ 2. GLOBÁLNÍ REFERENČNÍ GEODATA ═══
("2. Globální geodata","Natural Earth","naturalearthdata.com","Public-domain vektor + raster v 1:10m/50m/110m — hranice, pobřeží, řeky, města, stínovaný reliéf. Kartografický základ","https://www.naturalearthdata.com/"),
("2. Globální geodata","World Factbook Archive","worldfactbookarchive.org","Nezávislý archiv všech ročníků CIA World Factbooku 1990-2025 (284 entit, přes milion polí) — vyhledávání, otevřené JSON API a export do CSV; po zrušení originálu v únoru 2026 jediná cesta k těmto datům","https://worldfactbookarchive.org/"),
("2. Globální geodata","GADM","gadm.org","Administrativní hranice všech zemí do úrovně ADM5 v GeoPackage/shapefile/KMZ — jen pro akademické a nekomerční použití, redistribuce a komerční užití bez svolení zakázány","https://gadm.org/"),
("2. Globální geodata","geoBoundaries","geoboundaries.org","Otevřená alternativa GADM s jasnou licencí a verzováním","https://www.geoboundaries.org/"),
("2. Globální geodata","US Census TIGER/Line","census.gov","TIGER/Line shapefiles — US hranice, ulice, bloky, ZCTA, tracts (\"geotiger\")","https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html"),
("2. Globální geodata","Overture Maps Foundation","overturemaps.org","Otevřená základní data v šesti tématech — addresses, base, buildings, divisions, places a transportation (adresy přes 470 mil. bodů, zatím alfa); měsíční release v GeoParquet na S3 a Azure, dotazovatelné DuckDB","https://overturemaps.org/"),
("2. Globální geodata","Geofabrik Downloads","download.geofabrik.de","Denní OSM extrakty po zemích a regionech (.osm.pbf, .shp.zip)","https://download.geofabrik.de/"),
("2. Globální geodata","OpenStreetMap","openstreetmap.org","Základní vrstva všeho — editace, historie, export","https://www.openstreetmap.org/"),
("2. Globální geodata","Overpass Turbo","overpass-turbo.eu","Interaktivní dotazování OSM podle tagů, bboxu, relací; export GeoJSON","https://overpass-turbo.eu/"),
("2. Globální geodata","HDX (UN OCHA)","data.humdata.org","Globální populace ve vektorových H3 hexagonech 400 m (varianty 3 km a 22 km) — fúze GHSL, Facebook HRSL, Microsoft Buildings, Copernicus Land Cover a OSM","https://data.humdata.org/"),
("2. Globální geodata","OpenCelliD","opencellid.org","Otevřená databáze pozic BTS/cell towers — užitečné pro geolokaci","https://opencellid.org/"),
("2. Globální geodata","OSM Planet","planet.openstreetmap.org","Týdenní kompletní dumpy databáze OSM — XML (~165 GB) i PBF (~88 GB), full-history planet se všemi verzemi prvků, changesety a replikační diffy pro průběžnou synchronizaci","https://planet.openstreetmap.org/"),
("2. Globální geodata","HydroSHEDS","hydrosheds.org","Globální hydrologická data odvozená z DEM — říční sítě, hierarchická povodí a jezera ve standardních GIS formátech; verze 2 z TanDEM-X zatím jen pro Ameriku, globální pokrytí se dokončuje","https://www.hydrosheds.org/"),
("2. Globální geodata","Protected Planet (WDPA)","protectedplanet.net","WDPA a WDOECM od UNEP-WCMC a IUCN — polygony a body přes 300 tisíc chráněných území a OECM celého světa, měsíční aktualizace, hromadné stahování i API","https://www.protectedplanet.net/"),
("2. Globální geodata","Marine Regions","marineregions.org","Gazetteer a hranice na moři od VLIZ — výlučné ekonomické zóny, teritoriální a vnitřní vody, rozšířené šelfy a volné moře v GeoPackage/shp/KML, přes OGC služby i balík mregions2","https://www.marineregions.org/"),
("2. Globální geodata","Open Infrastructure Map","openinframap.org","Prohlížečka infrastruktury vykreslené z OSM — elektrické vedení, trafostanice a elektrárny, ropovody, plynovody a telekomunikační síť; bez exportu dat","https://openinframap.org/"),

# ═══ 3. ČR — KATASTR A NÁRODNÍ GEODATA ═══
("3. ČR — katastr a geodata","ČÚZK — Dálkový přístup do KN","katastr.cuzk.gov.cz","Dálkový přístup do KN — placená služba pro registrované uživatele, on-line výstupy z ISKN (LV, parcely, řízení); kořen domény dnes vede na cuzk.gov.cz/aplikace-dp","https://katastr.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","Nahlížení do KN","nahlizenidokn.cuzk.gov.cz","Veřejné nahlížení do KN zdarma a bez registrace — parcely, budovy, jednotky, LV a vlastníci; API zde není, na strojový přístup slouží samostatné REST API na api-kn.cuzk.gov.cz","https://nahlizenidokn.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","SGI Nahlížení do KN","sgi-nahlizenidokn.cuzk.gov.cz","Grafická část — katastrální mapa, mapové služby","https://sgi-nahlizenidokn.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","Geoportál ČÚZK","geoportal.cuzk.gov.cz","WMS/WFS/WMTS, ZABAGED, Ortofoto ČR, DMR 5G/DMP 1G, Data50/200. Klíčový CZ zdroj","https://geoportal.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","ČÚZK — Žádosti","zadosti.cuzk.gov.cz","Žádosti o zřízení dálkového přístupu do KN, o výdej dat ve výměnném formátu ISKN (VFK) a o souhlas se šířením údajů katastru","https://zadosti.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","ČÚZK (rozcestník)","cuzk.gov.cz","Hlavní web zeměměřického a katastrálního úřadu","https://www.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","Národní geoportál INSPIRE (CENIA)","geoportal.gov.cz","CZ INSPIRE katalog — metadata a služby napříč resorty, včetně historického ortofota z 50. let","https://geoportal.gov.cz/"),
("3. ČR — katastr a geodata","ArcČR (ARCDATA Praha)","arcdata.cz","ArcČR 4.3 — administrativní členění ČR s geometrií z RÚIAN k 1. 1. 2024 a napojenými statistikami ČSÚ a ÚAP, zdarma pod CC BY 4.0; starší ArcČR 500 v3.3 (sídla, vodstvo, doprava) je už jen archivní ke stažení","https://www.arcdata.cz/cs-cz/produkty/data/arccr"),
("3. ČR — katastr a geodata","DIBAVOD (VÚV TGM)","dibavod.cz","Digitální báze vodohospodářských dat — povodí, vodní toky, nádrže","https://www.dibavod.cz/"),
("3. ČR — katastr a geodata","AOPK — Ochrana přírody","gis-aopkcr.opendata.arcgis.com","Chráněná území, Natura 2000, biotopy jako open data","https://gis-aopkcr.opendata.arcgis.com/"),
("3. ČR — katastr a geodata","LPIS — veřejný registr půdy (MZe)","mze.gov.cz","Zemědělské půdní bloky, využití půdy, WMS/WFS","https://mze.gov.cz/public/app/lpisext/lpis/verejny2/plpis/"),
("3. ČR — katastr a geodata","Česká geologická služba","cgs.gov.cz","Geologické, hydrogeologické a půdní mapy, sesuvy, poddolování","https://cgs.gov.cz/mapy-a-data"),
("3. ČR — katastr a geodata","Geoportál Praha","geoportalpraha.cz","Pražská geodata a open data — ortofota, územní plán, 3D model","https://www.geoportalpraha.cz/"),
("3. ČR — katastr a geodata","Portál DMVS (ČÚZK)","dmvs.cuzk.gov.cz","Portál digitální mapy veřejné správy — bezešvé prohlížení krajských digitálních technických map (DTM) a stahování dat v jednotném formátu JVF DTM","https://dmvs.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","REST API dat katastru nemovitostí (ČÚZK)","api-kn.cuzk.gov.cz","Bezplatné REST API ke katastru — parcely, budovy, jednotky a řízení v JSON, po registraci přes Identitu občana nebo účet dálkového přístupu","https://api-kn.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","ČÚZK — Mapové služby","services.cuzk.gov.cz","Mapový server ČÚZK — bezúplatné WMS/WFS/WMTS endpointy katastrální mapy, ortofota, ZABAGED a RÚIAN, odtud se berou URL do QGIS nebo skriptu","https://services.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","ČÚZK — Stahovací služby ATOM","atom.cuzk.gov.cz","ATOM feedy ČÚZK pro dávkové stahování po mapových listech — ortofoto, katastrální mapa, RÚIAN a INSPIRE témata bezúplatně pod CC BY 4.0, skriptovatelná alternativa k eShopu","https://atom.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","Půda v mapách (VÚMOP)","mapy.vumop.cz","Mapový server VÚMOP — ohroženost vodní a větrnou erozí (SEO/MEO pro DZES 5), vlastnosti půd odvozené z BPEJ, třídy ochrany ZPF a zranitelnost podzemních vod","https://mapy.vumop.cz/"),

# ═══ 4. ČR — DOPRAVA A MOBILITA ═══
("4. ČR — doprava / mobilita","Golemio (Praha)","golemio.cz","Datová platforma hl. m. Prahy — MHD, parkování, senzory, sdílená mobilita","https://golemio.cz/"),
("4. ČR — doprava / mobilita","Golemio API","api.golemio.cz","API dokumentace a správa klíčů — Public Transport, GTFS, polohy vozidel; OpenAPI pro PID je na /pid/docs/openapi/","https://api.golemio.cz/"),
("4. ČR — doprava / mobilita","ŘSD MobilityData","mobilitydata.rsd.cz","Registr odběrů NDIC — registrace k odběru dopravních informací ve formátech DATEX II a nativní NDIC XML včetně lokačních tabulek ALERT-C; přístup jen po přihlášení","https://mobilitydata.rsd.cz/"),
("4. ČR — doprava / mobilita","Geoportál ŘSD","geoportal.rsd.cz","Silniční a dálniční síť ČR — mapové aplikace, datové vrstvy, uzly a úseky","https://geoportal.rsd.cz/web"),
("4. ČR — doprava / mobilita","Dopravní info (NDIC)","dopravniinfo.gov.cz","Uzavírky, nehody, sjízdnost, real-time dopravní události","https://dopravniinfo.gov.cz/"),
("4. ČR — doprava / mobilita","NAIS API","api-nais.dopravniinfo.cz","API vrstva nad národními dopravními informacemi (DATEX II) — přístup jen s účtem zřízeným přes Registr odběrů NDIC","https://api-nais.dopravniinfo.cz/"),
("4. ČR — doprava / mobilita","PID","pid.cz","Pražská integrovaná doprava — jízdní řády a mapy linek; GTFS feed se stahuje z data.pid.cz (https://data.pid.cz/PID_GTFS.zip)","https://pid.cz/"),
("4. ČR — doprava / mobilita","Ministerstvo dopravy","md.gov.cz","Web Ministerstva dopravy — sekce Statistiky, Dokumenty a Otevřená data (datové sady rezortu)","https://md.gov.cz/"),
("4. ČR — doprava / mobilita","Sčítání dopravy ŘSD","scitani.rsd.cz","Výsledky celostátního sčítání dopravy 2010, 2016 a 2020 — intenzity automobilové dopravy po úsecích dálniční a silniční sítě ČR","https://scitani.rsd.cz/"),
("4. ČR — doprava / mobilita","Dopravní nehody v ČR (CDV)","nehody.cdv.cz","Nehody evidované Policií ČR od roku 2006 — filtrování podle času, území a 64 evidovaných parametrů, měsíční aktualizace, export do PDF","https://nehody.cdv.cz/"),
("4. ČR — doprava / mobilita","Geoportál DTMŽ (Správa železnic)","geoportal.spravazeleznic.cz","Digitální technická mapa železnic — mapový klient, Všeobecná železniční mapa, vyhledávání metadat a žádost o výdej dat","https://geoportal.spravazeleznic.cz/"),
("4. ČR — doprava / mobilita","Portál CIS JŘ","portal.cisjr.cz","Celostátní informační systém o jízdních řádech (Ministerstvo dopravy a CHAPS) — jízdní řády autobusů, MHD, vlaků a lanových drah, strojově čitelná data (JDF, NeTEx) v adresáři /pub/","https://portal.cisjr.cz/"),

# ═══ 5. CRIME / IZS / VEŘEJNÁ BEZPEČNOST ═══
("5. Crime / IZS / bezpečnost","SFPD Crime Dashboard","sanfranciscopolice.org","Incident-level crime data SF s prostorovou složkou — referenční vzor crime dashboardu","https://www.sanfranciscopolice.org/stay-safe/crime-data/crime-dashboard"),
("5. Crime / IZS / bezpečnost","data.police.uk","data.police.uk","UK street-level crime + outcomes API, měsíční CSV s lat/lon a force area","https://data.police.uk/"),
("5. Crime / IZS / bezpečnost","Portál krizového řízení Stč. kraje","pkr.kr-stredocesky.cz","Zásahy jednotek požární ochrany — mapa a feed událostí IZS","https://pkr.kr-stredocesky.cz/"),
("5. Crime / IZS / bezpečnost","HZS Královéhradecký — Události","udalostikhk.hzscr.cz","Veřejný výpis zásahů HZS s lokalizací","https://udalostikhk.hzscr.cz/"),
("5. Crime / IZS / bezpečnost","HZS Vysočina — Webohled","webohled.hasici-vysocina.cz","Veřejný portál událostí hasičů kraje Vysočina — pozor, TLS certifikát vypršel v srpnu 2020 a je vystavený na jiný název","https://webohled.hasici-vysocina.cz/"),
("5. Crime / IZS / bezpečnost","NYC Open Data","opendata.cityofnewyork.us","Vzorový municipální portál — NYPD complaints, 311, PLUTO parcely","https://opendata.cityofnewyork.us/"),
("5. Crime / IZS / bezpečnost","Chicago Data Portal","data.cityofchicago.org","Crimes 2001-present s lat/lon — klasický dataset pro prostorovou analytiku","https://data.cityofchicago.org/"),
("5. Crime / IZS / bezpečnost","ACLED","acleddata.com","Armed Conflict Location & Event Data — georeferencované konflikty a protesty","https://acleddata.com/"),
("5. Crime / IZS / bezpečnost","GDELT","gdeltproject.org","Globální event database z médií s geokódováním, BigQuery dataset","https://www.gdeltproject.org/"),
("5. Crime / IZS / bezpečnost","Mapa kriminality (Policie ČR)","kriminalita.policie.gov.cz","Oficiální mapa kriminality Policie ČR — evidované a objasněné skutky podle druhu trestné činnosti a územních obvodů policie; aplikace vyžaduje JavaScript","https://kriminalita.policie.gov.cz/"),
("5. Crime / IZS / bezpečnost","GDACS","gdacs.org","Globální upozornění na katastrofy (EC-JRC a OSN) — zemětřesení, cyklóny, povodně a sopky s geodaty a odhadem zasažené populace","https://www.gdacs.org/"),
("5. Crime / IZS / bezpečnost","Copernicus EMS","emergency.copernicus.eu","Emergency Management Service — On-Demand Mapping satelitních map škod pro aktivované mimořádné události, povodně EFAS/GloFAS, sucho EDO/GDO a lesní požáry na forest-fire.emergency.copernicus.eu","https://emergency.copernicus.eu/"),
("5. Crime / IZS / bezpečnost","UCDP","ucdp.uu.se","Uppsala Conflict Data Program — georeferencovaná databáze událostí ozbrojených konfliktů (GED) od roku 1989, delší časová řada a jiná metodika kódování než ACLED","https://ucdp.uu.se/"),

# ═══ 6. REMOTE SENSING / RASTR ═══
("6. Remote sensing / rastr","Copernicus Data Space","dataspace.copernicus.eu","Sentinel-1/2/3/5P zdarma — browser, STAC, OData, S3 přístup","https://dataspace.copernicus.eu/"),
("6. Remote sensing / rastr","USGS EarthExplorer","earthexplorer.usgs.gov","Landsat archiv od 1972, letecké snímky, DEM","https://earthexplorer.usgs.gov/"),
("6. Remote sensing / rastr","NASA Earthdata","earthdata.nasa.gov","MODIS, VIIRS, SRTM, GPM, GRACE — CMR API","https://www.earthdata.nasa.gov/"),
("6. Remote sensing / rastr","OpenTopography","opentopography.org","LiDAR point clouds a globální DEM (SRTM, Copernicus DEM, ALOS)","https://opentopography.org/"),
("6. Remote sensing / rastr","Microsoft Planetary Computer","planetarycomputer.microsoft.com","STAC katalog a API nad otevřenými EO datasety (Sentinel, Landsat, NAIP, Copernicus DEM) — hostovaný JupyterHub byl vypnut v červnu 2024, data a API běží dál","https://planetarycomputer.microsoft.com/"),
("6. Remote sensing / rastr","Google Earth Engine","earthengine.google.com","Planetární petabajtový katalog s cloudovým zpracováním","https://earthengine.google.com/"),
("6. Remote sensing / rastr","ESA WorldCover","esa-worldcover.org","Globální land cover 10 m ze Sentinelu-1 a -2, 11 tříd — existují jen ročníky 2020 (v100) a 2021 (v200), novější nevznikly","https://esa-worldcover.org/"),
("6. Remote sensing / rastr","Copernicus Land Monitoring Service (CORINE)","land.copernicus.eu","Portál Copernicus Land Monitoring Service — CORINE Land Cover (referenční roky 1990-2018, aktualizace po šesti letech, poslední 2018) plus Urban Atlas, High Resolution Layers a CLCplus Backbone","https://land.copernicus.eu/"),
("6. Remote sensing / rastr","GHSL (Global Human Settlement)","human-settlement.emergency.copernicus.eu","Zastavěnost, populační rastr, urbanizace — JRC","https://human-settlement.emergency.copernicus.eu/"),
("6. Remote sensing / rastr","STAC Index","stacindex.org","Katalog veřejných STAC endpointů","https://stacindex.org/"),
("6. Remote sensing / rastr","ASF DAAC (Vertex)","asf.alaska.edu","NASA DAAC pro radarová data — archiv Sentinel-1 (včetně 1D) a NISAR, vyhledávač Vertex, Python asf_search a on-demand zpracování HyP3 (RTC, InSAR, OPERA RTC-S1)","https://asf.alaska.edu/"),
("6. Remote sensing / rastr","NASA FIRMS","firms.modaps.eosdis.nasa.gov","Detekce aktivních požárů a tepelných anomálií z MODIS (Aqua, Terra) a VIIRS (S-NPP, NOAA-20/21) do tří hodin od přeletu, pro USA a Kanadu v reálném čase — SHP/KML/TXT, WMS, API i e-mailové alerty","https://firms.modaps.eosdis.nasa.gov/"),
("6. Remote sensing / rastr","Vantor Open Data Program","vantor.com","Snímky WorldView ze zasažených oblastí zdarma pod CC BY-NC 4.0 (dřívější Maxar Open Data) — jen po aktivaci programu u velkých náhlých katastrof, ne souvislé pokrytí","https://vantor.com/company/open-data-program/"),
("6. Remote sensing / rastr","Global Nature Watch","globalnaturewatch.org","Nástupce Global Forest Watch od WRI — úbytek lesního krytu 30 m (UMD/Hansen, 2001-2025), integrované deforestační alerty 30 m aktualizované týdně a globální land cover, s mapou a otevřeným datovým portálem","https://globalnaturewatch.org/"),
("6. Remote sensing / rastr","Registry of Open Data on AWS","registry.opendata.aws","Rejstřík otevřených dat ležících na AWS S3 — Sentinel-2 COG se STACem, Landsat, NOAA GOES a stovky dalších v cloud-native formátech (COG, Zarr, NetCDF) čitelných přímo z GDAL přes /vsis3/","https://registry.opendata.aws/"),

# ═══ 7. STATISTIKA / DEMOGRAFIE ═══
("7. Statistika / demografie","ČSÚ","csu.gov.cz","ČSÚ Ceny nemovitostí — průměrné ceny rodinných domů a bytů a cenové indexy po krajích a okresech za tříleté klouzavé období","https://csu.gov.cz/"),
("7. Statistika / demografie","Eurostat GISCO","ec.europa.eu","Evropské admin hranice NUTS, populační grid 1 km, geodata ke statistice","https://ec.europa.eu/eurostat/web/gisco"),
("7. Statistika / demografie","EU Data Portal","data.europa.eu","Agregátor otevřených dat EU včetně INSPIRE geodatových sad","https://data.europa.eu/"),
("7. Statistika / demografie","WorldPop","worldpop.org","Rastr hustoty populace 100 m, věkové struktury, migrace","https://www.worldpop.org/"),
("7. Statistika / demografie","Kontur Population Dataset","data.humdata.org","H3-indexovaný globální populační dataset","https://data.humdata.org/dataset/kontur-population-dataset"),
("7. Statistika / demografie","Our World in Data","ourworldindata.org","Kurátorované country-level časové řady","https://ourworldindata.org/"),
("7. Statistika / demografie","ČSÚ Statistický geoportál","geodata.csu.gov.cz","Statistický geoportál ČSÚ — gridy SLDB 2021, ZSJ, registr sčítacích obvodů a budov (RSO) a hranice NUTS/LAU přes ArcGIS REST, WMS/WFS a INSPIRE služby","https://geodata.csu.gov.cz/"),
("7. Statistika / demografie","UN World Population Prospects","population.un.org","Odhady a projekce populace OSN po zemích do roku 2100 — věkové struktury, fertilita, mortalita a migrace, kompletní datové sady ke stažení","https://population.un.org/wpp/"),
("7. Statistika / demografie","OECD Data Explorer","data-explorer.oecd.org","Statistiky OECD včetně regionálních ukazatelů TL2/TL3 a metropolitních areálů — strojový přístup přes SDMX API na sdmx.oecd.org","https://data-explorer.oecd.org/"),
("7. Statistika / demografie","IPUMS International","international.ipums.org","Harmonizovaná census mikrodata ze 104 zemí (656 sčítání) včetně hranic administrativních jednotek — zdarma, ale až po registraci a schválení účelu použití","https://international.ipums.org/international/"),

# ═══ 8. HISTORICKÉ MAPY ═══
("8. Historické mapy","David Rumsey Map Collection","davidrumsey.com","Přes 150 000 naskenovaných map a atlasů online s IIIF — georeferencovaná přes Georeferencer je jen část sbírky","https://www.davidrumsey.com/"),
("8. Historické mapy","Old Maps Online","oldmapsonline.org","Meta-vyhledávač historických map podle místa a času","https://www.oldmapsonline.org/"),
("8. Historické mapy","Mapire (Arcanum Maps)","maps.arcanum.com","Habsburská vojenská mapování (I.-III.) georeferencovaná — ideální pro ČR","https://maps.arcanum.com/en/"),
("8. Historické mapy","Archivní mapy ČÚZK","ags.cuzk.gov.cz","Archivní mapy ČÚZK — císařské otisky a indikační skici stabilního katastru, stará státní mapová díla a archiv leteckých měřických snímků od roku 1936","https://ags.cuzk.gov.cz/archiv/"),
("8. Historické mapy","Chartae Antiquae","chartae-antiquae.cz","Virtuální mapová sbírka historických map ČR","https://www.chartae-antiquae.cz/cs/"),
("8. Historické mapy","National Library of Scotland — Map Images","maps.nls.uk","Zoomovatelné mapy Britských ostrovů 16.–20. století, velká část georeferencovaná — side-by-side a spyglass prohlížeč, vrstvy použitelné jako XYZ v QGIS přes Historic Maps API","https://maps.nls.uk/"),
("8. Historické mapy","Allmaps","allmaps.org","Georeferencování IIIF map přímo v prohlížeči — editor, viewer a tile server, který z Georeference Annotation udělá XYZ vrstvu pro QGIS, MapLibre, OpenLayers i Leaflet bez vytváření GeoTIFFů","https://allmaps.org/"),
("8. Historické mapy","USGS topoView","ngmdb.usgs.gov","Přes 178 000 historických topografických map USGS z let 1884–2006 — zdarma ke stažení jako GeoTIFF, GeoPDF, KMZ nebo JPEG","https://ngmdb.usgs.gov/topoview/"),
("8. Historické mapy","Library of Congress — Maps","loc.gov","Mapová sbírka Geography & Map Division včetně požárních plánů Sanborn — velká část public domain, ke stažení až v plném TIFF","https://www.loc.gov/maps/"),

# ═══ 9. MAPOVÉ KNIHOVNY, BASEMAPY, RENDERING ═══
("9. Mapové knihovny / basemapy","MapLibre GL JS","maplibre.org","OSS fork Mapbox GL — vektorové dlaždice, WebGL, style spec","https://maplibre.org/"),
("9. Mapové knihovny / basemapy","Leaflet","leafletjs.com","Lehká JS mapová knihovna, de facto standard pro rychlé mapy","https://leafletjs.com/"),
("9. Mapové knihovny / basemapy","deck.gl","deck.gl","WebGL vrstvy pro miliony bodů, integrace s MapLibre a Kepler","https://deck.gl/"),
("9. Mapové knihovny / basemapy","OpenLayers","openlayers.org","Plnotučná knihovna s WMS/WFS/WMTS a projekcemi","https://openlayers.org/"),
("9. Mapové knihovny / basemapy","sigma.js + @sigma/layer-maplibre","sigmajs.org","Graf rendering nad mapou — kombinace síťové a prostorové analýzy. Hodně jsi to procházel","https://www.sigmajs.org/"),
("9. Mapové knihovny / basemapy","Protomaps / PMTiles","protomaps.com","Jednosouborové dlaždice bez serveru, hostovatelné na S3/CDN","https://protomaps.com/"),
("9. Mapové knihovny / basemapy","MapTiler","maptiler.com","Hostované vektorové basemapy, styly, self-hosted server","https://www.maptiler.com/"),
("9. Mapové knihovny / basemapy","OpenFreeMap","openfreemap.org","Zdarma hostované OSM vektorové dlaždice bez API klíče","https://openfreemap.org/"),
("9. Mapové knihovny / basemapy","Stadia Maps","stadiamaps.com","Basemapy, geokódování a routing s férovým free tierem","https://stadiamaps.com/"),
("9. Mapové knihovny / basemapy","Turf.js","turfjs.org","Geoprostorová analýza v JS — buffer, intersect, nearest, clusters","https://turfjs.org/"),
("9. Mapové knihovny / basemapy","CesiumJS","cesium.com","3D glóbus a mapy ve WebGL — 3D Tiles, globální terén, glTF modely a časová osa; knihovna pod Apache 2.0, hostované služby ion placené","https://cesium.com/platform/cesiumjs/"),
("9. Mapové knihovny / basemapy","MapProxy","mapproxy.org","Proxy a dlaždicová cache nad WMS — z pomalé WMS udělá rychlé WMTS/XYZ dlaždice, umí reprojekci, slučování vrstev a offline seeding","https://mapproxy.org/"),
("9. Mapové knihovny / basemapy","OpenMapTiles","openmaptiles.org","Otevřené schéma vektorových dlaždic z OSM a Natural Earth — nástroje na generování vlastních dlaždic a self-hosting, BSD/CC-BY s povinnou atribucí","https://openmaptiles.org/"),
("9. Mapové knihovny / basemapy","Mapbox","mapbox.com","Komerční mapová platforma — hostované vektorové a satelitní basemapy, Studio pro tvorbu stylů a Mapbox GL JS (od v2 proprietární licence); free tier s měsíčním limitem","https://www.mapbox.com/"),
("9. Mapové knihovny / basemapy","OpenTopoMap","opentopomap.org","Topografická rastrová basemapa z OSM a SRTM ve stylu německých topo map — vrstevnice a stínovaný reliéf, dlaždice bez API klíče pod CC-BY-SA 3.0","https://opentopomap.org/"),

# ═══ 10. SPATIAL DB, ANALYTIKA, ZPRACOVÁNÍ ═══
("10. Spatial DB / analytika","PostGIS","postgis.net","Prostorové rozšíření PostgreSQL — typy geometry a geography a GiST indexy; rastr a topologie se instalují jako samostatné extenze (postgis_raster, postgis_topology), pgRouting je samostatný projekt","https://postgis.net/"),
("10. Spatial DB / analytika","PostgreSQL","postgresql.org","Hostitelská DB pro PostGIS","https://www.postgresql.org/"),
("10. Spatial DB / analytika","GDAL / OGR","gdal.org","Univerzální konverze a transformace — ogr2ogr, gdalwarp, gdal_translate","https://gdal.org/"),
("10. Spatial DB / analytika","QGIS","qgis.org","Desktopové GIS — vizualizace, editace, Processing toolbox, modely","https://qgis.org/"),
("10. Spatial DB / analytika","GeoPandas","geopandas.org","Pandas s geometrií (Shapely + pyproj + pyogrio) — základ Python geo analytiky","https://geopandas.org/"),
("10. Spatial DB / analytika","Shapely","shapely.readthedocs.io","Planární geometrické operace v Pythonu nad GEOS","https://shapely.readthedocs.io/"),
("10. Spatial DB / analytika","Rasterio","rasterio.readthedocs.io","Pythonic čtení a zápis rastrů nad GDAL","https://rasterio.readthedocs.io/"),
("10. Spatial DB / analytika","rioxarray","corteva.github.io","Multidimenzionální rastr a časové řady pro EO analytiku","https://corteva.github.io/rioxarray/"),
("10. Spatial DB / analytika","DuckDB spatial","duckdb.org","In-process SQL analytika s prostorovým rozšířením, čte GeoParquet i přímo z S3","https://duckdb.org/docs/current/core_extensions/spatial/overview"),
("10. Spatial DB / analytika","Apache Sedona","sedona.apache.org","Distribuovaná prostorová analytika nad Sparkem/Flinkem","https://sedona.apache.org/"),
("10. Spatial DB / analytika","H3","h3geo.org","Hierarchický index nad hexagonální sítí (na každé úrovni 12 pětiúhelníků) — agregace bodů, sousedství, gridDisk","https://h3geo.org/"),
("10. Spatial DB / analytika","S2 Geometry","s2geometry.io","Sférická geometrie a indexování buňkami, alternativa k H3","https://s2geometry.io/"),
("10. Spatial DB / analytika","PySAL","pysal.org","Prostorová statistika — autokorelace, Moran's I, LISA, regionalizace","https://pysal.org/"),
("10. Spatial DB / analytika","MovingPandas","movingpandas.org","Analýza trajektorií a pohybu nad GeoPandas","https://movingpandas.org/"),
("10. Spatial DB / analytika","Lonboard","developmentseed.org","Rychlá vizualizace velkých GeoDataFrames v notebooku přes deck.gl","https://developmentseed.org/lonboard/"),
("10. Spatial DB / analytika","Kepler.gl","kepler.gl","Geo-analytické UI nad deck.gl pro rychlý průzkum velkých datasetů","https://kepler.gl/"),
("10. Spatial DB / analytika","CARTO","carto.com","Cloud location intelligence nad Snowflake/BigQuery/Databricks","https://carto.com/"),
("10. Spatial DB / analytika","Felt","felt.com","Kolaborativní webové mapy, rychlé sdílení analýz","https://felt.com/"),
("10. Spatial DB / analytika","GRASS GIS","grass.osgeo.org","Rastrová, terénní a hydrologická analytika s vlastní datovou strukturou (moduly r.*, v.*) — sklony, povodí, viewshed a časové řady, volatelné i z QGIS Processingu","https://grass.osgeo.org/"),
("10. Spatial DB / analytika","sf (Simple Features for R)","r-spatial.github.io","Simple features pro R — geometrie jako sloupec v data.frame, operace přes GEOS, čtení a zápis přes GDAL, transformace přes PROJ, sférická geometrie přes s2","https://r-spatial.github.io/sf/"),
("10. Spatial DB / analytika","PDAL","pdal.org","Pipeline pro zpracování mračen bodů — čtení LAS/LAZ/COPC, filtrace a klasifikace, výřezy a převod na rastr, deklarativně v JSON","https://pdal.org/"),
("10. Spatial DB / analytika","GEOS","libgeos.org","C/C++ knihovna geometrických predikátů a operací (intersects, buffer, overlay, validace) — jádro, na kterém stojí PostGIS, QGIS, GDAL, Shapely i R sf","https://libgeos.org/"),
("10. Spatial DB / analytika","xarray","xarray.dev","Pojmenovaná N-rozměrná pole s indexy a líným výpočtem přes Dask — datový model pro EO časové řady a datové kostky, čte NetCDF, HDF, Zarr i GRIB","https://xarray.dev/"),

# ═══ 11. ROUTING / SÍŤOVÁ ANALÝZA ═══
("11. Routing / síťová analýza","OSRM","project-osrm.org","Rychlý routing nad OSM — table (matrix), match, trip","https://project-osrm.org/"),
("11. Routing / síťová analýza","Valhalla","valhalla.github.io","Tile-based routing, isochrony, map-matching, multimodal","https://valhalla.github.io/valhalla/"),
("11. Routing / síťová analýza","GraphHopper","graphhopper.com","Routing engine + isochrony, dobrá Java knihovna i API","https://www.graphhopper.com/"),
("11. Routing / síťová analýza","pgRouting","pgrouting.org","Routing přímo v PostGIS — Dijkstra, TSP, driving distance","https://pgrouting.org/"),
("11. Routing / síťová analýza","OSMnx","osmnx.readthedocs.io","Stažení a analýza uličních sítí z OSM v Pythonu (NetworkX)","https://osmnx.readthedocs.io/"),
("11. Routing / síťová analýza","R5 / Conveyal","conveyal.com","Multimodální dostupnostní analýza nad GTFS + OSM","https://conveyal.com/"),
("11. Routing / síťová analýza","OpenTripPlanner","opentripplanner.org","Multimodální plánovač spojení nad GTFS a OSM — itineráře MHD s přestupy a dostupnostní analýzy přes GraphQL API (GTFS i Transmodel)","https://www.opentripplanner.org/"),
("11. Routing / síťová analýza","openrouteservice","openrouteservice.org","Hostované routovací API nad OSM od HeiGIT — trasy, matice vzdáleností, isochrony, výškové profily a optimalizace rozvozu, s bezplatnou vrstvou po registraci klíče i možností self-hostingu","https://openrouteservice.org/"),
("11. Routing / síťová analýza","NetworkX","networkx.org","Grafové algoritmy v Pythonu — nejkratší cesty, centrality, komponenty a toky; datová struktura, ve které OSMnx vrací uliční síť","https://networkx.org/documentation/stable/"),
("11. Routing / síťová analýza","Google OR-Tools","developers.google.com","Solver na okružní a rozvozní úlohy — TSP a VRP s časovými okny, kapacitami a více vozidly, typicky nad maticí jízdních dob z OSRM nebo Valhally","https://developers.google.com/optimization"),
("11. Routing / síťová analýza","Pandana","udst.github.io","Výpočet dostupnosti v síti přes contraction hierarchies — agregace POI a vah do vzdálenostních pásem kolem každého uzlu, řádově rychleji než obyčejný Dijkstra","https://udst.github.io/pandana/"),

# ═══ 12. FORMÁTY, PROJEKCE, STANDARDY ═══
("12. Formáty / projekce / standardy","EPSG.io","epsg.io","Vyhledávání souřadnicových systémů, WKT/proj4 definice (S-JTSK = 5514)","https://epsg.io/"),
("12. Formáty / projekce / standardy","PROJ","proj.org","Knihovna transformací souřadnicových systémů","https://proj.org/"),
("12. Formáty / projekce / standardy","GeoJSON (RFC 7946)","geojson.org","Specifikace nejběžnějšího výměnného formátu","https://geojson.org/"),
("12. Formáty / projekce / standardy","GeoParquet","geoparquet.org","Sloupcový formát pro velké geodatové sady, čitelný DuckDB i Sedonou","https://geoparquet.org/"),
("12. Formáty / projekce / standardy","Cloud Optimized GeoTIFF","cogeo.org","COG — rastr čitelný po částech přímo z HTTP/S3","https://www.cogeo.org/"),
("12. Formáty / projekce / standardy","FlatGeobuf","flatgeobuf.org","Binární streamovatelný vektorový formát s prostorovým indexem","https://flatgeobuf.org/"),
("12. Formáty / projekce / standardy","OGC API","ogcapi.ogc.org","Moderní REST nástupci WMS/WFS — Features, Tiles, Processes","https://ogcapi.ogc.org/"),
("12. Formáty / projekce / standardy","STAC","stacspec.org","SpatioTemporal Asset Catalog — standard pro katalogizaci EO dat","https://stacspec.org/"),
("12. Formáty / projekce / standardy","GeoPackage","geopackage.org","OGC standard (adoptovaná verze 1.4.0) — jeden SQLite soubor s vektory, dlaždicemi i atributy, výchozí výstupní formát QGIS a náhrada za Shapefile","https://www.geopackage.org/"),
("12. Formáty / projekce / standardy","EPSG Registry (IOGP)","epsg.org","Oficiální registr EPSG Geodetic Parameter Dataset od IOGP (v13.102) — primární zdroj, ze kterého žijí epsg.io i PROJ; online vyhledávání zdarma, offline export datasetu, datový model dle ISO 19111:2019","https://epsg.org/"),
("12. Formáty / projekce / standardy","Zarr","zarr.dev","Formát pro chunkovaná komprimovaná N-rozměrná pole v object storage (v2/v3, implementace v 10 jazycích) — základ cloud-native klimatických a EO datasetů čtených přes xarray","https://zarr.dev/"),
("12. Formáty / projekce / standardy","COPC","copc.io","Cloud Optimized Point Cloud 1.0 — LAZ 1.4 s body uspořádanými do clusterovaného oktree, čitelný po částech přes HTTP range requesty, podporuje PDAL i QGIS","https://copc.io/"),
("12. Formáty / projekce / standardy","GTFS","gtfs.org","Referenční specifikace GTFS Schedule a GTFS Realtime pod správou MobilityData — jízdní řády, zastávky, tarify a živé polohy vozidel","https://gtfs.org/"),

# ═══ 13. OPEN DATA / REGISTRY CZ (OSINT overlap) ═══
("13. Open data / registry CZ","Národní katalog otevřených dat","data.gov.cz","Centrální CZ katalog datových sad včetně geodat a INSPIRE","https://data.gov.cz/"),
("13. Open data / registry CZ","Hlídač státu","hlidacstatu.cz","Smlouvy, dotace, zakázky, politici — API V2. Máš registrovaný účet","https://www.hlidacstatu.cz/"),
("13. Open data / registry CZ","Registr smluv","smlouvy.gov.cz","Otevřený registr smluv státu","https://smlouvy.gov.cz/"),
("13. Open data / registry CZ","ARES","ares.gov.cz","Ekonomické subjekty ČR — REST API, adresy sídel (geokódovatelné)","https://ares.gov.cz/"),
("13. Open data / registry CZ","Obchodní rejstřík","or.justice.cz","Veřejný rejstřík — vazby, sídla, statutáři","https://or.justice.cz/"),
("13. Open data / registry CZ","ISIR","isir.justice.cz","Insolvenční rejstřík","https://isir.justice.cz/"),
("13. Open data / registry CZ","Evidence skutečných majitelů","esm.justice.cz","Rejstřík skutečných majitelů obchodních korporací a svěřenských fondů (MSp) — kdo za firmou reálně stojí za nastrčenými statutáry","https://esm.justice.cz/"),
("13. Open data / registry CZ","Registr živnostenského podnikání","rzp.gov.cz","Živnostenská oprávnění fyzických i právnických osob — včetně seznamu provozoven s adresami (geokódovatelné)","https://rzp.gov.cz/"),
("13. Open data / registry CZ","Monitor státní pokladny","monitor.statnipokladna.gov.cz","Rozpočty a účetní výkazy obcí, krajů a státních institucí — včetně ročních dumpů ke stažení","https://monitor.statnipokladna.gov.cz/"),
("13. Open data / registry CZ","Národní elektronický nástroj (NEN)","nen.nipez.cz","Systém MMR pro zadávání veřejných zakázek — zadávací řízení, profily zadavatelů a registry dodavatelů, přístupné bez přihlášení","https://nen.nipez.cz/"),
("13. Open data / registry CZ","Nabídka majetku státu (ÚZSVM)","nabidkamajetku.gov.cz","Katalog ÚZSVM s nabídkami státního majetku — prodeje, elektronické dražby a pronájmy nemovitostí, filtrovatelné podle kraje a obce","https://nabidkamajetku.gov.cz/"),

# ═══ 14. OSINT / INVESTIGACE (tvoje projekty a nástroje) ═══
("14. OSINT / investigace","Progresus OSINT","osint.cloud.progresus.cz","Tvoje platforma pro due diligence z veřejných zdrojů — zdroje, laboratoř, architektura","https://osint.cloud.progresus.cz/"),
("14. OSINT / investigace","vomaste.cz","vomaste.cz","Tvůj projekt — Registr tvrzení / zdrojů / kauz, dossiery, Globální mapa","https://vomaste.cz/"),
("14. OSINT / investigace","Situační radar (HzsRadar)","situacni-radar.fly.dev","Tvoje agregace událostí IZS v Phoenixu","https://situacni-radar.fly.dev/"),
("14. OSINT / investigace","Maltego","maltego.com","Link-analysis platforma pro OSINT vyšetřování","https://www.maltego.com/"),
("14. OSINT / investigace","OpenAlex","openalex.org","Otevřený katalog vědeckých prací s afiliacemi institucí (geokódovatelné)","https://openalex.org/"),
("14. OSINT / investigace","Common Crawl","commoncrawl.org","Otevřený webový crawl korpus","https://commoncrawl.org/"),
("14. OSINT / investigace","North Data","northdata.com","Firemní rejstříky, účetní závěrky a vazby osob a firem ve 26 zemích Evropy včetně ČR (v záběru je i Izrael)","https://www.northdata.com/"),
("14. OSINT / investigace","Investigace.cz","investigace.cz","České centrum investigativní žurnalistiky (OCCRP)","https://www.investigace.cz/"),
("14. OSINT / investigace","OpenSanctions","opensanctions.org","Sankční seznamy, PEP a watchlisty z ~460 zdrojů (přes 1,9 mil. entit) — bulk data ve FollowTheMoney i screening API; zdarma pro nekomerční užití, komerčně za licenci","https://www.opensanctions.org/"),
("14. OSINT / investigace","ICIJ Offshore Leaks Database","offshoreleaks.icij.org","Přes 810 tisíc offshore entit z Pandora, Paradise, Panama Papers, Bahamas Leaks a Offshore Leaks — ke stažení pod ODbL i přes REST API","https://offshoreleaks.icij.org/"),
("14. OSINT / investigace","Bellingcat","bellingcat.com","Investigace z otevřených zdrojů — metodický toolkit pro geolokaci a verifikaci snímků a videí","https://www.bellingcat.com/"),
("14. OSINT / investigace","ADS-B Exchange","adsbexchange.com","Nefiltrované sledování letadel z komunitní sítě 25 tis. přijímačů — veřejná mapa zdarma, historická data, API, gRPC stream a S3 jen za placené předplatné","https://www.adsbexchange.com/"),
("14. OSINT / investigace","Global Fishing Watch","globalfishingwatch.org","Pohyb plavidel z AIS a satelitní detekce — mapa, Vessel Viewer a datasety; API zdarma, ale až po registraci a vydání tokenu","https://globalfishingwatch.org/"),

# ═══ 15. POČASÍ / KLIMA ═══
("15. Počasí / klima","ČHMÚ","chmi.cz","Předpovědi, radar, srážky, hydrologie; otevřená data na opendata.chmi.cz","https://www.chmi.cz/"),
("15. Počasí / klima","Meteoradar.cz","meteoradar.cz","Online srážkový radar ČR a Evropa","https://www.meteoradar.cz/"),
("15. Počasí / klima","In-počasí","in-pocasi.cz","Předpovědi, radar, síť stanic","https://www.in-pocasi.cz/"),
("15. Počasí / klima","Copernicus Climate Data Store","cds.climate.copernicus.eu","ERA5 reanalýza, klimatické projekce, API","https://cds.climate.copernicus.eu/"),
("15. Počasí / klima","Open-Meteo","open-meteo.com","Free weather API bez klíče, historická i předpovědní data po souřadnicích","https://open-meteo.com/"),
("15. Počasí / klima","WorldClim","worldclim.org","Globální klimatické rastry — měsíční srážky a teploty a 19 bioklimatických proměnných v rozlišení 30 s až 10 min, historie i budoucí scénáře","https://worldclim.org/"),
("15. Počasí / klima","ECMWF Open Data","ecmwf.int","Otevřená část předpovědí ECMWF (IFS a AIFS) v GRIB2 pod CC BY 4.0 — datový endpoint data.ecmwf.int agresivně rate-limituje, přes klienta ecmwf-opendata to jde lépe než ručně","https://www.ecmwf.int/en/forecasts/datasets/open-data"),
("15. Počasí / klima","NOAA NOMADS","nomads.ncep.noaa.gov","Operativní modely NCEP (GFS, GEFS, HRRR) v GRIB2 a přes OPeNDAP — včetně částečného stahování polí přes filtry","https://nomads.ncep.noaa.gov/"),
("15. Počasí / klima","Copernicus Atmosphere Data Store","ads.atmosphere.copernicus.eu","CAMS analýzy a předpovědi kvality ovzduší, aerosolů a složení atmosféry — stejné katalogové rozhraní, API i earthkit jako Climate Data Store","https://ads.atmosphere.copernicus.eu/"),
("15. Počasí / klima","Klimatická změna (CzechGlobe)","klimatickazmena.cz","Klimatický portál Ústavu výzkumu globální změny AV ČR — mapy, grafy a infografiky ke klimatu ČR: pozorované změny, scénáře a dopady na lesnictví, zemědělství a vodní prostředí","https://www.klimatickazmena.cz/"),

# ═══ 16. NEMOVITOSTI / TRH (prostorová složka) ═══
("16. Nemovitosti / trh","Sreality","sreality.cz","CZ inzerce s geokódovanými nabídkami","https://www.sreality.cz/"),
("16. Nemovitosti / trh","Flat Zone","flatzone.cz","Vyhledávač novostaveb a developerských projektů v ČR — odhad ceny a datová platforma; B2B větev běží na b2b.flatzone.cz (dataligence.cz tam dnes redirectuje)","https://www.flatzone.cz/"),
("16. Nemovitosti / trh","ČSÚ — Ceny nemovitostí","csu.gov.cz","Ceny nemovitostí 2022-2024 podle území — v historii máš přesně tuhle stránku","https://csu.gov.cz/produkty/ceny-nemovitosti"),
("16. Nemovitosti / trh","CBRE","cbre.cz","Komerční realitní analytika a market reporty","https://www.cbre.cz/"),
("16. Nemovitosti / trh","Bezrealitky","bezrealitky.cz","CZ inzerce prodeje a pronájmu bez provize — velký podíl přímých majitelů, mutace SK a EN","https://www.bezrealitky.cz/"),
("16. Nemovitosti / trh","Valuo","valuo.cz","Odhady cen nemovitostí v ČR — mapa realizovaných prodejů z katastru a inzerce a cenový index; mapa a odhad zdarma, PROFI a API za 5 000–10 000 Kč/rok bez DPH","https://www.valuo.cz/"),
("16. Nemovitosti / trh","ČNB — finanční stabilita","cnb.cz","Zprávy o finanční stabilitě, zátěžové testy a limity úvěrových ukazatelů LTV, DTI a DSTI — makro pohled na trh bydlení","https://www.cnb.cz/cs/financni-stabilita/"),

# ═══ 17. UČENÍ / KOMUNITA ═══
("17. Učení / komunita","UofT Map and Data Library","mdl.library.utoronto.ca","Mapová a datová knihovna University of Toronto — veřejná knihovna návodů a workshopů ke GIS a statistice; většina datových sad je přístupná jen příslušníkům univerzity","https://mdl.library.utoronto.ca/"),
("17. Učení / komunita","GIS StackExchange","gis.stackexchange.com","Nejrychlejší cesta k odpovědi na konkrétní GIS problém","https://gis.stackexchange.com/"),
("17. Učení / komunita","Awesome Geospatial","github.com","Kurátorovaný seznam geo nástrojů a datasetů","https://github.com/sacridini/Awesome-Geospatial"),
("17. Učení / komunita","Observable","observablehq.com","D3 notebooky — kartografické projekce a vizualizace","https://observablehq.com/"),
("17. Učení / komunita","Spatial Thoughts","spatialthoughts.com","Kvalitní kurzy QGIS, GEE a Python geo","https://spatialthoughts.com/"),
("17. Učení / komunita","OSGeo","osgeo.org","Nadace zastřešující ~50 open source geo projektů (QGIS, GDAL, PostGIS, GeoServer, GRASS, pgRouting) — pořádá konferenci FOSS4G, vydává OSGeoLive a sdružuje lokální chaptery","https://www.osgeo.org/"),
("17. Učení / komunita","OpenStreetMap Wiki","wiki.openstreetmap.org","Referenční dokumentace tagovacího schématu OSM — co který key a value znamená a jak se regionálně používá; bez ní se Overpass dotaz nedá napsat","https://wiki.openstreetmap.org/"),
("17. Učení / komunita","geocompx (Geocomputation with R / Python)","geocompx.org","Volně dostupné učebnice Geocomputation with R (CC-BY-NC-ND) a Geocomputation with Python — plus rozpracované verze pro Julii a tmap","https://geocompx.org/"),
("17. Učení / komunita","Introduction to Python for Geographic Data Analysis","pythongis.org","Volná online učebnice (Tenkanen, Heikinheimo, Whipp) od základů Pythonu po GIS s geopandas a shapely, CC 4.0","https://pythongis.org/"),
("17. Učení / komunita","Anita Graser — Free and Open Source GIS Ramblings","anitagraser.com","Blog autorky MovingPandas — QGIS, PyQGIS, Trajectools a analýza pohybových dat","https://anitagraser.com/"),
]

DATA.mkdir(exist_ok=True)
with open(DATA/"catalog.csv","w",newline='',encoding='utf-8-sig') as fh:
    w=csv.writer(fh)
    w.writerow(["Kategorie","Web","Doména","Popis","Zdroj","Návštěvy","Unikátních URL","Poslední návštěva","URL"])
    for cat,name,dom,desc,url in C:
        sr,v,nu,last = evidence(url,dom)
        w.writerow([cat,name,dom,desc,sr,v,nu,last,url])

own=sum(1 for c in C if evidence(c[4],c[2])[0]!='reference')
print(f"curated: {len(C)}  (z toho {own} doložených z tvých dat, {len(C)-own} doplněných referenčně)")

cand=json.load(open(CACHE/"candidates.json", encoding="utf-8"))
NOISE=re.compile(r"google\.com|accounts\.|signin|login|auth|aws\.amazon|slack|atlassian|microsoft|claude|openai|chatgpt|facebook|linkedin|youtube|spotify|github|gitlab|bitbucket|docusign|stripe|godaddy|localhost|ngrok|proton|icloud|apple|netflix|zoom|revolut|temu|ebay|cloudflare|docker|tailscale|awstrack|twimg|licdn|fbcdn|afcdn|slack-edge|gemius|go2cloud",re.I)
# Syrový long list obsahuje nefiltrovanou historii — zůstává v .cache/,
# která je v .gitignore. Do data/ se dostane až po sanitize.py.
with open(CACHE/"longlist.raw.csv","w",newline='',encoding='utf-8-sig') as fh:
    w=csv.writer(fh)
    w.writerow(["Doména","Návštěvy","Unikátních URL","V záložkách","Z historie","Poslední návštěva","Ukázkový titulek","Ukázková URL"])
    n=0
    for d,e in cand.items():
        if NOISE.search(d): continue
        t=collections.Counter(e['titles']).most_common(1)
        w.writerow([d,e['visits'],len(e['urls']),e['bm'],e['hist'],e['last'][:10],
                    t[0][0] if t else '', sorted(e['urls'])[0][:150]])
        n+=1
print("longlist:",n)
