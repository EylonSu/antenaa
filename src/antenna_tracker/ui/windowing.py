"""Shared desktop-window behavior for setup and the tracking screen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

# QWidget's default maximum. QWizard lowers its own, which blocks zoom on a large display.
_WIDGET_SIZE_MAX = 16777215

# Same starting size for both screens, clamped so a smaller desktop still fits.
_DEFAULT_WIDTH = 1500
_DEFAULT_HEIGHT = 940

# Matches a QMainWindow: title bar with minimize, zoom, and close.
# QWizard is a QDialog, which omits the zoom button on macOS and Windows.
_STANDARD_FLAGS = (
    Qt.WindowType.Window
    | Qt.WindowType.WindowTitleHint
    | Qt.WindowType.WindowSystemMenuHint
    | Qt.WindowType.WindowMinimizeButtonHint
    | Qt.WindowType.WindowMaximizeButtonHint
    | Qt.WindowType.WindowCloseButtonHint
    | Qt.WindowType.WindowFullscreenButtonHint
)


def default_window_size(widget: QWidget) -> tuple[int, int]:
    screen = widget.screen()
    if screen is None:
        return _DEFAULT_WIDTH, _DEFAULT_HEIGHT
    area = screen.availableGeometry()
    return min(_DEFAULT_WIDTH, area.width()), min(_DEFAULT_HEIGHT, max(0, area.height() - 30))


def prepare_desktop_window(widget: QWidget) -> None:
    """Give a dialog-style window the same chrome and size as the main screen."""
    widget.setWindowFlags(_STANDARD_FLAGS)
    widget.setMaximumSize(_WIDGET_SIZE_MAX, _WIDGET_SIZE_MAX)
    width, height = default_window_size(widget)
    widget.resize(width, height)


def show_matching(widget: QWidget, source: QWidget | None) -> None:
    """Show `widget` at `source`'s size, position, and maximized or fullscreen state."""
    if source is None:
        widget.show()
        widget.raise_()
        widget.activateWindow()
        return
    maximized = source.isMaximized()
    fullscreen = source.isFullScreen()
    # pos() is the window frame. geometry() is the client area, so copying it
    # shifts the next window by the difference in title-bar height.
    top_left = source.pos()
    size = source.size()
    normal = source.normalGeometry() if maximized or fullscreen else None
    source.hide()
    widget.show()
    if normal is not None and normal.isValid() and not normal.isEmpty():
        widget.setGeometry(normal)
    if fullscreen:
        widget.showFullScreen()
    elif maximized:
        widget.showMaximized()
    else:
        widget.resize(size)
        widget.move(top_left)
    widget.raise_()
    widget.activateWindow()
