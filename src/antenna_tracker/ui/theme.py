from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from antenna_tracker.i18n import is_rtl, t

VALUE_FONT = '"SF Mono", "Cascadia Mono", Menlo, Consolas, monospace'

_ASSETS = Path(__file__).resolve().parent / "assets"
_SPIN_UP = _ASSETS / "spin-up.png"
_SPIN_DOWN = _ASSETS / "spin-down.png"
_SPIN_UP_HOVER = _ASSETS / "spin-up-hover.png"
_SPIN_DOWN_HOVER = _ASSETS / "spin-down-hover.png"
_SPIN_UP_DISABLED = _ASSETS / "spin-up-disabled.png"
_SPIN_DOWN_DISABLED = _ASSETS / "spin-down-disabled.png"


@dataclass(frozen=True)
class ThemePalette:
    name: str
    bg: str
    surface: str
    raised: str
    border: str
    hairline: str
    text: str
    muted: str
    faint: str
    accent: str
    accent_hover: str
    accent_pressed: str
    green: str
    amber: str
    red: str
    blue: str
    input_bg: str
    btn_hover: str
    btn_hover_border: str
    btn_pressed: str
    btn_disabled_bg: str
    danger_hover_bg: str
    danger_hover_border: str
    selection_bg: str
    spin_hover: str
    spin_pressed: str
    scrollbar: str
    primary_label: str
    mode_btn_bg: str
    sim_bar_bg: str
    body_secondary: str
    instruction: str
    overlay_lost: str
    overlay_back: str
    alert_card_bg: str
    alert_card_border: str
    alert_btn_border: str
    alert_btn_hover_bg: str
    alert_btn_pressed_bg: str
    alert_title: str
    alert_detail: str
    alert_hint: str
    gps_warn_bg: str
    gps_warn_fg: str
    gps_warn_border: str
    gps_ok_bg: str
    gps_ok_fg: str
    gps_ok_border: str
    qr_ok_fg: str
    qr_bad_fg: str
    qr_bad_bg: str
    qr_bad_border: str


_LIGHT = ThemePalette(
    name="light",
    bg="#eef2f7",
    surface="#ffffff",
    raised="#f4f7fb",
    border="#c5d0de",
    hairline="#dce3ed",
    text="#0c1524",
    muted="#5c7089",
    faint="#8a9bb0",
    accent="#0093b8",
    accent_hover="#00b4e0",
    accent_pressed="#007a99",
    green="#1a9d57",
    amber="#c77700",
    red="#d63b4a",
    blue="#2563eb",
    input_bg="#ffffff",
    btn_hover="#e3eaf3",
    btn_hover_border="#aebdcf",
    btn_pressed="#d5dfea",
    btn_disabled_bg="#f4f7fb",
    danger_hover_bg="#fde8eb",
    danger_hover_border="#e08a96",
    selection_bg="#cfe9f3",
    spin_hover="#e3eaf3",
    spin_pressed="#cfe9f3",
    scrollbar="#c5d0de",
    primary_label="#04121c",
    mode_btn_bg="#eef2f7",
    sim_bar_bg="#f4f7fb",
    body_secondary="#3d5168",
    instruction="#334155",
    overlay_lost="rgba(248, 250, 252, 228)",
    overlay_back="rgba(236, 253, 245, 220)",
    alert_card_bg="#ffffff",
    alert_card_border="#c5d0de",
    alert_btn_border="#94a3b8",
    alert_btn_hover_bg="#eef2f7",
    alert_btn_pressed_bg="#e2e8f0",
    alert_title="#0f172a",
    alert_detail="#475569",
    alert_hint="#64748b",
    gps_warn_bg="#fef3c7",
    gps_warn_fg="#92400e",
    gps_warn_border="#f59e0b",
    gps_ok_bg="#ecfdf5",
    gps_ok_fg="#047857",
    gps_ok_border="#34d399",
    qr_ok_fg="#047857",
    qr_bad_fg="#be123c",
    qr_bad_bg="#fff1f2",
    qr_bad_border="#fda4af",
)

_DARK = ThemePalette(
    name="dark",
    bg="#05080e",
    surface="#0a111c",
    raised="#0e1726",
    border="#1d2b42",
    hairline="#162032",
    text="#e9eff7",
    muted="#7f93ab",
    faint="#54657c",
    accent="#46d9ff",
    accent_hover="#7ce4ff",
    accent_pressed="#22c4ea",
    green="#3ddc84",
    amber="#ffb224",
    red="#ff5d6c",
    blue="#5aa2ff",
    input_bg="#070d17",
    btn_hover="#142136",
    btn_hover_border="#2c425f",
    btn_pressed="#080f1a",
    btn_disabled_bg="#0a111c",
    danger_hover_bg="#1a1218",
    danger_hover_border="#8b394b",
    selection_bg="#1a3a52",
    spin_hover="#142136",
    spin_pressed="#1a3a52",
    scrollbar="#22344d",
    primary_label="#04121c",
    mode_btn_bg="#0e1726",
    sim_bar_bg="#070d17",
    body_secondary="#c9d5e5",
    instruction="#c9d5e5",
    overlay_lost="rgba(10, 7, 13, 218)",
    overlay_back="rgba(5, 15, 12, 195)",
    alert_card_bg="#101b2e",
    alert_card_border="#2b3a52",
    alert_btn_border="#5b6b84",
    alert_btn_hover_bg="#142136",
    alert_btn_pressed_bg="#0b1626",
    alert_title="#f1f5f9",
    alert_detail="#aebdcc",
    alert_hint="#6d7f94",
    gps_warn_bg="#4a3410",
    gps_warn_fg="#ffd57b",
    gps_warn_border="#8d6724",
    gps_ok_bg="#123c2b",
    gps_ok_fg="#7ce8ad",
    gps_ok_border="#286b4d",
    qr_ok_fg="#6ee7a4",
    qr_bad_fg="#ff9daa",
    qr_bad_bg="#4b1f2a",
    qr_bad_border="#8b394b",
)

_ACTIVE = _LIGHT

# Semantic exports — updated by ``set_ui_theme``.
BG = _ACTIVE.bg
SURFACE = _ACTIVE.surface
RAISED = _ACTIVE.raised
BORDER = _ACTIVE.border
HAIRLINE = _ACTIVE.hairline
TEXT = _ACTIVE.text
MUTED = _ACTIVE.muted
FAINT = _ACTIVE.faint
ACCENT = _ACTIVE.accent
GREEN = _ACTIVE.green
AMBER = _ACTIVE.amber
RED = _ACTIVE.red
BLUE = _ACTIVE.blue


def normalized_ui_theme(code: str | None) -> str:
    return "dark" if code == "dark" else "light"


def ui_theme() -> str:
    return _ACTIVE.name


def is_dark_theme() -> bool:
    return _ACTIVE.name == "dark"


def active_palette() -> ThemePalette:
    return _ACTIVE


def set_ui_theme(code: str | None) -> str:
    """Switch palette tokens and module-level color exports."""
    global _ACTIVE, BG, SURFACE, RAISED, BORDER, HAIRLINE, TEXT, MUTED, FAINT
    global ACCENT, GREEN, AMBER, RED, BLUE
    name = normalized_ui_theme(code)
    _ACTIVE = _DARK if name == "dark" else _LIGHT
    BG = _ACTIVE.bg
    SURFACE = _ACTIVE.surface
    RAISED = _ACTIVE.raised
    BORDER = _ACTIVE.border
    HAIRLINE = _ACTIVE.hairline
    TEXT = _ACTIVE.text
    MUTED = _ACTIVE.muted
    FAINT = _ACTIVE.faint
    ACCENT = _ACTIVE.accent
    GREEN = _ACTIVE.green
    AMBER = _ACTIVE.amber
    RED = _ACTIVE.red
    BLUE = _ACTIVE.blue
    return name


def apply_app_stylesheet(app: QApplication | None = None, *, rtl: bool | None = None) -> None:
    qapp = app or QApplication.instance()
    if qapp is None:
        return
    direction = is_rtl() if rtl is None else rtl
    qapp.setStyleSheet(app_style(direction))


def app_style(rtl: bool = False) -> str:
    p = _ACTIVE
    cap_spacing = "0" if rtl else "2px"
    if rtl:
        spin_padding = "padding-left: 26px;"
        spin_edge = f"border-right: 1px solid {p.hairline};"
        spin_up_pos = "top left"
        spin_down_pos = "bottom left"
        spin_up_radius = "border-top-left-radius: 7px;"
        spin_down_radius = "border-bottom-left-radius: 7px;"
    else:
        spin_padding = "padding-right: 26px;"
        spin_edge = f"border-left: 1px solid {p.hairline};"
        spin_up_pos = "top right"
        spin_down_pos = "bottom right"
        spin_up_radius = "border-top-right-radius: 7px;"
        spin_down_radius = "border-bottom-right-radius: 7px;"
    return f"""
QWidget {{
    color: {p.text};
    font-size: 13px;
}}
QMainWindow, QDialog, QWizard, QWizardPage, QScrollArea, QScrollArea > QWidget > QWidget {{ background: {p.bg}; }}
QLabel[muted="true"] {{ color: {p.muted}; }}
QLabel[val="true"] {{
    font-family: {VALUE_FONT};
    font-size: 15px;
    font-weight: 700;
    color: {p.text};
}}
QLabel[cap="true"] {{
    color: {p.muted};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: {cap_spacing};
}}
QFrame[card="true"] {{
    background: {p.surface};
    border: 1px solid {p.hairline};
    border-radius: 10px;
}}
QFrame[divider="true"] {{ background: {p.border}; border: none; min-height: 1px; max-height: 1px; }}
QPushButton {{
    background: {p.raised};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {p.btn_hover}; border: 1px solid {p.btn_hover_border}; }}
QPushButton:pressed {{ background: {p.btn_pressed}; border: 1px solid {p.border}; }}
QPushButton:disabled {{ color: {p.faint}; background: {p.btn_disabled_bg}; border: 1px solid {p.hairline}; }}
QPushButton[primary="true"] {{ color: {p.primary_label}; background: {p.accent}; border: 1px solid {p.accent}; }}
QPushButton[primary="true"]:hover {{ color: {p.primary_label}; background: {p.accent_hover}; border: 1px solid {p.accent_hover}; }}
QPushButton[primary="true"]:pressed {{ color: {p.primary_label}; background: {p.accent_pressed}; border: 1px solid {p.accent_pressed}; }}
QPushButton[primary="true"]:disabled {{ color: {p.faint}; background: {p.btn_disabled_bg}; border: 1px solid {p.hairline}; }}
QPushButton[danger="true"] {{ color: {p.red}; background: {p.raised}; border: 1px solid #5c2a36; }}
QPushButton[danger="true"]:hover {{ color: {p.red}; background: {p.danger_hover_bg}; border: 1px solid {p.danger_hover_border}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {p.input_bg};
    border: 1px solid {p.border};
    border-radius: 8px;
    padding: 8px 10px;
}}
QLineEdit, QSpinBox, QDoubleSpinBox {{
    selection-background-color: {p.accent};
    selection-color: {p.primary_label};
}}
QComboBox {{
    color: {p.text};
    selection-background-color: {p.selection_bg};
    selection-color: {p.text};
    combobox-popup: 0;
}}
QSpinBox, QDoubleSpinBox {{
    {spin_padding}
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {p.accent};
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
    border-bottom: 1px solid {p.hairline};
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: {spin_down_pos};
    {spin_down_radius}
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {p.spin_hover};
}}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed, QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    background: {p.spin_pressed};
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
    background: {p.raised};
    color: {p.text};
    border: 1px solid {p.border};
    selection-background-color: {p.selection_bg};
    selection-color: {p.text};
    outline: 0;
}}
QComboBox QAbstractItemView::item:selected {{
    background: {p.selection_bg};
    color: {p.text};
}}
QCheckBox {{ spacing: 9px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; }}
QSlider::groove:horizontal {{ height: 4px; background: {p.border}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {p.accent}; width: 15px; margin: -6px 0; border-radius: 7px; }}
QToolTip {{ background: {p.raised}; color: {p.text}; border: 1px solid {p.border}; padding: 5px; }}
QSplitter::handle {{ background: {p.bg}; width: 6px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p.scrollbar}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QWizard QPushButton {{ min-width: 92px; padding: 10px 20px; }}
"""


def wizard_stylesheet() -> str:
    p = _ACTIVE
    return f"""
            QWizard {{ background: {p.bg}; border: none; }}
            QWizardPage {{ background: {p.bg}; border: none; }}
            QLabel#qt_wizard_title {{
                color: {p.text}; font-size: 22px; font-weight: 800; background: transparent; border: none;
            }}
            QLabel#qt_wizard_subtitle {{
                color: {p.muted}; font-size: 14px; background: transparent; border: none;
            }}
            QWizard QFrame {{ border: none; }}
            QWizard QPushButton {{ min-width: 100px; padding: 10px 22px; }}
        """


def reference_toggle_style() -> str:
    p = _ACTIVE
    return (
        f"QPushButton {{ font-weight: 700; color: {p.muted}; background: {p.raised}; "
        f"border: 1px solid {p.border}; border-radius: 8px; }}"
        f"QPushButton:hover {{ color: {p.text}; background: {p.btn_hover}; border: 1px solid {p.btn_hover_border}; }}"
        f"QPushButton:checked {{ color: {p.primary_label}; background: {p.accent}; border: 1px solid {p.accent}; }}"
        f"QPushButton:checked:hover {{ color: {p.primary_label}; background: {p.accent_hover}; "
        f"border: 1px solid {p.accent_hover}; }}"
    )


def gps_banner_styles() -> tuple[str, str]:
    p = _ACTIVE
    no_gps = (
        f"background: {p.gps_warn_bg}; color: {p.gps_warn_fg}; "
        f"border: 1px solid {p.gps_warn_border}; border-radius: 8px;"
    )
    back = (
        f"background: {p.gps_ok_bg}; color: {p.gps_ok_fg}; "
        f"border: 1px solid {p.gps_ok_border}; border-radius: 8px;"
    )
    return no_gps, back


def qr_indicator_styles() -> tuple[str, str]:
    p = _ACTIVE
    ok = (
        f"font-size: 11px; font-weight: 800; color: {p.qr_ok_fg}; background: {p.gps_ok_bg}; "
        f"padding: 4px 8px; border: 1px solid {p.gps_ok_border}; border-radius: 9px;"
    )
    bad = (
        f"font-size: 11px; font-weight: 800; color: {p.qr_bad_fg}; background: {p.qr_bad_bg}; "
        f"padding: 4px 8px; border: 1px solid {p.qr_bad_border}; border-radius: 9px;"
    )
    return ok, bad


def mode_button_style(color: str) -> str:
    p = _ACTIVE
    return (
        f"QPushButton {{ font-size: 13px; font-weight: 800; border: 1px solid {p.border}; "
        f"background: {p.mode_btn_bg}; color: {p.muted}; border-radius: 8px; }}"
        f"QPushButton:checked {{ background: {color}; color: {p.primary_label}; border: 1px solid {color}; }}"
        f"QPushButton:checked:hover {{ background: {color}; color: {p.primary_label}; border: 1px solid {color}; }}"
    )


def settings_gear_style() -> str:
    return "font-size: 24px; padding: 0;"


def sim_bar_style() -> str:
    p = _ACTIVE
    return f"QWidget#simBar {{ background: {p.sim_bar_bg}; border-top: 1px solid {p.border}; }}"


def side_rail_style(*, rtl: bool) -> str:
    p = _ACTIVE
    rail_edge = "border-right" if rtl else "border-left"
    return f"""
            QWidget#sideRail {{
                background: {p.surface};
                {rail_edge}: 1px solid {p.border};
            }}
            QWidget#sideRail QScrollArea,
            QWidget#sideRail QScrollArea > QWidget,
            QWidget#sideRail QScrollArea > QWidget > QWidget {{
                background: {p.surface};
                border: none;
            }}
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


def theme_combo(current: str, on_change: Callable[[str], None]) -> QComboBox:
    combo = QComboBox()
    combo.addItem(t("Light"), "light")
    combo.addItem(t("Dark"), "dark")
    code = normalized_ui_theme(current)
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


def theme_row(current: str, on_change: Callable[[str], None]) -> QWidget:
    host = QWidget()
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(8)
    label = QLabel(t("Appearance"))
    combo = theme_combo(current, on_change)
    combo.setMinimumWidth(140)
    row.addWidget(label)
    row.addWidget(combo)
    row.addStretch(1)
    return host
