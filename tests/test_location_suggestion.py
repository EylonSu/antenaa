import math

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest

from antenna_tracker.config import AppConfig
from antenna_tracker.geo.coords import utm_to_latlon
from antenna_tracker.ui.wizard.location_page import LocationPage

JERUSALEM = utm_to_latlon(711000, 3_513_000)
TEL_AVIV = utm_to_latlon(667000, 3_550_500)


class ScriptedFix(QObject):
    found = Signal(float, float, float)
    unavailable = Signal()

    def __init__(self, parent=None, fix=None, fail: bool = False) -> None:
        super().__init__(parent)
        self._fix = fix
        self._fail = fail
        self.requests = 0
        self.stopped = 0

    def request(self) -> None:
        self.requests += 1
        if self._fail:
            self.unavailable.emit()
        elif self._fix is not None:
            self.found.emit(*self._fix)

    def stop(self) -> None:
        self.stopped += 1


def _page(config: AppConfig | None = None, **fix_kwargs) -> tuple[LocationPage, list[ScriptedFix]]:
    held: list[ScriptedFix] = []

    def factory(parent):
        src = ScriptedFix(parent, **fix_kwargs)
        held.append(src)
        return src

    return LocationPage(config or AppConfig(), location_source=factory), held


def test_constructing_the_page_does_not_look_up_location(qapp) -> None:
    page, held = _page()
    assert page._lookup is None
    assert held == []
    page.close()


def test_saved_grid_is_not_replaced(qapp) -> None:
    page, held = _page(
        AppConfig(utm_easting="667000", utm_northing="550500"),
        fix=(JERUSALEM.lat, JERUSALEM.lon, 10),
    )
    page.initializePage()
    assert held == []
    assert page.easting.text() == "667000"
    assert page.northing.text() == "550500"
    assert "Found it" in page.message.text()
    page.close()


def test_empty_grid_uses_computer_fix(qapp) -> None:
    page, held = _page(fix=(JERUSALEM.lat, JERUSALEM.lon, 754.2))
    page.initializePage()
    assert held[0].requests == 1
    assert page.easting.text() == "711000"
    assert page.northing.text() == "513000"
    assert page.alt.value() == 754
    assert page.takeoff_alt.value() == 754
    assert page.isComplete()
    assert page.message.text().startswith("Suggested from this computer")
    page.cleanupPage()
    assert held[0].stopped == 1
    page.close()


def test_fresher_fix_updates_until_the_user_types(qapp) -> None:
    page, held = _page(fix=(JERUSALEM.lat, JERUSALEM.lon, float("nan")))
    page.initializePage()
    held[0].found.emit(TEL_AVIV.lat, TEL_AVIV.lon, 30)
    assert page.easting.text() == "667000"
    assert page.northing.text() == "550500"
    assert page.alt.value() == 30
    page.close()


def test_typing_keeps_the_typed_grid(qapp) -> None:
    page, held = _page()
    page.show()
    page.initializePage()
    page.easting.setFocus()
    QTest.keyClicks(page.easting, "667000")
    qapp.processEvents()
    held[0].found.emit(JERUSALEM.lat, JERUSALEM.lon, 80)
    assert page.easting.text() == "667000"
    assert page.northing.text() == ""
    assert not page.isComplete()
    page.close()


def test_edited_altitude_is_kept(qapp) -> None:
    page, held = _page()
    page.initializePage()
    page.alt.setValue(42)
    held[0].found.emit(JERUSALEM.lat, JERUSALEM.lon, 800)
    assert page.alt.value() == 42
    assert page.easting.text() == "711000"
    page.close()


def test_fix_outside_the_operating_area_leaves_the_grid_empty(qapp) -> None:
    page, _held = _page(fix=(40.7, -74.0, float("nan")))
    page.initializePage()
    assert page.easting.text() == ""
    assert page.northing.text() == ""
    assert "outside the operating area" in page.message.text()
    assert not page.isComplete()
    page.close()


def test_missing_fix_asks_for_the_grid(qapp) -> None:
    page, _held = _page(fail=True)
    page.initializePage()
    assert "Could not read this computer's location" in page.message.text()
    assert not page.isComplete()
    page.close()


def test_unknown_altitude_keeps_the_entered_height(qapp) -> None:
    page, _held = _page(
        AppConfig(antenna_alt_amsl=15),
        fix=(JERUSALEM.lat, JERUSALEM.lon, math.nan),
    )
    page.initializePage()
    assert page.easting.text() == "711000"
    assert page.alt.value() == 15
    page.close()
