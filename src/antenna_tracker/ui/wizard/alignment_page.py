from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWizard, QWizardPage,
)

from antenna_tracker.config import AppConfig
from antenna_tracker.hardware.turret_client import TurretClient

INSTRUCTIONS = (
    "1. Press <b>Reset tracker</b>. The antenna turns to its middle position.<br>"
    "2. Rotate the <b>whole tracker</b> (the base) so the antenna faces a known direction, "
    "ideally toward where the drone will fly.<br>"
    "3. Type that direction below (0 = north, 90 = east)."
)


class AlignmentPage(QWizardPage):
    def __init__(self, config: AppConfig, turret: TurretClient, parent=None) -> None:
        super().__init__(parent)
        self.config, self.turret = config, turret
        self.setTitle("Step 3 of 3: Point the tracker")
        self.setSubTitle("The tracker can only turn about 85\u00b0 to each side of this direction.")
        self.reset_btn = QPushButton("\u27f2  Reset tracker")
        self.reset_btn.setStyleSheet("font-size: 26px; font-weight: bold; padding: 18px;")
        self.reset_btn.clicked.connect(self.reset)
        self.reset_status = QLabel(styleSheet="font-size: 18px;")
        self.turret.position.connect(self._on_position)

        self.azimuth = QSpinBox(minimum=0, maximum=359, wrapping=True, suffix="\u00b0")
        self.azimuth.setStyleSheet("font-size: 36px; padding: 6px; min-width: 160px;")
        self.azimuth.setValue(int(config.ref_azimuth) % 360)

        self.ref_group = QButtonGroup(self)
        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel("Measured with:", styleSheet="font-size: 20px;"))
        for i, text in enumerate(("Map", "Compass")):
            b = QPushButton(text, checkable=True)
            b.setStyleSheet("font-size: 20px; padding: 10px 24px;")
            self.ref_group.addButton(b, i)
            ref_row.addWidget(b)
        self.ref_group.button(1 if config.ref_is_magnetic else 0).setChecked(True)
        ref_row.addStretch(1)

        illo = QLabel("\U0001F4E1  \u2192  \U0001F9ED", alignment=Qt.AlignmentFlag.AlignCenter)
        illo.setStyleSheet("font-size: 56px;")
        text = QLabel(INSTRUCTIONS, wordWrap=True, styleSheet="font-size: 19px;")
        az_row = QHBoxLayout()
        az_row.addWidget(QLabel("The antenna faces:", styleSheet="font-size: 22px; font-weight: bold;"))
        az_row.addWidget(self.azimuth)
        az_row.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addWidget(illo)
        lay.addWidget(text)
        lay.addWidget(self.reset_btn)
        lay.addWidget(self.reset_status)
        lay.addLayout(az_row)
        lay.addLayout(ref_row)
        lay.addStretch(1)
        self.setButtonText(QWizard.WizardButton.FinishButton, "Start tracking \u25b6")

    def reset(self) -> None:
        self.turret.init()
        self.reset_status.setText("Sent reset... waiting for the tracker")
        self.reset_status.setStyleSheet("font-size: 18px; color: #555;")

    def _on_position(self, pan: int, tilt: int) -> None:
        if (pan, tilt) == (90, 90):
            self.reset_status.setText("\u2714 Tracker is at its middle position.")
            self.reset_status.setStyleSheet("font-size: 18px; color: #2e7d32; font-weight: bold;")

    def validatePage(self) -> bool:
        self.config.ref_azimuth = float(self.azimuth.value())
        self.config.ref_is_magnetic = self.ref_group.checkedId() == 1
        return True
