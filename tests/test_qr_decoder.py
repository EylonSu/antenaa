from __future__ import annotations

import time

import numpy as np
import pytest
import segno
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage

from antenna_tracker.video.qr_decoder import QrDecoder, Roi, crop_gray, decode_gray, qimage_to_gray

SAMPLE = ("1748FEV3HMK824291553|32.08|34.78|-7.8525233|-60.916748|-52.309998|198.534|0.0|11.69|1|"
          "0.5083778|4|3437.2869|-22918.311805|73.8062|58.66283|[]")


def qr_frame(text: str = SAMPLE, size: int = 200, x: int = 20, y: int = 20,
             w: int = 1280, h: int = 720) -> np.ndarray:
    qr = segno.make(text, error="m")
    m = np.array(list(qr.matrix), dtype=np.uint8)
    m = np.pad(m, 4)
    scale = max(1, size // m.shape[0])
    code = np.where(np.kron(m, np.ones((scale, scale), np.uint8)) > 0, 0, 255).astype(np.uint8)
    frame = np.full((h, w), 90, np.uint8)
    frame[y:y + code.shape[0], x:x + code.shape[1]] = code
    return frame


def blur(img: np.ndarray, k: int = 3) -> np.ndarray:
    p = np.pad(img.astype(np.float32), k // 2, mode="edge")
    out = np.zeros(img.shape, np.float32)
    for dy in range(k):
        for dx in range(k):
            out += p[dy:dy + img.shape[0], dx:dx + img.shape[1]]
    return (out / (k * k)).astype(np.uint8)


def downscale(img: np.ndarray, f: int) -> np.ndarray:
    h, w = (img.shape[0] // f) * f, (img.shape[1] // f) * f
    return img[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3)).astype(np.uint8)


def to_qimage(gray: np.ndarray) -> QImage:
    gray = np.ascontiguousarray(gray)
    return QImage(gray.data, gray.shape[1], gray.shape[0], gray.strides[0],
                  QImage.Format.Format_Grayscale8).copy()


def jpeg(gray: np.ndarray, quality: int) -> QImage:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    to_qimage(gray).save(buf, "JPEG", quality)
    out = QImage()
    out.loadFromData(ba, "JPEG")
    return out


def test_clean_frame_roi_decodes():
    assert decode_gray(crop_gray(qr_frame(), Roi())) == SAMPLE


@pytest.mark.parametrize("k,f,q", [(3, 1, 70), (3, 2, 60), (5, 1, 50), (3, 2, 40)])
def test_degraded_frame_decodes(k, f, q):
    frame = downscale(blur(qr_frame(size=240), k), f)
    img = jpeg(frame, q)
    gray = qimage_to_gray(img, Roi())
    assert decode_gray(gray) == SAMPLE


def test_qimage_rgb_crop():
    img = to_qimage(qr_frame()).convertToFormat(QImage.Format.Format_RGB32)
    gray = qimage_to_gray(img, Roi())
    assert gray.shape == (round(720 * 0.35), round(1280 * 0.25))
    assert decode_gray(gray) == SAMPLE


def test_outside_roi_not_in_crop():
    frame = qr_frame(x=900, y=400)
    assert decode_gray(crop_gray(frame, Roi())) is None
    assert decode_gray(frame) == SAMPLE


def _wait(qapp, cond, timeout=5.0):
    end = time.monotonic() + timeout
    while not cond() and time.monotonic() < end:
        qapp.processEvents()
        time.sleep(0.005)
    return cond()


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_decoder_thread_emits(qapp):
    d = QrDecoder()
    got = []
    d.decoded.connect(lambda text, t: got.append((text, t)))
    try:
        assert d.submit(to_qimage(qr_frame()), t=123.0)
        assert _wait(qapp, lambda: got)
        assert got[0] == (SAMPLE, 123.0)
        assert d.last_text == SAMPLE
        assert d.rate() == 1.0
    finally:
        d.shutdown()


def test_throttle_drops_fast_frames(qapp):
    d = QrDecoder(max_fps=10)
    try:
        frame = qr_frame()
        assert d.submit(frame)
        assert not d.submit(frame)
        time.sleep(0.11)
        assert d.submit(frame)
    finally:
        d.shutdown()


def test_full_frame_fallback_after_misses(qapp):
    d = QrDecoder(max_fps=0, full_frame_after_misses=3)
    got = []
    d.decoded.connect(lambda text, t: got.append(text))
    try:
        frame = qr_frame(x=900, y=400)
        for _ in range(3):
            d.submit(frame)
            _wait(qapp, lambda: not d._busy, 2)
        assert got == []
        d.submit(frame)
        assert _wait(qapp, lambda: got)
        assert got == [SAMPLE]
    finally:
        d.shutdown()


def test_latest_frame_only(qapp):
    d = QrDecoder(max_fps=0)
    got = []
    d.decoded.connect(lambda text, t: got.append(text))
    try:
        frames = [qr_frame(SAMPLE.replace("198.534", f"{i}.0")) for i in range(20)]
        for f in frames:
            d.submit(f)
        assert _wait(qapp, lambda: not d._busy and got)
        _wait(qapp, lambda: False, 0.2)
        assert got[-1] == SAMPLE.replace("198.534", "19.0")
        assert len(got) < 20
    finally:
        d.shutdown()
