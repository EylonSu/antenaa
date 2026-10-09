from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import (
    QCamera,
    QCameraDevice,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaPlayer,
    QVideoFrame,
    QVideoSink,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from antenna_tracker.i18n import t

_video_file_override: str | None = None


def set_video_file_override(path: str | None) -> None:
    """Developer playback: every VideoPreview plays this file (looped) instead of a capture device."""
    global _video_file_override
    _video_file_override = str(Path(path).resolve()) if path else None


def video_file_override() -> str | None:
    return _video_file_override


def device_id(dev: QCameraDevice) -> str:
    return bytes(dev.id()).decode("utf-8", errors="replace")


def list_video_inputs() -> list[tuple[str, str]]:
    """(device id, human name) for every capture device."""
    return [(device_id(d), d.description()) for d in QMediaDevices.videoInputs()]


def find_device(dev_id: str | None) -> QCameraDevice | None:
    if not dev_id:
        return None
    for d in QMediaDevices.videoInputs():
        if device_id(d) == dev_id:
            return d
    return None


class VideoPreview(QWidget):
    """Live preview of a capture device, or a placeholder when none is selected.

    ``show_preview=False`` keeps decoding frames for QR without drawing a picture.
    """

    frame_ready = Signal(QVideoFrame)

    def __init__(self, parent=None, *, show_preview: bool = True) -> None:
        super().__init__(parent)
        self._session = QMediaCaptureSession(self)
        self._camera: QCamera | None = None
        self._player: QMediaPlayer | None = None
        self._stack: QStackedLayout | None = None
        if show_preview:
            self.video = QVideoWidget()
            self._output = self.video
            self.video.videoSink().videoFrameChanged.connect(self._on_frame)
            self.placeholder = QLabel(t("No video"), alignment=Qt.AlignmentFlag.AlignCenter)
            self.placeholder.setStyleSheet("background: #222; color: #aaa; font-size: 20px;")
            self._stack = QStackedLayout(self)
            self._stack.addWidget(self.placeholder)
            self._stack.addWidget(self.video)
            self.setMinimumSize(240, 135)
        else:
            self.video = None
            self.placeholder = None
            self._output = QVideoSink(self)
            self._output.videoFrameChanged.connect(self._on_frame)
            self.hide()
        self._session.setVideoOutput(self._output)

    def _on_frame(self, frame: QVideoFrame) -> None:
        if frame.isValid():
            self.frame_ready.emit(frame)

    def set_device(self, dev_id: str | None) -> None:
        if _video_file_override:
            self.play_file(_video_file_override)
            return
        self.stop()
        dev = find_device(dev_id)
        if dev is None:
            if self.placeholder is not None and self._stack is not None:
                self.placeholder.setText(t("No video") if not dev_id else t("Video device not found"))
                self._stack.setCurrentWidget(self.placeholder)
            return
        self._camera = QCamera(dev, self)
        self._session.setCamera(self._camera)
        if self._stack is not None and self.video is not None:
            self._stack.setCurrentWidget(self.video)
        self._camera.start()

    def play_file(self, path: str) -> None:
        self.stop()
        self._player = QMediaPlayer(self)
        self._player.setVideoOutput(self._output)
        self._player.setLoops(QMediaPlayer.Loops.Infinite)
        self._player.setSource(QUrl.fromLocalFile(path))
        if self._stack is not None and self.video is not None:
            self._stack.setCurrentWidget(self.video)
        self._player.play()

    def stop(self) -> None:
        if self._camera is not None:
            self._camera.stop()
            self._session.setCamera(None)
            self._camera.deleteLater()
            self._camera = None
        if self._player is not None:
            self._player.stop()
            self._player.setVideoOutput(None)
            self._player.deleteLater()
            self._player = None
            self._session.setVideoOutput(self._output)
