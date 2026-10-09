from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from PySide6.QtCore import QObject, QTimer, Signal

from antenna_tracker.geo import pointing
from antenna_tracker.geo.pointing import Solution
from antenna_tracker.sources.base import PositionSource


class Mode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class TrackStatus(str, Enum):
    TRACKING = "tracking"
    MANUAL = "manual"
    OUT_OF_RANGE = "out_of_range"
    NO_POSITION = "no_position"
    STALE = "stale"
    NO_POWER = "no_power"
    NO_GPS = "no_gps"


@dataclass(frozen=True)
class AntennaSite:
    lat: float
    lon: float
    alt_amsl: float
    ref_az_true: float


class TurretLike(Protocol):
    @property
    def is_connected(self) -> bool: ...
    @property
    def last_position(self) -> tuple[int, int] | None: ...
    def move(self, pan: int, tilt: int) -> None: ...


class TrackingController(QObject):
    recommendation = Signal(object)  # Solution | None
    status_changed = Signal(str)     # TrackStatus value
    mode_changed = Signal(str)       # Mode value
    command_sent = Signal(int, int)

    def __init__(
        self,
        turret: TurretLike,
        site: AntennaSite | None = None,
        source: PositionSource | None = None,
        parent: QObject | None = None,
        interval_s: float = 1.0,
        stale_timeout_s: float = 5.0,
        deadband_deg: int = 1,
    ) -> None:
        super().__init__(parent)
        self.turret = turret
        self.site = site
        self.source = source
        self.stale_timeout_s = stale_timeout_s
        self.deadband_deg = deadband_deg
        self._mode = Mode.AUTO
        self._status: TrackStatus | None = None
        self._last_cmd: tuple[int, int] | None = None
        self._last_solution: Solution | None = None
        self._drone_gps_ok = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)
        self.set_interval(interval_s)

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def status(self) -> TrackStatus | None:
        return self._status

    @property
    def last_solution(self) -> Solution | None:
        return self._last_solution

    def set_interval(self, seconds: float) -> None:
        self._timer.setInterval(max(50, int(seconds * 1000)))

    def set_site(self, site: AntennaSite) -> None:
        self.site = site
        self._last_cmd = None

    def set_source(self, source: PositionSource | None) -> None:
        self.source = source

    def start(self) -> None:
        self._timer.start()
        self.tick()

    def stop(self) -> None:
        self._timer.stop()

    def set_mode(self, mode: Mode) -> None:
        if mode is self._mode:
            return
        self._mode = mode
        self._last_cmd = None
        self.mode_changed.emit(mode.value)
        self.tick()

    @property
    def drone_gps_ok(self) -> bool:
        return self._drone_gps_ok

    def set_drone_gps(self, ok: bool, switch_to_manual: bool = True) -> None:
        """Lost GPS shows NO_GPS (and goes MANUAL); restored never returns to AUTO by itself."""
        if ok == self._drone_gps_ok:
            return
        self._drone_gps_ok = ok
        if not ok and switch_to_manual and self._mode is not Mode.MANUAL:
            self.set_mode(Mode.MANUAL)
        else:
            self.tick()

    def on_gps_lost(self) -> None:
        self.set_drone_gps(False)

    def on_gps_restored(self) -> None:
        self.set_drone_gps(True)

    def reset_last_command(self) -> None:
        """Call after power restore or INIT so the next AUTO tick resends."""
        self._last_cmd = None

    def compute(self, now: float | None = None) -> Solution | None:
        if self.site is None or self.source is None:
            return None
        pos = self.source.latest()
        if pos is None or pos.age(now) > self.stale_timeout_s:
            return None
        s = self.site
        return pointing.solve(s.lat, s.lon, s.alt_amsl, pos.lat, pos.lon, pos.alt_amsl, s.ref_az_true)

    def _position_state(self, now: float) -> TrackStatus | None:
        pos = self.source.latest() if self.source else None
        if pos is None:
            return TrackStatus.NO_POSITION
        if pos.age(now) > self.stale_timeout_s:
            return TrackStatus.STALE
        return None

    def tick(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        sol = self.compute(now)
        self._last_solution = sol
        self.recommendation.emit(sol)

        if not self.turret.is_connected:
            self._set_status(TrackStatus.NO_POWER)
            return
        if not self._drone_gps_ok:
            self._set_status(TrackStatus.NO_GPS)
            return
        if self._mode is Mode.MANUAL:
            self._set_status(TrackStatus.MANUAL)
            return
        missing = self._position_state(now)
        if missing is not None or sol is None:
            self._set_status(missing or TrackStatus.NO_POSITION)
            return

        in_range = sol.status is pointing.PointingStatus.IN_RANGE
        self._set_status(TrackStatus.TRACKING if in_range else TrackStatus.OUT_OF_RANGE)
        if self._needs_move(sol.pan, sol.tilt):
            self._command(sol.pan, sol.tilt)

    def _needs_move(self, pan: int, tilt: int) -> bool:
        ref = self._last_cmd or self.turret.last_position
        if ref is None:
            return True
        return abs(pan - ref[0]) >= self.deadband_deg or abs(tilt - ref[1]) >= self.deadband_deg

    def _command(self, pan: int, tilt: int) -> None:
        self._last_cmd = (pan, tilt)
        self.turret.move(pan, tilt)
        self.command_sent.emit(pan, tilt)

    def point_to_recommended(self) -> bool:
        sol = self.compute()
        if sol is None or not self.turret.is_connected:
            return False
        self._command(sol.pan, sol.tilt)
        return True

    def manual_target(self, d_pan: int, d_tilt: int) -> tuple[int, int] | None:
        """Target for a manual nudge, or None if unreachable (grey out the button)."""
        cur = self._last_cmd or self.turret.last_position
        if cur is None:
            return None
        pan, tilt = cur[0] + d_pan, cur[1] + d_tilt
        return (pan, tilt) if pointing.is_reachable(pan, tilt) else None

    def nudge(self, d_pan: int, d_tilt: int) -> bool:
        target = self.manual_target(d_pan, d_tilt)
        if target is None or not self.turret.is_connected:
            return False
        if self._mode is not Mode.MANUAL:
            self.set_mode(Mode.MANUAL)
        self._command(*target)
        return True

    def _set_status(self, status: TrackStatus) -> None:
        if status is not self._status:
            self._status = status
            self.status_changed.emit(status.value)
