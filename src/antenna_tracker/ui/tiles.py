"""Serve OSM tiles to the map page as tiles:/z/x/y.png through Qt's network stack with a disk cache."""
from __future__ import annotations

import re
from pathlib import Path

from platformdirs import user_cache_dir
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkReply, QNetworkRequest
from PySide6.QtWebEngineCore import QWebEngineUrlRequestJob, QWebEngineUrlScheme, QWebEngineUrlSchemeHandler

from antenna_tracker.config import APP_NAME

SCHEME = b"tiles"
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT = b"AntennaTracker/0.1 (desktop app)"
CACHE_BYTES = 500 * 1024 * 1024
_PATH_RE = re.compile(r"^/?(\d+)/(\d+)/(\d+)\.png$")


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
        self._jobs: dict[QNetworkReply, QWebEngineUrlRequestJob] = {}

    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:
        m = _PATH_RE.match(job.requestUrl().path())
        if m is None:
            job.fail(QWebEngineUrlRequestJob.Error.UrlInvalid)
            return
        z, x, y = m.groups()
        req = QNetworkRequest(QUrl(TILE_URL.format(z=z, x=x, y=y)))
        req.setRawHeader(b"User-Agent", USER_AGENT)
        req.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                         QNetworkRequest.CacheLoadControl.PreferCache)
        reply = self._nam.get(req)
        self._jobs[reply] = job
        job.destroyed.connect(lambda *_: self._jobs.pop(reply, None) and reply.abort())
        reply.finished.connect(lambda: self._finish(reply))

    def _finish(self, reply: QNetworkReply) -> None:
        reply.deleteLater()
        job = self._jobs.pop(reply, None)
        if job is None:
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
            return
        buf = QBuffer(job)
        buf.setData(reply.readAll())
        buf.open(QIODevice.OpenModeFlag.ReadOnly)
        job.reply(b"image/png", buf)
