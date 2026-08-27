<!-- Generováno `just docs` — needituj ručně. -->

# Katalog

**218** položek v **17** kategoriích — **52** doložených v datech prohlížeče, **166** doplněných referenčně.

Sloupec **Zdroj**: `bookmarks` / `history` / `bookmarks+history` znamená, že položka
je doložená v exportu; `reference` znamená doplněno ručně.
U odkazů s hlubší cestou se návštěvy počítají jen při skutečné shodě URL —
statistika celé domény se na ně nepřenáší, aby `github.com` nedělal dojem,
že jsi navštívil konkrétní repozitář.

## Kategorie

- [1. Gazetteer / geokódování](#1-gazetteer--geokódování) — 12
- [2. Globální geodata](#2-globální-geodata) — 16
- [3. ČR — katastr a geodata](#3-čr--katastr-a-geodata) — 18
- [4. ČR — doprava / mobilita](#4-čr--doprava--mobilita) — 12
- [5. Crime / IZS / bezpečnost](#5-crime--izs--bezpečnost) — 13
- [6. Remote sensing / rastr](#6-remote-sensing--rastr) — 15
- [7. Statistika / demografie](#7-statistika--demografie) — 10
- [8. Historické mapy](#8-historické-mapy) — 9
- [9. Mapové knihovny / basemapy](#9-mapové-knihovny--basemapy) — 15
- [10. Spatial DB / analytika](#10-spatial-db--analytika) — 23
- [11. Routing / síťová analýza](#11-routing--síťová-analýza) — 11
- [12. Formáty / projekce / standardy](#12-formáty--projekce--standardy) — 13
- [13. Open data / registry CZ](#13-open-data--registry-cz) — 11
- [14. OSINT / investigace](#14-osint--investigace) — 13
- [15. Počasí / klima](#15-počasí--klima) — 10
- [16. Nemovitosti / trh](#16-nemovitosti--trh) — 7
- [17. Učení / komunita](#17-učení--komunita) — 10


## 1. Gazetteer / geokódování

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Nominatim](https://nominatim.org/) | `nominatim.org` | OSM geocoder — forward/reverse, self-hosted i veřejný. Import, admin, maintenance docs máš v záložkách Geo & Maps | bookmarks+history | 0 | 2026-08-27 |
| [GeoNames](https://www.geonames.org/) | `geonames.org` | Globální gazetteer pod CC-BY 4.0 — 12M unikátních objektů a 25M jmen (z toho 4,8M sídel a 16M alternate names), admin hierarchie ADM1-4 a populace; dumpy zdarma (allCountries.zip) | history | 1 | 2026-08-27 |
| [Pelias](https://pelias.io/) | `pelias.io` | Modulární OSS geocoder (OSM + WOF + OpenAddresses + Geonames), Elasticsearch backend | reference | – | – |
| [Who's on First](https://whosonfirst.org/) | `whosonfirst.org` | Gazetteer admin i POI entit se stabilními ID a hierarchií, podklad Pelias | reference | – | – |
| [OpenAddresses](https://openaddresses.io/) | `openaddresses.io` | Agregované otevřené adresní body globálně — živý pipeline na batch.openaddresses.io vydává týdenní kolekce po zemích a regionech v line-delimited GeoJSON, starý CSV výstup na results.openaddresses.io je zamrzlý archiv z 10/2021 | reference | – | – |
| [RÚIAN / VDP ČÚZK](https://vdp.cuzk.cz/) | `vdp.cuzk.cz` | Autoritativní CZ registr adres a územní identifikace — výměnný formát, adresní body, definiční body parcel | reference | – | – |
| [Mapy.com REST API](https://developer.mapy.com/) | `developer.mapy.com` | CZ geokódování, suggest, routing, dlaždice. Máš tam aktivní projekt s consumption trackingem | bookmarks+history | 0 | 2026-08-27 |
| [Photon](https://photon.komoot.io/) | `photon.komoot.io` | Rychlý OSM geocoder s type-ahead, snadný self-hosting | reference | – | – |
| [OpenCage Geocoding API](https://opencagedata.com/) | `opencagedata.com` | Hostované geokódovací API nad OSM a dalšími otevřenými geokodéry — forward i reverse, u výsledku časová zóna, Wikidata ID, NUTS a FIPS kódy, výsledky lze ukládat; free trial 2 500 dotazů/den, dál placené tarify | reference | – | – |
| [NGA GEOnet Names Server (GNS)](https://geonames.nga.mil/) | `geonames.nga.mil` | Gazetteer NGA a US Board on Geographic Names pro toponyma mimo USA — schválené tvary jmen, varianty, historické i nelatinkové zápisy, souřadnice a admin zařazení; country files ke stažení bez licenčních omezení | reference | – | – |
| [Wikidata](https://www.wikidata.org/) | `wikidata.org` | Otevřená znalostní báze — místa nesou souřadnici (P625), stabilní QID a křížové odkazy na GeoNames a OSM, rekonciliace toponym přes SPARQL endpoint | reference | – | – |
| [World Historical Gazetteer](https://whgazetteer.org/) | `whgazetteer.org` | Historický gazetteer (v3.2, University of Pittsburgh) — přes 2,2 mil. míst propojených napříč epochami a jazyky, rekonciliace proti GeoNames a Wikidata, API i stahování datasetů | reference | – | – |

## 2. Globální geodata

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Natural Earth](https://www.naturalearthdata.com/) | `naturalearthdata.com` | Public-domain vektor + raster v 1:10m/50m/110m — hranice, pobřeží, řeky, města, stínovaný reliéf. Kartografický základ | history | 1 | 2026-08-27 |
| [World Factbook Archive](https://worldfactbookarchive.org/) | `worldfactbookarchive.org` | Nezávislý archiv všech ročníků CIA World Factbooku 1990-2025 (284 entit, přes milion polí) — vyhledávání, otevřené JSON API a export do CSV; po zrušení originálu v únoru 2026 jediná cesta k těmto datům | history | 6 | 2026-08-27 |
| [GADM](https://gadm.org/) | `gadm.org` | Administrativní hranice všech zemí do úrovně ADM5 v GeoPackage/shapefile/KMZ — jen pro akademické a nekomerční použití, redistribuce a komerční užití bez svolení zakázány | reference | – | – |
| [geoBoundaries](https://www.geoboundaries.org/) | `geoboundaries.org` | Otevřená alternativa GADM s jasnou licencí a verzováním | reference | – | – |
| [US Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | `census.gov` | TIGER/Line shapefiles — US hranice, ulice, bloky, ZCTA, tracts ("geotiger") | reference | – | – |
| [Overture Maps Foundation](https://overturemaps.org/) | `overturemaps.org` | Otevřená základní data v šesti tématech — addresses, base, buildings, divisions, places a transportation (adresy přes 470 mil. bodů, zatím alfa); měsíční release v GeoParquet na S3 a Azure, dotazovatelné DuckDB | reference | – | – |
| [Geofabrik Downloads](https://download.geofabrik.de/) | `download.geofabrik.de` | Denní OSM extrakty po zemích a regionech (.osm.pbf, .shp.zip) | reference | – | – |
| [OpenStreetMap](https://www.openstreetmap.org/) | `openstreetmap.org` | Základní vrstva všeho — editace, historie, export | history | 34 | 2026-08-24 |
| [Overpass Turbo](https://overpass-turbo.eu/) | `overpass-turbo.eu` | Interaktivní dotazování OSM podle tagů, bboxu, relací; export GeoJSON | reference | – | – |
| [HDX (UN OCHA)](https://data.humdata.org/) | `data.humdata.org` | Globální populace ve vektorových H3 hexagonech 400 m (varianty 3 km a 22 km) — fúze GHSL, Facebook HRSL, Microsoft Buildings, Copernicus Land Cover a OSM | reference | – | – |
| [OpenCelliD](https://opencellid.org/) | `opencellid.org` | Otevřená databáze pozic BTS/cell towers — užitečné pro geolokaci | reference | – | – |
| [OSM Planet](https://planet.openstreetmap.org/) | `planet.openstreetmap.org` | Týdenní kompletní dumpy databáze OSM — XML (~165 GB) i PBF (~88 GB), full-history planet se všemi verzemi prvků, changesety a replikační diffy pro průběžnou synchronizaci | reference | – | – |
| [HydroSHEDS](https://www.hydrosheds.org/) | `hydrosheds.org` | Globální hydrologická data odvozená z DEM — říční sítě, hierarchická povodí a jezera ve standardních GIS formátech; verze 2 z TanDEM-X zatím jen pro Ameriku, globální pokrytí se dokončuje | reference | – | – |
| [Protected Planet (WDPA)](https://www.protectedplanet.net/) | `protectedplanet.net` | WDPA a WDOECM od UNEP-WCMC a IUCN — polygony a body přes 300 tisíc chráněných území a OECM celého světa, měsíční aktualizace, hromadné stahování i API | reference | – | – |
| [Marine Regions](https://www.marineregions.org/) | `marineregions.org` | Gazetteer a hranice na moři od VLIZ — výlučné ekonomické zóny, teritoriální a vnitřní vody, rozšířené šelfy a volné moře v GeoPackage/shp/KML, přes OGC služby i balík mregions2 | reference | – | – |
| [Open Infrastructure Map](https://openinframap.org/) | `openinframap.org` | Prohlížečka infrastruktury vykreslené z OSM — elektrické vedení, trafostanice a elektrárny, ropovody, plynovody a telekomunikační síť; bez exportu dat | reference | – | – |

## 3. ČR — katastr a geodata

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [ČÚZK — Dálkový přístup do KN](https://katastr.cuzk.gov.cz/) | `katastr.cuzk.gov.cz` | Dálkový přístup do KN — placená služba pro registrované uživatele, on-line výstupy z ISKN (LV, parcely, řízení); kořen domény dnes vede na cuzk.gov.cz/aplikace-dp | history | 36 | 2026-08-20 |
| [Nahlížení do KN](https://nahlizenidokn.cuzk.gov.cz/) | `nahlizenidokn.cuzk.gov.cz` | Veřejné nahlížení do KN zdarma a bez registrace — parcely, budovy, jednotky, LV a vlastníci; API zde není, na strojový přístup slouží samostatné REST API na api-kn.cuzk.gov.cz | history | 9 | 2026-06-25 |
| [SGI Nahlížení do KN](https://sgi-nahlizenidokn.cuzk.gov.cz/) | `sgi-nahlizenidokn.cuzk.gov.cz` | Grafická část — katastrální mapa, mapové služby | history | 4 | 2026-06-26 |
| [Geoportál ČÚZK](https://geoportal.cuzk.gov.cz/) | `geoportal.cuzk.gov.cz` | WMS/WFS/WMTS, ZABAGED, Ortofoto ČR, DMR 5G/DMP 1G, Data50/200. Klíčový CZ zdroj | history | 3 | 2026-08-27 |
| [ČÚZK — Žádosti](https://zadosti.cuzk.gov.cz/) | `zadosti.cuzk.gov.cz` | Žádosti o zřízení dálkového přístupu do KN, o výdej dat ve výměnném formátu ISKN (VFK) a o souhlas se šířením údajů katastru | history | 4 | 2026-08-06 |
| [ČÚZK (rozcestník)](https://www.cuzk.gov.cz/) | `cuzk.gov.cz` | Hlavní web zeměměřického a katastrálního úřadu | history | 9 | 2026-08-20 |
| [Národní geoportál INSPIRE (CENIA)](https://geoportal.gov.cz/) | `geoportal.gov.cz` | CZ INSPIRE katalog — metadata a služby napříč resorty, včetně historického ortofota z 50. let | reference | – | – |
| [ArcČR (ARCDATA Praha)](https://www.arcdata.cz/cs-cz/produkty/data/arccr) | `arcdata.cz` | ArcČR 4.3 — administrativní členění ČR s geometrií z RÚIAN k 1. 1. 2024 a napojenými statistikami ČSÚ a ÚAP, zdarma pod CC BY 4.0; starší ArcČR 500 v3.3 (sídla, vodstvo, doprava) je už jen archivní ke stažení | reference | – | – |
| [DIBAVOD (VÚV TGM)](https://www.dibavod.cz/) | `dibavod.cz` | Digitální báze vodohospodářských dat — povodí, vodní toky, nádrže | reference | – | – |
| [AOPK — Ochrana přírody](https://gis-aopkcr.opendata.arcgis.com/) | `gis-aopkcr.opendata.arcgis.com` | Chráněná území, Natura 2000, biotopy jako open data | reference | – | – |
| [LPIS — veřejný registr půdy (MZe)](https://mze.gov.cz/public/app/lpisext/lpis/verejny2/plpis/) | `mze.gov.cz` | Zemědělské půdní bloky, využití půdy, WMS/WFS | reference | – | – |
| [Česká geologická služba](https://cgs.gov.cz/mapy-a-data) | `cgs.gov.cz` | Geologické, hydrogeologické a půdní mapy, sesuvy, poddolování | reference | – | – |
| [Geoportál Praha](https://www.geoportalpraha.cz/) | `geoportalpraha.cz` | Pražská geodata a open data — ortofota, územní plán, 3D model | reference | – | – |
| [Portál DMVS (ČÚZK)](https://dmvs.cuzk.gov.cz/) | `dmvs.cuzk.gov.cz` | Portál digitální mapy veřejné správy — bezešvé prohlížení krajských digitálních technických map (DTM) a stahování dat v jednotném formátu JVF DTM | reference | – | – |
| [REST API dat katastru nemovitostí (ČÚZK)](https://api-kn.cuzk.gov.cz/) | `api-kn.cuzk.gov.cz` | Bezplatné REST API ke katastru — parcely, budovy, jednotky a řízení v JSON, po registraci přes Identitu občana nebo účet dálkového přístupu | reference | – | – |
| [ČÚZK — Mapové služby](https://services.cuzk.gov.cz/) | `services.cuzk.gov.cz` | Mapový server ČÚZK — bezúplatné WMS/WFS/WMTS endpointy katastrální mapy, ortofota, ZABAGED a RÚIAN, odtud se berou URL do QGIS nebo skriptu | reference | – | – |
| [ČÚZK — Stahovací služby ATOM](https://atom.cuzk.gov.cz/) | `atom.cuzk.gov.cz` | ATOM feedy ČÚZK pro dávkové stahování po mapových listech — ortofoto, katastrální mapa, RÚIAN a INSPIRE témata bezúplatně pod CC BY 4.0, skriptovatelná alternativa k eShopu | reference | – | – |
| [Půda v mapách (VÚMOP)](https://mapy.vumop.cz/) | `mapy.vumop.cz` | Mapový server VÚMOP — ohroženost vodní a větrnou erozí (SEO/MEO pro DZES 5), vlastnosti půd odvozené z BPEJ, třídy ochrany ZPF a zranitelnost podzemních vod | reference | – | – |

## 4. ČR — doprava / mobilita

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Golemio (Praha)](https://golemio.cz/) | `golemio.cz` | Datová platforma hl. m. Prahy — MHD, parkování, senzory, sdílená mobilita | history | 4 | 2026-08-26 |
| [Golemio API](https://api.golemio.cz/) | `api.golemio.cz` | API dokumentace a správa klíčů — Public Transport, GTFS, polohy vozidel; OpenAPI pro PID je na /pid/docs/openapi/ | history | 39 | 2026-08-26 |
| [ŘSD MobilityData](https://mobilitydata.rsd.cz/) | `mobilitydata.rsd.cz` | Registr odběrů NDIC — registrace k odběru dopravních informací ve formátech DATEX II a nativní NDIC XML včetně lokačních tabulek ALERT-C; přístup jen po přihlášení | history | 27 | 2026-08-27 |
| [Geoportál ŘSD](https://geoportal.rsd.cz/web) | `geoportal.rsd.cz` | Silniční a dálniční síť ČR — mapové aplikace, datové vrstvy, uzly a úseky | history | 2 | 2026-08-26 |
| [Dopravní info (NDIC)](https://dopravniinfo.gov.cz/) | `dopravniinfo.gov.cz` | Uzavírky, nehody, sjízdnost, real-time dopravní události | history | 9 | 2026-08-26 |
| [NAIS API](https://api-nais.dopravniinfo.cz/) | `api-nais.dopravniinfo.cz` | API vrstva nad národními dopravními informacemi (DATEX II) — přístup jen s účtem zřízeným přes Registr odběrů NDIC | history | 4 | 2026-08-26 |
| [PID](https://pid.cz/) | `pid.cz` | Pražská integrovaná doprava — jízdní řády a mapy linek; GTFS feed se stahuje z data.pid.cz (https://data.pid.cz/PID_GTFS.zip) | history | 1 | 2026-08-25 |
| [Ministerstvo dopravy](https://md.gov.cz/) | `md.gov.cz` | Web Ministerstva dopravy — sekce Statistiky, Dokumenty a Otevřená data (datové sady rezortu) | history | 4 | 2026-06-18 |
| [Sčítání dopravy ŘSD](https://scitani.rsd.cz/) | `scitani.rsd.cz` | Výsledky celostátního sčítání dopravy 2010, 2016 a 2020 — intenzity automobilové dopravy po úsecích dálniční a silniční sítě ČR | reference | – | – |
| [Dopravní nehody v ČR (CDV)](https://nehody.cdv.cz/) | `nehody.cdv.cz` | Nehody evidované Policií ČR od roku 2006 — filtrování podle času, území a 64 evidovaných parametrů, měsíční aktualizace, export do PDF | reference | – | – |
| [Geoportál DTMŽ (Správa železnic)](https://geoportal.spravazeleznic.cz/) | `geoportal.spravazeleznic.cz` | Digitální technická mapa železnic — mapový klient, Všeobecná železniční mapa, vyhledávání metadat a žádost o výdej dat | reference | – | – |
| [Portál CIS JŘ](https://portal.cisjr.cz/) | `portal.cisjr.cz` | Celostátní informační systém o jízdních řádech (Ministerstvo dopravy a CHAPS) — jízdní řády autobusů, MHD, vlaků a lanových drah, strojově čitelná data (JDF, NeTEx) v adresáři /pub/ | reference | – | – |

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
| [Mapa kriminality (Policie ČR)](https://kriminalita.policie.gov.cz/) | `kriminalita.policie.gov.cz` | Oficiální mapa kriminality Policie ČR — evidované a objasněné skutky podle druhu trestné činnosti a územních obvodů policie; aplikace vyžaduje JavaScript | reference | – | – |
| [GDACS](https://www.gdacs.org/) | `gdacs.org` | Globální upozornění na katastrofy (EC-JRC a OSN) — zemětřesení, cyklóny, povodně a sopky s geodaty a odhadem zasažené populace | reference | – | – |
| [Copernicus EMS](https://emergency.copernicus.eu/) | `emergency.copernicus.eu` | Emergency Management Service — On-Demand Mapping satelitních map škod pro aktivované mimořádné události, povodně EFAS/GloFAS, sucho EDO/GDO a lesní požáry na forest-fire.emergency.copernicus.eu | reference | – | – |
| [UCDP](https://ucdp.uu.se/) | `ucdp.uu.se` | Uppsala Conflict Data Program — georeferencovaná databáze událostí ozbrojených konfliktů (GED) od roku 1989, delší časová řada a jiná metodika kódování než ACLED | reference | – | – |

## 6. Remote sensing / rastr

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Copernicus Data Space](https://dataspace.copernicus.eu/) | `dataspace.copernicus.eu` | Sentinel-1/2/3/5P zdarma — browser, STAC, OData, S3 přístup | reference | – | – |
| [USGS EarthExplorer](https://earthexplorer.usgs.gov/) | `earthexplorer.usgs.gov` | Landsat archiv od 1972, letecké snímky, DEM | reference | – | – |
| [NASA Earthdata](https://www.earthdata.nasa.gov/) | `earthdata.nasa.gov` | MODIS, VIIRS, SRTM, GPM, GRACE — CMR API | reference | – | – |
| [OpenTopography](https://opentopography.org/) | `opentopography.org` | LiDAR point clouds a globální DEM (SRTM, Copernicus DEM, ALOS) | reference | – | – |
| [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) | `planetarycomputer.microsoft.com` | STAC katalog a API nad otevřenými EO datasety (Sentinel, Landsat, NAIP, Copernicus DEM) — hostovaný JupyterHub byl vypnut v červnu 2024, data a API běží dál | reference | – | – |
| [Google Earth Engine](https://earthengine.google.com/) | `earthengine.google.com` | Planetární petabajtový katalog s cloudovým zpracováním | reference | – | – |
| [ESA WorldCover](https://esa-worldcover.org/) | `esa-worldcover.org` | Globální land cover 10 m ze Sentinelu-1 a -2, 11 tříd — existují jen ročníky 2020 (v100) a 2021 (v200), novější nevznikly | reference | – | – |
| [Copernicus Land Monitoring Service (CORINE)](https://land.copernicus.eu/) | `land.copernicus.eu` | Portál Copernicus Land Monitoring Service — CORINE Land Cover (referenční roky 1990-2018, aktualizace po šesti letech, poslední 2018) plus Urban Atlas, High Resolution Layers a CLCplus Backbone | reference | – | – |
| [GHSL (Global Human Settlement)](https://human-settlement.emergency.copernicus.eu/) | `human-settlement.emergency.copernicus.eu` | Zastavěnost, populační rastr, urbanizace — JRC | reference | – | – |
| [STAC Index](https://stacindex.org/) | `stacindex.org` | Katalog veřejných STAC endpointů | reference | – | – |
| [ASF DAAC (Vertex)](https://asf.alaska.edu/) | `asf.alaska.edu` | NASA DAAC pro radarová data — archiv Sentinel-1 (včetně 1D) a NISAR, vyhledávač Vertex, Python asf_search a on-demand zpracování HyP3 (RTC, InSAR, OPERA RTC-S1) | reference | – | – |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | `firms.modaps.eosdis.nasa.gov` | Detekce aktivních požárů a tepelných anomálií z MODIS (Aqua, Terra) a VIIRS (S-NPP, NOAA-20/21) do tří hodin od přeletu, pro USA a Kanadu v reálném čase — SHP/KML/TXT, WMS, API i e-mailové alerty | reference | – | – |
| [Vantor Open Data Program](https://vantor.com/company/open-data-program/) | `vantor.com` | Snímky WorldView ze zasažených oblastí zdarma pod CC BY-NC 4.0 (dřívější Maxar Open Data) — jen po aktivaci programu u velkých náhlých katastrof, ne souvislé pokrytí | reference | – | – |
| [Global Nature Watch](https://globalnaturewatch.org/) | `globalnaturewatch.org` | Nástupce Global Forest Watch od WRI — úbytek lesního krytu 30 m (UMD/Hansen, 2001-2025), integrované deforestační alerty 30 m aktualizované týdně a globální land cover, s mapou a otevřeným datovým portálem | reference | – | – |
| [Registry of Open Data on AWS](https://registry.opendata.aws/) | `registry.opendata.aws` | Rejstřík otevřených dat ležících na AWS S3 — Sentinel-2 COG se STACem, Landsat, NOAA GOES a stovky dalších v cloud-native formátech (COG, Zarr, NetCDF) čitelných přímo z GDAL přes /vsis3/ | reference | – | – |

## 7. Statistika / demografie

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [ČSÚ](https://csu.gov.cz/) | `csu.gov.cz` | ČSÚ Ceny nemovitostí — průměrné ceny rodinných domů a bytů a cenové indexy po krajích a okresech za tříleté klouzavé období | history | 2 | 2026-06-16 |
| [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco) | `ec.europa.eu` | Evropské admin hranice NUTS, populační grid 1 km, geodata ke statistice | reference | – | – |
| [EU Data Portal](https://data.europa.eu/) | `data.europa.eu` | Agregátor otevřených dat EU včetně INSPIRE geodatových sad | reference | – | – |
| [WorldPop](https://www.worldpop.org/) | `worldpop.org` | Rastr hustoty populace 100 m, věkové struktury, migrace | reference | – | – |
| [Kontur Population Dataset](https://data.humdata.org/dataset/kontur-population-dataset) | `data.humdata.org` | H3-indexovaný globální populační dataset | reference | – | – |
| [Our World in Data](https://ourworldindata.org/) | `ourworldindata.org` | Kurátorované country-level časové řady | reference | – | – |
| [ČSÚ Statistický geoportál](https://geodata.csu.gov.cz/) | `geodata.csu.gov.cz` | Statistický geoportál ČSÚ — gridy SLDB 2021, ZSJ, registr sčítacích obvodů a budov (RSO) a hranice NUTS/LAU přes ArcGIS REST, WMS/WFS a INSPIRE služby | reference | – | – |
| [UN World Population Prospects](https://population.un.org/wpp/) | `population.un.org` | Odhady a projekce populace OSN po zemích do roku 2100 — věkové struktury, fertilita, mortalita a migrace, kompletní datové sady ke stažení | reference | – | – |
| [OECD Data Explorer](https://data-explorer.oecd.org/) | `data-explorer.oecd.org` | Statistiky OECD včetně regionálních ukazatelů TL2/TL3 a metropolitních areálů — strojový přístup přes SDMX API na sdmx.oecd.org | reference | – | – |
| [IPUMS International](https://international.ipums.org/international/) | `international.ipums.org` | Harmonizovaná census mikrodata ze 104 zemí (656 sčítání) včetně hranic administrativních jednotek — zdarma, ale až po registraci a schválení účelu použití | reference | – | – |

## 8. Historické mapy

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [David Rumsey Map Collection](https://www.davidrumsey.com/) | `davidrumsey.com` | Přes 150 000 naskenovaných map a atlasů online s IIIF — georeferencovaná přes Georeferencer je jen část sbírky | reference | – | – |
| [Old Maps Online](https://www.oldmapsonline.org/) | `oldmapsonline.org` | Meta-vyhledávač historických map podle místa a času | reference | – | – |
| [Mapire (Arcanum Maps)](https://maps.arcanum.com/en/) | `maps.arcanum.com` | Habsburská vojenská mapování (I.-III.) georeferencovaná — ideální pro ČR | reference | – | – |
| [Archivní mapy ČÚZK](https://ags.cuzk.gov.cz/archiv/) | `ags.cuzk.gov.cz` | Archivní mapy ČÚZK — císařské otisky a indikační skici stabilního katastru, stará státní mapová díla a archiv leteckých měřických snímků od roku 1936 | reference | – | – |
| [Chartae Antiquae](https://www.chartae-antiquae.cz/cs/) | `chartae-antiquae.cz` | Virtuální mapová sbírka historických map ČR | reference | – | – |
| [National Library of Scotland — Map Images](https://maps.nls.uk/) | `maps.nls.uk` | Zoomovatelné mapy Britských ostrovů 16.–20. století, velká část georeferencovaná — side-by-side a spyglass prohlížeč, vrstvy použitelné jako XYZ v QGIS přes Historic Maps API | reference | – | – |
| [Allmaps](https://allmaps.org/) | `allmaps.org` | Georeferencování IIIF map přímo v prohlížeči — editor, viewer a tile server, který z Georeference Annotation udělá XYZ vrstvu pro QGIS, MapLibre, OpenLayers i Leaflet bez vytváření GeoTIFFů | reference | – | – |
| [USGS topoView](https://ngmdb.usgs.gov/topoview/) | `ngmdb.usgs.gov` | Přes 178 000 historických topografických map USGS z let 1884–2006 — zdarma ke stažení jako GeoTIFF, GeoPDF, KMZ nebo JPEG | reference | – | – |
| [Library of Congress — Maps](https://www.loc.gov/maps/) | `loc.gov` | Mapová sbírka Geography & Map Division včetně požárních plánů Sanborn — velká část public domain, ke stažení až v plném TIFF | reference | – | – |

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
| [CesiumJS](https://cesium.com/platform/cesiumjs/) | `cesium.com` | 3D glóbus a mapy ve WebGL — 3D Tiles, globální terén, glTF modely a časová osa; knihovna pod Apache 2.0, hostované služby ion placené | reference | – | – |
| [MapProxy](https://mapproxy.org/) | `mapproxy.org` | Proxy a dlaždicová cache nad WMS — z pomalé WMS udělá rychlé WMTS/XYZ dlaždice, umí reprojekci, slučování vrstev a offline seeding | reference | – | – |
| [OpenMapTiles](https://openmaptiles.org/) | `openmaptiles.org` | Otevřené schéma vektorových dlaždic z OSM a Natural Earth — nástroje na generování vlastních dlaždic a self-hosting, BSD/CC-BY s povinnou atribucí | reference | – | – |
| [Mapbox](https://www.mapbox.com/) | `mapbox.com` | Komerční mapová platforma — hostované vektorové a satelitní basemapy, Studio pro tvorbu stylů a Mapbox GL JS (od v2 proprietární licence); free tier s měsíčním limitem | reference | – | – |
| [OpenTopoMap](https://opentopomap.org/) | `opentopomap.org` | Topografická rastrová basemapa z OSM a SRTM ve stylu německých topo map — vrstevnice a stínovaný reliéf, dlaždice bez API klíče pod CC-BY-SA 3.0 | reference | – | – |

## 10. Spatial DB / analytika

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [PostGIS](https://postgis.net/) | `postgis.net` | Prostorové rozšíření PostgreSQL — typy geometry a geography a GiST indexy; rastr a topologie se instalují jako samostatné extenze (postgis_raster, postgis_topology), pgRouting je samostatný projekt | reference | – | – |
| [PostgreSQL](https://www.postgresql.org/) | `postgresql.org` | Hostitelská DB pro PostGIS | bookmarks+history | 1 | 2026-08-27 |
| [GDAL / OGR](https://gdal.org/) | `gdal.org` | Univerzální konverze a transformace — ogr2ogr, gdalwarp, gdal_translate | reference | – | – |
| [QGIS](https://qgis.org/) | `qgis.org` | Desktopové GIS — vizualizace, editace, Processing toolbox, modely | reference | – | – |
| [GeoPandas](https://geopandas.org/) | `geopandas.org` | Pandas s geometrií (Shapely + pyproj + pyogrio) — základ Python geo analytiky | reference | – | – |
| [Shapely](https://shapely.readthedocs.io/) | `shapely.readthedocs.io` | Planární geometrické operace v Pythonu nad GEOS | reference | – | – |
| [Rasterio](https://rasterio.readthedocs.io/) | `rasterio.readthedocs.io` | Pythonic čtení a zápis rastrů nad GDAL | reference | – | – |
| [rioxarray](https://corteva.github.io/rioxarray/) | `corteva.github.io` | Multidimenzionální rastr a časové řady pro EO analytiku | reference | – | – |
| [DuckDB spatial](https://duckdb.org/docs/current/core_extensions/spatial/overview) | `duckdb.org` | In-process SQL analytika s prostorovým rozšířením, čte GeoParquet i přímo z S3 | reference | – | – |
| [Apache Sedona](https://sedona.apache.org/) | `sedona.apache.org` | Distribuovaná prostorová analytika nad Sparkem/Flinkem | reference | – | – |
| [H3](https://h3geo.org/) | `h3geo.org` | Hierarchický index nad hexagonální sítí (na každé úrovni 12 pětiúhelníků) — agregace bodů, sousedství, gridDisk | reference | – | – |
| [S2 Geometry](https://s2geometry.io/) | `s2geometry.io` | Sférická geometrie a indexování buňkami, alternativa k H3 | reference | – | – |
| [PySAL](https://pysal.org/) | `pysal.org` | Prostorová statistika — autokorelace, Moran's I, LISA, regionalizace | reference | – | – |
| [MovingPandas](https://movingpandas.org/) | `movingpandas.org` | Analýza trajektorií a pohybu nad GeoPandas | reference | – | – |
| [Lonboard](https://developmentseed.org/lonboard/) | `developmentseed.org` | Rychlá vizualizace velkých GeoDataFrames v notebooku přes deck.gl | reference | – | – |
| [Kepler.gl](https://kepler.gl/) | `kepler.gl` | Geo-analytické UI nad deck.gl pro rychlý průzkum velkých datasetů | reference | – | – |
| [CARTO](https://carto.com/) | `carto.com` | Cloud location intelligence nad Snowflake/BigQuery/Databricks | history | 2 | 2026-08-26 |
| [Felt](https://felt.com/) | `felt.com` | Kolaborativní webové mapy, rychlé sdílení analýz | reference | – | – |
| [GRASS GIS](https://grass.osgeo.org/) | `grass.osgeo.org` | Rastrová, terénní a hydrologická analytika s vlastní datovou strukturou (moduly r.*, v.*) — sklony, povodí, viewshed a časové řady, volatelné i z QGIS Processingu | reference | – | – |
| [sf (Simple Features for R)](https://r-spatial.github.io/sf/) | `r-spatial.github.io` | Simple features pro R — geometrie jako sloupec v data.frame, operace přes GEOS, čtení a zápis přes GDAL, transformace přes PROJ, sférická geometrie přes s2 | reference | – | – |
| [PDAL](https://pdal.org/) | `pdal.org` | Pipeline pro zpracování mračen bodů — čtení LAS/LAZ/COPC, filtrace a klasifikace, výřezy a převod na rastr, deklarativně v JSON | reference | – | – |
| [GEOS](https://libgeos.org/) | `libgeos.org` | C/C++ knihovna geometrických predikátů a operací (intersects, buffer, overlay, validace) — jádro, na kterém stojí PostGIS, QGIS, GDAL, Shapely i R sf | reference | – | – |
| [xarray](https://xarray.dev/) | `xarray.dev` | Pojmenovaná N-rozměrná pole s indexy a líným výpočtem přes Dask — datový model pro EO časové řady a datové kostky, čte NetCDF, HDF, Zarr i GRIB | reference | – | – |

## 11. Routing / síťová analýza

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [OSRM](https://project-osrm.org/) | `project-osrm.org` | Rychlý routing nad OSM — table (matrix), match, trip | reference | – | – |
| [Valhalla](https://valhalla.github.io/valhalla/) | `valhalla.github.io` | Tile-based routing, isochrony, map-matching, multimodal | reference | – | – |
| [GraphHopper](https://www.graphhopper.com/) | `graphhopper.com` | Routing engine + isochrony, dobrá Java knihovna i API | reference | – | – |
| [pgRouting](https://pgrouting.org/) | `pgrouting.org` | Routing přímo v PostGIS — Dijkstra, TSP, driving distance | reference | – | – |
| [OSMnx](https://osmnx.readthedocs.io/) | `osmnx.readthedocs.io` | Stažení a analýza uličních sítí z OSM v Pythonu (NetworkX) | reference | – | – |
| [R5 / Conveyal](https://conveyal.com/) | `conveyal.com` | Multimodální dostupnostní analýza nad GTFS + OSM | reference | – | – |
| [OpenTripPlanner](https://www.opentripplanner.org/) | `opentripplanner.org` | Multimodální plánovač spojení nad GTFS a OSM — itineráře MHD s přestupy a dostupnostní analýzy přes GraphQL API (GTFS i Transmodel) | reference | – | – |
| [openrouteservice](https://openrouteservice.org/) | `openrouteservice.org` | Hostované routovací API nad OSM od HeiGIT — trasy, matice vzdáleností, isochrony, výškové profily a optimalizace rozvozu, s bezplatnou vrstvou po registraci klíče i možností self-hostingu | reference | – | – |
| [NetworkX](https://networkx.org/documentation/stable/) | `networkx.org` | Grafové algoritmy v Pythonu — nejkratší cesty, centrality, komponenty a toky; datová struktura, ve které OSMnx vrací uliční síť | reference | – | – |
| [Google OR-Tools](https://developers.google.com/optimization) | `developers.google.com` | Solver na okružní a rozvozní úlohy — TSP a VRP s časovými okny, kapacitami a více vozidly, typicky nad maticí jízdních dob z OSRM nebo Valhally | reference | – | – |
| [Pandana](https://udst.github.io/pandana/) | `udst.github.io` | Výpočet dostupnosti v síti přes contraction hierarchies — agregace POI a vah do vzdálenostních pásem kolem každého uzlu, řádově rychleji než obyčejný Dijkstra | reference | – | – |

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
| [GeoPackage](https://www.geopackage.org/) | `geopackage.org` | OGC standard (adoptovaná verze 1.4.0) — jeden SQLite soubor s vektory, dlaždicemi i atributy, výchozí výstupní formát QGIS a náhrada za Shapefile | reference | – | – |
| [EPSG Registry (IOGP)](https://epsg.org/) | `epsg.org` | Oficiální registr EPSG Geodetic Parameter Dataset od IOGP (v13.102) — primární zdroj, ze kterého žijí epsg.io i PROJ; online vyhledávání zdarma, offline export datasetu, datový model dle ISO 19111:2019 | reference | – | – |
| [Zarr](https://zarr.dev/) | `zarr.dev` | Formát pro chunkovaná komprimovaná N-rozměrná pole v object storage (v2/v3, implementace v 10 jazycích) — základ cloud-native klimatických a EO datasetů čtených přes xarray | reference | – | – |
| [COPC](https://copc.io/) | `copc.io` | Cloud Optimized Point Cloud 1.0 — LAZ 1.4 s body uspořádanými do clusterovaného oktree, čitelný po částech přes HTTP range requesty, podporuje PDAL i QGIS | reference | – | – |
| [GTFS](https://gtfs.org/) | `gtfs.org` | Referenční specifikace GTFS Schedule a GTFS Realtime pod správou MobilityData — jízdní řády, zastávky, tarify a živé polohy vozidel | reference | – | – |

## 13. Open data / registry CZ

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Národní katalog otevřených dat](https://data.gov.cz/) | `data.gov.cz` | Centrální CZ katalog datových sad včetně geodat a INSPIRE | history | 2 | 2026-08-27 |
| [Hlídač státu](https://www.hlidacstatu.cz/) | `hlidacstatu.cz` | Smlouvy, dotace, zakázky, politici — API V2. Máš registrovaný účet | history | 23 | 2026-08-20 |
| [Registr smluv](https://smlouvy.gov.cz/) | `smlouvy.gov.cz` | Otevřený registr smluv státu | history | 3 | 2026-07-24 |
| [ARES](https://ares.gov.cz/) | `ares.gov.cz` | Ekonomické subjekty ČR — REST API, adresy sídel (geokódovatelné) | history | 7 | 2026-08-05 |
| [Obchodní rejstřík](https://or.justice.cz/) | `or.justice.cz` | Veřejný rejstřík — vazby, sídla, statutáři | history | 16 | 2026-08-05 |
| [ISIR](https://isir.justice.cz/) | `isir.justice.cz` | Insolvenční rejstřík | history | 5 | 2026-08-11 |
| [Evidence skutečných majitelů](https://esm.justice.cz/) | `esm.justice.cz` | Rejstřík skutečných majitelů obchodních korporací a svěřenských fondů (MSp) — kdo za firmou reálně stojí za nastrčenými statutáry | reference | – | – |
| [Registr živnostenského podnikání](https://rzp.gov.cz/) | `rzp.gov.cz` | Živnostenská oprávnění fyzických i právnických osob — včetně seznamu provozoven s adresami (geokódovatelné) | reference | – | – |
| [Monitor státní pokladny](https://monitor.statnipokladna.gov.cz/) | `monitor.statnipokladna.gov.cz` | Rozpočty a účetní výkazy obcí, krajů a státních institucí — včetně ročních dumpů ke stažení | reference | – | – |
| [Národní elektronický nástroj (NEN)](https://nen.nipez.cz/) | `nen.nipez.cz` | Systém MMR pro zadávání veřejných zakázek — zadávací řízení, profily zadavatelů a registry dodavatelů, přístupné bez přihlášení | reference | – | – |
| [Nabídka majetku státu (ÚZSVM)](https://nabidkamajetku.gov.cz/) | `nabidkamajetku.gov.cz` | Katalog ÚZSVM s nabídkami státního majetku — prodeje, elektronické dražby a pronájmy nemovitostí, filtrovatelné podle kraje a obce | reference | – | – |

## 14. OSINT / investigace

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Progresus OSINT](https://osint.cloud.progresus.cz/) | `osint.cloud.progresus.cz` | Tvoje platforma pro due diligence z veřejných zdrojů — zdroje, laboratoř, architektura | history | 72 | 2026-08-23 |
| [vomaste.cz](https://vomaste.cz/) | `vomaste.cz` | Tvůj projekt — Registr tvrzení / zdrojů / kauz, dossiery, Globální mapa | history | 1407 | 2026-08-15 |
| [Situační radar (HzsRadar)](https://situacni-radar.fly.dev/) | `situacni-radar.fly.dev` | Tvoje agregace událostí IZS v Phoenixu | history | 41 | 2026-08-27 |
| [Maltego](https://www.maltego.com/) | `maltego.com` | Link-analysis platforma pro OSINT vyšetřování | history | 2 | 2026-08-05 |
| [OpenAlex](https://openalex.org/) | `openalex.org` | Otevřený katalog vědeckých prací s afiliacemi institucí (geokódovatelné) | history | 9 | 2026-08-11 |
| [Common Crawl](https://commoncrawl.org/) | `commoncrawl.org` | Otevřený webový crawl korpus | bookmarks+history | 0 | 2026-08-27 |
| [North Data](https://www.northdata.com/) | `northdata.com` | Firemní rejstříky, účetní závěrky a vazby osob a firem ve 26 zemích Evropy včetně ČR (v záběru je i Izrael) | history | 22 | 2026-07-22 |
| [Investigace.cz](https://www.investigace.cz/) | `investigace.cz` | České centrum investigativní žurnalistiky (OCCRP) | bookmarks+history | 0 | 2026-08-27 |
| [OpenSanctions](https://www.opensanctions.org/) | `opensanctions.org` | Sankční seznamy, PEP a watchlisty z ~460 zdrojů (přes 1,9 mil. entit) — bulk data ve FollowTheMoney i screening API; zdarma pro nekomerční užití, komerčně za licenci | reference | – | – |
| [ICIJ Offshore Leaks Database](https://offshoreleaks.icij.org/) | `offshoreleaks.icij.org` | Přes 810 tisíc offshore entit z Pandora, Paradise, Panama Papers, Bahamas Leaks a Offshore Leaks — ke stažení pod ODbL i přes REST API | reference | – | – |
| [Bellingcat](https://www.bellingcat.com/) | `bellingcat.com` | Investigace z otevřených zdrojů — metodický toolkit pro geolokaci a verifikaci snímků a videí | reference | – | – |
| [ADS-B Exchange](https://www.adsbexchange.com/) | `adsbexchange.com` | Nefiltrované sledování letadel z komunitní sítě 25 tis. přijímačů — veřejná mapa zdarma, historická data, API, gRPC stream a S3 jen za placené předplatné | reference | – | – |
| [Global Fishing Watch](https://globalfishingwatch.org/) | `globalfishingwatch.org` | Pohyb plavidel z AIS a satelitní detekce — mapa, Vessel Viewer a datasety; API zdarma, ale až po registraci a vydání tokenu | reference | – | – |

## 15. Počasí / klima

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [ČHMÚ](https://www.chmi.cz/) | `chmi.cz` | Předpovědi, radar, srážky, hydrologie; otevřená data na opendata.chmi.cz | reference | – | – |
| [Meteoradar.cz](https://www.meteoradar.cz/) | `meteoradar.cz` | Online srážkový radar ČR a Evropa | history | 2 | 2026-06-26 |
| [In-počasí](https://www.in-pocasi.cz/) | `in-pocasi.cz` | Předpovědi, radar, síť stanic | history | 1 | 2026-08-17 |
| [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/) | `cds.climate.copernicus.eu` | ERA5 reanalýza, klimatické projekce, API | reference | – | – |
| [Open-Meteo](https://open-meteo.com/) | `open-meteo.com` | Free weather API bez klíče, historická i předpovědní data po souřadnicích | reference | – | – |
| [WorldClim](https://worldclim.org/) | `worldclim.org` | Globální klimatické rastry — měsíční srážky a teploty a 19 bioklimatických proměnných v rozlišení 30 s až 10 min, historie i budoucí scénáře | reference | – | – |
| [ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data) | `ecmwf.int` | Otevřená část předpovědí ECMWF (IFS a AIFS) v GRIB2 pod CC BY 4.0 — datový endpoint data.ecmwf.int agresivně rate-limituje, přes klienta ecmwf-opendata to jde lépe než ručně | reference | – | – |
| [NOAA NOMADS](https://nomads.ncep.noaa.gov/) | `nomads.ncep.noaa.gov` | Operativní modely NCEP (GFS, GEFS, HRRR) v GRIB2 a přes OPeNDAP — včetně částečného stahování polí přes filtry | reference | – | – |
| [Copernicus Atmosphere Data Store](https://ads.atmosphere.copernicus.eu/) | `ads.atmosphere.copernicus.eu` | CAMS analýzy a předpovědi kvality ovzduší, aerosolů a složení atmosféry — stejné katalogové rozhraní, API i earthkit jako Climate Data Store | reference | – | – |
| [Klimatická změna (CzechGlobe)](https://www.klimatickazmena.cz/) | `klimatickazmena.cz` | Klimatický portál Ústavu výzkumu globální změny AV ČR — mapy, grafy a infografiky ke klimatu ČR: pozorované změny, scénáře a dopady na lesnictví, zemědělství a vodní prostředí | reference | – | – |

## 16. Nemovitosti / trh

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [Sreality](https://www.sreality.cz/) | `sreality.cz` | CZ inzerce s geokódovanými nabídkami | history | 5 | 2026-06-16 |
| [Flat Zone](https://www.flatzone.cz/) | `flatzone.cz` | Vyhledávač novostaveb a developerských projektů v ČR — odhad ceny a datová platforma; B2B větev běží na b2b.flatzone.cz (dataligence.cz tam dnes redirectuje) | history | 5 | 2026-08-14 |
| [ČSÚ — Ceny nemovitostí](https://csu.gov.cz/produkty/ceny-nemovitosti) | `csu.gov.cz` | Ceny nemovitostí 2022-2024 podle území — v historii máš přesně tuhle stránku | reference | – | – |
| [CBRE](https://www.cbre.cz/) | `cbre.cz` | Komerční realitní analytika a market reporty | history | 1 | 2026-06-16 |
| [Bezrealitky](https://www.bezrealitky.cz/) | `bezrealitky.cz` | CZ inzerce prodeje a pronájmu bez provize — velký podíl přímých majitelů, mutace SK a EN | reference | – | – |
| [Valuo](https://www.valuo.cz/) | `valuo.cz` | Odhady cen nemovitostí v ČR — mapa realizovaných prodejů z katastru a inzerce a cenový index; mapa a odhad zdarma, PROFI a API za 5 000–10 000 Kč/rok bez DPH | reference | – | – |
| [ČNB — finanční stabilita](https://www.cnb.cz/cs/financni-stabilita/) | `cnb.cz` | Zprávy o finanční stabilitě, zátěžové testy a limity úvěrových ukazatelů LTV, DTI a DSTI — makro pohled na trh bydlení | reference | – | – |

## 17. Učení / komunita

| Web | Doména | Popis | Zdroj | Návštěv | Poslední |
|---|---|---|---|--:|---|
| [UofT Map and Data Library](https://mdl.library.utoronto.ca/) | `mdl.library.utoronto.ca` | Mapová a datová knihovna University of Toronto — veřejná knihovna návodů a workshopů ke GIS a statistice; většina datových sad je přístupná jen příslušníkům univerzity | history | 1 | 2026-08-27 |
| [GIS StackExchange](https://gis.stackexchange.com/) | `gis.stackexchange.com` | Nejrychlejší cesta k odpovědi na konkrétní GIS problém | reference | – | – |
| [Awesome Geospatial](https://github.com/sacridini/Awesome-Geospatial) | `github.com` | Kurátorovaný seznam geo nástrojů a datasetů | reference | – | – |
| [Observable](https://observablehq.com/) | `observablehq.com` | D3 notebooky — kartografické projekce a vizualizace | bookmarks+history | 0 | 2026-08-27 |
| [Spatial Thoughts](https://spatialthoughts.com/) | `spatialthoughts.com` | Kvalitní kurzy QGIS, GEE a Python geo | reference | – | – |
| [OSGeo](https://www.osgeo.org/) | `osgeo.org` | Nadace zastřešující ~50 open source geo projektů (QGIS, GDAL, PostGIS, GeoServer, GRASS, pgRouting) — pořádá konferenci FOSS4G, vydává OSGeoLive a sdružuje lokální chaptery | reference | – | – |
| [OpenStreetMap Wiki](https://wiki.openstreetmap.org/) | `wiki.openstreetmap.org` | Referenční dokumentace tagovacího schématu OSM — co který key a value znamená a jak se regionálně používá; bez ní se Overpass dotaz nedá napsat | reference | – | – |
| [geocompx (Geocomputation with R / Python)](https://geocompx.org/) | `geocompx.org` | Volně dostupné učebnice Geocomputation with R (CC-BY-NC-ND) a Geocomputation with Python — plus rozpracované verze pro Julii a tmap | reference | – | – |
| [Introduction to Python for Geographic Data Analysis](https://pythongis.org/) | `pythongis.org` | Volná online učebnice (Tenkanen, Heikinheimo, Whipp) od základů Pythonu po GIS s geopandas a shapely, CC 4.0 | reference | – | – |
| [Anita Graser — Free and Open Source GIS Ramblings](https://anitagraser.com/) | `anitagraser.com` | Blog autorky MovingPandas — QGIS, PyQGIS, Trajectools a analýza pohybových dat | reference | – | – |
