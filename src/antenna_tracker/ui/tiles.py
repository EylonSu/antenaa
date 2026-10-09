"""Serve street and satellite tiles to the map page through Qt's network stack with a disk cache."""
from __future__ import annotations

import re
from pathlib import Path

from platformdirs import user_cache_dir
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkReply, QNetworkRequest
from PySide6.QtWebEngineCore import QWebEngineUrlRequestJob, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler

from antenna_tracker.config import APP_NAME

SCHEME = b"tiles"
OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
# WMTS row (y) comes before column (x).
SATELLITE_TILE_URL = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg"
USER_AGENT = b"AntennaTracker/0.1 (desktop app)"
CACHE_BYTES = 500 * 1024 * 1024
_TILE_RE = re.compile(
    r"^/?(?P<layer>osm|satellite)/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+)\.(?P<ext>png|jpg)$")


def parse_tile_path(path: str) -> tuple[str, bytes] | None:
    """Map a tiles: path to (upstream URL, content type), or None if it is not a tile we serve."""
    m = _TILE_RE.match(path)
    if m is None:
        return None
    layer, z, x, y, ext = m.group("layer", "z", "x", "y", "ext")
    if layer == "osm" and ext == "png":
        return OSM_TILE_URL.format(z=z, x=x, y=y), b"image/png"
    if layer == "satellite" and ext == "jpg":
        return SATELLITE_TILE_URL.format(z=z, y=y, x=x), b"image/jpeg"
    return None


def register_scheme() -> None:
    """Must run before the QApplication is created."""
    if QWebEngineUrlScheme.schemeByName(QByteArray(SCHEME)).name() == QByteArray(SCHEME):
        return
    s = QWebEngineUrlScheme(SCHEME)
    s.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    s.setFlags(QWebEngineUrlScheme.Flag.SecureScheme | QWebEngineUrlScheme.Flag.LocalAccessAllowed
               | QWebEngineUrlScheme.Flag.CorsEnabled)
    QWebEngineUrlScheme.registerScheme(s)


class TileSchemeHandler(QWebEngineUrlSchemeHandler):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._nam = QNetworkAccessManager(self)
        cache = QNetworkDiskCache(self)
        cache.setCacheDirectory(str(Path(user_cache_dir(APP_NAME, appauthor=False)) / "tiles"))
        cache.setMaximumCacheSize(CACHE_BYTES)
        self._nam.setCache(cache)
        self._jobs: dict[QNetworkReply, tuple[QWebEngineUrlRequestJob, bytes]] = {}

    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:
        parsed = parse_tile_path(job.requestUrl().path())
        if parsed is None:
            job.fail(QWebEngineUrlRequestJob.Error.UrlInvalid)
            return
        url, mime = parsed
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", USER_AGENT)
        req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                         QNetworkRequest.CacheLoadControl.PreferCache)
        reply = self._nam.get(req)
        self._jobs[reply] = (job, mime)
        job.destroyed.connect(lambda *_: self._jobs.pop(reply, None) and reply.abort())
        reply.finished.connect(lambda: self._finish(reply))

    def _finish(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        found = self._jobs.pop(reply, None)
        if found is None:
            return
        job, mime = found
        if reply.error() != QNetworkReply.NetworkError.NoError:
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return
        buf = QBuffer(job)
        buf.setData(reply.readAll())
        buf.open(QIODevice.OpenModeFlag.ReadOnly)
        job.reply(mime, buf)
