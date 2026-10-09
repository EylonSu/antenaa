from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

REC_COLOR = QColor("#4ea1ff")
ACT_COLOR = QColor("#35d07f")
TEXT_COLOR = QColor("#e8eef7")
MUTED_COLOR = QColor("#8296b0")
RING_COLOR = QColor("#33445d")
FACE_COLOR = QColor("#0a1525")


class _Gauge(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.recommended: float | None = None
        self.actual: float | None = None
        self.setMinimumSize(175, 175)

    def set_values(self, recommended: float | None, actual: float | None) -> None:
        self.recommended, self.actual = recommended, actual
        self.update()

    @staticmethod
    def _fmt(v: float | None) -> str:
        return "--" if v is None else f"{v:.0f}\u00b0"

    def _needle(self, p: QPainter, c: QPointF, length: float, screen_deg: float,
                color: QColor, dashed: bool) -> None:
        pen = QPen(color, 5 if not dashed else 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        r = math.radians(screen_deg)
        p.drawLine(c, QPointF(c.x() + length * math.cos(r), c.y() - length * math.sin(r)))

    def _legend(self, p: QPainter, rect: QRectF) -> None:
        p.setFont(QFont(self.font().family(), 11, QFont.Weight.Bold))
        p.setPen(MUTED_COLOR)
        p.drawText(rect.adjusted(0, 0, 0, -rect.height() + 22), Qt.AlignmentFlag.AlignHCenter, self.title)
        p.setFont(QFont(self.font().family(), 10, QFont.Weight.DemiBold))
        bottom = QRectF(rect.left(), rect.bottom() - 22, rect.width(), 22)
        p.setPen(REC_COLOR)
        p.drawText(bottom, Qt.AlignmentFlag.AlignLeft, f"Target {self._fmt(self.recommended)}")
        p.setPen(ACT_COLOR)
        p.drawText(bottom, Qt.AlignmentFlag.AlignRight, f"Antenna {self._fmt(self.actual)}")


class CompassGauge(_Gauge):
    """Azimuth: 0 = north at the top, clockwise."""

    def __init__(self, parent=None) -> None:
        super().__init__("Direction (azimuth)", parent)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        size = min(rect.width(), rect.height() - 50)
        c = QPointF(rect.center().x(), rect.top() + 25 + size / 2)
        rad = size / 2
        p.setPen(QPen(RING_COLOR, 2))
        p.setBrush(FACE_COLOR)
        p.drawEllipse(c, rad, rad)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#223650"), 1))
        for fraction in (0.25, 0.5, 0.75):
            p.drawEllipse(c, rad * fraction, rad * fraction)
        for deg in range(0, 360, 30):
            r = math.radians(deg)
            p.drawLine(c, QPointF(c.x() + rad * math.cos(r), c.y() - rad * math.sin(r)))
        p.setFont(QFont(self.font().family(), 12, QFont.Weight.Bold))
        for label, deg in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            r = math.radians(90 - deg)
            pt = QPointF(c.x() + (rad - 14) * math.cos(r), c.y() - (rad - 14) * math.sin(r))
            p.setPen(QColor("#ff6b78") if label == "N" else TEXT_COLOR)
            p.drawText(QRectF(pt.x() - 10, pt.y() - 10, 20, 20), Qt.AlignmentFlag.AlignCenter, label)
        if self.recommended is not None:
            self._needle(p, c, rad - 26, 90 - self.recommended, REC_COLOR, True)
        if self.actual is not None:
            self._needle(p, c, rad - 30, 90 - self.actual, ACT_COLOR, False)
        self._legend(p, rect)


class ElevationGauge(_Gauge):
    """Elevation arc from -30 (down) to +90 (straight up); 0 is level, pointing right."""

    LO, HI = -30.0, 90.0

    def __init__(self, parent=None) -> None:
        super().__init__("Height angle (elevation)", parent)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        rad = min(rect.width() * 0.75, rect.height() - 60)
        c = QPointF(rect.left() + rect.width() * 0.2, rect.top() + 30 + rad * 0.85)
        p.setPen(QPen(RING_COLOR, 2))
        p.setBrush(FACE_COLOR)
        arc = QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad)
        p.drawPie(arc, int(self.LO * 16), int((self.HI - self.LO) * 16))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor("#223650"), 1))
        for fraction in (0.25, 0.5, 0.75):
            inner = QRectF(c.x() - rad * fraction, c.y() - rad * fraction,
                           2 * rad * fraction, 2 * rad * fraction)
            p.drawArc(inner, int(self.LO * 16), int((self.HI - self.LO) * 16))
        for deg in range(-30, 91, 15):
            r = math.radians(deg)
            p.drawLine(c, QPointF(c.x() + rad * math.cos(r), c.y() - rad * math.sin(r)))
        p.setPen(QPen(RING_COLOR, 1, Qt.PenStyle.DotLine))
        p.drawLine(c, QPointF(c.x() + rad, c.y()))
        p.setFont(QFont(self.font().family(), 10))
        p.setPen(MUTED_COLOR)
        for deg in (-30, 0, 30, 60, 90):
            r = math.radians(deg)
            pt = QPointF(c.x() + (rad + 12) * math.cos(r), c.y() - (rad + 12) * math.sin(r))
            p.drawText(QRectF(pt.x() - 16, pt.y() - 8, 32, 16), Qt.AlignmentFlag.AlignCenter, str(deg))
        if self.recommended is not None:
            self._needle(p, c, rad - 8, max(self.LO, min(self.HI, self.recommended)), REC_COLOR, True)
        if self.actual is not None:
            self._needle(p, c, rad - 12, max(self.LO, min(self.HI, self.actual)), ACT_COLOR, False)
        self._legend(p, rect)
