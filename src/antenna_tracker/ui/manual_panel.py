from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

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
        grid = QGridLayout()
        grid.setSpacing(5)
        places = {"up": (0, 1), "left": (1, 0), "right": (1, 2), "down": (2, 1)}
        for name, (glyph, dp, dt) in ARROWS.items():
            b = QPushButton(glyph)
            b.setFixedSize(62, 46)
            b.setStyleSheet("font-size: 20px; font-weight: 700;")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setAutoRepeat(True)
            b.setAutoRepeatDelay(400)
            b.setAutoRepeatInterval(250)
            b.clicked.connect(lambda _=False, n=name: self.nudge(n))
            self.buttons[name] = b
            grid.addWidget(b, *places[name])

        self.point_btn = QPushButton("Point to target")
        self.point_btn.setProperty("primary", True)
        self.point_btn.setMinimumHeight(42)
        self.point_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.point_btn.clicked.connect(self.controller.point_to_recommended)

        side = QVBoxLayout()
        side.addWidget(QLabel("Arrow keys nudge 1°", styleSheet="color: #8fa3bd; font-size: 12px;"))
        side.addWidget(self.point_btn)
        side.addStretch(1)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(grid)
        lay.addSpacing(14)
        lay.addLayout(side)
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
            b.setToolTip("" if b.isEnabled() else "The tracker cannot move further this way")
        self.point_btn.setEnabled(connected and self.controller.last_solution is not None)
