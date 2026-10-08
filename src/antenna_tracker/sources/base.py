from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class DronePosition:
    lat: float
    lon: float
    alt_amsl: float
    t: float

    def age(self, now: float | None = None) -> float:
        return (time.time() if now is None else now) - self.t


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
