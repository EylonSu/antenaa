from __future__ import annotations

import io
import math
import struct
import tempfile
import wave
from functools import partial
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from antenna_tracker.i18n import is_rtl, t

ALERT_POWER, ALERT_SPOOF, ALERT_QR = "power", "spoof", "qr"
_PRIORITY = (ALERT_POWER, ALERT_SPOOF, ALERT_QR)
SNOOZE_MS = 15 * 60 * 1000

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

BADGE_BASE = "font-size: 22px; border-radius: 28px; min-width: 56px; min-height: 56px; max-width: 56px; max-height: 56px;"
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


def _harsh_wav() -> bytes:
    """Short dissonant square-wave beep. Loud at full playback volume."""
    rate = 22050
    n = int(rate * 0.16)
    fade = rate // 40
    frames = bytearray()
    for i in range(n):
        t_s = i / rate
        env = 1.0 if i < n - fade else (n - i) / fade
        low = 1.0 if math.sin(2 * math.pi * 1480 * t_s) >= 0 else -1.0
        high = 1.0 if math.sin(2 * math.pi * 1960 * t_s) >= 0 else -1.0
        sample = int(max(-32767, min(32767, (0.72 * low + 0.28 * high) * env * 30000)))
        frames += struct.pack("<h", sample)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))
    return buf.getvalue()


def _tone_url() -> QUrl | None:
    try:
        path = Path(tempfile.gettempdir()) / "antenaa-alarm.wav"
        if not path.is_file() or path.stat().st_size < 44:
            path.write_bytes(_harsh_wav())
        return QUrl.fromLocalFile(str(path))
    except OSError:
        return None


class PowerOverlay(QWidget):
    """Full-window alert. Highest unsnoozed condition wins: power, then spoofing, then QR."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("PowerOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.snooze_ms = SNOOZE_MS

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
        self.hide_btn = QPushButton(t("Hide for 15 min"))
        self.silence_btn = QPushButton(t("Silence for 15 min"))
        for button, slot in ((self.hide_btn, self.hide_current), (self.silence_btn, self.silence)):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(slot)
        self.hint = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("font-size: 12px; color: #6d7f94;")

        card = QFrame()
        card.setObjectName("PowerCard")
        card.setStyleSheet(CARD_STYLE)
        card.setMinimumWidth(420)
        card.setMaximumWidth(540)
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
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)
        actions.addWidget(self.hide_btn)
        actions.addWidget(self.silence_btn)
        actions.addStretch(1)
        card_lay.addLayout(actions)
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
        self._sound_enabled = True
        self._restored = False
        self._shown_kind: str | None = None
        self._shown_reason = ""
        self._active: dict[str, str] = {}
        self._hidden: set[str] = set()
        self._silenced: set[str] = set()
        self._hide_timers: dict[str, QTimer] = {}
        self._silence_timers: dict[str, QTimer] = {}
        self._hide_gen: dict[str, int] = {}
        self._silence_gen: dict[str, int] = {}
        self._beep = QTimer(self)
        self._beep.setInterval(1000)
        self._beep.timeout.connect(self._beat)
        self._back_timer = QTimer(self, singleShot=True, interval=3000)
        self._back_timer.timeout.connect(self._on_restored_done)
        self._effect: QSoundEffect | None = None
        try:
            tone = _tone_url()
            if tone is not None:
                self._effect = QSoundEffect(self)
                self._effect.setVolume(1.0)
                self._effect.setLoopCount(1)
                self._effect.setSource(tone)
        except Exception:
            self._effect = None
        parent.installEventFilter(self)
        self.hide()

    @property
    def beeping(self) -> bool:
        """Alarm timer, so tests do not depend on an audio device."""
        return self._beep.isActive()

    @property
    def alert_kind(self) -> str | None:
        return None if self._restored else self._shown_kind

    @property
    def showing_restored(self) -> bool:
        return self._restored

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return False

    def set_sound_enabled(self, enabled: bool) -> None:
        self._sound_enabled = bool(enabled)
        if not self._restored:
            self._apply()

    def set_active(self, kind: str, active: bool, reason: str = "", *, restored: bool = False) -> None:
        if kind not in _PRIORITY:
            return
        if active:
            turning_on = kind not in self._active
            self._active[kind] = reason
            if self._restored:
                self._restored = False
                self._back_timer.stop()
                self._apply()
                return
            if turning_on or self._shown_kind != self._pick() or not self.isVisible() or reason != self._shown_reason:
                self._apply()
            return
        was = kind in self._active
        self._active.pop(kind, None)
        if was:
            self._cancel_snooze(kind)
        if restored and kind == ALERT_POWER:
            self._show_restored()
            return
        if was or self._shown_kind == kind:
            self._apply()

    def hide_current(self) -> None:
        kind = self._shown_kind
        if kind is None or self._restored:
            return
        self._hidden.add(kind)
        self._arm(self._hide_timers, self._hide_gen, kind, self._end_hide)
        self._apply()

    def silence(self) -> None:
        kind = self._shown_kind
        if kind is None or self._restored:
            return
        self._silenced.add(kind)
        self._arm(self._silence_timers, self._silence_gen, kind, self._end_silence)
        self._apply()

    def shutdown(self) -> None:
        self._stop_alarm()
        self._back_timer.stop()
        for timers in (self._hide_timers, self._silence_timers):
            for timer in timers.values():
                timer.stop()

    def _pick(self) -> str | None:
        for kind in _PRIORITY:
            if kind in self._active and kind not in self._hidden:
                return kind
        return None

    def _apply(self) -> None:
        if self._restored:
            return
        kind = self._pick()
        if kind is None:
            self._shown_kind = None
            self._shown_reason = ""
            self._stop_alarm()
            self.hide()
            return
        reason = self._active.get(kind, "")
        if kind != self._shown_kind or not self.isVisible() or reason != self._shown_reason:
            self._render_alert(kind, reason)
            self._shown_kind = kind
            self._shown_reason = reason
            self._show()
        if self._sound_enabled and kind not in self._silenced:
            self._start_alarm()
        else:
            self._stop_alarm()

    def _render_alert(self, kind: str, reason: str) -> None:
        self.setStyleSheet(LOST_STYLE)
        badge, eyebrow, title, detail, hint = _ALERT_TEXT[kind]
        self.badge.setText(badge)
        self.badge.setStyleSheet(BADGE_LOST)
        self._pulse_on = True
        self.eyebrow.setText(t(eyebrow))
        self.eyebrow.setStyleSheet(_eyebrow_style(False))
        self.title.setText(t(title))
        self.detail.setText(t(detail))
        shown = f"({reason})" if kind == ALERT_POWER and reason else ""
        self.reason.setText(shown)
        self.reason.setVisible(bool(shown))
        self.hide_btn.show()
        self.silence_btn.show()
        self.hint.setText(t(hint))
        self.hint.show()

    def _show_restored(self) -> None:
        self._restored = True
        self._shown_kind = None
        self._shown_reason = ""
        self._stop_alarm()
        self.setStyleSheet(BACK_STYLE)
        self.badge.setText("\u2713")
        self.badge.setStyleSheet(BADGE_OK)
        self.eyebrow.setText(t("POWER RESTORED"))
        self.eyebrow.setStyleSheet(_eyebrow_style(True))
        self.title.setText(t("Tracker is back"))
        self.detail.setText(t("Tracking resumes automatically."))
        self.reason.setVisible(False)
        self.hide_btn.hide()
        self.silence_btn.hide()
        self.hint.hide()
        self._show()
        self._back_timer.start()

    def _on_restored_done(self) -> None:
        self._restored = False
        self._apply()

    def _beat(self) -> None:
        self._play_tone()
        self._pulse_on = not self._pulse_on
        self.badge.setStyleSheet(BADGE_LOST if self._pulse_on else BADGE_LOST_DIM)

    def _play_tone(self) -> None:
        effect = self._effect
        if effect is None:
            return
        try:
            if effect.isPlaying():
                effect.stop()
            effect.play()
        except Exception:
            return

    def _start_alarm(self) -> None:
        if self._beep.isActive():
            return
        self._pulse_on = False
        self._beat()
        self._beep.start()

    def _stop_alarm(self) -> None:
        self._beep.stop()
        effect = self._effect
        if effect is not None:
            try:
                effect.stop()
            except Exception:
                return

    def _arm(self, timers: dict[str, QTimer], gens: dict[str, int], kind: str, slot) -> None:
        previous = timers.get(kind)
        if previous is not None:
            previous.stop()
        gen = gens[kind] = gens.get(kind, 0) + 1
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(max(0, int(self.snooze_ms)))
        timer.timeout.connect(partial(slot, kind, gen))
        timers[kind] = timer
        timer.start()

    def _end_hide(self, kind: str, gen: int) -> None:
        if self._hide_gen.get(kind) != gen:
            return
        self._hidden.discard(kind)
        self._hide_timers.pop(kind, None)
        if not self._restored:
            self._apply()

    def _end_silence(self, kind: str, gen: int) -> None:
        if self._silence_gen.get(kind) != gen:
            return
        self._silenced.discard(kind)
        self._silence_timers.pop(kind, None)
        if not self._restored:
            self._apply()

    def _cancel_snooze(self, kind: str) -> None:
        self._hidden.discard(kind)
        self._silenced.discard(kind)
        self._hide_gen[kind] = self._hide_gen.get(kind, 0) + 1
        self._silence_gen[kind] = self._silence_gen.get(kind, 0) + 1
        for timers in (self._hide_timers, self._silence_timers):
            timer = timers.pop(kind, None)
            if timer is not None:
                timer.stop()

    def _show(self) -> None:
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()


_ALERT_TEXT = {
    ALERT_POWER: (
        "\u23fb",
        "POWER LOST",
        "Tracker has no power",
        "Check the battery and power cable.\nThe app will reconnect by itself.",
        "Reconnects automatically",
    ),
    ALERT_SPOOF: (
        "!",
        "SPOOFING",
        "Drone position jumped",
        "The position moved 5 km or more in one second.\nAim the antenna manually until you return to AUTO.",
        "Stays until you return to AUTO.",
    ),
    ALERT_QR: (
        "QR",
        "QR READ FAILED",
        "QR code not reading",
        "No usable code is coming from the video.\nCheck the camera and the QR code.",
        "Clears when a code is read.",
    ),
}
