from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from antenna_tracker.ui.theme import active_palette


@dataclass(frozen=True)
class _GaugeColors:
    rec: QColor
    act: QColor
    text: QColor
    muted: QColor
    ring: QColor
    grid: QColor
    face: QColor
    hub: QColor
    north: QColor


def _colors() -> _GaugeColors:
    p = active_palette()
    return _GaugeColors(
        rec=QColor(p.blue),
        act=QColor(p.green),
        text=QColor(p.text),
        muted=QColor(p.muted),
        ring=QColor(p.border),
        grid=QColor(p.hairline),
        face=QColor(p.input_bg if p.name == "dark" else p.raised),
        hub=QColor(p.scrollbar),
        north=QColor(p.red),
    )


class _Gauge(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.recommended: float | None = None
        self.actual: float | None = None
        self.setMinimumSize(190, 190)

    def set_values(self, recommended: float | None, actual: float | None) -> None:
        self.recommended, self.actual = recommended, actual
        self.update()

    @staticmethod
    def _fmt(v: float | None) -> str:
        return "--" if v is None else f"{v:.0f}\u00b0"

    def _needle(self, p: QPainter, c: QPointF, length: float, screen_deg: float,
                color: QColor, dashed: bool, width: int = 5) -> None:
        pen = QPen(color, width if not dashed else width - 1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        r = math.radians(screen_deg)
        p.drawLine(c, QPointF(c.x() + length * math.cos(r), c.y() - length * math.sin(r)))

    def _hub(self, p: QPainter, c: QPointF, colors: _GaugeColors) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(colors.hub)
        p.drawEllipse(c, 5, 5)


class CompassGauge(_Gauge):
    """Azimuth: 0 = north at the top, clockwise."""

    def __init__(self, parent=None) -> None:
        super().__init__("Direction (azimuth)", parent)

    def paintEvent(self, _event) -> None:
        colors = _colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        size = min(rect.width(), rect.height())
        c = QPointF(rect.center().x(), rect.center().y())
        rad = size / 2
        p.setPen(QPen(colors.ring, 2))
        p.setBrush(colors.face)
        p.drawEllipse(c, rad, rad)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(colors.grid, 1))
        for fraction in (0.33, 0.66):
            p.drawEllipse(c, rad * fraction, rad * fraction)
        for deg in range(0, 360, 15):
            r = math.radians(deg)
            inner = rad - (12 if deg % 90 == 0 else 6)
            p.drawLine(QPointF(c.x() + inner * math.cos(r), c.y() - inner * math.sin(r)),
                       QPointF(c.x() + (rad - 3) * math.cos(r), c.y() - (rad - 3) * math.sin(r)))
        p.setFont(QFont(self.font().family(), 13, QFont.Weight.Bold))
        for label, deg in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
            r = math.radians(90 - deg)
            pt = QPointF(c.x() + (rad - 26) * math.cos(r), c.y() - (rad - 26) * math.sin(r))
            p.setPen(colors.north if label == "N" else colors.text)
            p.drawText(QRectF(pt.x() - 11, pt.y() - 11, 22, 22), Qt.AlignmentFlag.AlignCenter, label)
        if self.recommended is not None:
            self._needle(p, c, rad - 34, 90 - self.recommended, colors.rec, True)
        if self.actual is not None:
            self._needle(p, c, rad - 38, 90 - self.actual, colors.act, False)
        self._hub(p, c, colors)


class ElevationGauge(_Gauge):
    """Elevation arc from -30 (down) to +90 (straight up); 0 is level, pointing right."""

    LO, HI = -30.0, 90.0

    def __init__(self, parent=None) -> None:
        super().__init__("Height angle (elevation)", parent)

    def paintEvent(self, _event) -> None:
        colors = _colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        rad = min(rect.width() * 0.72, rect.height() - 14)
        c = QPointF(rect.left() + rect.width() * 0.22, rect.bottom() - 8 - rad * 0.12)
        p.setPen(QPen(colors.ring, 2))
        p.setBrush(colors.face)
        arc = QRectF(c.x() - rad, c.y() - rad, 2 * rad, 2 * rad)
        p.drawPie(arc, int(self.LO * 16), int((self.HI - self.LO) * 16))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(colors.grid, 1))
        for fraction in (0.33, 0.66):
            inner = QRectF(c.x() - rad * fraction, c.y() - rad * fraction,
                           2 * rad * fraction, 2 * rad * fraction)
            p.drawArc(inner, int(self.LO * 16), int((self.HI - self.LO) * 16))
        for deg in range(int(self.LO), int(self.HI) + 1, 15):
            r = math.radians(deg)
            p.drawLine(QPointF(c.x() + (rad - 10) * math.cos(r), c.y() - (rad - 10) * math.sin(r)),
                       QPointF(c.x() + (rad - 3) * math.cos(r), c.y() - (rad - 3) * math.sin(r)))
        p.setPen(QPen(colors.ring, 1, Qt.PenStyle.DotLine))
        p.drawLine(c, QPointF(c.x() + rad, c.y()))
        p.setFont(QFont(self.font().family(), 10))
        p.setPen(colors.muted)
        for deg in (-30, 0, 30, 60, 90):
            r = math.radians(deg)
            pt = QPointF(c.x() + (rad + 12) * math.cos(r), c.y() - (rad + 12) * math.sin(r))
            p.drawText(QRectF(pt.x() - 16, pt.y() - 8, 32, 16), Qt.AlignmentFlag.AlignCenter, str(deg))
        if self.recommended is not None:
            self._needle(p, c, rad - 10, max(self.LO, min(self.HI, self.recommended)), colors.rec, True)
        if self.actual is not None:
            self._needle(p, c, rad - 14, max(self.LO, min(self.HI, self.actual)), colors.act, False)
        self._hub(p, c, colors)
