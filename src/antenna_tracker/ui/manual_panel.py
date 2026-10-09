from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from antenna_tracker.i18n import t
from antenna_tracker.tracking.controller import TrackingController

ARROWS = {
    "up": ("\u25b2", 0, 1),
    "down": ("\u25bc", 0, -1),
    "left": ("\u25c0", -1, 0),
    "right": ("\u25b6", 1, 0),
}
STEP_DEG = 1


class ManualPanel(QWidget):
    def __init__(self, controller: TrackingController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.buttons: dict[str, QPushButton] = {}
        # The pad stays geographically left-to-right. A mirrored grid would put the left arrow on the right.
        pad_widget = QWidget()
        pad_widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        grid = QGridLayout(pad_widget)
        grid.setSpacing(6)
        places = {"up": (0, 1), "left": (1, 0), "right": (1, 2), "down": (2, 1)}
        for name, (glyph, dp, dt) in ARROWS.items():
            b = QPushButton(glyph)
            b.setFixedSize(64, 50)
            b.setStyleSheet("font-size: 17px; border-radius: 10px;")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setAutoRepeat(True)
            b.setAutoRepeatDelay(400)
            b.setAutoRepeatInterval(250)
            b.clicked.connect(lambda _=False, n=name: self.nudge(n))
            self.buttons[name] = b
            grid.addWidget(b, *places[name])

        pad = QHBoxLayout()
        pad.addStretch(1)
        pad.addWidget(pad_widget)
        pad.addStretch(1)

        self.point_btn = QPushButton(t("Point to target"))
        self.point_btn.setProperty("primary", True)
        self.point_btn.setMinimumHeight(40)
        self.point_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.point_btn.clicked.connect(self.controller.point_to_recommended)

        hint = QLabel(t("Arrow keys nudge 1\u00b0 \u00b7 hold to repeat"), alignment=Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #54657c; font-size: 11px;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addLayout(pad)
        lay.addWidget(self.point_btn)
        lay.addWidget(hint)
        self.refresh()

    def nudge(self, name: str) -> bool:
        _, dp, dt = ARROWS[name]
        ok = self.controller.nudge(dp * STEP_DEG, dt * STEP_DEG)
        self.refresh()
        return ok

    def refresh(self) -> None:
        connected = self.controller.turret.is_connected
        for name, (_, dp, dt) in ARROWS.items():
            target = self.controller.manual_target(dp * STEP_DEG, dt * STEP_DEG)
            b = self.buttons[name]
            b.setEnabled(connected and target is not None)
            b.setToolTip("" if b.isEnabled() else t("The tracker cannot move further this way"))
        self.point_btn.setEnabled(connected and self.controller.last_solution is not None)
