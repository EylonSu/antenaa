from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QWidget

_LOGO = Path(__file__).resolve().parent / "assets" / "section-636.jpg"
_LOGO_HEIGHT = 68
_MARGIN = 12
_WHITE_KEY = 245


@lru_cache(maxsize=4)
def _logo_pixmap(scaled_height: int) -> QPixmap:
    src = QPixmap(str(_LOGO))
    if src.isNull():
        return src
    img = src.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            r, g, b = c.red(), c.green(), c.blue()
            if r >= _WHITE_KEY and g >= _WHITE_KEY and b >= _WHITE_KEY:
                c.setAlpha(0)
            elif r >= _WHITE_KEY - 18 and g >= _WHITE_KEY - 18 and b >= _WHITE_KEY - 18:
                fringe = min(r, g, b) - (_WHITE_KEY - 18)
                c.setAlpha(max(0, min(255, fringe * 14)))
            img.setPixelColor(x, y, c)
    return QPixmap.fromImage(img).scaledToHeight(
        scaled_height, Qt.TransformationMode.SmoothTransformation,
    )


class _TopCenterAnchor(QObject):
    def __init__(self, host: QWidget, mark: QLabel) -> None:
        super().__init__(mark)
        self._host = host
        self._mark = mark

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._host and event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.LayoutRequest):
            self._place()
        return False

    def _place(self) -> None:
        host = self._host
        mark = self._mark
        w = mark.width()
        x = max(0, (host.width() - w) // 2)
        mark.move(x, _MARGIN)
        mark.raise_()


def attach_section_logo(host: QWidget) -> QLabel:
    """Section mark centered at the top, stacked above sibling layout content."""
    mark = QLabel(host)
    mark.setObjectName("SectionLogo")
    pixmap = _logo_pixmap(_LOGO_HEIGHT)
    if not pixmap.isNull():
        mark.setPixmap(pixmap)
    mark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    mark.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    mark.setStyleSheet("background: transparent; border: none;")
    mark.adjustSize()
    anchor = _TopCenterAnchor(host, mark)
    host.installEventFilter(anchor)
    setattr(host, "_section_logo_anchor", anchor)
    mark.show()
    anchor._place()
    return mark
