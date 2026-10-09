from __future__ import annotations

import math
from dataclasses import dataclass

from antenna_tracker.config import QrFields


class QrParseError(ValueError):
    pass


@dataclass(frozen=True)
class DroneTelemetry:
    serial: str
    lat: float
    lon: float
    rel_alt: float
    heading: float | None
    home_dist: float | None
    reported_antenna_dist: float | None
    has_gps: bool  # False when lat == 0.0 and lon == 0.0
    raw: str


def _number(parts: list[str], idx: int) -> float:
    try:
        v = float(parts[idx])
    except ValueError:
        raise QrParseError(f"field {idx} is not a number: {parts[idx]!r}") from None
    if not math.isfinite(v):
        raise QrParseError(f"field {idx} is not a finite number: {parts[idx]!r}")
    return v


def _optional(parts: list[str], idx: int | None) -> float | None:
    if idx is None or idx >= len(parts):
        return None
    try:
        v = float(parts[idx])
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def parse_payload(text: str, fields: QrFields | None = None) -> DroneTelemetry:
    fields = fields or QrFields()
    parts = [p.strip() for p in text.strip().split("|")]
    required = (fields.serial, fields.lat, fields.lon, fields.rel_alt)
    if len(parts) <= max(required):
        raise QrParseError(f"too few fields: got {len(parts)}, need at least {max(required) + 1}")
    lat = _number(parts, fields.lat)
    lon = _number(parts, fields.lon)
    rel_alt = _number(parts, fields.rel_alt)
    has_gps = not (lat == 0.0 and lon == 0.0)
    if has_gps:
        if not -90.0 <= lat <= 90.0:
            raise QrParseError(f"field {fields.lat} latitude out of range: {lat}")
        if not -180.0 <= lon <= 180.0:
            raise QrParseError(f"field {fields.lon} longitude out of range: {lon}")
    heading = _optional(parts, fields.heading)
    return DroneTelemetry(
        serial=parts[fields.serial],
        lat=lat,
        lon=lon,
        rel_alt=rel_alt,
        heading=None if heading is None else heading % 360.0,
        home_dist=_optional(parts, fields.home_dist),
        reported_antenna_dist=_optional(parts, fields.antenna_dist),
        has_gps=has_gps,
        raw=text,
    )
