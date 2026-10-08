from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from antenna_tracker.tracking.controller import TrackingController

ARROWS = {
    "up": ("\u25b2", 0, 1),
    "down": ("\u25bc", 0, -1),
    "left": ("\u25c0", -1, 0),
    "right": ("\u25b6", 1, 0),
}


class ManualPanel(QWidget):
    back_to_auto = Signal()

    def __init__(self, controller: TrackingController, parent=None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.buttons: dict[str, QPushButton] = {}
        grid = QGridLayout()
        grid.setSpacing(6)
        places = {"up": (0, 1), "left": (1, 0), "right": (1, 2), "down": (2, 1)}
        for name, (glyph, dp, dt) in ARROWS.items():
            b = QPushButton(glyph)
            b.setFixedSize(76, 66)
            b.setStyleSheet("font-size: 30px;")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setAutoRepeat(True)
            b.setAutoRepeatDelay(400)
            b.setAutoRepeatInterval(250)
            b.clicked.connect(lambda _=False, n=name: self.nudge(n))
            self.buttons[name] = b
            grid.addWidget(b, *places[name])

        self.step_group = QButtonGroup(self)
        step_row = QHBoxLayout()
        step_row.addWidget(QLabel("Step:", styleSheet="font-size: 18px;"))
        for i, step in enumerate((1, 5)):
            b = QPushButton(f"{step}\u00b0", checkable=True, checked=(step == 1))
            b.setStyleSheet("font-size: 18px; padding: 8px 14px;")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.step_group.addButton(b, step)
            step_row.addWidget(b)
        self.step_group.idClicked.connect(lambda _: self.refresh())

        self.point_btn = QPushButton("Point to target")
        self.auto_btn = QPushButton("Back to AUTO")
        for b in (self.point_btn, self.auto_btn):
            b.setStyleSheet("font-size: 18px; padding: 10px;")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.point_btn.clicked.connect(self.controller.point_to_recommended)
        self.auto_btn.clicked.connect(self.back_to_auto)

        side = QVBoxLayout()
        side.addLayout(step_row)
        side.addWidget(self.point_btn)
        side.addWidget(self.auto_btn)
        side.addStretch(1)
        lay = QHBoxLayout(self)
        lay.addLayout(grid)
        lay.addSpacing(10)
        lay.addLayout(side)
        self.refresh()

    @property
    def step(self) -> int:
        return self.step_group.checkedId()

    def nudge(self, name: str) -> bool:
        _, dp, dt = ARROWS[name]
        ok = self.controller.nudge(dp * self.step, dt * self.step)
        self.refresh()
        return ok

    def refresh(self) -> None:
        connected = self.controller.turret.is_connected
        for name, (_, dp, dt) in ARROWS.items():
            target = self.controller.manual_target(dp * self.step, dt * self.step)
            b = self.buttons[name]
            b.setEnabled(connected and target is not None)
            b.setToolTip("" if b.isEnabled() else "The tracker cannot move further this way")
        self.point_btn.setEnabled(connected and self.controller.last_solution is not None)
