from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from antenna_tracker.i18n import is_rtl, t

OVERLAY_BASE = """
QWidget#PowerOverlay { border: none; }
QWidget#PowerOverlay QLabel { border: none; background: transparent; }
"""

LOST_STYLE = OVERLAY_BASE + "QWidget#PowerOverlay { background: rgba(10, 7, 13, 218); }"
BACK_STYLE = OVERLAY_BASE + "QWidget#PowerOverlay { background: rgba(5, 15, 12, 195); }"

CARD_STYLE = """
QFrame#PowerCard {
    background: #101b2e;
    border: 1px solid #2b3a52;
    border-radius: 18px;
}
QFrame#PowerCard QLabel { border: none; background: transparent; }
QFrame#PowerCard QPushButton {
    background: transparent;
    border: 1px solid #5b6b84;
    border-radius: 10px;
    color: #e8eef7;
    font-size: 14px;
    font-weight: 600;
    padding: 10px 22px;
}
QFrame#PowerCard QPushButton:hover { border-color: #7f93ab; background: #142136; }
QFrame#PowerCard QPushButton:pressed { background: #0b1626; }
"""

BADGE_BASE = "font-size: 24px; border-radius: 28px; min-width: 56px; min-height: 56px; max-width: 56px; max-height: 56px;"
BADGE_LOST = BADGE_BASE + "color: #ff8d99; background: rgba(255, 93, 108, 26); border: 1px solid #8b394b;"
BADGE_LOST_DIM = BADGE_BASE + "color: #ff8d99; background: rgba(255, 93, 108, 12); border: 1px solid #5c2a36;"
BADGE_OK = BADGE_BASE + "color: #6ee7a4; background: rgba(53, 208, 127, 26); border: 1px solid #286b4d;"

def _eyebrow_style(ok: bool) -> str:
    color = "#6ee7a4" if ok else "#ff8d99"
    spacing = "0" if is_rtl() else "3px"
    return f"font-size: 11px; font-weight: 800; letter-spacing: {spacing}; color: {color};"
TITLE_STYLE = "font-size: 26px; font-weight: 700; color: #f1f5f9;"
DETAIL_STYLE = "font-size: 14px; color: #aebdcc;"
REASON_STYLE = "font-size: 12px; color: #6d7f94;"


class PowerOverlay(QWidget):
    """Dimmed full-window alert with a centered status card while the tracker has no power."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("PowerOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.badge = QLabel("\u23fb", alignment=Qt.AlignmentFlag.AlignCenter)
        self.eyebrow = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.eyebrow.setStyleSheet(_eyebrow_style(False))
        self.title = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setStyleSheet(TITLE_STYLE)
        self.detail = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet(DETAIL_STYLE)
        self.reason = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.reason.setWordWrap(True)
        self.reason.setStyleSheet(REASON_STYLE)
        self.mute = QPushButton(t("Silence alarm"))
        self.mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute.clicked.connect(self.silence)
        self.hint = QLabel(t("Reconnects automatically"), alignment=Qt.AlignmentFlag.AlignCenter)
        self.hint.setStyleSheet("font-size: 12px; color: #6d7f94;")

        card = QFrame()
        card.setObjectName("PowerCard")
        card.setStyleSheet(CARD_STYLE)
        card.setMinimumWidth(400)
        card.setMaximumWidth(520)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(40, 34, 40, 30)
        card_lay.setSpacing(8)
        card_lay.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignCenter)
        card_lay.addSpacing(4)
        card_lay.addWidget(self.eyebrow)
        card_lay.addWidget(self.title)
        card_lay.addWidget(self.detail)
        card_lay.addWidget(self.reason)
        card_lay.addSpacing(10)
        card_lay.addWidget(self.mute, alignment=Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(self.hint)

        center = QHBoxLayout()
        center.addStretch(1)
        center.addWidget(card)
        center.addStretch(1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.addStretch(1)
        lay.addLayout(center)
        lay.addStretch(1)

        self._pulse_on = False
        self._beep = QTimer(self)
        self._beep.setInterval(1000)
        self._beep.timeout.connect(self._beat)
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

    def _beat(self) -> None:
        QApplication.beep()
        self._pulse_on = not self._pulse_on
        self.badge.setStyleSheet(BADGE_LOST if self._pulse_on else BADGE_LOST_DIM)

    def show_lost(self, reason: str = "") -> None:
        self._hide_timer.stop()
        self.setStyleSheet(LOST_STYLE)
        self.badge.setText("\u23fb")
        self.badge.setStyleSheet(BADGE_LOST)
        self._pulse_on = True
        self.eyebrow.setText(t("POWER LOST"))
        self.eyebrow.setStyleSheet(_eyebrow_style(False))
        self.title.setText(t("Tracker has no power"))
        self.detail.setText(t("Check the battery and power cable.\nThe app will reconnect by itself."))
        self.reason.setText(f"({reason})" if reason else "")
        self.reason.setVisible(bool(reason))
        self.mute.show()
        self.hint.show()
        self._show()
        self._beat()
        self._beep.start()

    def show_restored(self) -> None:
        self._beep.stop()
        self.setStyleSheet(BACK_STYLE)
        self.badge.setText("\u2713")
        self.badge.setStyleSheet(BADGE_OK)
        self.eyebrow.setText(t("POWER RESTORED"))
        self.eyebrow.setStyleSheet(_eyebrow_style(True))
        self.title.setText(t("Tracker is back"))
        self.detail.setText(t("Tracking resumes automatically."))
        self.reason.setVisible(False)
        self.mute.hide()
        self.hint.hide()
        self._show()
        self._hide_timer.start()

    def silence(self) -> None:
        self._beep.stop()

    def _show(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
