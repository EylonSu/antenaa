from __future__ import annotations

import re
from dataclasses import dataclass

from pyproj import Transformer

UTM_EPSG = 32636
ISRAEL_BBOX = (29.3, 33.5, 34.0, 36.0)  # lat_min, lat_max, lon_min, lon_max

_transformer = Transformer.from_crs(f"EPSG:{UTM_EPSG}", "EPSG:4326", always_xy=True)
_inverse = Transformer.from_crs("EPSG:4326", f"EPSG:{UTM_EPSG}", always_xy=True)


class UtmError(ValueError):
    pass


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


def _six_digits(value: str, name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise UtmError(f"Please enter the {name} (6 digits).")
    if not cleaned.isdigit():
        raise UtmError(f"The {name} must contain digits only.")
    if len(cleaned) != 6:
        raise UtmError(f"The {name} must be exactly 6 digits (you entered {len(cleaned)}).")
    return cleaned


def parse_utm(easting: str, northing: str) -> tuple[float, float]:
    """Return full (easting, northing) metres in UTM 36N from the two 6-digit halves."""
    e = _six_digits(easting, "easting")
    n = _six_digits(northing, "northing")
    return float(e), float("3" + n)


def parse_utm12(text: str) -> tuple[float, float]:
    digits = re.sub(r"[\s,]", "", text)
    if not digits.isdigit() or len(digits) != 12:
        raise UtmError("Enter 12 digits: 6 for easting, then 6 for northing.")
    return parse_utm(digits[:6], digits[6:])


def utm_to_latlon(easting_m: float, northing_m: float) -> LatLon:
    lon, lat = _transformer.transform(easting_m, northing_m)
    return LatLon(lat=lat, lon=lon)


def latlon_to_utm(lat: float, lon: float) -> tuple[float, float]:
    e, n = _inverse.transform(lon, lat)
    return e, n


def in_israel(p: LatLon) -> bool:
    lat_min, lat_max, lon_min, lon_max = ISRAEL_BBOX
    return lat_min <= p.lat <= lat_max and lon_min <= p.lon <= lon_max


def utm_input_to_latlon(easting: str, northing: str) -> LatLon:
    """Parse and validate user UTM input; raise UtmError with a friendly message."""
    e, n = parse_utm(easting, northing)
    p = utm_to_latlon(e, n)
    if not in_israel(p):
        raise UtmError(
            f"That position ({p.lat:.4f}, {p.lon:.4f}) is outside Israel. "
            "Check that the easting and northing are not swapped or mistyped."
        )
    return p
