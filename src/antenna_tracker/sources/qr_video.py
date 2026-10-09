from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal, Slot

from antenna_tracker.config import ISRAEL_BOUNDS, QrFields
from antenna_tracker.sources.base import JAM_DISTANCE_M, DronePosition, PositionSource, separation_m
from antenna_tracker.sources.qr_payload import DroneTelemetry, QrParseError, parse_payload

JAM_WINDOW_S = 1.0


class QrVideoSource(PositionSource):
    """Drone position from QR text decoded off the video feed.

    Wire a decoder's ``decoded(str, float)`` signal to :meth:`feed`.
    """

    telemetry = Signal(object)      # DroneTelemetry, every parsed reading
    gps_lost = Signal()
    gps_restored = Signal()
    possible_jamming = Signal()
    rejected = Signal(str)          # reason
    parse_failed = Signal(str)      # reason

    def __init__(
        self,
        video_device_id: str | None = None,
        parent: QObject | None = None,
        *,
        takeoff_alt_amsl: float = 0.0,
        fields: QrFields | None = None,
        max_speed_mps: float = 60.0,
        bounds: tuple[float, float, float, float] = ISRAEL_BOUNDS,
        gps_debounce: int = 3,
    ) -> None:
        super().__init__(parent)
        self.video_device_id = video_device_id
        self.takeoff_alt_amsl = takeoff_alt_amsl
        self.fields = fields or QrFields()
        self.max_speed_mps = max_speed_mps
        self.bounds = bounds
        self.gps_debounce = max(1, gps_debounce)
        self.reset()

    @classmethod
    def from_config(cls, config, parent: QObject | None = None) -> QrVideoSource:
        return cls(
            config.video_device_id, parent,
            takeoff_alt_amsl=config.effective_takeoff_alt_amsl,
            fields=config.qr_fields,
            max_speed_mps=config.qr_max_speed_mps,
            bounds=tuple(config.qr_bounds),
            gps_debounce=config.qr_gps_debounce,
        )

    def reset(self) -> None:
        self._latest = None
        self.gps_ok = True
        self._no_gps_run = 0
        self._gps_run = 0
        self.last_raw: str | None = None
        self.last_telemetry: DroneTelemetry | None = None
        self.parse_errors = 0
        self.rejected_count = 0
        self.rejected_by_reason: dict[str, int] = {}

    def set_takeoff_alt(self, alt_amsl: float) -> None:
        self.takeoff_alt_amsl = alt_amsl

    def start(self) -> None:
        pass

    @Slot(str, float)
    def feed(self, text: str, t: float | None = None) -> None:
        t = time.time() if t is None else t
        self.last_raw = text
        try:
            tel = parse_payload(text, self.fields)
        except QrParseError as e:
            self.parse_errors += 1
            self.parse_failed.emit(str(e))
            return
        self.last_telemetry = tel
        self.telemetry.emit(tel)

        if not tel.has_gps:
            self._gps_run = 0
            self._no_gps_run += 1
            if self.gps_ok and self._no_gps_run >= self.gps_debounce:
                self.gps_ok = False
                self.gps_lost.emit()
            return

        reason = self._reject_reason(tel, t)
        if reason is not None:
            self.rejected_count += 1
            self.rejected_by_reason[reason] = self.rejected_by_reason.get(reason, 0) + 1
            self.rejected.emit(reason)
            if reason == "possible jamming":
                self.possible_jamming.emit()
            return

        self._no_gps_run = 0
        self._gps_run += 1
        if not self.gps_ok and self._gps_run >= self.gps_debounce:
            self.gps_ok = True
            self.gps_restored.emit()
        self.publish(DronePosition(tel.lat, tel.lon, self.takeoff_alt_amsl + tel.rel_alt, t))

    def _reject_reason(self, tel: DroneTelemetry, t: float) -> str | None:
        lat_min, lat_max, lon_min, lon_max = self.bounds
        if not (lat_min <= tel.lat <= lat_max and lon_min <= tel.lon <= lon_max):
            return "outside area"
        prev = self._latest
        if prev is not None:
            dt = t - prev.t
            alt = self.takeoff_alt_amsl + tel.rel_alt
            dist = _distance(prev, tel.lat, tel.lon, alt)
            if dist >= JAM_DISTANCE_M and dt <= JAM_WINDOW_S:
                return "possible jamming"
            if dt <= 0:
                return "too fast" if dist > 1.0 else None
            if dist / dt > self.max_speed_mps:
                return "too fast"
        return None


def _distance(prev: DronePosition, lat: float, lon: float, alt: float) -> float:
    return separation_m(prev.lat, prev.lon, prev.alt_amsl, lat, lon, alt)
