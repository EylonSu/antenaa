"""Background QR decoding of video frames (latest-frame-only, throttled)."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass

import numpy as np
import zxingcpp
from PySide6.QtCore import QObject, QRect, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QVideoFrame


@dataclass(frozen=True)
class Roi:
    """Crop area as fractions of the frame, from the top-left corner."""
    width: float = 0.25
    height: float = 0.35


def qimage_to_gray(img: QImage, roi: Roi | None = None) -> np.ndarray:
    if roi is not None:
        w = max(1, round(img.width() * roi.width))
        h = max(1, round(img.height() * roi.height))
        img = img.copy(QRect(0, 0, w, h))
    img = img.convertToFormat(QImage.Format.Format_Grayscale8)
    w, h, stride = img.width(), img.height(), img.bytesPerLine()
    buf = np.frombuffer(img.constBits(), dtype=np.uint8, count=stride * h)
    return buf.reshape(h, stride)[:, :w].copy()


def crop_gray(gray: np.ndarray, roi: Roi) -> np.ndarray:
    h, w = gray.shape[:2]
    return gray[: max(1, round(h * roi.height)), : max(1, round(w * roi.width))]


def decode_gray(gray: np.ndarray) -> str | None:
    """Decode the first QR code in a grayscale image; retry 2x upscaled for tiny codes."""
    for img in (gray, None):
        if img is None:
            if gray.shape[0] * gray.shape[1] > 1_000_000:
                break
            img = np.repeat(np.repeat(gray, 2, axis=0), 2, axis=1)
        hits = zxingcpp.read_barcodes(np.ascontiguousarray(img), formats=zxingcpp.BarcodeFormat.QRCode)
        for b in hits:
            if b.valid and b.text:
                return b.text
    return None


class _Worker(QObject):
    decoded = Signal(str, float)
    missed = Signal()

    def __init__(self, decoder: QrDecoder) -> None:
        super().__init__()
        self._d = decoder
        self._misses = 0

    @Slot()
    def process(self) -> None:
        while True:
            item = self._d._take()
            if item is None:
                return
            src, t = item
            text = self._decode(src)
            if text is None:
                self.missed.emit()
            else:
                self.decoded.emit(text, t)

    def _decode(self, src: QVideoFrame | QImage | np.ndarray) -> str | None:
        roi = self._d.roi
        full_try = self._misses >= self._d.full_frame_after_misses
        if isinstance(src, np.ndarray):
            gray = src if src.ndim == 2 else src.mean(axis=2).astype(np.uint8)
            roi_gray = crop_gray(gray, roi)
            full = (lambda: gray)
        else:
            img = src.toImage() if isinstance(src, QVideoFrame) else src
            if img.isNull():
                return None
            roi_gray = qimage_to_gray(img, roi)
            full = (lambda: qimage_to_gray(img))
        text = decode_gray(roi_gray)
        if text is None and full_try:
            self._misses = 0
            text = decode_gray(full())
        if text is None:
            self._misses += 1
        else:
            self._misses = 0
        return text


class QrDecoder(QObject):
    """Decodes QR codes from video frames on a background thread.

    Feed it with ``preview.frame_ready.connect(decoder.submit_frame)``. Frames arriving
    faster than ``max_fps`` or while the worker is busy are dropped (only the newest is kept).
    """

    decoded = Signal(str, float)   # QR text, frame arrival time (time.time())
    stats = Signal(float)          # successful decodes per second, emitted every second
    _wake = Signal()

    def __init__(self, max_fps: float = 10.0, roi: Roi = Roi(),
                 full_frame_after_misses: int = 10, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.max_fps = max_fps
        self.roi = roi
        self.full_frame_after_misses = full_frame_after_misses
        self._lock = threading.Lock()
        self._pending: tuple[object, float] | None = None
        self._busy = False
        self._last_accept = 0.0
        self._ok_times: deque[float] = deque()
        self.last_text: str | None = None

        self._thread = QThread()
        self._thread.setObjectName("QrDecoder")
        self._worker = _Worker(self)
        self._worker.moveToThread(self._thread)
        self._wake.connect(self._worker.process)
        self._worker.decoded.connect(self._on_decoded)
        self._thread.start()

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(1000)
        self._stats_timer.timeout.connect(self._emit_stats)
        self._stats_timer.start()

    @Slot(QVideoFrame)
    def submit_frame(self, frame: QVideoFrame) -> None:
        self.submit(frame)

    def submit(self, src: QVideoFrame | QImage | np.ndarray, t: float | None = None,
               throttle: bool = True) -> bool:
        """Queue a frame for decoding; returns False if dropped by the rate limit."""
        now = time.monotonic()
        if throttle and self.max_fps > 0 and now - self._last_accept < 1.0 / self.max_fps:
            return False
        self._last_accept = now
        with self._lock:
            self._pending = (src, time.time() if t is None else t)
            wake = not self._busy
            self._busy = True
        if wake:
            self._wake.emit()
        return True

    def _take(self) -> tuple[object, float] | None:
        with self._lock:
            item, self._pending = self._pending, None
            if item is None:
                self._busy = False
            return item

    def _on_decoded(self, text: str, t: float) -> None:
        self.last_text = text
        self._ok_times.append(time.monotonic())
        self.decoded.emit(text, t)

    def rate(self) -> float:
        cutoff = time.monotonic() - 1.0
        while self._ok_times and self._ok_times[0] < cutoff:
            self._ok_times.popleft()
        return float(len(self._ok_times))

    def _emit_stats(self) -> None:
        self.stats.emit(self.rate())

    def shutdown(self) -> None:
        self._stats_timer.stop()
        with self._lock:
            self._pending = None
        self._thread.quit()
        self._thread.wait(2000)
