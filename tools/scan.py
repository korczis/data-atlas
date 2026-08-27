import json, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
rows=json.load(open(CACHE/"raw.json", encoding="utf-8"))

KW = r"""gis|geo|geograph|geodat|geojson|geotiff|geocod|geocoder|gazetteer|nominatim|postgis|
map|mapa|mapy|mapbox|maplibre|leaflet|openlayers|cesium|deck\.gl|carto|kepler|
spatial|geospatial|shapefile|shp|kml|gpx|wms|wfs|wmts|tms|epsg|proj4|crs|srid|
osm|openstreetmap|overpass|osrm|valhalla|graphhopper|routing|isochrone|
katastr|kataster|cuzk|ruian|ortofoto|orthophoto|dmr|dmp|lidar|
census|demograph|population|statistic|csu\.gov|eurostat|
boundar|admin.?level|nuts|lau|region|municipal|okres|kraj|obec|
elevation|terrain|topograph|dem|dted|srtm|contour|hillshade|
satellite|sentinel|landsat|copernicus|remote.?sensing|imagery|raster|tile|basemap|
crime|police|incident|emergency|hazard|risk|flood|povodn|
traffic|doprav|transit|gtfs|mobility|rsd\.cz|golemio|pid\.cz|
weather|meteo|pocasi|chmi|radar|forecast|climate|
open.?data|opendata|datovy|dataset|data.?portal|portal|catalog|
naturalearth|geonames|factbook|tiger|gadm|whosonfirst|pelias|
address|adresa|parcel|cadast|land.?use|zoning|zastav|urban|
gdal|ogr|qgis|arcgis|esri|grass|saga|whitebox|rasterio|shapely|fiona|geopandas|turf|h3|s2|geohash|
navig|gps|coordinate|latitude|longitude|
osint|intelligence|recon|maltego|shodan|
real.?estate|reality|sreality|flatzone|cbre|nemovitost"""
KW = "|".join(x.strip() for x in KW.split("|") if x.strip())
rx = re.compile(KW, re.I|re.X)

# noise filters
PORN = re.compile(r"xvideos|xnxx|pornhub|youporn|xhamster|youjizz|hdzog|pornzog|txxx|tnaflix|trahkino|faphouse|zeenite|fpo\.xxx|annatube|pakistanipornx|xnnz", re.I)
SKIP_FOLDER = re.compile(r"Selection", re.I)

# domains that match keyword only spuriously
by = collections.defaultdict(lambda: dict(urls=set(), titles=[], visits=0, bm=0, hist=0, last=''))
for r in rows:
    d=r['domain']
    if not d or PORN.search(d): continue
    if r['source']=='bookmark' and SKIP_FOLDER.search(r['folder']): continue
    hay = f"{d} {r['url']} {r['title']}"
    if not rx.search(hay): continue
    e=by[d]
    e['urls'].add(r['url']); e['visits'] += r['visits']
    if r['title']: e['titles'].append(r['title'])
    if r['source']=='bookmark': e['bm']+=1
    else: e['hist']+=1
    if r['last']>e['last']: e['last']=r['last']

out=sorted(by.items(), key=lambda kv: -kv[1]['visits'])

# Úplný výpis je na stovky řádků — patří do souboru, ne do terminálu.
listing = CACHE / "candidates.txt"
with listing.open("w", encoding="utf-8") as fh:
    for d,e in out:
        t = collections.Counter(e['titles']).most_common(1)
        t = t[0][0][:60] if t else ''
        fh.write(f"{d:38s} v={e['visits']:<5d} u={len(e['urls']):<4d} bm={e['bm']:<3d} last={e['last'][:10]:12s} {t}\n")
print(f"{len(out)} kandidátských domén → {listing.relative_to(ROOT)}")
json.dump({d:{**e,"urls":sorted(e["urls"])} for d,e in out},
          open(CACHE/"candidates.json","w",encoding="utf-8"), ensure_ascii=False, default=list)
