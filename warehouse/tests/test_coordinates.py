"""Unit tests for DMS coordinate parsing.

The edge cases here are the ones that produce a plausible-looking point in the
wrong place: hemispheres, the antimeridian, the poles, and components written in
the other order. A coordinate that is nearly right is worse than one that is
absent, because it plots somewhere and looks fine.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from atlasdata.parsers.coordinates import parse_coordinate

failures: list[str] = []
checks = 0


def check(label: str, actual, expected) -> None:
    global checks
    checks += 1
    ok = (abs(actual - expected) < 1e-9) if isinstance(expected, float) and \
         isinstance(actual, float) else actual == expected
    if not ok:
        failures.append(f"{label}\n      expected {expected!r}\n      got      {actual!r}")


# ── the ordinary case ────────────────────────────────────────────────────────

c = parse_coordinate("49 45 N, 15 30 E")
check("prague-ish lat", c.latitude, 49.75)
check("prague-ish lon", c.longitude, 15.5)
check("status", c.status, "parsed_exact")
check("raw preserved", c.raw, "49 45 N, 15 30 E")

# ── hemispheres ──────────────────────────────────────────────────────────────

c = parse_coordinate("33 55 S, 18 25 E")
check("south is negative", round(c.latitude, 6), -33.916667)
check("east is positive", round(c.longitude, 6), 18.416667)

c = parse_coordinate("38 53 N, 77 02 W")
check("west is negative", round(c.longitude, 6), -77.033333)

c = parse_coordinate("34 36 S, 58 22 W")
check("both negative lat", round(c.latitude, 6), -34.6)
check("both negative lon", round(c.longitude, 6), -58.366667)

# ── seconds, and order reversal ──────────────────────────────────────────────

c = parse_coordinate("12 30 45 N, 69 58 30 W")
check("seconds lat", round(c.latitude, 6), 12.5125)
check("seconds lon", round(c.longitude, 6), -69.975)

c = parse_coordinate("15 30 E, 49 45 N")
check("reversed order lat", c.latitude, 49.75)
check("reversed order lon", c.longitude, 15.5)
check("reversed order noted", "longitude-first" in c.note, True)

# ── poles and the antimeridian ───────────────────────────────────────────────

c = parse_coordinate("90 00 S, 0 00 E")
check("south pole", c.latitude, -90.0)
check("south pole ok", c.ok, True)

c = parse_coordinate("0 00 N, 180 00 E")
check("antimeridian east", c.longitude, 180.0)
check("antimeridian not clamped", c.ok, True)

c = parse_coordinate("0 00 N, 180 00 W")
check("antimeridian west", c.longitude, -180.0)

# ── refusals ─────────────────────────────────────────────────────────────────

c = parse_coordinate("95 00 N, 15 30 E")
check("latitude beyond pole rejected", c.ok, False)
check("out of range code", c.failure_code, "out_of_range")

c = parse_coordinate("mountainous interior")
check("prose rejected", c.ok, False)
check("prose code", c.failure_code, "no_coordinate_found")

c = parse_coordinate("")
check("empty rejected", c.ok, False)
check("empty code", c.failure_code, "empty")

c = parse_coordinate("49 45 N, 15 30 N")
check("two latitudes rejected", c.ok, False)
check("ambiguous code", c.failure_code, "ambiguous_hemispheres")

# A refusal always keeps the original text, so a better parser can retry it.
for bad in ("95 00 N, 15 30 E", "mountainous interior", "49 45 N, 15 30 N"):
    check(f"raw kept for {bad[:18]!r}", parse_coordinate(bad).raw, bad)

if failures:
    print(f"test_coordinates: {len(failures)} of {checks} checks FAILED", file=sys.stderr)
    for f in failures:
        print(f"  ✗ {f}", file=sys.stderr)
    raise SystemExit(1)
print(f"test_coordinates: {checks} checks passed")
