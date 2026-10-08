from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from pyproj import Geod

PAN_MIN, PAN_MAX = 5, 175
TILT_MIN, TILT_MAX = 60, 160
PAN_CENTER = 90
TILT_LEVEL = 90

_geod = Geod(ellps="WGS84")


class PointingStatus(str, Enum):
    IN_RANGE = "in_range"
    AZIMUTH_OUT_OF_COVERAGE = "azimuth_out_of_coverage"
    ELEVATION_LIMITED = "elevation_limited"


@dataclass(frozen=True)
class Solution:
    azimuth: float
    elevation: float
    distance_m: float
    pan_ideal: float
    tilt_ideal: float
    pan: int
    tilt: int
    status: PointingStatus


def wrap180(deg: float) -> float:
    return (deg + 180.0) % 360.0 - 180.0


def tilt_min(pan: float) -> float:
    return max(TILT_MIN, pan - 90, 90 - pan)


def tilt_max(pan: float) -> float:
    return min(TILT_MAX, pan + 90, 270 - pan)


def is_reachable(pan: int, tilt: int) -> bool:
    """Exactly mirrors the firmware's MOVE acceptance check."""
    if not (PAN_MIN <= pan <= PAN_MAX and TILT_MIN <= tilt <= TILT_MAX):
        return False
    raw_left = 270 - pan - tilt
    raw_right = tilt - pan + 90
    return 0 <= raw_left <= 180 and 0 <= raw_right <= 180


def az_el_dist(
    ant_lat: float, ant_lon: float, ant_alt: float,
    tgt_lat: float, tgt_lon: float, tgt_alt: float,
) -> tuple[float, float, float]:
    az, _, dist = _geod.inv(ant_lon, ant_lat, tgt_lon, tgt_lat)
    el = math.degrees(math.atan2(tgt_alt - ant_alt, dist))
    return az % 360.0, el, dist


def az_el_to_pan_tilt(azimuth: float, elevation: float, ref_az_true: float) -> tuple[float, float]:
    return PAN_CENTER + wrap180(azimuth - ref_az_true), TILT_LEVEL + elevation


def pan_tilt_to_az_el(pan: float, tilt: float, ref_az_true: float) -> tuple[float, float]:
    return (ref_az_true + pan - PAN_CENTER) % 360.0, tilt - TILT_LEVEL


def clamp_pan_tilt(pan: float, tilt: float) -> tuple[int, int, PointingStatus]:
    """Azimuth has priority: clamp pan first, then tilt into the linked range for that pan."""
    status = PointingStatus.IN_RANGE
    p = round(pan)
    if p < PAN_MIN or p > PAN_MAX:
        status = PointingStatus.AZIMUTH_OUT_OF_COVERAGE
        p = min(max(p, PAN_MIN), PAN_MAX)
    lo, hi = math.ceil(tilt_min(p)), math.floor(tilt_max(p))
    t = round(tilt)
    if t < lo or t > hi:
        if status is PointingStatus.IN_RANGE:
            status = PointingStatus.ELEVATION_LIMITED
        t = min(max(t, lo), hi)
    return p, t, status


def solve(
    ant_lat: float, ant_lon: float, ant_alt: float,
    tgt_lat: float, tgt_lon: float, tgt_alt: float,
    ref_az_true: float,
) -> Solution:
    az, el, dist = az_el_dist(ant_lat, ant_lon, ant_alt, tgt_lat, tgt_lon, tgt_alt)
    pan_i, tilt_i = az_el_to_pan_tilt(az, el, ref_az_true)
    pan, tilt, status = clamp_pan_tilt(pan_i, tilt_i)
    return Solution(az, el, dist, pan_i, tilt_i, pan, tilt, status)


def destination(lat: float, lon: float, azimuth: float, distance_m: float) -> tuple[float, float]:
    lon2, lat2, _ = _geod.fwd(lon, lat, azimuth, distance_m)
    return lat2, lon2


def reachable_envelope(step: int = 5) -> list[tuple[int, float, float]]:
    """(pan, min_elevation, max_elevation) samples for drawing the reachable sector."""
    pans = list(range(PAN_MIN, PAN_MAX + 1, step))
    if pans[-1] != PAN_MAX:
        pans.append(PAN_MAX)
    return [(p, tilt_min(p) - TILT_LEVEL, tilt_max(p) - TILT_LEVEL) for p in pans]
