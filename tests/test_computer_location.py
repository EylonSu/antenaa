import math
import plistlib
import sys

import pytest

from antenna_tracker.geo.computer_location import position_fix, uses_macos_helper
from antenna_tracker.geo.macos_helper import parse_helper_output


def test_parse_helper_output() -> None:
    assert parse_helper_output("32.100000 34.800000 42.0") == (32.1, 34.8, 42.0)
    lat, lon, alt = parse_helper_output("32.1 34.8 nan")
    assert (lat, lon) == (32.1, 34.8)
    assert math.isnan(alt)
    assert parse_helper_output("nope") is None
    assert parse_helper_output("95 0 0") is None
    lat, lon, alt = parse_helper_output("32 34 9000")
    assert math.isnan(alt)


def test_macos_helper_is_only_for_an_unfrozen_mac(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert uses_macos_helper()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert not uses_macos_helper()
    monkeypatch.setattr(sys, "platform", "win32")
    assert not uses_macos_helper()


def test_helper_plist_declares_location_use() -> None:
    from importlib.resources import files

    root = files("antenna_tracker.geo")
    plist = plistlib.loads(root.joinpath("macos_location_helper.plist").read_bytes())
    assert plist["CFBundlePackageType"] == "APPL"
    assert plist["CFBundleExecutable"] == "antenaa-location"
    assert "LSUIElement" not in plist
    assert "location" in plist["NSLocationWhenInUseUsageDescription"].lower()
    source = root.joinpath("macos_location_helper.swift").read_text(encoding="utf-8")
    assert "CLLocationManager" in source and "NSApplication" in source


def test_position_fix_reads_height_only_when_usable(qapp) -> None:
    from PySide6.QtCore import QDateTime
    from PySide6.QtPositioning import QGeoCoordinate, QGeoPositionInfo

    now = QDateTime.currentDateTimeUtc()
    info = QGeoPositionInfo(QGeoCoordinate(32.0, 34.8, 120.0), now)
    assert position_fix(info) == (32.0, 34.8, 120.0)

    flat = QGeoPositionInfo(QGeoCoordinate(32.0, 34.8), now)
    lat, lon, alt = position_fix(flat)
    assert (lat, lon) == (32.0, 34.8)
    assert math.isnan(alt)

    high = QGeoPositionInfo(QGeoCoordinate(32.0, 34.8, 9000.0), now)
    assert math.isnan(position_fix(high)[2])
    assert position_fix(QGeoPositionInfo()) is None


@pytest.mark.parametrize("text", ["", "   ", "lat lon"])
def test_blank_helper_output_is_ignored(text: str) -> None:
    assert parse_helper_output(text) is None
