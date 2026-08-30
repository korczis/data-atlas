# Geospatial

## The rule: geometry is never a property of an entity

`country.geometry` is wrong, and it is wrong in a way that only shows up years
later. Borders move; an entity outlives any one polygon; two sources disagree
about a disputed boundary and both disagreements are real.

```
geo.feature            a spatial thing that persists  ("the land boundary of Poland")
  └─ geo.feature_version   one version of its geometry, from one source, over one period
geo.entity_feature     links an entity to a feature, in a role, over a period
geo.entity_point       a point a source published, with the original text beside it
```

Several versions may coexist for the same feature and period: two boundary
sources disagreeing are two rows, and the model does not have to pick. ADR-0011.

The role on `geo.entity_feature` matters: an entity's *administered* extent and
its *claimed* extent are different polygons, and a single link per entity would
force encoding one claim as fact.

## CRS

Canonical storage is **EPSG:4326**, as `geometry`, because that is what every
exchange format and every other spatial tool expects.

`source_srid` records what the source actually supplied, so a reprojection stays
auditable rather than assumed. Losing it makes the transformation unreviewable.

`geometry` rather than `geography` for storage: geodesic work casts to
`geography` or projects explicitly at query time. What is never acceptable is
naive planar arithmetic on lon/lat — an area computed that way is wrong
everywhere except near the equator.

```sql
-- correct: geodesic area in square metres
SELECT ST_Area(geom::geography) FROM geo.feature_version WHERE feature_id = 1;
```

`ST_IsValid` is a CHECK constraint on insert. An invalid polygon silently
produces wrong areas and wrong intersections rather than an error, so it is
refused at the boundary.

## Coordinates as published

The Factbook gives coordinates as text: `49 45 N, 15 30 E`. `geo.entity_point`
keeps both the parsed decimal degrees and the original string, and its `geom` is
a **generated column** derived from latitude and longitude so the point and its
coordinates cannot drift apart. A generated column is right here precisely
because the derivation is immutable and trivial.

The parser refuses rather than guesses. Tested edge cases: both hemispheres,
components written longitude-first, seconds, the poles, and the antimeridian at
both ±180 — which is *not* clamped to 179.999. A coordinate that is nearly right
is worse than one that is absent, because it plots somewhere and looks fine.

## H3

`h3` 4.5.0 is installed and available for **derived** spatial indexes only.

An H3 cell is a hexagon covering an area; a country is not a hexagon. Cells may
index geometry — for bucketing, for joining datasets whose geometries do not
align, for multi-resolution aggregation — but they are never canonical geometry,
and no canonical table has an H3 column.

`h3_postgis` is deliberately not installed: it hard-requires `postgis_raster`.
Core `h3` provides `h3_lat_lng_to_cell` and the cell arithmetic, which is what a
derived index needs; that this suffices was checked before deciding.

Any derived H3 table must document its resolution, why that resolution, the
precision trade-off, and be reproducible by a refresh.

## Rasters

Not in the database. The intended shape is Cloud Optimized GeoTIFF in object
storage with STAC metadata, and PostgreSQL holding metadata and indexes only.
`postgis_raster` stays out until there is a concrete DB-side raster use case.

## Current state

`geo.feature` and `geo.feature_version` are **empty**. No boundary dataset has
been ingested — the Factbook publishes coordinates and area figures, not
geometry. `geo.entity_point` is populated from parsed coordinates.

Ingesting boundaries (Natural Earth, GISCO, OSM extracts) is the obvious next
geospatial step and needs no schema change: it is a new dataset, a new adapter,
and rows in the existing tables.
