"""Generate an mp4 of changing QR codes (drone telemetry) for --video-file testing.

Usage: python scripts/make_qr_video.py [OUT.mp4] [--seconds 40] [--fps 10]

Uses Qt's own encoder (QMediaRecorder + QVideoFrameInput), so no ffmpeg is needed.
"""
from __future__ import annotations

import argparse
import io
import math
import sys
import time
from pathlib import Path

import segno
from PySide6.QtCore import QCoreApplication, QEventLoop, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtMultimedia import (
    QMediaCaptureSession, QMediaFormat, QMediaRecorder, QVideoFrame, QVideoFrameFormat, QVideoFrameInput,
)

DEMO_ANTENNA = (32.0784, 34.7694)  # the --demo antenna (UTM 667000 / 550500), Tel Aviv


def payload(serial: str, lat: float, lon: float, rel_alt: float, heading: float, home_dist: float) -> str:
    """Same layout as the real feed: serial|lat|lon|...|heading|rel_alt|...|home_dist|antenna_dist."""
    f = ["0"] * 14
    f[0], f[1], f[2] = serial, f"{lat:.7f}", f"{lon:.7f}"
    f[5], f[6], f[12], f[13] = f"{heading:.1f}", f"{rel_alt:.1f}", f"{home_dist:.0f}", "-1"
    return "|".join(f)


def demo_payloads(seconds: float, fps: int, serial: str = "DRN-4521", period_s: float | None = None) -> list[str]:
    """Drone circling (500 m radius, ~25 m/s) north-east of the antenna; GPS drops out from 45% to 60% of the clip."""
    lat0, lon0 = DEMO_ANTENNA
    cx, cy = lat0 + 0.006, lon0 + 0.006
    n = int(seconds * fps)
    period_frames = (period_s or seconds) * fps
    out = []
    for i in range(n):
        a = 2 * math.pi * i / period_frames
        lat = cx + 0.0045 * math.cos(a)
        lon = cy + 0.0053 * math.sin(a)
        heading = (math.degrees(a) + 90) % 360
        alt = 120 + 40 * math.sin(2 * a)
        home = math.hypot((lat - lat0) * 111_000, (lon - lon0) * 94_000)
        if 0.45 * n <= i < 0.60 * n:
            lat = lon = 0.0
        out.append(payload(serial, lat, lon, alt, heading, home))
    return out


def qr_image(text: str, scale: int = 5) -> QImage:
    buf = io.BytesIO()
    segno.make_qr(text, error="m").save(buf, kind="png", scale=scale, border=4)
    return QImage.fromData(buf.getvalue())


def render_frame(text: str, size: QSize, i: int) -> QImage:
    img = QImage(size, QImage.Format.Format_RGBA8888)
    img.fill(QColor(70, 90, 70))
    p = QPainter(img)
    p.fillRect(0, int(size.height() * 0.6), size.width(), size.height(), QColor(110, 100, 80))
    p.setPen(Qt.GlobalColor.white)
    p.setFont(QFont("Helvetica", 28))
    p.drawText(size.width() // 2, size.height() // 2, f"frame {i}")
    p.drawImage(12, 12, qr_image(text))
    p.end()
    return img


def _finalized(path: Path) -> bool:
    """The MP4 index (moov box) is written last, after recorderStateChanged(Stopped)."""
    return path.is_file() and b"moov" in path.read_bytes()


def write_qr_video(path: str | Path, payloads: list[str], fps: int = 10, size: QSize = QSize(1280, 720),
                   timeout_s: float = 120.0) -> bool:
    """Encode one QR payload per frame into an mp4. Returns False if this Qt build can't encode."""
    app = QCoreApplication.instance()
    if app is None:
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication(sys.argv[:1])
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    fmt = QVideoFrameFormat(size, QVideoFrameFormat.PixelFormat.Format_RGBA8888)
    fmt.setStreamFrameRate(fps)
    frame_input = QVideoFrameInput(fmt)
    session = QMediaCaptureSession()
    recorder = QMediaRecorder()
    session.setVideoFrameInput(frame_input)
    session.setRecorder(recorder)
    mf = QMediaFormat(QMediaFormat.FileFormat.MPEG4)
    mf.setVideoCodec(QMediaFormat.VideoCodec.H264)
    recorder.setMediaFormat(mf)
    recorder.setQuality(QMediaRecorder.Quality.VeryHighQuality)
    recorder.setVideoFrameRate(fps)
    recorder.setVideoResolution(size)
    recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))

    state = {"i": 0, "error": None, "done": False}
    loop = QEventLoop()

    def send() -> None:
        while state["i"] < len(payloads):
            i = state["i"]
            frame = QVideoFrame(render_frame(payloads[i], size, i))
            frame.setStartTime(int(i * 1_000_000 / fps))
            frame.setEndTime(int((i + 1) * 1_000_000 / fps))
            if not frame_input.sendVideoFrame(frame):
                return  # wait for readyToSendVideoFrame
            state["i"] += 1
        if recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState:
            recorder.stop()

    def on_state(s) -> None:
        if s == QMediaRecorder.RecorderState.StoppedState and state["i"] > 0:
            state["done"] = True
            loop.quit()

    def on_error(err, msg) -> None:
        state["error"] = msg or str(err)
        loop.quit()

    frame_input.readyToSendVideoFrame.connect(send)
    recorder.recorderStateChanged.connect(on_state)
    recorder.errorOccurred.connect(on_error)
    QTimer.singleShot(int(timeout_s * 1000), loop.quit)
    recorder.record()
    if recorder.error() != QMediaRecorder.Error.NoError:
        return False
    QTimer.singleShot(0, send)
    loop.exec()
    deadline = time.monotonic() + 10
    while state["done"] and time.monotonic() < deadline and not _finalized(path):
        app.processEvents()
        time.sleep(0.05)
    return state["done"] and state["error"] is None and _finalized(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="samples/demo_qr.mp4")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--fps", type=int, default=10)
    args = ap.parse_args()
    ok = write_qr_video(args.out, demo_payloads(args.seconds, args.fps), args.fps)
    print(("wrote " if ok else "FAILED to write ") + args.out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
