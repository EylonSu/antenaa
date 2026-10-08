from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from antenna_tracker.geo import pointing
from antenna_tracker.ui import tiles

tiles.register_scheme()

MAP_HTML = Path(__file__).resolve().parent / "web" / "map.html"
_tile_handler: tiles.TileSchemeHandler | None = None


def _install_tile_handler() -> None:
    global _tile_handler
    if _tile_handler is None:
        profile = QWebEngineProfile.defaultProfile()
        _tile_handler = tiles.TileSchemeHandler(profile)
        profile.installUrlSchemeHandler(tiles.SCHEME, _tile_handler)
SECTOR_RADIUS_M = 3000.0
FULL_ELEVATION_PANS = (70, 110)


class MapBridge(QObject):
    ready = Signal()
    drone_moved = Signal(float, float)

    @Slot()
    def mapReady(self) -> None:
        self.ready.emit()

    @Slot(float, float)
    def droneMoved(self, lat: float, lon: float) -> None:
        self.drone_moved.emit(lat, lon)


def sector_polygon(lat: float, lon: float, ref_az_true: float, pan_lo: int, pan_hi: int,
                   radius_m: float = SECTOR_RADIUS_M) -> list[list[float]]:
    pts = [[lat, lon]]
    for pan in range(pan_lo, pan_hi + 1, 5):
        az, _ = pointing.pan_tilt_to_az_el(pan, pointing.TILT_LEVEL, ref_az_true)
        pts.append(list(pointing.destination(lat, lon, az, radius_m)))
    return pts


class MapView(QWebEngineView):
    """Leaflet map; Python->JS via runJavaScript (queued until the page is ready)."""

    drone_moved = Signal(float, float)

    def __init__(self, parent=None) -> None:
        _install_tile_handler()
        super().__init__(parent)
        self._ready = False
        self._pending: list[str] = []
        self.bridge = MapBridge(self)
        self.bridge.ready.connect(self._on_ready)
        self.bridge.drone_moved.connect(self.drone_moved)
        self._channel = QWebChannel(self.page())
        self._channel.registerObject("bridge", self.bridge)
        self.page().setWebChannel(self._channel)
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.setMinimumSize(300, 250)
        self.load(QUrl.fromLocalFile(str(MAP_HTML)))

    @property
    def is_ready(self) -> bool:
        return self._ready

    def _on_ready(self) -> None:
        self._ready = True
        for js in self._pending:
            self.page().runJavaScript(js)
        self._pending.clear()

    def _call(self, fn: str, *args) -> None:
        js = f"window.api && window.api.{fn}({', '.join(json.dumps(a) for a in args)});"
        if self._ready:
            self.page().runJavaScript(js)
        else:
            self._pending.append(js)

    def set_antenna(self, lat: float, lon: float, zoom: int | None = None) -> None:
        self._call("setAntenna", lat, lon, zoom)

    def set_sector(self, lat: float, lon: float, ref_az_true: float) -> None:
        outer = sector_polygon(lat, lon, ref_az_true, pointing.PAN_MIN, pointing.PAN_MAX)
        inner = sector_polygon(lat, lon, ref_az_true, *FULL_ELEVATION_PANS)
        self._call("setSector", outer, inner)

    def set_drone(self, lat: float, lon: float, draggable: bool = True) -> None:
        self._call("setDrone", lat, lon, draggable)

    def set_recommended(self, line: list[list[float]] | None) -> None:
        self._call("setRecommended", line)

    def set_actual(self, line: list[list[float]] | None) -> None:
        self._call("setActual", line)
