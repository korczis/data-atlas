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
("1. Gazetteer / geokódování","GeoNames","geonames.org","Globální gazetteer, 12M+ toponym, admin hierarchie ADM1-4, alternate names, populace. Dumpy zdarma (allCountries.zip)","https://www.geonames.org/"),
("1. Gazetteer / geokódování","Pelias","pelias.io","Modulární OSS geocoder (OSM + WOF + OpenAddresses + Geonames), Elasticsearch backend","https://pelias.io/"),
("1. Gazetteer / geokódování","Who's on First","whosonfirst.org","Gazetteer admin i POI entit se stabilními ID a hierarchií, podklad Pelias","https://whosonfirst.org/"),
("1. Gazetteer / geokódování","OpenAddresses","openaddresses.io","Agregované otevřené adresní body globálně, CSV s lat/lon","https://openaddresses.io/"),
("1. Gazetteer / geokódování","RÚIAN / VDP ČÚZK","vdp.cuzk.cz","Autoritativní CZ registr adres a územní identifikace — výměnný formát, adresní body, definiční body parcel","https://vdp.cuzk.cz/"),
("1. Gazetteer / geokódování","Mapy.cz Developer API","developer.mapy.cz","CZ geokódování, suggest, routing, dlaždice. Máš tam aktivní projekt s consumption trackingem","https://developer.mapy.com/"),
("1. Gazetteer / geokódování","Photon","photon.komoot.io","Rychlý OSM geocoder s type-ahead, snadný self-hosting","https://photon.komoot.io/"),

# ═══ 2. GLOBÁLNÍ REFERENČNÍ GEODATA ═══
("2. Globální geodata","Natural Earth","naturalearthdata.com","Public-domain vektor + raster v 1:10m/50m/110m — hranice, pobřeží, řeky, města, stínovaný reliéf. Kartografický základ","https://www.naturalearthdata.com/"),
("2. Globální geodata","World Factbook Archive","worldfactbookarchive.org","Archivní ročníky CIA World Factbooku — časové řady country-level dat","https://worldfactbookarchive.org/"),
("2. Globální geodata","CIA World Factbook","cia.gov","Aktuální country profily: geografie, demografie, ekonomika, komunikace","https://www.cia.gov/the-world-factbook/"),
("2. Globální geodata","GADM","gadm.org","Administrativní hranice všech zemí do úrovně ADM3-5, GeoPackage/shp","https://gadm.org/"),
("2. Globální geodata","geoBoundaries","geoboundaries.org","Otevřená alternativa GADM s jasnou licencí a verzováním","https://www.geoboundaries.org/"),
("2. Globální geodata","US Census TIGER/Line","census.gov","TIGER/Line shapefiles — US hranice, ulice, bloky, ZCTA, tracts (\"geotiger\")","https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html"),
("2. Globální geodata","Overture Maps Foundation","overturemaps.org","Otevřená základní data: places, buildings, transportation, divisions, base. Distribuce v GeoParquet","https://overturemaps.org/"),
("2. Globální geodata","Geofabrik Downloads","download.geofabrik.de","Denní OSM extrakty po zemích a regionech (.osm.pbf, .shp.zip)","https://download.geofabrik.de/"),
("2. Globální geodata","OpenStreetMap","openstreetmap.org","Základní vrstva všeho — editace, historie, export","https://www.openstreetmap.org/"),
("2. Globální geodata","Overpass Turbo","overpass-turbo.eu","Interaktivní dotazování OSM podle tagů, bboxu, relací; export GeoJSON","https://overpass-turbo.eu/"),
("2. Globální geodata","HDX (UN OCHA)","data.humdata.org","Humanitarian Data Exchange — COD admin boundaries, populace, infrastruktura","https://data.humdata.org/"),
("2. Globální geodata","OpenCelliD","opencellid.org","Otevřená databáze pozic BTS/cell towers — užitečné pro geolokaci","https://opencellid.org/"),

# ═══ 3. ČR — KATASTR A NÁRODNÍ GEODATA ═══
("3. ČR — katastr a geodata","ČÚZK — Dálkový přístup do KN","katastr.cuzk.gov.cz","Dálkový přístup ke katastru nemovitostí. Nejnavštěvovanější geo zdroj v tvé historii","https://katastr.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","Nahlížení do KN","nahlizenidokn.cuzk.gov.cz","Veřejné nahlížení — parcely, budovy, LV, vlastníci; má i jednoduché API","https://nahlizenidokn.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","SGI Nahlížení do KN","sgi-nahlizenidokn.cuzk.gov.cz","Grafická část — katastrální mapa, mapové služby","https://sgi-nahlizenidokn.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","Geoportál ČÚZK","geoportal.cuzk.cz","WMS/WFS/WMTS, ZABAGED, Ortofoto ČR, DMR 5G/DMP 1G, Data50/200. Klíčový CZ zdroj","https://geoportal.cuzk.cz/"),
("3. ČR — katastr a geodata","ČÚZK — Žádosti","zadosti.cuzk.gov.cz","Objednávky výstupů a datových sad","https://zadosti.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","ČÚZK (rozcestník)","cuzk.gov.cz","Hlavní web zeměměřického a katastrálního úřadu","https://www.cuzk.gov.cz/"),
("3. ČR — katastr a geodata","Národní geoportál INSPIRE (CENIA)","geoportal.gov.cz","CZ INSPIRE katalog — metadata a služby napříč resorty, včetně historického ortofota z 50. let","https://geoportal.gov.cz/"),
("3. ČR — katastr a geodata","ArcČR (ARCDATA Praha)","arcdata.cz","Volně dostupná digitální geografická databáze ČR — administrativní členění, sídla, vodstvo, doprava; navazuje na ArcČR 500","https://www.arcdata.cz/cs-cz/produkty/data/arccr"),
("3. ČR — katastr a geodata","DIBAVOD (VÚV TGM)","dibavod.cz","Digitální báze vodohospodářských dat — povodí, vodní toky, nádrže","https://www.dibavod.cz/"),
("3. ČR — katastr a geodata","AOPK — Ochrana přírody","gis-aopk.opendata.arcgis.com","Chráněná území, Natura 2000, biotopy jako open data","https://gis-aopk.opendata.arcgis.com/"),
("3. ČR — katastr a geodata","LPIS / eAGRI","eagri.cz","Zemědělské půdní bloky, využití půdy, WMS/WFS","https://mze.gov.cz/public/app/lpisext/lpis/verejny2/plpis/"),
("3. ČR — katastr a geodata","Česká geologická služba","mapy.geology.cz","Geologické, hydrogeologické a půdní mapy, sesuvy, poddolování","https://mapy.geology.cz/"),
("3. ČR — katastr a geodata","Geoportál Praha","geoportalpraha.cz","Pražská geodata a open data — ortofota, územní plán, 3D model","https://www.geoportalpraha.cz/"),

# ═══ 4. ČR — DOPRAVA A MOBILITA ═══
("4. ČR — doprava / mobilita","Golemio (Praha)","golemio.cz","Datová platforma hl. m. Prahy — MHD, parkování, senzory, sdílená mobilita","https://golemio.cz/"),
("4. ČR — doprava / mobilita","Golemio API","api.golemio.cz","API dokumentace + správa klíčů: Public Transport, GTFS, vehicle positions","https://api.golemio.cz/"),
("4. ČR — doprava / mobilita","ŘSD MobilityData","mobilitydata.rsd.cz","Registr odběrů dat ŘSD — sčítání dopravy, zdroje, licence","https://mobilitydata.rsd.cz/"),
("4. ČR — doprava / mobilita","Geoportál ŘSD","geoportal.rsd.cz","Silniční a dálniční síť ČR — mapové aplikace, datové vrstvy, uzly a úseky","https://geoportal.rsd.cz/web"),
("4. ČR — doprava / mobilita","Dopravní info (NDIC)","dopravniinfo.cz","Uzavírky, nehody, sjízdnost, real-time dopravní události","https://www.dopravniinfo.cz/"),
("4. ČR — doprava / mobilita","NAIS API","api-nais.dopravniinfo.cz","API vrstva nad národními dopravními informacemi (DATEX II)","https://api-nais.dopravniinfo.cz/"),
("4. ČR — doprava / mobilita","PID","pid.cz","Pražská integrovaná doprava — GTFS feed, jízdní řády, mapy linek","https://pid.cz/"),
("4. ČR — doprava / mobilita","Ministerstvo dopravy","md.gov.cz","Rezortní registry a data","https://md.gov.cz/"),

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

# ═══ 6. REMOTE SENSING / RASTR ═══
("6. Remote sensing / rastr","Copernicus Data Space","dataspace.copernicus.eu","Sentinel-1/2/3/5P zdarma — browser, STAC, OData, S3 přístup","https://dataspace.copernicus.eu/"),
("6. Remote sensing / rastr","USGS EarthExplorer","earthexplorer.usgs.gov","Landsat archiv od 1972, letecké snímky, DEM","https://earthexplorer.usgs.gov/"),
("6. Remote sensing / rastr","NASA Earthdata","earthdata.nasa.gov","MODIS, VIIRS, SRTM, GPM, GRACE — CMR API","https://www.earthdata.nasa.gov/"),
("6. Remote sensing / rastr","OpenTopography","opentopography.org","LiDAR point clouds a globální DEM (SRTM, Copernicus DEM, ALOS)","https://opentopography.org/"),
("6. Remote sensing / rastr","Microsoft Planetary Computer","planetarycomputer.microsoft.com","STAC katalog + hosted compute nad velkými EO datasety","https://planetarycomputer.microsoft.com/"),
("6. Remote sensing / rastr","Google Earth Engine","earthengine.google.com","Planetární petabajtový katalog s cloudovým zpracováním","https://earthengine.google.com/"),
("6. Remote sensing / rastr","ESA WorldCover","esa-worldcover.org","Globální land cover 10 m","https://esa-worldcover.org/"),
("6. Remote sensing / rastr","CORINE Land Cover","land.copernicus.eu","Evropské využití území, časové řady 1990-2018","https://land.copernicus.eu/"),
("6. Remote sensing / rastr","GHSL (Global Human Settlement)","human-settlement.emergency.copernicus.eu","Zastavěnost, populační rastr, urbanizace — JRC","https://human-settlement.emergency.copernicus.eu/"),
("6. Remote sensing / rastr","STAC Index","stacindex.org","Katalog veřejných STAC endpointů","https://stacindex.org/"),

# ═══ 7. STATISTIKA / DEMOGRAFIE ═══
("7. Statistika / demografie","ČSÚ","csu.gov.cz","Český statistický úřad — SLDB, ceny nemovitostí, územní číselníky CZ-NUTS/LAU","https://csu.gov.cz/"),
("7. Statistika / demografie","Eurostat GISCO","ec.europa.eu","Evropské admin hranice NUTS, populační grid 1 km, geodata ke statistice","https://ec.europa.eu/eurostat/web/gisco"),
("7. Statistika / demografie","EU Data Portal","data.europa.eu","Agregátor otevřených dat EU včetně INSPIRE geodatových sad","https://data.europa.eu/"),
("7. Statistika / demografie","WorldPop","worldpop.org","Rastr hustoty populace 100 m, věkové struktury, migrace","https://www.worldpop.org/"),
("7. Statistika / demografie","Kontur Population Dataset","data.humdata.org","H3-indexovaný globální populační dataset","https://data.humdata.org/dataset/kontur-population-dataset"),
("7. Statistika / demografie","Our World in Data","ourworldindata.org","Kurátorované country-level časové řady","https://ourworldindata.org/"),

# ═══ 8. HISTORICKÉ MAPY ═══
("8. Historické mapy","David Rumsey Map Collection","davidrumsey.com","~200k georeferencovaných historických map, IIIF a Georeferencer","https://www.davidrumsey.com/"),
("8. Historické mapy","Old Maps Online","oldmapsonline.org","Meta-vyhledávač historických map podle místa a času","https://www.oldmapsonline.org/"),
("8. Historické mapy","Mapire (Arcanum Maps)","maps.arcanum.com","Habsburská vojenská mapování (I.-III.) georeferencovaná — ideální pro ČR","https://maps.arcanum.com/en/"),
("8. Historické mapy","Archivní mapy ČÚZK","ags.cuzk.gov.cz","Císařské otisky stabilního katastru, indikační skici","https://ags.cuzk.gov.cz/archiv/"),
("8. Historické mapy","Chartae Antiquae","chartae-antiquae.cz","Virtuální mapová sbírka historických map ČR","https://www.chartae-antiquae.cz/"),

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

# ═══ 10. SPATIAL DB, ANALYTIKA, ZPRACOVÁNÍ ═══
("10. Spatial DB / analytika","PostGIS","postgis.net","Prostorové rozšíření PostgreSQL — geometry, geography, raster, topology, pgRouting","https://postgis.net/"),
("10. Spatial DB / analytika","PostgreSQL","postgresql.org","Hostitelská DB pro PostGIS","https://www.postgresql.org/"),
("10. Spatial DB / analytika","GDAL / OGR","gdal.org","Univerzální konverze a transformace — ogr2ogr, gdalwarp, gdal_translate","https://gdal.org/"),
("10. Spatial DB / analytika","QGIS","qgis.org","Desktopové GIS — vizualizace, editace, Processing toolbox, modely","https://qgis.org/"),
("10. Spatial DB / analytika","GeoPandas","geopandas.org","Pandas s geometrií (Shapely + pyproj + Fiona) — základ Python geo analytiky","https://geopandas.org/"),
("10. Spatial DB / analytika","Shapely","shapely.readthedocs.io","Planární geometrické operace v Pythonu nad GEOS","https://shapely.readthedocs.io/"),
("10. Spatial DB / analytika","Rasterio","rasterio.readthedocs.io","Pythonic čtení a zápis rastrů nad GDAL","https://rasterio.readthedocs.io/"),
("10. Spatial DB / analytika","rioxarray / xarray","corteva.github.io","Multidimenzionální rastr a časové řady pro EO analytiku","https://corteva.github.io/rioxarray/"),
("10. Spatial DB / analytika","DuckDB spatial","duckdb.org","In-process SQL analytika s prostorovým rozšířením, čte GeoParquet i přímo z S3","https://duckdb.org/docs/stable/core_extensions/spatial/overview"),
("10. Spatial DB / analytika","Apache Sedona","sedona.apache.org","Distribuovaná prostorová analytika nad Sparkem/Flinkem","https://sedona.apache.org/"),
("10. Spatial DB / analytika","H3","h3geo.org","Hexagonální hierarchický index — agregace bodů, sousedství, k-ring","https://h3geo.org/"),
("10. Spatial DB / analytika","S2 Geometry","s2geometry.io","Sférická geometrie a indexování buňkami, alternativa k H3","https://s2geometry.io/"),
("10. Spatial DB / analytika","PySAL","pysal.org","Prostorová statistika — autokorelace, Moran's I, LISA, regionalizace","https://pysal.org/"),
("10. Spatial DB / analytika","MovingPandas","movingpandas.org","Analýza trajektorií a pohybu nad GeoPandas","https://movingpandas.org/"),
("10. Spatial DB / analytika","Lonboard","developmentseed.org","Rychlá vizualizace velkých GeoDataFrames v notebooku přes deck.gl","https://developmentseed.org/lonboard/"),
("10. Spatial DB / analytika","Kepler.gl","kepler.gl","Geo-analytické UI nad deck.gl pro rychlý průzkum velkých datasetů","https://kepler.gl/"),
("10. Spatial DB / analytika","CARTO","carto.com","Cloud location intelligence nad Snowflake/BigQuery/Databricks","https://carto.com/"),
("10. Spatial DB / analytika","Felt","felt.com","Kolaborativní webové mapy, rychlé sdílení analýz","https://felt.com/"),

# ═══ 11. ROUTING / SÍŤOVÁ ANALÝZA ═══
("11. Routing / síťová analýza","OSRM","project-osrm.org","Rychlý routing nad OSM — table (matrix), match, trip","https://project-osrm.org/"),
("11. Routing / síťová analýza","Valhalla","valhalla.github.io","Tile-based routing, isochrony, map-matching, multimodal","https://valhalla.github.io/valhalla/"),
("11. Routing / síťová analýza","GraphHopper","graphhopper.com","Routing engine + isochrony, dobrá Java knihovna i API","https://www.graphhopper.com/"),
("11. Routing / síťová analýza","pgRouting","pgrouting.org","Routing přímo v PostGIS — Dijkstra, TSP, driving distance","https://pgrouting.org/"),
("11. Routing / síťová analýza","OSMnx","osmnx.readthedocs.io","Stažení a analýza uličních sítí z OSM v Pythonu (NetworkX)","https://osmnx.readthedocs.io/"),
("11. Routing / síťová analýza","R5 / Conveyal","conveyal.com","Multimodální dostupnostní analýza nad GTFS + OSM","https://conveyal.com/"),

# ═══ 12. FORMÁTY, PROJEKCE, STANDARDY ═══
("12. Formáty / projekce / standardy","EPSG.io","epsg.io","Vyhledávání souřadnicových systémů, WKT/proj4 definice (S-JTSK = 5514)","https://epsg.io/"),
("12. Formáty / projekce / standardy","PROJ","proj.org","Knihovna transformací souřadnicových systémů","https://proj.org/"),
("12. Formáty / projekce / standardy","GeoJSON (RFC 7946)","geojson.org","Specifikace nejběžnějšího výměnného formátu","https://geojson.org/"),
("12. Formáty / projekce / standardy","GeoParquet","geoparquet.org","Sloupcový formát pro velké geodatové sady, čitelný DuckDB i Sedonou","https://geoparquet.org/"),
("12. Formáty / projekce / standardy","Cloud Optimized GeoTIFF","cogeo.org","COG — rastr čitelný po částech přímo z HTTP/S3","https://www.cogeo.org/"),
("12. Formáty / projekce / standardy","FlatGeobuf","flatgeobuf.org","Binární streamovatelný vektorový formát s prostorovým indexem","https://flatgeobuf.org/"),
("12. Formáty / projekce / standardy","OGC API","ogcapi.ogc.org","Moderní REST nástupci WMS/WFS — Features, Tiles, Processes","https://ogcapi.ogc.org/"),
("12. Formáty / projekce / standardy","STAC","stacspec.org","SpatioTemporal Asset Catalog — standard pro katalogizaci EO dat","https://stacspec.org/"),

# ═══ 13. OPEN DATA / REGISTRY CZ (OSINT overlap) ═══
("13. Open data / registry CZ","Národní katalog otevřených dat","data.gov.cz","Centrální CZ katalog datových sad včetně geodat a INSPIRE","https://data.gov.cz/"),
("13. Open data / registry CZ","Hlídač státu","hlidacstatu.cz","Smlouvy, dotace, zakázky, politici — API V2. Máš registrovaný účet","https://www.hlidacstatu.cz/"),
("13. Open data / registry CZ","Registr smluv","smlouvy.gov.cz","Otevřený registr smluv státu","https://smlouvy.gov.cz/"),
("13. Open data / registry CZ","ARES","ares.gov.cz","Ekonomické subjekty ČR — REST API, adresy sídel (geokódovatelné)","https://ares.gov.cz/"),
("13. Open data / registry CZ","Obchodní rejstřík","or.justice.cz","Veřejný rejstřík — vazby, sídla, statutáři","https://or.justice.cz/"),
("13. Open data / registry CZ","ISIR","isir.justice.cz","Insolvenční rejstřík","https://isir.justice.cz/"),

# ═══ 14. OSINT / INVESTIGACE (tvoje projekty a nástroje) ═══
("14. OSINT / investigace","Progresus OSINT","osint.cloud.progresus.cz","Tvoje platforma pro due diligence z veřejných zdrojů — zdroje, laboratoř, architektura","https://osint.cloud.progresus.cz/"),
("14. OSINT / investigace","vomaste.cz","vomaste.cz","Tvůj projekt — Registr tvrzení / zdrojů / kauz, dossiery, Globální mapa","https://vomaste.cz/"),
("14. OSINT / investigace","Situační radar (HzsRadar)","situacni-radar.fly.dev","Tvoje agregace událostí IZS v Phoenixu","https://situacni-radar.fly.dev/"),
("14. OSINT / investigace","Maltego","maltego.com","Link-analysis platforma pro OSINT vyšetřování","https://www.maltego.com/"),
("14. OSINT / investigace","OpenAlex","openalex.org","Otevřený katalog vědeckých prací s afiliacemi institucí (geokódovatelné)","https://openalex.org/"),
("14. OSINT / investigace","Common Crawl","commoncrawl.org","Otevřený webový crawl korpus","https://commoncrawl.org/"),
("14. OSINT / investigace","North Data","northdata.com","Firemní data a vazby v DACH/EU","https://www.northdata.com/"),
("14. OSINT / investigace","Investigace.cz","investigace.cz","České centrum investigativní žurnalistiky (OCCRP)","https://www.investigace.cz/"),

# ═══ 15. POČASÍ / KLIMA ═══
("15. Počasí / klima","ČHMÚ","chmi.cz","Předpovědi, radar, srážky, hydrologie; otevřená data na opendata.chmi.cz","https://www.chmi.cz/"),
("15. Počasí / klima","Meteoradar.cz","meteoradar.cz","Online srážkový radar ČR a Evropa","https://www.meteoradar.cz/"),
("15. Počasí / klima","In-počasí","in-pocasi.cz","Předpovědi, radar, síť stanic","https://www.in-pocasi.cz/"),
("15. Počasí / klima","Copernicus Climate Data Store","cds.climate.copernicus.eu","ERA5 reanalýza, klimatické projekce, API","https://cds.climate.copernicus.eu/"),
("15. Počasí / klima","Open-Meteo","open-meteo.com","Free weather API bez klíče, historická i předpovědní data po souřadnicích","https://open-meteo.com/"),

# ═══ 16. NEMOVITOSTI / TRH (prostorová složka) ═══
("16. Nemovitosti / trh","Sreality","sreality.cz","CZ inzerce s geokódovanými nabídkami","https://www.sreality.cz/"),
("16. Nemovitosti / trh","Flatzone","flatzone.cz","Data o novostavbách a cenách bytů; B2B i studio rozhraní","https://www.flatzone.cz/"),
("16. Nemovitosti / trh","ČSÚ — Ceny nemovitostí","csu.gov.cz","Ceny nemovitostí 2022-2024 podle území — v historii máš přesně tuhle stránku","https://csu.gov.cz/produkty/ceny-nemovitosti"),
("16. Nemovitosti / trh","CBRE","cbre.cz","Komerční realitní analytika a market reporty","https://www.cbre.cz/"),

# ═══ 17. UČENÍ / KOMUNITA ═══
("17. Učení / komunita","UofT Map and Data Library","mdl.library.utoronto.ca","Univerzitní mapová a datová knihovna — návody, datové sady","https://mdl.library.utoronto.ca/"),
("17. Učení / komunita","GIS StackExchange","gis.stackexchange.com","Nejrychlejší cesta k odpovědi na konkrétní GIS problém","https://gis.stackexchange.com/"),
("17. Učení / komunita","Awesome Geospatial","github.com","Kurátorovaný seznam geo nástrojů a datasetů","https://github.com/sacridini/Awesome-Geospatial"),
("17. Učení / komunita","Observable","observablehq.com","D3 notebooky — kartografické projekce a vizualizace","https://observablehq.com/"),
("17. Učení / komunita","Spatial Thoughts","spatialthoughts.com","Kvalitní kurzy QGIS, GEE a Python geo","https://spatialthoughts.com/"),
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
