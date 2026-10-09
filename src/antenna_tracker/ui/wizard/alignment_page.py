from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWizard, QWizardPage,
)

from antenna_tracker.config import AppConfig
from antenna_tracker.hardware.turret_client import TurretClient
from antenna_tracker.i18n import is_rtl, t
from antenna_tracker.ui.theme import ACCENT, BORDER, GREEN, MUTED, RAISED, TEXT, card

INSTRUCTIONS = (
    "<b>1</b> &nbsp; Center the turret using the button below.<br><br>"
    "<b>2</b> &nbsp; Rotate the entire base toward a known direction, ideally the flight area.<br><br>"
    "<b>3</b> &nbsp; Enter that direction (0° north, 90° east)."
)

# Checked state has to be explicit: the app theme styles pressed buttons, not selected ones.
_REF_STYLE = (
    f"QPushButton {{ font-weight: 700; color: {MUTED}; background: {RAISED}; "
    f"border: 1px solid {BORDER}; border-radius: 8px; }}"
    f"QPushButton:hover {{ color: {TEXT}; background: #142136; border: 1px solid #2c425f; }}"
    f"QPushButton:checked {{ color: #04121c; background: {ACCENT}; border: 1px solid {ACCENT}; }}"
    f"QPushButton:checked:hover {{ color: #04121c; background: #7ce4ff; border: 1px solid #7ce4ff; }}"
)
_REF_SOURCES = (
    "\u2714 Map \u2014 true north.",
    "\u2714 Compass \u2014 magnetic north.",
)


class AlignmentPage(QWizardPage):
    def __init__(self, config: AppConfig, turret: TurretClient, parent=None) -> None:
        super().__init__(parent)
        self.config, self.turret = config, turret
        self.setTitle(t("Align the tracker"))
        self.setSubTitle(t("Set the center direction carefully; the turret can rotate about 85° to either side."))
        self.reset_btn = QPushButton(t("Center tracker"))
        self.reset_btn.setProperty("primary", True)
        self.reset_btn.setMinimumHeight(46)
        self.reset_btn.clicked.connect(self.reset)
        self.reset_status = QLabel(styleSheet=f"font-size: 14px; color: {MUTED};")
        self.turret.position.connect(self._on_position)

        self.azimuth = QSpinBox(minimum=0, maximum=359, wrapping=True, suffix="\u00b0")
        self.azimuth.setStyleSheet("font-size: 28px; padding: 7px; min-width: 150px;")
        self.azimuth.setValue(int(config.ref_azimuth) % 360)

        self.ref_group = QButtonGroup(self)
        ref_row = QHBoxLayout()
        ref_row.addWidget(QLabel(t("Direction measured with")))
        for i, text in enumerate((t("Map"), t("Compass"))):
            b = QPushButton(text, checkable=True)
            b.setMinimumHeight(38)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setStyleSheet(_REF_STYLE)
            self.ref_group.addButton(b, i)
            ref_row.addWidget(b)
        self.ref_group.button(1 if config.ref_is_magnetic else 0).setChecked(True)
        self.ref_group.idClicked.connect(self._show_ref_source)
        ref_row.addStretch(1)
        self.ref_hint = QLabel()
        self.ref_hint.setStyleSheet(f"font-size: 14px; color: {GREEN}; font-weight: bold;")
        self._show_ref_source(self.ref_group.checkedId())

        step_spacing = "0" if is_rtl() else "2px"
        illo = QLabel(t("CENTER  →  AIM  →  CONFIRM"), alignment=Qt.AlignmentFlag.AlignCenter)
        illo.setStyleSheet(
            f"font-size: 15px; color: #46d9ff; font-weight: 800; letter-spacing: {step_spacing};")
        text = QLabel(t(INSTRUCTIONS), wordWrap=True, styleSheet="font-size: 15px; color: #c9d5e5;")
        az_row = QHBoxLayout()
        az_row.addWidget(QLabel(t("Center direction"), styleSheet="font-size: 15px; font-weight: bold;"))
        az_row.addWidget(self.azimuth)
        az_row.addStretch(1)

        instructions_card, instructions = card(t("PHYSICAL ALIGNMENT"))
        instructions.addWidget(illo)
        instructions.addWidget(text)
        instructions.addWidget(self.reset_btn)
        instructions.addWidget(self.reset_status)
        direction_card, direction = card(t("REFERENCE DIRECTION"))
        direction.addLayout(az_row)
        direction.addLayout(ref_row)
        direction.addWidget(self.ref_hint)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 8)
        lay.setSpacing(14)
        lay.addWidget(instructions_card)
        lay.addWidget(direction_card)
        lay.addStretch(1)
        self.setButtonText(QWizard.WizardButton.FinishButton, t("Start tracking"))

    def _show_ref_source(self, source_id: int) -> None:
        self.ref_hint.setText(t(_REF_SOURCES[1 if source_id == 1 else 0]))

    def reset(self) -> None:
        self.turret.init()
        self.reset_status.setText(t("Sent reset... waiting for the tracker"))
        self.reset_status.setStyleSheet(f"font-size: 14px; color: {MUTED};")

    def _on_position(self, pan: int, tilt: int) -> None:
        if (pan, tilt) == (90, 90):
            self.reset_status.setText(t("\u2714 Tracker is at its middle position."))
            self.reset_status.setStyleSheet("font-size: 14px; color: #3ddc84; font-weight: bold;")

    def validatePage(self) -> bool:
        self.config.ref_azimuth = float(self.azimuth.value())
        self.config.ref_is_magnetic = self.ref_group.checkedId() == 1
        return True
