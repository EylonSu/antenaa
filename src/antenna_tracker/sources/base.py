from __future__ import annotations

import math
import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

JAM_DISTANCE_M = 5000.0


@dataclass(frozen=True)
class DronePosition:
    lat: float
    lon: float
    alt_amsl: float
    t: float

    def age(self, now: float | None = None) -> float:
        return (time.time() if now is None else now) - self.t


def separation_m(lat1: float, lon1: float, alt1: float, lat2: float, lon2: float, alt2: float) -> float:
    """3D distance in metres between two lat/lon/altitude points."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    ground = 2 * r * math.asin(math.sqrt(a))
    return math.hypot(ground, alt2 - alt1)


class PositionSource(QObject):
    """Base class for drone position providers. Subclasses call publish()."""

    position_changed = Signal(object)  # DronePosition

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._latest: DronePosition | None = None

    @property
    def name(self) -> str:
        return type(self).__name__

    def latest(self) -> DronePosition | None:
        return self._latest

    def publish(self, pos: DronePosition) -> None:
        self._latest = pos
        self.position_changed.emit(pos)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
