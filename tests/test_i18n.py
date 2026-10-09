"""Hebrew catalog and right-to-left layout. Module language stays English unless a test opts in."""

import ast
import re
from pathlib import Path

import pytest

from antenna_tracker.i18n import hebrew_translations, is_rtl, set_language, t

_HEBREW = re.compile(r"[\u0590-\u05FF]")
# Units, compass marks, and pure acronyms may be a whole catalog value with no Hebrew letters.
_ALLOW = {"m", "km", "°", "N", "E", "S", "W", "QR", "GPS", "USB", "GET"}
_SRC = Path(__file__).resolve().parents[1] / "src"


def test_hebrew_catalog_values_are_hebrew() -> None:
    catalog = hebrew_translations()
    assert catalog
    for source, hebrew in catalog.items():
        assert hebrew.strip(), source
        if hebrew.strip() in _ALLOW:
            continue
        assert _HEBREW.search(hebrew), source


def test_t_calls_and_status_pills_are_in_the_catalog() -> None:
    catalog = hebrew_translations()
    missing: list[str] = []
    for path in _SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "t":
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            key = node.args[0].value
            if isinstance(key, str) and key not in catalog:
                missing.append(f"{path.name}:{node.lineno}: {key}")
    assert missing == []
    from antenna_tracker.ui.main_window import PILL
    from antenna_tracker.ui.wizard.alignment_page import INSTRUCTIONS

    assert INSTRUCTIONS in catalog
    for text, _color in PILL.values():
        assert text in catalog
    assert "easting" in catalog and "northing" in catalog


def test_unknown_language_is_hebrew_and_missing_keys_stay_english() -> None:
    set_language("zz")
    try:
        assert is_rtl()
        assert t("Antenna Tracker") == "עוקב אנטנה"
        assert t("not a catalog key") == "not a catalog key"
    finally:
        set_language("en")
        assert not is_rtl()
        assert t("Antenna Tracker") == "Antenna Tracker"


def test_hebrew_label_and_rtl_direction(qapp) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel

    assert isinstance(qapp, QApplication)
    set_language("he")
    try:
        qapp.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight)
        label = QLabel(t("Antenna Tracker"))
        assert label.text() == "עוקב אנטנה"
        assert _HEBREW.search(label.text())
        assert qapp.layoutDirection() == Qt.LayoutDirection.RightToLeft
    finally:
        set_language("en")
        qapp.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        assert t("Antenna Tracker") == "Antenna Tracker"
        assert qapp.layoutDirection() == Qt.LayoutDirection.LeftToRight


def test_rtl_stylesheet_moves_spin_buttons() -> None:
    from antenna_tracker.ui.theme import app_style

    english = app_style(False)
    hebrew = app_style(True)
    assert "padding-right: 26px;" in english
    assert "subcontrol-position: top right;" in english
    assert "subcontrol-position: bottom right;" in english
    assert "letter-spacing: 2px;" in english
    assert "padding-left: 26px;" in hebrew
    assert "subcontrol-position: top left;" in hebrew
    assert "subcontrol-position: bottom left;" in hebrew
    assert "border-right: 1px solid" in hebrew
    assert "letter-spacing: 0;" in hebrew
    assert "padding-right: 26px;" not in hebrew


def test_relaunch_command_frozen_and_module(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    from antenna_tracker.app import relaunch_command

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/app/AntennaTracker")
    monkeypatch.setattr(sys, "argv", ["/app/AntennaTracker", "--demo"])
    assert relaunch_command() == ("/app/AntennaTracker", ["--demo"])

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    monkeypatch.setattr(sys, "argv", ["/tmp/antenna_tracker/__main__.py", "--dev"])
    assert relaunch_command() == ("/usr/bin/python3", ["-m", "antenna_tracker", "--dev"])

    monkeypatch.setattr(sys, "argv", ["/usr/local/bin/antenna-tracker", "--video-file", "clip.mp4"])
    assert relaunch_command() == (
        "/usr/bin/python3",
        ["/usr/local/bin/antenna-tracker", "--video-file", "clip.mp4"],
    )
