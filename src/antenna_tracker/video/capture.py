from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QCamera, QCameraDevice, QMediaCaptureSession, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget


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
    """Live preview of a capture device, or a placeholder when none is selected."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._session = QMediaCaptureSession(self)
        self._camera: QCamera | None = None
        self.video = QVideoWidget()
        self._session.setVideoOutput(self.video)
        self.placeholder = QLabel("No video", alignment=Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("background: #222; color: #aaa; font-size: 20px;")
        self._stack = QStackedLayout(self)
        self._stack.addWidget(self.placeholder)
        self._stack.addWidget(self.video)
        self.setMinimumSize(240, 135)

    def set_device(self, dev_id: str | None) -> None:
        self.stop()
        dev = find_device(dev_id)
        if dev is None:
            self.placeholder.setText("No video" if not dev_id else "Video device not found")
            self._stack.setCurrentWidget(self.placeholder)
            return
        self._camera = QCamera(dev, self)
        self._session.setCamera(self._camera)
        self._stack.setCurrentWidget(self.video)
        self._camera.start()

    def stop(self) -> None:
        if self._camera is not None:
            self._camera.stop()
            self._session.setCamera(None)
            self._camera.deleteLater()
            self._camera = None
