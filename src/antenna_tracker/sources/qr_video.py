from __future__ import annotations

from PySide6.QtCore import QObject

from antenna_tracker.sources.base import PositionSource


class QrVideoSource(PositionSource):
    """Phase 2: decode drone position QR codes from video frames."""

    def __init__(self, video_device_id: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.video_device_id = video_device_id

    def start(self) -> None:
        raise NotImplementedError("QR video source is planned for phase 2")
