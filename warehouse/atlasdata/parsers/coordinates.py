"""Degrees-minutes-seconds coordinates, as the corpus writes them.

The published form is "49 45 N, 15 30 E" — degrees and minutes, hemisphere
letter after the number, no symbols. Seconds appear occasionally in older
editions. Conversion is deterministic, and the raw string is kept regardless,
because the edge cases here are real: the antimeridian, the poles, and a
hemisphere letter that occasionally goes missing. §77.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# "49 45 N" / "49 45 00 N" / "49.75 N" / "S 12 30"
_DMS = r"(\d{1,3})(?:\s+(\d{1,2}))?(?:\s+(\d{1,2}))?\s*([NSEW])"
PAIR_RE = re.compile(rf"{_DMS}\s*,?\s*{_DMS}", re.I)
DECIMAL_PAIR_RE = re.compile(
    r"(-?\d{1,3}(?:\.\d+)?)\s*([NS])\s*,?\s*(-?\d{1,3}(?:\.\d+)?)\s*([EW])", re.I)


@dataclass
class ParsedCoordinate:
    raw: str
    latitude: float | None = None
    longitude: float | None = None
    status: str = "unparsed"          # parsed_exact | parsed_partial | unparsed
    failure_code: str | None = None
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.latitude is not None and self.longitude is not None


def _to_degrees(d: str, m: str | None, s: str | None, hemisphere: str) -> float | None:
    deg = float(d) + (float(m or 0) / 60.0) + (float(s or 0) / 3600.0)
    h = hemisphere.upper()
    if h in ("S", "W"):
        deg = -deg
    if h in ("N", "S") and not (-90.0 <= deg <= 90.0):
        return None
    if h in ("E", "W") and not (-180.0 <= deg <= 180.0):
        return None
    return deg


def parse_coordinate(raw: str) -> ParsedCoordinate:
    """Parse a published coordinate pair into decimal degrees.

    Returns status='unparsed' with a failure code rather than a guess when the
    string does not contain an unambiguous pair. A coordinate that is nearly
    right is worse than one that is absent, because it will plot somewhere and
    look plausible.
    """
    original = raw if isinstance(raw, str) else str(raw)
    text = re.sub(r"\s+", " ", original).strip()
    out = ParsedCoordinate(raw=original)

    if not text:
        out.failure_code = "empty"
        return out

    m = PAIR_RE.search(text)
    if m:
        first = _to_degrees(m.group(1), m.group(2), m.group(3), m.group(4))
        second = _to_degrees(m.group(5), m.group(6), m.group(7), m.group(8))
        h1, h2 = m.group(4).upper(), m.group(8).upper()

        # Latitude is whichever component carries N/S, regardless of the order
        # the source wrote them in.
        if h1 in "NS" and h2 in "EW":
            lat, lon = first, second
        elif h1 in "EW" and h2 in "NS":
            lat, lon = second, first
            out.note = "components given longitude-first"
        else:
            out.failure_code = "ambiguous_hemispheres"
            out.note = f"hemispheres {h1} and {h2} do not form a lat/long pair"
            return out

        if lat is None or lon is None:
            out.failure_code = "out_of_range"
            out.note = "component outside the valid range for its hemisphere"
            return out

        out.latitude, out.longitude = lat, lon
        out.status = "parsed_exact"
        return out

    d = DECIMAL_PAIR_RE.search(text)
    if d:
        lat = float(d.group(1)) * (-1 if d.group(2).upper() == "S" else 1)
        lon = float(d.group(3)) * (-1 if d.group(4).upper() == "W" else 1)
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            out.latitude, out.longitude = lat, lon
            out.status = "parsed_exact"
            out.note = "decimal degrees"
            return out
        out.failure_code = "out_of_range"
        return out

    out.failure_code = "no_coordinate_found"
    return out
