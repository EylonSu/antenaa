from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer

from antenna_tracker.geo.pointing import destination
from antenna_tracker.sources.base import DronePosition, PositionSource


class SimulatedSource(PositionSource):
    """Position set by the UI (draggable marker), optionally flying a circle around a center."""

    def __init__(self, parent: QObject | None = None, tick_s: float = 0.2) -> None:
        super().__init__(parent)
        self._lat = 0.0
        self._lon = 0.0
        self._alt = 0.0
        self._has_pos = False
        self._center: tuple[float, float] | None = None
        self._radius_m = 0.0
        self._period_s = 60.0
        self._bearing = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(int(tick_s * 1000))
        self._timer.timeout.connect(self._tick)
        self._tick_s = tick_s

    @property
    def circling(self) -> bool:
        return self._timer.isActive()

    def set_position(self, lat: float, lon: float, alt_amsl: float | None = None) -> None:
        self._lat, self._lon = lat, lon
        if alt_amsl is not None:
            self._alt = alt_amsl
        self._has_pos = True
        self._emit()

    def set_altitude(self, alt_amsl: float) -> None:
        self._alt = alt_amsl
        if self._has_pos:
            self._emit()

    def start_circle(self, center_lat: float, center_lon: float, radius_m: float, period_s: float = 60.0) -> None:
        self._center = (center_lat, center_lon)
        self._radius_m = radius_m
        self._period_s = max(period_s, 1.0)
        self._bearing = 0.0
        self._tick()
        self._timer.start()

    def stop_circle(self) -> None:
        self._timer.stop()

    def stop(self) -> None:
        self.stop_circle()

    def step_circle(self, dt_s: float) -> None:
        self._bearing = (self._bearing + 360.0 * dt_s / self._period_s) % 360.0
        self._place_on_circle()

    def _tick(self) -> None:
        if self._center is None:
            return
        if self._timer.isActive():
            self.step_circle(self._tick_s)
        else:
            self._place_on_circle()

    def _place_on_circle(self) -> None:
        assert self._center is not None
        self._lat, self._lon = destination(*self._center, self._bearing, self._radius_m)
        self._has_pos = True
        self._emit()

    def _emit(self) -> None:
        self.publish(DronePosition(self._lat, self._lon, self._alt, time.time()))
