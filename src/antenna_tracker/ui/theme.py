from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

BG = "#08111f"
SURFACE = "#0f1b2d"
SURFACE_2 = "#16243a"
BORDER = "#263751"
TEXT = "#f1f5f9"
MUTED = "#8fa3bd"
ACCENT = "#35bdf5"
GREEN = "#35d07f"
AMBER = "#f5b942"
RED = "#ff5d6c"
BLUE = "#4ea1ff"

APP_STYLE = f"""
QWidget {{
    color: {TEXT};
    font-size: 14px;
}}
QMainWindow, QDialog, QWizard, QWizardPage {{ background: {BG}; }}
QLabel[muted="true"] {{ color: {MUTED}; }}
QFrame[card="true"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QPushButton {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #1d304b; border-color: #3b526f; }}
QPushButton:pressed {{ background: #0b1626; }}
QPushButton:disabled {{ color: #52657d; background: #101a29; border-color: #1b293c; }}
QPushButton[primary="true"] {{ color: #04121c; background: {ACCENT}; border-color: {ACCENT}; }}
QPushButton[primary="true"]:hover {{ background: #6bd0f8; }}
QPushButton[danger="true"] {{ color: {RED}; border-color: #6d3240; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: #0a1525;
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 8px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: #244461;
}}
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QSlider::groove:horizontal {{ height: 5px; background: {BORDER}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; margin: -6px 0; border-radius: 8px; }}
QToolTip {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 5px; }}
QSplitter::handle {{ background: {BG}; width: 6px; }}
QWizard QPushButton {{ min-width: 92px; padding: 10px 20px; }}
"""


def title(text: str, size: int = 20) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"font-size: {size}px; font-weight: 700;")
    return label


def muted(text: str, wrap: bool = False) -> QLabel:
    label = QLabel(text, wordWrap=wrap)
    label.setProperty("muted", True)
    return label


def card(title_text: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("card", True)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    if title_text:
        layout.addWidget(title(title_text, 13))
    return frame, layout


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
