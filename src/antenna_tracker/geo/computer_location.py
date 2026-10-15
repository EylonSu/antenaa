"""One-shot position of the computer running the app."""

from __future__ import annotations

import math
import sys

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtPositioning import QGeoCoordinate, QGeoPositionInfo, QGeoPositionInfoSource
from PySide6.QtWidgets import QApplication

_ALT_MIN = -500.0
_ALT_MAX = 4000.0


def uses_macos_helper() -> bool:
    """Source checkouts on macOS cannot prompt for location from inside Python.

    The packaged app carries the usage string in its Info.plist, so Qt can ask.
    """
    return sys.platform == "darwin" and not getattr(sys, "frozen", False)


def position_fix(info: QGeoPositionInfo) -> tuple[float, float, float] | None:
    """Latitude, longitude, and altitude in metres. Altitude is NaN when unknown."""
    if not info.isValid():
        return None
    coord = info.coordinate()
    if not coord.isValid():
        return None
    alt = coord.altitude()
    if (
        coord.type() != QGeoCoordinate.CoordinateType.Coordinate3D
        or not math.isfinite(alt)
        or not _ALT_MIN <= alt <= _ALT_MAX
    ):
        alt = math.nan
    return coord.latitude(), coord.longitude(), alt


class ComputerLocation(QObject):
    """Ask the operating system where this computer is.

    `found` is (latitude, longitude, altitude metres). Altitude is NaN when the
    fix has no usable height. `unavailable` means the lookup will not produce one.
    """

    found = Signal(float, float, float)
    unavailable = Signal()

    _GIVE_UP_MS = 30_000

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source: QGeoPositionInfoSource | None = None
        self._helper = None
        self._got_fix = False
        self._busy = False
        self._stopped = False
        self._give_up = QTimer(self)
        self._give_up.setSingleShot(True)
        self._give_up.timeout.connect(self._on_timeout)
        if parent is not None:
            parent.destroyed.connect(self.stop)

    def request(self) -> None:
        if self._busy:
            return
        self._stopped = False
        self._busy = True
        if uses_macos_helper():
            self._start_helper()
            return
        self._start_qt()

    def stop(self) -> None:
        self._stopped = True
        self._busy = False
        self._give_up.stop()
        if self._source is not None:
            self._source.stopUpdates()
        helper = self._helper
        if helper is not None and helper.isRunning():
            helper.stop()
            helper.wait(20_000)

    def _start_helper(self) -> None:
        from antenna_tracker.geo.macos_helper import MacosLocationThread

        if self._helper is None:
            self._helper = MacosLocationThread(self)
            self._helper.found.connect(self._deliver)
            self._helper.unavailable.connect(self._fail)
        if not self._helper.isRunning():
            self._helper.start()

    def _start_qt(self) -> None:
        app = QApplication.instance()
        permission = self._permission()
        if app is None:
            self._start_updates()
            return
        status = app.checkPermission(permission)
        if status == Qt.PermissionStatus.Granted:
            self._start_updates()
        elif status == Qt.PermissionStatus.Undetermined:
            app.requestPermission(permission, self, self._after_permission)
        else:
            QTimer.singleShot(0, self._fail)

    def _after_permission(self, permission) -> None:
        if self._stopped:
            return
        app = QApplication.instance()
        if app is None or app.checkPermission(permission) != Qt.PermissionStatus.Granted:
            self._fail()
            return
        self._start_updates()

    def _start_updates(self) -> None:
        if self._stopped:
            return
        if self._source is None:
            self._source = QGeoPositionInfoSource.createDefaultSource(self)
            if self._source is None:
                self._fail()
                return
            self._source.setPreferredPositioningMethods(
                QGeoPositionInfoSource.PositioningMethod.AllPositioningMethods
            )
            self._source.positionUpdated.connect(self._on_position)
            self._source.errorOccurred.connect(self._on_error)
        self._give_up.start(self._GIVE_UP_MS)
        cached = self._source.lastKnownPosition()
        if cached.isValid():
            fix = position_fix(cached)
            if fix is not None:
                self._deliver(*fix)
        if not self._stopped:
            self._source.startUpdates()

    def _on_position(self, info: QGeoPositionInfo) -> None:
        fix = position_fix(info)
        if fix is None:
            return
        self._deliver(*fix)
        self._give_up.stop()
        if self._source is not None:
            self._source.stopUpdates()

    def _on_timeout(self) -> None:
        if self._stopped or self._got_fix:
            return
        self.unavailable.emit()

    def _on_error(self, error: QGeoPositionInfoSource.Error) -> None:
        if error in (
            QGeoPositionInfoSource.Error.NoError,
            QGeoPositionInfoSource.Error.UpdateTimeoutError,
        ):
            return
        if not self._got_fix:
            self._fail()
        self._give_up.stop()
        if self._source is not None:
            self._source.stopUpdates()

    def _deliver(self, lat: float, lon: float, alt: float) -> None:
        if self._stopped:
            return
        self._got_fix = True
        self._busy = False
        self.found.emit(lat, lon, alt)

    def _fail(self) -> None:
        if self._stopped:
            return
        self._busy = False
        self.unavailable.emit()

    @staticmethod
    def _permission():
        from PySide6.QtCore import QLocationPermission

        permission = QLocationPermission()
        permission.setAccuracy(QLocationPermission.Accuracy.Precise)
        permission.setAvailability(QLocationPermission.Availability.WhenInUse)
        return permission
