from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from antenna_tracker.i18n import t

# "Console" design language: near-black background, hairline dividers,
# flat sections (no chunky cards), tabular numerals for live values.
BG = "#05080e"
SURFACE = "#0a111c"
RAISED = "#0e1726"
BORDER = "#1d2b42"
HAIRLINE = "#162032"
TEXT = "#e9eff7"
MUTED = "#7f93ab"
FAINT = "#54657c"
ACCENT = "#46d9ff"
GREEN = "#3ddc84"
AMBER = "#ffb224"
RED = "#ff5d6c"
BLUE = "#5aa2ff"

VALUE_FONT = '"SF Mono", "Cascadia Mono", Menlo, Consolas, monospace'

_ASSETS = Path(__file__).resolve().parent / "assets"
_SPIN_UP = _ASSETS / "spin-up.png"
_SPIN_DOWN = _ASSETS / "spin-down.png"
_SPIN_UP_HOVER = _ASSETS / "spin-up-hover.png"
_SPIN_DOWN_HOVER = _ASSETS / "spin-down-hover.png"
_SPIN_UP_DISABLED = _ASSETS / "spin-up-disabled.png"
_SPIN_DOWN_DISABLED = _ASSETS / "spin-down-disabled.png"

def app_style(rtl: bool = False) -> str:
    cap_spacing = "0" if rtl else "2px"
    if rtl:
        spin_padding = "padding-left: 26px;"
        spin_edge = f"border-right: 1px solid {HAIRLINE};"
        spin_up_pos = "top left"
        spin_down_pos = "bottom left"
        spin_up_radius = "border-top-left-radius: 7px;"
        spin_down_radius = "border-bottom-left-radius: 7px;"
    else:
        spin_padding = "padding-right: 26px;"
        spin_edge = f"border-left: 1px solid {HAIRLINE};"
        spin_up_pos = "top right"
        spin_down_pos = "bottom right"
        spin_up_radius = "border-top-right-radius: 7px;"
        spin_down_radius = "border-bottom-right-radius: 7px;"
    return f"""
QWidget {{
    color: {TEXT};
    font-size: 13px;
}}
QMainWindow, QDialog, QWizard, QWizardPage, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG}; }}
QLabel[muted="true"] {{ color: {MUTED}; }}
QLabel[val="true"] {{
    font-family: {VALUE_FONT};
    font-size: 15px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel[cap="true"] {{
    color: {MUTED};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: {cap_spacing};
}}
QFrame[card="true"] {{
    background: {SURFACE};
    border: 1px solid {HAIRLINE};
    border-radius: 10px;
}}
QFrame[divider="true"] {{ background: {BORDER}; border: none; min-height: 1px; max-height: 1px; }}
QPushButton {{
    background: {RAISED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #142136; border: 1px solid #2c425f; }}
QPushButton:pressed {{ background: #080f1a; border: 1px solid {BORDER}; }}
QPushButton:disabled {{ color: {FAINT}; background: #0a111c; border: 1px solid {HAIRLINE}; }}
QPushButton[primary="true"] {{ color: #04121c; background: {ACCENT}; border: 1px solid {ACCENT}; }}
QPushButton[primary="true"]:hover {{ color: #04121c; background: #7ce4ff; border: 1px solid #7ce4ff; }}
QPushButton[primary="true"]:pressed {{ color: #04121c; background: #22c4ea; border: 1px solid #22c4ea; }}
QPushButton[primary="true"]:disabled {{ color: {FAINT}; background: #0a111c; border: 1px solid {HAIRLINE}; }}
QPushButton[danger="true"] {{ color: {RED}; background: {RAISED}; border: 1px solid #5c2a36; }}
QPushButton[danger="true"]:hover {{ color: {RED}; background: #1a1218; border: 1px solid #8b394b; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: #070d17;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: {ACCENT};
}}
QSpinBox, QDoubleSpinBox {{
    {spin_padding}
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: transparent;
    border: none;
    {spin_edge}
    width: 24px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: {spin_up_pos};
    {spin_up_radius}
    border-bottom: 1px solid {HAIRLINE};
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: {spin_down_pos};
    {spin_down_radius}
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: #142136;
}}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed, QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background: #1a3a52;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{_SPIN_UP}");
    width: 12px;
    height: 12px;
}}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{
    image: url("{_SPIN_UP_HOVER}");
}}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{
    image: url("{_SPIN_UP_DISABLED}");
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{_SPIN_DOWN}");
    width: 12px;
    height: 12px;
}}
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
    image: url("{_SPIN_DOWN_HOVER}");
}}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
    image: url("{_SPIN_DOWN_DISABLED}");
}}
QComboBox QAbstractItemView {{
    background: {RAISED};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: #1a3a52;
}}
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 15px; margin: -6px 0; border-radius: 7px; }}
QToolTip {{ background: {RAISED}; color: {TEXT}; border: 1px solid {BORDER}; padding: 5px; }}
QSplitter::handle {{ background: {BG}; width: 6px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #22344d; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QWizard QPushButton {{ min-width: 92px; padding: 10px 20px; }}
"""


def title(text: str, size: int = 20) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"font-size: {size}px; font-weight: 700;")
    return label


def caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("cap", True)
    return label


def muted(text: str, wrap: bool = False) -> QLabel:
    label = QLabel(text, wordWrap=wrap)
    label.setProperty("muted", True)
    return label


def divider() -> QFrame:
    line = QFrame()
    line.setProperty("divider", True)
    line.setFrameShape(QFrame.Shape.HLine)
    return line


def card(title_text: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    """Flat section: small-caps header, hairline rule, content."""
    frame = QFrame()
    frame.setProperty("card", True)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 14)
    layout.setSpacing(8)
    if title_text:
        layout.addWidget(caption(title_text))
        layout.addWidget(divider())
    return frame, layout


def kv_row(label_text: str, value_text: str = "\u2014") -> tuple[QWidget, QLabel]:
    """One telemetry row: muted label left, tabular value right. Never overlaps."""
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 2, 0, 2)
    lay.setSpacing(8)
    name = QLabel(label_text)
    name.setStyleSheet(f"font-size: 12px; color: {MUTED};")
    value = QLabel(value_text)
    value.setProperty("val", True)
    value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lay.addWidget(name)
    lay.addStretch(1)
    lay.addWidget(value)
    return row, value


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def language_combo(current: str, on_change: Callable[[str], None]) -> QComboBox:
    """Native names, so the choice is readable before the UI language matches."""
    combo = QComboBox()
    combo.addItem("עברית", "he")
    combo.addItem("English", "en")
    code = "en" if current == "en" else "he"
    combo.blockSignals(True)
    combo.setCurrentIndex(max(combo.findData(code), 0))
    combo.blockSignals(False)
    combo.currentIndexChanged.connect(lambda _index: on_change(str(combo.currentData())))
    return combo


def language_row(current: str, on_change: Callable[[str], None]) -> QWidget:
    host = QWidget()
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    label = QLabel(t("Language"))
    combo = language_combo(current, on_change)
    combo.setMinimumWidth(140)
    row.addWidget(label)
    row.addWidget(combo)
    row.addStretch(1)
    return host
