from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWizardPage,
)

from antenna_tracker.config import AppConfig
from antenna_tracker.hardware import port_finder
from antenna_tracker.hardware.port_finder import PortInfo, TestResult
from antenna_tracker.hardware.turret_client import TurretClient
from antenna_tracker.i18n import t
from antenna_tracker.ui.theme import ACCENT, MUTED, card, muted
from antenna_tracker.video.capture import VideoPreview, list_video_inputs

BIG = "font-size: 15px; padding: 8px;"


class _Tester(QObject):
    done = Signal(object)  # TestResult

    def run(self, device: str) -> None:
        threading.Thread(target=lambda: self.done.emit(port_finder.test_port(device)), daemon=True).start()


class ConnectPage(QWizardPage):
    def __init__(self, config: AppConfig, turret: TurretClient, dev_mode: bool, parent=None) -> None:
        super().__init__(parent)
        self.config, self.turret, self.dev_mode = config, turret, dev_mode
        self.setTitle(t("Connect your equipment"))
        self.setSubTitle(t("Select the tracker and receiver video, then verify the hardware link."))
        self._ports: list[PortInfo] = []
        self._tested: str | None = None
        self._tester = _Tester(self)
        self._tester.done.connect(self._on_tested)

        self.port_combo = QComboBox(styleSheet=BIG)
        self.port_combo.currentIndexChanged.connect(self._port_changed)
        self.refresh_btn = QPushButton(t("\u21bb Refresh"), styleSheet=BIG)
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.test_btn = QPushButton(t("Test"), styleSheet=BIG + "font-weight: bold; min-width: 120px;")
        self.test_btn.clicked.connect(self.test)
        self.result = QLabel(styleSheet=f"font-size: 14px; color: {MUTED};", wordWrap=True)

        self.video_combo = QComboBox(styleSheet=BIG)
        self.video_combo.currentIndexChanged.connect(self._video_changed)
        self.preview = VideoPreview()
        self.preview.setFixedSize(384, 216)
        self.preview.setStyleSheet("border: 1px solid #1d2b42; border-radius: 8px; background: #050b13;")

        port_row = QHBoxLayout()
        port_row.addWidget(self.port_combo, 1)
        port_row.addWidget(self.refresh_btn)
        port_row.addWidget(self.test_btn)
        tracker_card, tracker = card(t("TRACKER LINK"))
        tracker.addWidget(muted(t("Choose the USB device and test the connection before continuing.")))
        tracker.addLayout(port_row)
        tracker.addWidget(self.result)
        video_card, video = card(t("DRONE RECEIVER VIDEO"))
        video.addWidget(muted(t("Choose the feed containing the drone telemetry QR code.")))
        video.addWidget(self.video_combo)
        video.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignLeft)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 8)
        lay.setSpacing(14)
        lay.addWidget(tracker_card)
        lay.addWidget(video_card)
        lay.addStretch(1)

        self.refresh_ports()
        self._load_videos()

    def refresh_ports(self) -> None:
        self._ports = port_finder.list_candidates(include_fake=self.dev_mode)
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        for p in self._ports:
            self.port_combo.addItem(p.label, p.device)
        if not self._ports:
            self.port_combo.addItem(t("No tracker found - check the USB cable"), None)
        devices = [p.device for p in self._ports]
        if self.config.port_device in devices:
            self.port_combo.setCurrentIndex(devices.index(self.config.port_device))
        self.port_combo.blockSignals(False)
        self._port_changed()

    def _load_videos(self) -> None:
        self.video_combo.blockSignals(True)
        self.video_combo.addItem(t("No video"), None)
        for dev_id, name in list_video_inputs():
            self.video_combo.addItem(name, dev_id)
        idx = self.video_combo.findData(self.config.video_device_id)
        self.video_combo.setCurrentIndex(max(idx, 0))
        self.video_combo.blockSignals(False)
        self._video_changed()

    def selected_port(self) -> PortInfo | None:
        dev = self.port_combo.currentData()
        return next((p for p in self._ports if p.device == dev), None)

    def _port_changed(self) -> None:
        self._tested = None
        self.result.setText(t("Press Test to check the tracker."))
        self.result.setStyleSheet(f"font-size: 14px; color: {MUTED};")
        self.test_btn.setEnabled(self.selected_port() is not None)
        self.completeChanged.emit()

    def _video_changed(self) -> None:
        self.preview.set_device(self.video_combo.currentData())

    def test(self) -> None:
        port = self.selected_port()
        if port is None:
            return
        self.turret.close()
        self.test_btn.setEnabled(False)
        self.result.setText(t("Testing... please wait"))
        self.result.setStyleSheet(f"font-size: 14px; color: {MUTED};")
        self._tester.run(port.device)

    def _on_tested(self, res: TestResult) -> None:
        self.test_btn.setEnabled(True)
        port = self.selected_port()
        if res.ok and port is not None:
            self._tested = port.device
            self.result.setText(f"\u2714 {res.message}")
            self.result.setStyleSheet("font-size: 14px; color: #3ddc84; font-weight: bold;")
        else:
            self._tested = None
            self.result.setText(f"\u2716 {res.message}")
            self.result.setStyleSheet("font-size: 14px; color: #ff5d6c; font-weight: bold;")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        port = self.selected_port()
        return port is not None and self._tested == port.device

    def validatePage(self) -> bool:
        port = self.selected_port()
        if port is None:
            return False
        c = self.config
        c.port_device, c.port_vid, c.port_pid, c.port_serial_number = (
            port.device, port.vid, port.pid, port.serial_number)
        c.video_device_id = self.video_combo.currentData()
        self.preview.stop()
        self.turret.open(port.identity)
        return True
