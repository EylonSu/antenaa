from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

LOST_STYLE = "background: rgba(198, 40, 40, 235); color: white;"
BACK_STYLE = "background: rgba(46, 125, 50, 235); color: white;"


class PowerOverlay(QWidget):
    """Full-window alert shown over its parent while the tracker has no power."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.title = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size: 54px; font-weight: bold;")
        self.detail = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("font-size: 28px;")
        self.mute = QPushButton("Silence alarm")
        self.mute.setStyleSheet("font-size: 22px; padding: 14px 30px; color: black; background: white;")
        self.mute.clicked.connect(self.silence)
        lay = QVBoxLayout(self)
        lay.addStretch(1)
        lay.addWidget(self.title)
        lay.addWidget(self.detail)
        lay.addSpacing(30)
        lay.addWidget(self.mute, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(1)
        self._beep = QTimer(self)
        self._beep.setInterval(1000)
        self._beep.timeout.connect(QApplication.beep)
        self._hide_timer = QTimer(self, singleShot=True, interval=3000)
        self._hide_timer.timeout.connect(self.hide)
        parent.installEventFilter(self)
        self.hide()

    @property
    def beeping(self) -> bool:
        return self._beep.isActive()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return False

    def show_lost(self, reason: str = "") -> None:
        self._hide_timer.stop()
        self.setStyleSheet(LOST_STYLE)
        self.title.setText("TRACKER HAS NO POWER")
        self.detail.setText("Check the battery / power cable.\nThe app will reconnect by itself."
                            + (f"\n\n({reason})" if reason else ""))
        self.mute.show()
        self._show()
        QApplication.beep()
        self._beep.start()

    def show_restored(self) -> None:
        self._beep.stop()
        self.setStyleSheet(BACK_STYLE)
        self.title.setText("Tracker is back")
        self.detail.setText("Tracking resumes automatically.")
        self.mute.hide()
        self._show()
        self._hide_timer.start()

    def silence(self) -> None:
        self._beep.stop()

    def _show(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
