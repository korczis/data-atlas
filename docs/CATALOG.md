<!-- Generováno `just docs` — needituj ručně. -->

# Katalog

**141** položek v **17** kategoriích — **53** doložených v datech prohlížeče, **88** doplněných referenčně.

Sloupec **Zdroj**: `bookmarks` / `history` / `bookmarks+history` znamená, že položka
je doložená v exportu; `reference` znamená doplněno ručně.
U odkazů s hlubší cestou se návštěvy počítají jen při skutečné shodě URL —
statistika celé domény se na ně nepřenáší, aby `github.com` nedělal dojem,
že jsi navštívil konkrétní repozitář.

## Kategorie

- [1. Gazetteer / geokódování](#1-gazetteer--geokódování) — 8
- [2. Globální geodata](#2-globální-geodata) — 12
- [3. ČR — katastr a geodata](#3-čr--katastr-a-geodata) — 13
- [4. ČR — doprava / mobilita](#4-čr--doprava--mobilita) — 8
- [5. Crime / IZS / bezpečnost](#5-crime--izs--bezpečnost) — 9
- [6. Remote sensing / rastr](#6-remote-sensing--rastr) — 10
- [7. Statistika / demografie](#7-statistika--demografie) — 6
- [8. Historické mapy](#8-historické-mapy) — 5
- [9. Mapové knihovny / basemapy](#9-mapové-knihovny--basemapy) — 10
- [10. Spatial DB / analytika](#10-spatial-db--analytika) — 18
- [11. Routing / síťová analýza](#11-routing--síťová-analýza) — 6
- [12. Formáty / projekce / standardy](#12-formáty--projekce--standardy) — 8
- [13. Open data / registry CZ](#13-open-data--registry-cz) — 6
- [14. OSINT / investigace](#14-osint--investigace) — 8
- [15. Počasí / klima](#15-počasí--klima) — 5
- [16. Nemovitosti / trh](#16-nemovitosti--trh) — 4
- [17. Učení / komunita](#17-učení--komunita) — 5


## 1. Gazetteer / geokódování

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Nominatim](https://nominatim.org/) | `nominatim.org` | OSM geocoder — forward/reverse, self-hosted i veřejný. Import, admin, maintenance docs máš v záložkách Geo & Maps | bookmarks+history | 0 | 2026-08-27 |
| [GeoNames](https://www.geonames.org/) | `geonames.org` | Globální gazetteer, 12M+ toponym, admin hierarchie ADM1-4, alternate names, populace. Dumpy zdarma (allCountries.zip) | history | 1 | 2026-08-27 |
| [Pelias](https://pelias.io/) | `pelias.io` | Modulární OSS geocoder (OSM + WOF + OpenAddresses + Geonames), Elasticsearch backend | reference | – | – |
| [Who's on First](https://whosonfirst.org/) | `whosonfirst.org` | Gazetteer admin i POI entit se stabilními ID a hierarchií, podklad Pelias | reference | – | – |
| [OpenAddresses](https://openaddresses.io/) | `openaddresses.io` | Agregované otevřené adresní body globálně, CSV s lat/lon | reference | – | – |
| [RÚIAN / VDP ČÚZK](https://vdp.cuzk.cz/) | `vdp.cuzk.cz` | Autoritativní CZ registr adres a územní identifikace — výměnný formát, adresní body, definiční body parcel | reference | – | – |
| [Mapy.cz Developer API](https://developer.mapy.com/) | `developer.mapy.cz` | CZ geokódování, suggest, routing, dlaždice. Máš tam aktivní projekt s consumption trackingem | bookmarks+history | 0 | 2026-08-27 |
| [Photon](https://photon.komoot.io/) | `photon.komoot.io` | Rychlý OSM geocoder s type-ahead, snadný self-hosting | reference | – | – |

## 2. Globální geodata

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Natural Earth](https://www.naturalearthdata.com/) | `naturalearthdata.com` | Public-domain vektor + raster v 1:10m/50m/110m — hranice, pobřeží, řeky, města, stínovaný reliéf. Kartografický základ | history | 1 | 2026-08-27 |
| [World Factbook Archive](https://worldfactbookarchive.org/) | `worldfactbookarchive.org` | Archivní ročníky CIA World Factbooku — časové řady country-level dat | history | 6 | 2026-08-27 |
| [CIA World Factbook](https://www.cia.gov/the-world-factbook/) | `cia.gov` | Aktuální country profily: geografie, demografie, ekonomika, komunikace | history | 1 | 2026-08-27 |
| [GADM](https://gadm.org/) | `gadm.org` | Administrativní hranice všech zemí do úrovně ADM3-5, GeoPackage/shp | reference | – | – |
| [geoBoundaries](https://www.geoboundaries.org/) | `geoboundaries.org` | Otevřená alternativa GADM s jasnou licencí a verzováním | reference | – | – |
| [US Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | `census.gov` | TIGER/Line shapefiles — US hranice, ulice, bloky, ZCTA, tracts ("geotiger") | reference | – | – |
| [Overture Maps Foundation](https://overturemaps.org/) | `overturemaps.org` | Otevřená základní data: places, buildings, transportation, divisions, base. Distribuce v GeoParquet | reference | – | – |
| [Geofabrik Downloads](https://download.geofabrik.de/) | `download.geofabrik.de` | Denní OSM extrakty po zemích a regionech (.osm.pbf, .shp.zip) | reference | – | – |
| [OpenStreetMap](https://www.openstreetmap.org/) | `openstreetmap.org` | Základní vrstva všeho — editace, historie, export | history | 34 | 2026-08-24 |
| [Overpass Turbo](https://overpass-turbo.eu/) | `overpass-turbo.eu` | Interaktivní dotazování OSM podle tagů, bboxu, relací; export GeoJSON | reference | – | – |
| [HDX (UN OCHA)](https://data.humdata.org/) | `data.humdata.org` | Humanitarian Data Exchange — COD admin boundaries, populace, infrastruktura | reference | – | – |
| [OpenCelliD](https://opencellid.org/) | `opencellid.org` | Otevřená databáze pozic BTS/cell towers — užitečné pro geolokaci | reference | – | – |

## 3. ČR — katastr a geodata

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [ČÚZK — Dálkový přístup do KN](https://katastr.cuzk.gov.cz/) | `katastr.cuzk.gov.cz` | Dálkový přístup ke katastru nemovitostí. Nejnavštěvovanější geo zdroj v tvé historii | history | 36 | 2026-08-20 |
| [Nahlížení do KN](https://nahlizenidokn.cuzk.gov.cz/) | `nahlizenidokn.cuzk.gov.cz` | Veřejné nahlížení — parcely, budovy, LV, vlastníci; má i jednoduché API | history | 9 | 2026-06-25 |
| [SGI Nahlížení do KN](https://sgi-nahlizenidokn.cuzk.gov.cz/) | `sgi-nahlizenidokn.cuzk.gov.cz` | Grafická část — katastrální mapa, mapové služby | history | 4 | 2026-06-26 |
| [Geoportál ČÚZK](https://geoportal.cuzk.cz/) | `geoportal.cuzk.cz` | WMS/WFS/WMTS, ZABAGED, Ortofoto ČR, DMR 5G/DMP 1G, Data50/200. Klíčový CZ zdroj | history | 3 | 2026-08-27 |
| [ČÚZK — Žádosti](https://zadosti.cuzk.gov.cz/) | `zadosti.cuzk.gov.cz` | Objednávky výstupů a datových sad | history | 4 | 2026-08-06 |
| [ČÚZK (rozcestník)](https://www.cuzk.gov.cz/) | `cuzk.gov.cz` | Hlavní web zeměměřického a katastrálního úřadu | history | 9 | 2026-08-20 |
| [Národní geoportál INSPIRE (CENIA)](https://geoportal.gov.cz/) | `geoportal.gov.cz` | CZ INSPIRE katalog — metadata a služby napříč resorty, včetně historického ortofota z 50. let | reference | – | – |
| [ArcČR (ARCDATA Praha)](https://www.arcdata.cz/cs-cz/produkty/data/arccr) | `arcdata.cz` | Volně dostupná digitální geografická databáze ČR — administrativní členění, sídla, vodstvo, doprava; navazuje na ArcČR 500 | reference | – | – |
| [DIBAVOD (VÚV TGM)](https://www.dibavod.cz/) | `dibavod.cz` | Digitální báze vodohospodářských dat — povodí, vodní toky, nádrže | reference | – | – |
| [AOPK — Ochrana přírody](https://gis-aopk.opendata.arcgis.com/) | `gis-aopk.opendata.arcgis.com` | Chráněná území, Natura 2000, biotopy jako open data | reference | – | – |
| [LPIS / eAGRI](https://mze.gov.cz/public/app/lpisext/lpis/verejny2/plpis/) | `eagri.cz` | Zemědělské půdní bloky, využití půdy, WMS/WFS | reference | – | – |
| [Česká geologická služba](https://mapy.geology.cz/) | `mapy.geology.cz` | Geologické, hydrogeologické a půdní mapy, sesuvy, poddolování | reference | – | – |
| [Geoportál Praha](https://www.geoportalpraha.cz/) | `geoportalpraha.cz` | Pražská geodata a open data — ortofota, územní plán, 3D model | reference | – | – |

## 4. ČR — doprava / mobilita

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Golemio (Praha)](https://golemio.cz/) | `golemio.cz` | Datová platforma hl. m. Prahy — MHD, parkování, senzory, sdílená mobilita | history | 4 | 2026-08-26 |
| [Golemio API](https://api.golemio.cz/) | `api.golemio.cz` | API dokumentace + správa klíčů: Public Transport, GTFS, vehicle positions | history | 39 | 2026-08-26 |
| [ŘSD MobilityData](https://mobilitydata.rsd.cz/) | `mobilitydata.rsd.cz` | Registr odběrů dat ŘSD — sčítání dopravy, zdroje, licence | history | 27 | 2026-08-27 |
| [Geoportál ŘSD](https://geoportal.rsd.cz/web) | `geoportal.rsd.cz` | Silniční a dálniční síť ČR — mapové aplikace, datové vrstvy, uzly a úseky | history | 2 | 2026-08-26 |
| [Dopravní info (NDIC)](https://www.dopravniinfo.cz/) | `dopravniinfo.cz` | Uzavírky, nehody, sjízdnost, real-time dopravní události | history | 8 | 2026-08-26 |
| [NAIS API](https://api-nais.dopravniinfo.cz/) | `api-nais.dopravniinfo.cz` | API vrstva nad národními dopravními informacemi (DATEX II) | history | 4 | 2026-08-26 |
| [PID](https://pid.cz/) | `pid.cz` | Pražská integrovaná doprava — GTFS feed, jízdní řády, mapy linek | history | 1 | 2026-08-25 |
| [Ministerstvo dopravy](https://md.gov.cz/) | `md.gov.cz` | Rezortní registry a data | history | 4 | 2026-06-18 |

## 5. Crime / IZS / bezpečnost

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [SFPD Crime Dashboard](https://www.sanfranciscopolice.org/stay-safe/crime-data/crime-dashboard) | `sanfranciscopolice.org` | Incident-level crime data SF s prostorovou složkou — referenční vzor crime dashboardu | history | 1 | 2026-08-27 |
| [data.police.uk](https://data.police.uk/) | `data.police.uk` | UK street-level crime + outcomes API, měsíční CSV s lat/lon a force area | reference | – | – |
| [Portál krizového řízení Stč. kraje](https://pkr.kr-stredocesky.cz/) | `pkr.kr-stredocesky.cz` | Zásahy jednotek požární ochrany — mapa a feed událostí IZS | history | 16 | 2026-08-24 |
| [HZS Královéhradecký — Události](https://udalostikhk.hzscr.cz/) | `udalostikhk.hzscr.cz` | Veřejný výpis zásahů HZS s lokalizací | history | 5 | 2026-08-24 |
| [HZS Vysočina — Webohled](https://webohled.hasici-vysocina.cz/) | `webohled.hasici-vysocina.cz` | Veřejný portál událostí hasičů kraje Vysočina — pozor, TLS certifikát vypršel v srpnu 2020 a je vystavený na jiný název | history | 9 | 2026-08-24 |
| [NYC Open Data](https://opendata.cityofnewyork.us/) | `opendata.cityofnewyork.us` | Vzorový municipální portál — NYPD complaints, 311, PLUTO parcely | reference | – | – |
| [Chicago Data Portal](https://data.cityofchicago.org/) | `data.cityofchicago.org` | Crimes 2001-present s lat/lon — klasický dataset pro prostorovou analytiku | reference | – | – |
| [ACLED](https://acleddata.com/) | `acleddata.com` | Armed Conflict Location & Event Data — georeferencované konflikty a protesty | reference | – | – |
| [GDELT](https://www.gdeltproject.org/) | `gdeltproject.org` | Globální event database z médií s geokódováním, BigQuery dataset | reference | – | – |

## 6. Remote sensing / rastr

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Copernicus Data Space](https://dataspace.copernicus.eu/) | `dataspace.copernicus.eu` | Sentinel-1/2/3/5P zdarma — browser, STAC, OData, S3 přístup | reference | – | – |
| [USGS EarthExplorer](https://earthexplorer.usgs.gov/) | `earthexplorer.usgs.gov` | Landsat archiv od 1972, letecké snímky, DEM | reference | – | – |
| [NASA Earthdata](https://www.earthdata.nasa.gov/) | `earthdata.nasa.gov` | MODIS, VIIRS, SRTM, GPM, GRACE — CMR API | reference | – | – |
| [OpenTopography](https://opentopography.org/) | `opentopography.org` | LiDAR point clouds a globální DEM (SRTM, Copernicus DEM, ALOS) | reference | – | – |
| [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) | `planetarycomputer.microsoft.com` | STAC katalog + hosted compute nad velkými EO datasety | reference | – | – |
| [Google Earth Engine](https://earthengine.google.com/) | `earthengine.google.com` | Planetární petabajtový katalog s cloudovým zpracováním | reference | – | – |
| [ESA WorldCover](https://esa-worldcover.org/) | `esa-worldcover.org` | Globální land cover 10 m | reference | – | – |
| [CORINE Land Cover](https://land.copernicus.eu/) | `land.copernicus.eu` | Evropské využití území, časové řady 1990-2018 | reference | – | – |
| [GHSL (Global Human Settlement)](https://human-settlement.emergency.copernicus.eu/) | `human-settlement.emergency.copernicus.eu` | Zastavěnost, populační rastr, urbanizace — JRC | reference | – | – |
| [STAC Index](https://stacindex.org/) | `stacindex.org` | Katalog veřejných STAC endpointů | reference | – | – |

## 7. Statistika / demografie

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [ČSÚ](https://csu.gov.cz/) | `csu.gov.cz` | Český statistický úřad — SLDB, ceny nemovitostí, územní číselníky CZ-NUTS/LAU | history | 2 | 2026-06-16 |
| [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco) | `ec.europa.eu` | Evropské admin hranice NUTS, populační grid 1 km, geodata ke statistice | reference | – | – |
| [EU Data Portal](https://data.europa.eu/) | `data.europa.eu` | Agregátor otevřených dat EU včetně INSPIRE geodatových sad | reference | – | – |
| [WorldPop](https://www.worldpop.org/) | `worldpop.org` | Rastr hustoty populace 100 m, věkové struktury, migrace | reference | – | – |
| [Kontur Population Dataset](https://data.humdata.org/dataset/kontur-population-dataset) | `data.humdata.org` | H3-indexovaný globální populační dataset | reference | – | – |
| [Our World in Data](https://ourworldindata.org/) | `ourworldindata.org` | Kurátorované country-level časové řady | reference | – | – |

## 8. Historické mapy

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [David Rumsey Map Collection](https://www.davidrumsey.com/) | `davidrumsey.com` | ~200k georeferencovaných historických map, IIIF a Georeferencer | reference | – | – |
| [Old Maps Online](https://www.oldmapsonline.org/) | `oldmapsonline.org` | Meta-vyhledávač historických map podle místa a času | reference | – | – |
| [Mapire (Arcanum Maps)](https://maps.arcanum.com/en/) | `maps.arcanum.com` | Habsburská vojenská mapování (I.-III.) georeferencovaná — ideální pro ČR | reference | – | – |
| [Archivní mapy ČÚZK](https://ags.cuzk.gov.cz/archiv/) | `ags.cuzk.gov.cz` | Císařské otisky stabilního katastru, indikační skici | reference | – | – |
| [Chartae Antiquae](https://www.chartae-antiquae.cz/) | `chartae-antiquae.cz` | Virtuální mapová sbírka historických map ČR | reference | – | – |

## 9. Mapové knihovny / basemapy

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [MapLibre GL JS](https://maplibre.org/) | `maplibre.org` | OSS fork Mapbox GL — vektorové dlaždice, WebGL, style spec | history | 1 | 2026-08-26 |
| [Leaflet](https://leafletjs.com/) | `leafletjs.com` | Lehká JS mapová knihovna, de facto standard pro rychlé mapy | history | 1 | 2026-08-26 |
| [deck.gl](https://deck.gl/) | `deck.gl` | WebGL vrstvy pro miliony bodů, integrace s MapLibre a Kepler | history | 2 | 2026-08-26 |
| [OpenLayers](https://openlayers.org/) | `openlayers.org` | Plnotučná knihovna s WMS/WFS/WMTS a projekcemi | reference | – | – |
| [sigma.js + @sigma/layer-maplibre](https://www.sigmajs.org/) | `sigmajs.org` | Graf rendering nad mapou — kombinace síťové a prostorové analýzy. Hodně jsi to procházel | history | 129 | 2026-08-01 |
| [Protomaps / PMTiles](https://protomaps.com/) | `protomaps.com` | Jednosouborové dlaždice bez serveru, hostovatelné na S3/CDN | reference | – | – |
| [MapTiler](https://www.maptiler.com/) | `maptiler.com` | Hostované vektorové basemapy, styly, self-hosted server | reference | – | – |
| [OpenFreeMap](https://openfreemap.org/) | `openfreemap.org` | Zdarma hostované OSM vektorové dlaždice bez API klíče | reference | – | – |
| [Stadia Maps](https://stadiamaps.com/) | `stadiamaps.com` | Basemapy, geokódování a routing s férovým free tierem | reference | – | – |
| [Turf.js](https://turfjs.org/) | `turfjs.org` | Geoprostorová analýza v JS — buffer, intersect, nearest, clusters | reference | – | – |

## 10. Spatial DB / analytika

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [PostGIS](https://postgis.net/) | `postgis.net` | Prostorové rozšíření PostgreSQL — geometry, geography, raster, topology, pgRouting | reference | – | – |
| [PostgreSQL](https://www.postgresql.org/) | `postgresql.org` | Hostitelská DB pro PostGIS | bookmarks+history | 1 | 2026-08-27 |
| [GDAL / OGR](https://gdal.org/) | `gdal.org` | Univerzální konverze a transformace — ogr2ogr, gdalwarp, gdal_translate | reference | – | – |
| [QGIS](https://qgis.org/) | `qgis.org` | Desktopové GIS — vizualizace, editace, Processing toolbox, modely | reference | – | – |
| [GeoPandas](https://geopandas.org/) | `geopandas.org` | Pandas s geometrií (Shapely + pyproj + Fiona) — základ Python geo analytiky | reference | – | – |
| [Shapely](https://shapely.readthedocs.io/) | `shapely.readthedocs.io` | Planární geometrické operace v Pythonu nad GEOS | reference | – | – |
| [Rasterio](https://rasterio.readthedocs.io/) | `rasterio.readthedocs.io` | Pythonic čtení a zápis rastrů nad GDAL | reference | – | – |
| [rioxarray / xarray](https://corteva.github.io/rioxarray/) | `corteva.github.io` | Multidimenzionální rastr a časové řady pro EO analytiku | reference | – | – |
| [DuckDB spatial](https://duckdb.org/docs/stable/core_extensions/spatial/overview) | `duckdb.org` | In-process SQL analytika s prostorovým rozšířením, čte GeoParquet i přímo z S3 | reference | – | – |
| [Apache Sedona](https://sedona.apache.org/) | `sedona.apache.org` | Distribuovaná prostorová analytika nad Sparkem/Flinkem | reference | – | – |
| [H3](https://h3geo.org/) | `h3geo.org` | Hexagonální hierarchický index — agregace bodů, sousedství, k-ring | reference | – | – |
| [S2 Geometry](https://s2geometry.io/) | `s2geometry.io` | Sférická geometrie a indexování buňkami, alternativa k H3 | reference | – | – |
| [PySAL](https://pysal.org/) | `pysal.org` | Prostorová statistika — autokorelace, Moran's I, LISA, regionalizace | reference | – | – |
| [MovingPandas](https://movingpandas.org/) | `movingpandas.org` | Analýza trajektorií a pohybu nad GeoPandas | reference | – | – |
| [Lonboard](https://developmentseed.org/lonboard/) | `developmentseed.org` | Rychlá vizualizace velkých GeoDataFrames v notebooku přes deck.gl | reference | – | – |
| [Kepler.gl](https://kepler.gl/) | `kepler.gl` | Geo-analytické UI nad deck.gl pro rychlý průzkum velkých datasetů | reference | – | – |
| [CARTO](https://carto.com/) | `carto.com` | Cloud location intelligence nad Snowflake/BigQuery/Databricks | history | 2 | 2026-08-26 |
| [Felt](https://felt.com/) | `felt.com` | Kolaborativní webové mapy, rychlé sdílení analýz | reference | – | – |

## 11. Routing / síťová analýza

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [OSRM](https://project-osrm.org/) | `project-osrm.org` | Rychlý routing nad OSM — table (matrix), match, trip | reference | – | – |
| [Valhalla](https://valhalla.github.io/valhalla/) | `valhalla.github.io` | Tile-based routing, isochrony, map-matching, multimodal | reference | – | – |
| [GraphHopper](https://www.graphhopper.com/) | `graphhopper.com` | Routing engine + isochrony, dobrá Java knihovna i API | reference | – | – |
| [pgRouting](https://pgrouting.org/) | `pgrouting.org` | Routing přímo v PostGIS — Dijkstra, TSP, driving distance | reference | – | – |
| [OSMnx](https://osmnx.readthedocs.io/) | `osmnx.readthedocs.io` | Stažení a analýza uličních sítí z OSM v Pythonu (NetworkX) | reference | – | – |
| [R5 / Conveyal](https://conveyal.com/) | `conveyal.com` | Multimodální dostupnostní analýza nad GTFS + OSM | reference | – | – |

## 12. Formáty / projekce / standardy

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [EPSG.io](https://epsg.io/) | `epsg.io` | Vyhledávání souřadnicových systémů, WKT/proj4 definice (S-JTSK = 5514) | reference | – | – |
| [PROJ](https://proj.org/) | `proj.org` | Knihovna transformací souřadnicových systémů | reference | – | – |
| [GeoJSON (RFC 7946)](https://geojson.org/) | `geojson.org` | Specifikace nejběžnějšího výměnného formátu | reference | – | – |
| [GeoParquet](https://geoparquet.org/) | `geoparquet.org` | Sloupcový formát pro velké geodatové sady, čitelný DuckDB i Sedonou | reference | – | – |
| [Cloud Optimized GeoTIFF](https://www.cogeo.org/) | `cogeo.org` | COG — rastr čitelný po částech přímo z HTTP/S3 | reference | – | – |
| [FlatGeobuf](https://flatgeobuf.org/) | `flatgeobuf.org` | Binární streamovatelný vektorový formát s prostorovým indexem | reference | – | – |
| [OGC API](https://ogcapi.ogc.org/) | `ogcapi.ogc.org` | Moderní REST nástupci WMS/WFS — Features, Tiles, Processes | reference | – | – |
| [STAC](https://stacspec.org/) | `stacspec.org` | SpatioTemporal Asset Catalog — standard pro katalogizaci EO dat | reference | – | – |

## 13. Open data / registry CZ

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Národní katalog otevřených dat](https://data.gov.cz/) | `data.gov.cz` | Centrální CZ katalog datových sad včetně geodat a INSPIRE | history | 2 | 2026-08-27 |
| [Hlídač státu](https://www.hlidacstatu.cz/) | `hlidacstatu.cz` | Smlouvy, dotace, zakázky, politici — API V2. Máš registrovaný účet | history | 23 | 2026-08-20 |
| [Registr smluv](https://smlouvy.gov.cz/) | `smlouvy.gov.cz` | Otevřený registr smluv státu | history | 3 | 2026-07-24 |
| [ARES](https://ares.gov.cz/) | `ares.gov.cz` | Ekonomické subjekty ČR — REST API, adresy sídel (geokódovatelné) | history | 7 | 2026-08-05 |
| [Obchodní rejstřík](https://or.justice.cz/) | `or.justice.cz` | Veřejný rejstřík — vazby, sídla, statutáři | history | 16 | 2026-08-05 |
| [ISIR](https://isir.justice.cz/) | `isir.justice.cz` | Insolvenční rejstřík | history | 5 | 2026-08-11 |

## 14. OSINT / investigace

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Progresus OSINT](https://osint.cloud.progresus.cz/) | `osint.cloud.progresus.cz` | Tvoje platforma pro due diligence z veřejných zdrojů — zdroje, laboratoř, architektura | history | 72 | 2026-08-23 |
| [vomaste.cz](https://vomaste.cz/) | `vomaste.cz` | Tvůj projekt — Registr tvrzení / zdrojů / kauz, dossiery, Globální mapa | history | 1407 | 2026-08-15 |
| [Situační radar (HzsRadar)](https://situacni-radar.fly.dev/) | `situacni-radar.fly.dev` | Tvoje agregace událostí IZS v Phoenixu | history | 41 | 2026-08-27 |
| [Maltego](https://www.maltego.com/) | `maltego.com` | Link-analysis platforma pro OSINT vyšetřování | history | 2 | 2026-08-05 |
| [OpenAlex](https://openalex.org/) | `openalex.org` | Otevřený katalog vědeckých prací s afiliacemi institucí (geokódovatelné) | history | 9 | 2026-08-11 |
| [Common Crawl](https://commoncrawl.org/) | `commoncrawl.org` | Otevřený webový crawl korpus | bookmarks+history | 0 | 2026-08-27 |
| [North Data](https://www.northdata.com/) | `northdata.com` | Firemní data a vazby v DACH/EU | history | 22 | 2026-07-22 |
| [Investigace.cz](https://www.investigace.cz/) | `investigace.cz` | České centrum investigativní žurnalistiky (OCCRP) | bookmarks+history | 0 | 2026-08-27 |

## 15. Počasí / klima

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [ČHMÚ](https://www.chmi.cz/) | `chmi.cz` | Předpovědi, radar, srážky, hydrologie; otevřená data na opendata.chmi.cz | reference | – | – |
| [Meteoradar.cz](https://www.meteoradar.cz/) | `meteoradar.cz` | Online srážkový radar ČR a Evropa | history | 2 | 2026-06-26 |
| [In-počasí](https://www.in-pocasi.cz/) | `in-pocasi.cz` | Předpovědi, radar, síť stanic | history | 1 | 2026-08-17 |
| [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/) | `cds.climate.copernicus.eu` | ERA5 reanalýza, klimatické projekce, API | reference | – | – |
| [Open-Meteo](https://open-meteo.com/) | `open-meteo.com` | Free weather API bez klíče, historická i předpovědní data po souřadnicích | reference | – | – |

## 16. Nemovitosti / trh

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Sreality](https://www.sreality.cz/) | `sreality.cz` | CZ inzerce s geokódovanými nabídkami | history | 5 | 2026-06-16 |
| [Flatzone](https://www.flatzone.cz/) | `flatzone.cz` | Data o novostavbách a cenách bytů; B2B i studio rozhraní | history | 5 | 2026-08-14 |
| [ČSÚ — Ceny nemovitostí](https://csu.gov.cz/produkty/ceny-nemovitosti) | `csu.gov.cz` | Ceny nemovitostí 2022-2024 podle území — v historii máš přesně tuhle stránku | reference | – | – |
| [CBRE](https://www.cbre.cz/) | `cbre.cz` | Komerční realitní analytika a market reporty | history | 1 | 2026-06-16 |

## 17. Učení / komunita

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [UofT Map and Data Library](https://mdl.library.utoronto.ca/) | `mdl.library.utoronto.ca` | Univerzitní mapová a datová knihovna — návody, datové sady | history | 1 | 2026-08-27 |
| [GIS StackExchange](https://gis.stackexchange.com/) | `gis.stackexchange.com` | Nejrychlejší cesta k odpovědi na konkrétní GIS problém | reference | – | – |
| [Awesome Geospatial](https://github.com/sacridini/Awesome-Geospatial) | `github.com` | Kurátorovaný seznam geo nástrojů a datasetů | reference | – | – |
| [Observable](https://observablehq.com/) | `observablehq.com` | D3 notebooky — kartografické projekce a vizualizace | bookmarks+history | 0 | 2026-08-27 |
| [Spatial Thoughts](https://spatialthoughts.com/) | `spatialthoughts.com` | Kvalitní kurzy QGIS, GEE a Python geo | reference | – | – |
