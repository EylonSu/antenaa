import math
import time

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")

from PySide6.QtWidgets import QApplication, QCheckBox  # noqa: E402

from antenna_tracker.config import AppConfig, load_config, save_config  # noqa: E402
from antenna_tracker.hardware import fake_turret  # noqa: E402
from antenna_tracker.hardware.port_finder import PortIdentity  # noqa: E402
from antenna_tracker.hardware.turret_client import TurretClient  # noqa: E402
from antenna_tracker.tracking.controller import Mode, TrackStatus  # noqa: E402
from antenna_tracker.ui.alerts import ALERT_POWER, ALERT_QR, ALERT_SPOOF  # noqa: E402
from antenna_tracker.ui.main_window import (  # noqa: E402
    QR_ALERT_AFTER_S, PILL, SOURCE_QR, SOURCE_SIM, MainWindow, SettingsDialog,
)
from antenna_tracker.ui.map_view import MAP_HTML  # noqa: E402
from antenna_tracker.ui.wizard import SetupWizard  # noqa: E402


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(utm_easting="667000", utm_northing="550500", antenna_alt_amsl=30.0,
                     ref_azimuth=45.0, port_device=fake_turret.FAKE_PORT)


@pytest.fixture
def turret(qapp):
    t = TurretClient(heartbeat_s=0.1, reply_timeout_s=0.3, reconnect_s=0.1, ready_timeout_s=0.3)
    yield t
    t.close()
    fake_turret.DEFAULT_DEVICE.power_on()


def test_qapp_is_widget_app(qapp):
    assert isinstance(qapp, QApplication)


def test_map_html_is_packaged():
    text = MAP_HTML.read_text(encoding="utf-8")
    assert "leaflet" in text and "qwebchannel.js" in text
    assert "tiles:/osm/{z}/{x}/{y}.png" in text
    assert "tiles:/satellite/{z}/{x}/{y}.jpg" in text
    assert 'data-basemap="osm"' in text and 'data-basemap="satellite"' in text
    assert '"Map"' in text and '"Satellite"' in text
    assert "setBasemap" in text and "basemapChanged" in text
    assert "maxNativeZoom: 14" in text and "maxZoom: 19" in text
    assert "OpenStreetMap contributors" in text and "https://cloudless.eox.at" in text
    assert (MAP_HTML.parent / "vendor" / "leaflet.js").is_file()
    assert (MAP_HTML.parent / "vendor" / "leaflet.css").is_file()
    assert (MAP_HTML.parent / "vendor" / "three.min.js").is_file()
    assert "three.min.js" in text and "setAntennaPose" in text
    assert "setAimArc" in text


def test_wizard_constructs_with_fake_port(qapp, config, turret):
    w = SetupWizard(config, turret, dev_mode=True)
    w.show()
    qapp.processEvents()
    page = w.connect_page
    assert any(page.port_combo.itemData(i) == fake_turret.FAKE_PORT for i in range(page.port_combo.count()))
    assert not page.isComplete()
    assert w.location_page.isComplete()
    w.close()


def test_setup_and_main_are_the_same_standard_window(qapp, config, turret):
    """Setup used to be a dialog: no zoom button, and a different size from the main screen."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget

    from antenna_tracker.ui.windowing import default_window_size, show_matching

    wizard = SetupWizard(config, turret, dev_mode=True)
    window = MainWindow(config, turret, dev_mode=True)
    try:
        assert _is_standard_desktop_window(wizard)
        assert _is_standard_desktop_window(window)
        assert (wizard.width(), wizard.height()) == default_window_size(wizard)
        assert (window.width(), window.height()) == (wizard.width(), wizard.height())
        wizard.show()
        qapp.processEvents()
        assert _is_standard_desktop_window(wizard)
        assert wizard.maximumWidth() > wizard.minimumWidth()
        assert wizard.maximumHeight() > wizard.minimumHeight()
    finally:
        window.shutdown()
        window.close()
        wizard.close()

    source = QWidget()
    source.resize(1100, 720)
    source.move(80, 90)
    source.show()
    qapp.processEvents()
    target = QWidget()
    show_matching(target, source)
    qapp.processEvents()
    assert not source.isVisible()
    assert target.isVisible()
    assert (target.x(), target.y(), target.width(), target.height()) == (
        source.x(), source.y(), source.width(), source.height())
    source.close()
    target.close()


def _is_standard_desktop_window(widget) -> bool:
    from PySide6.QtCore import Qt

    flags = widget.windowFlags()
    return (int(flags) & 0xFF) == int(Qt.WindowType.Window) and bool(
        flags & Qt.WindowType.WindowMinimizeButtonHint
        and flags & Qt.WindowType.WindowMaximizeButtonHint
        and flags & Qt.WindowType.WindowCloseButtonHint
    )


def test_site_coordinates_stay_east_left_of_north(qapp):
    """Easting stays left of northing, with a fixed 3 before north, in both directions."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLabel

    from antenna_tracker.ui.wizard.location_page import LocationPage

    previous = qapp.layoutDirection()
    try:
        for direction in (Qt.LayoutDirection.LeftToRight, Qt.LayoutDirection.RightToLeft):
            qapp.setLayoutDirection(direction)
            page = LocationPage(AppConfig(utm_easting="667000", utm_northing="550500"))
            page.resize(900, 700)
            page.show()
            qapp.processEvents()
            east_l, east_r = _span(page.easting, page)
            mark_l, mark_r = _span(page.northing_prefix, page)
            north_l, north_r = _span(page.northing, page)
            assert east_r <= mark_l < mark_r <= north_l
            assert north_r - north_l > 40
            assert isinstance(page.northing_prefix, QLabel)
            assert page.northing_prefix.text() == "3"
            assert page.northing_prefix.focusPolicy() == Qt.FocusPolicy.NoFocus
            page.close()
            page.deleteLater()

        qapp.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        page = LocationPage(AppConfig())
        page.resize(900, 700)
        page.show()
        qapp.processEvents()
        page.easting.setFocus()
        QTest.keyClicks(page.easting, "66700")
        qapp.processEvents()
        assert page.easting.text() == "66700"
        assert page.focusWidget() is page.easting
        assert page.northing.text() == ""
        QTest.keyClicks(page.easting, "0")
        qapp.processEvents()
        assert page.easting.text() == "667000"
        assert page.northing.text() == ""
        assert page.focusWidget() is page.northing

        page.easting.setFocus()
        page.easting.setSelection(5, 1)
        QTest.keyClick(page.easting, Qt.Key.Key_1)
        qapp.processEvents()
        assert page.easting.text() == "667001"
        assert page.focusWidget() is page.easting
        page.close()
    finally:
        qapp.setLayoutDirection(previous)


def _span(widget, ancestor) -> tuple[int, int]:
    origin = widget.mapTo(ancestor, widget.rect().topLeft())
    return origin.x(), origin.x() + widget.width()


def test_coordinate_digits_stay_inside_a_wide_field(qapp):
    """Hebrew placeholders used to push the example number off the left edge when maximized."""
    from PySide6.QtCore import Qt

    from antenna_tracker.i18n import set_language
    from antenna_tracker.ui.wizard.location_page import LocationPage

    previous = qapp.layoutDirection()
    set_language("he")
    qapp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    page = LocationPage(AppConfig())
    try:
        page.easting.setMinimumWidth(900)
        page.northing.setMinimumWidth(900)
        page.resize(2000, 420)
        page.show()
        qapp.processEvents()
        assert page.easting.placeholderText() == "667000"
        assert page.northing.placeholderText() == "550500"
        _assert_digits_visible(page.easting, "667000")
        page.easting.setText("667000")
        page.northing.setText("550500")
        qapp.processEvents()
        _assert_digits_visible(page.easting, "667000")
        _assert_digits_visible(page.northing, "550500")
    finally:
        page.close()
        set_language("en")
        qapp.setLayoutDirection(previous)


def _assert_digits_visible(field, text: str) -> None:
    start, end = _glyph_span(field)
    advance = field.fontMetrics().horizontalAdvance(text) * field.devicePixelRatio()
    assert start > 6, (start, end, field.width())
    assert end - start >= advance * 0.9, (start, end, advance)


def _glyph_span(widget) -> tuple[int, int]:
    from PySide6.QtGui import QImage

    image = widget.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
    width, height = image.width(), image.height()
    xs: list[int] = []
    for y in range(height // 3, 2 * height // 3, 2):
        for x in range(4, width - 4):
            color = image.pixelColor(x, y)
            if color.lightness() > 80 and color.blue() < 230:
                xs.append(x)
    assert xs, "no digits drawn"
    return min(xs), max(xs)


def test_wizard_combo_selection_is_readable(qapp, config, turret):
    """The open list used a cyan highlight with light text, so the current row vanished."""
    from PySide6.QtGui import QColor

    from antenna_tracker.ui.theme import ACCENT, app_style, set_ui_theme

    previous = qapp.styleSheet()
    set_ui_theme("dark")
    qapp.setStyleSheet(app_style(False))
    w = SetupWizard(config, turret, dev_mode=True)
    try:
        w.show()
        qapp.processEvents()
        combo = w.connect_page.port_combo
        combo.showPopup()
        qapp.processEvents()
        image = combo.view().window().grab().toImage()
        combo.hidePopup()
        highlight = _bluest_row_color(image)
        assert highlight != QColor(ACCENT)
        assert _luminance(highlight) < 0.2
        assert _light_edge_pixels(image) == 0
    finally:
        w.close()
        qapp.setStyleSheet(previous)


def _light_edge_pixels(image) -> int:
    """White macOS menu margins show up as light pixels along the popup edges."""
    width, height = image.width(), image.height()
    light = 0
    ys = list(range(0, min(10, height))) + list(range(max(0, height - 10), height))
    for y in ys:
        for x in range(0, width, 6):
            if image.pixelColor(x, y).lightness() > 200:
                light += 1
    return light


def _bluest_row_color(image):
    """Right-edge color of the dropdown row with the strongest blue highlight."""
    width = image.width()
    chosen = None
    for y in range(4, image.height() - 4):
        edge = image.pixelColor(width - 14, y)
        score = edge.blue() - edge.red()
        if chosen is None or score > chosen[0]:
            chosen = (score, edge)
    assert chosen is not None
    return chosen[1]


def _luminance(color) -> float:
    def linear(channel: int) -> float:
        value = channel / 255
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * linear(color.red())
        + 0.7152 * linear(color.green())
        + 0.0722 * linear(color.blue())
    )


def test_alignment_reference_choice_is_visible(qapp, config, turret):
    from PySide6.QtGui import QColor

    from antenna_tracker.ui.theme import ACCENT, RAISED, app_style, set_ui_theme

    previous = qapp.styleSheet()
    set_ui_theme("dark")
    qapp.setStyleSheet(app_style(False))
    w = SetupWizard(config, turret, dev_mode=True)
    try:
        page = w.alignment_page
        page_id = next(i for i in w.pageIds() if w.page(i) is page)
        w.setCurrentId(page_id)
        w.show()
        qapp.processEvents()
        map_btn = page.ref_group.button(0)
        compass_btn = page.ref_group.button(1)
        assert map_btn.isChecked()
        assert "true north" in page.ref_hint.text()
        assert _button_fill(map_btn) == QColor(ACCENT)
        assert _button_fill(compass_btn) == QColor(RAISED)

        compass_btn.click()
        qapp.processEvents()
        assert page.ref_group.checkedId() == 1
        assert not map_btn.isChecked()
        assert "magnetic north" in page.ref_hint.text()
        assert _button_fill(compass_btn) == QColor(ACCENT)
        assert _button_fill(map_btn) == QColor(RAISED)
    finally:
        w.close()
        qapp.setStyleSheet(previous)


def _button_fill(button):
    """Sample inside the left edge, clear of the label and the rounded border."""
    image = button.grab().toImage()
    return image.pixelColor(8, image.height() // 2)


def test_wizard_hides_fake_port_without_dev_mode(qapp, config, turret):
    w = SetupWizard(config, turret, dev_mode=False)
    combo = w.connect_page.port_combo
    assert all(combo.itemData(i) != fake_turret.FAKE_PORT for i in range(combo.count()))
    w.close()


def test_main_window_tracks_and_handles_power_loss(qapp, config, turret, wait_until):
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.set_source_kind(SOURCE_SIM)
    win.show()
    assert wait_until(lambda: turret.is_connected)
    assert wait_until(lambda: win.pill.text() == "TRACKING")
    assert win.controller.last_solution is not None

    win.manual_btn.click()
    assert win.controller.mode is Mode.MANUAL
    assert win.pill.text() == "MANUAL"
    win.auto_btn.click()
    assert win.controller.mode is Mode.AUTO

    win.power_off_btn.click()
    assert wait_until(lambda: win.overlay.isVisible() and win.overlay.beeping)
    assert win.overlay.alert_kind == ALERT_POWER
    assert win.overlay.eyebrow.text() == "POWER LOST"
    assert not any(b.isEnabled() for b in win.manual.buttons.values())
    win.power_on_btn.click()
    assert wait_until(lambda: turret.is_connected and win.overlay.showing_restored and not win.overlay.beeping)
    assert win.overlay.eyebrow.text() == "POWER RESTORED"
    win.shutdown()
    win.close()


def test_manual_panel_greys_out_unreachable(qapp, config, turret, wait_until):
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.set_source_kind(SOURCE_SIM)
    win.controller.set_mode(Mode.MANUAL)
    assert wait_until(lambda: turret.is_connected and turret.last_position is not None)
    turret.move(175, 90)
    assert wait_until(lambda: turret.last_position == (175, 90))
    win.controller.reset_last_command()
    win.manual.refresh()
    assert not win.manual.buttons["right"].isEnabled()
    assert win.manual.buttons["left"].isEnabled()
    win.shutdown()
    win.close()


def test_settings_dialog_applies(qapp, config, tmp_path):
    fresh = AppConfig()
    assert fresh.alert_power and fresh.alert_qr_read and fresh.alert_spoofing and fresh.alert_sound
    assert fresh.aim_arc_deg == 10
    dlg = SettingsDialog(config)
    dlg.declination.setValue(7.5)
    dlg.aim_arc.setValue(18)
    dlg.roi_w.setValue(0.4)
    dlg.roi_h.setValue(0.6)
    dlg.alert_power.setChecked(False)
    dlg.alert_qr_read.setChecked(False)
    dlg.alert_spoofing.setChecked(False)
    dlg.alert_sound.setChecked(False)
    dlg.apply(config)
    assert config.declination_deg == 7.5
    assert config.aim_arc_deg == 18
    assert config.qr_roi == (0.4, 0.6)
    assert not config.alert_power
    assert not config.alert_qr_read
    assert not config.alert_spoofing
    assert not config.alert_sound
    path = tmp_path / "config.json"
    save_config(config, path)
    loaded = load_config(path)
    assert loaded.alert_power is False
    assert loaded.alert_qr_read is False
    assert loaded.alert_spoofing is False
    assert loaded.alert_sound is False
    assert loaded.aim_arc_deg == 18
    assert load_config(tmp_path / "missing.json").alert_power is True
    path.write_text('{"aim_arc_deg": 400}', encoding="utf-8")
    assert load_config(path).aim_arc_deg == 90
    path.write_text('{"aim_arc_deg": "nope"}', encoding="utf-8")
    assert load_config(path).aim_arc_deg == 10


GOOD = "DRN-7|32.0900000|34.7900000|0|0|90.0|120.0|0|0|0|0|0|850|-1"
JAMMED = "DRN-7|32.1400000|34.7900000|0|0|90.0|120.0|0|0|0|0|0|850|-1"
NO_GPS = "DRN-7|0.0|0.0|0|0|90.0|120.0|0|0|0|0|0|850|-1"


def test_pill_has_every_status():
    assert set(PILL) == set(TrackStatus)
    assert PILL[TrackStatus.NO_GPS][0] == "NO DRONE GPS"


def test_qr_is_default_source_and_sim_needs_dev(qapp, config, turret):
    win = MainWindow(config, turret, dev_mode=False)
    assert win.source_kind == SOURCE_QR and win.controller.source is win.qr_source
    win.set_source_kind(SOURCE_SIM)
    assert win.source_kind == SOURCE_QR
    assert win.qr_indicator.text() == "NO QR CODE DETECTED"
    win.shutdown()
    win.close()


def test_gps_lost_and_restored_flow(qapp, config, turret, wait_until, monkeypatch):
    monkeypatch.setattr("antenna_tracker.ui.main_window.save_config", lambda *_: None)
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.show()
    t = time.time()
    for _ in range(3):
        win.qr_source.feed(GOOD, t)
        t += 0.5
    assert win.serial_label.text() == "DRN-7"
    assert "Height +120 m" in win.drone_info.text() and "0.85 km" in win.drone_info.text()
    assert win.qr_source.latest().alt_amsl == 30.0 + 120.0
    assert wait_until(lambda: win.pill.text() == "TRACKING")

    for _ in range(3):
        win.qr_source.feed(NO_GPS, t)
        t += 0.5
    assert win.controller.mode is Mode.MANUAL
    assert win.pill.text() == "NO DRONE GPS"
    assert not win.gps_banner.isHidden() and "NO GPS" in win.gps_text.text()
    assert win.overlay.alert_kind is None

    for _ in range(3):
        win.qr_source.feed(GOOD, t)
        t += 0.5
    assert win.gps_text.text() == "Drone GPS is back"
    assert win.controller.mode is Mode.MANUAL
    assert win.pill.text() == "MANUAL"

    win.auto_btn.click()
    assert win.controller.mode is Mode.AUTO
    assert win.gps_banner.isHidden()

    win.config.takeoff_near_antenna = False
    win.config.takeoff_alt_amsl = 55
    win.apply_site()
    assert win.qr_source.takeoff_alt_amsl == 55
    win.shutdown()
    win.close()


def test_possible_jamming_banner_switches_to_manual(qapp, config, turret, wait_until):
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.show()
    t = time.time()
    win.qr_source.feed(GOOD, t)
    assert wait_until(lambda: win.pill.text() == "TRACKING")
    win.qr_source.feed(JAMMED, t + 0.2)
    assert win.controller.mode is Mode.MANUAL
    assert win.pill.text() == "MANUAL"
    assert win.gps_banner.isHidden()
    assert win.overlay.alert_kind == ALERT_SPOOF
    assert win.overlay.isVisible() and win.overlay.beeping
    assert win.overlay.eyebrow.text() == "SPOOFING"
    assert "5 km" in win.overlay.detail.text()
    assert win.qr_source.latest().lat == pytest.approx(32.09)

    win.auto_btn.click()
    assert win.controller.mode is Mode.AUTO
    assert win.gps_banner.isHidden()
    assert win.overlay.alert_kind is None
    assert not win.overlay.isVisible()
    win.shutdown()
    win.close()


def test_sim_jump_shows_jamming_banner(qapp, config, turret, wait_until):
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.show()
    win.set_source_kind(SOURCE_SIM)
    assert wait_until(lambda: win.pill.text() == "TRACKING")
    pos = win.sim_source.latest()
    win.sim_source.set_position(pos.lat + math.degrees(6000 / 6_371_000), pos.lon)
    assert win.controller.mode is Mode.MANUAL
    assert win.pill.text() == "MANUAL"
    assert win.gps_banner.isHidden()
    assert win.overlay.alert_kind == ALERT_SPOOF
    assert win.overlay.isVisible() and win.overlay.beeping
    assert win.sim_source.latest().lat == pytest.approx(pos.lat)

    win.auto_btn.click()
    assert win.controller.mode is Mode.AUTO
    assert win.gps_banner.isHidden()
    assert not win.overlay.isVisible()
    win.shutdown()
    win.close()


OUTSIDE = "DRN-7|40.0000000|34.7900000|0|0|90.0|120.0|0|0|0|0|0|850|-1"
TOO_FAST = "DRN-7|32.0920000|34.7900000|0|0|90.0|120.0|0|0|0|0|0|850|-1"


def test_qr_read_failure_alert(qapp, config, turret, wait_until, monkeypatch):
    monkeypatch.setattr("antenna_tracker.ui.main_window.QR_ALERT_AFTER_S", 0.05)
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.show()
    assert wait_until(lambda: win.overlay.alert_kind == ALERT_QR and win.overlay.isVisible() and win.overlay.beeping)
    assert win.qr_indicator.text() == "NO QR CODE DETECTED"
    assert win.overlay.eyebrow.text() == "QR READ FAILED"

    t = time.time()
    win.qr_source.feed(GOOD, t)
    assert win.overlay.alert_kind is None and not win.overlay.isVisible()

    win.qr_source.feed("not-a-payload", t + 0.2)
    assert wait_until(lambda: win.overlay.alert_kind == ALERT_QR)

    win.qr_source.feed(OUTSIDE, t + 0.4)
    assert win.overlay.alert_kind is None
    win.qr_source.feed(GOOD, t + 1.0)
    win.qr_source.feed(TOO_FAST, t + 1.0)
    assert win.qr_source.rejected_by_reason.get("too fast") == 1
    assert win.overlay.alert_kind is None
    qapp.processEvents()
    assert win.overlay.alert_kind != ALERT_QR

    win.set_source_kind(SOURCE_SIM)
    win._qr_ok_at = time.monotonic() - 10
    win._sync_qr_alert()
    assert win.overlay.alert_kind is None
    win.shutdown()
    win.close()


def test_alert_hide_and_silence_snooze(qapp, config, turret, wait_until):
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.set_source_kind(SOURCE_SIM)
    win.show()
    assert wait_until(lambda: turret.is_connected)
    win.overlay.snooze_ms = 80

    win.power_off_btn.click()
    assert wait_until(lambda: win.overlay.alert_kind == ALERT_POWER and win.overlay.beeping)
    win.overlay.silence_btn.click()
    assert win.overlay.isVisible() and win.overlay.alert_kind == ALERT_POWER and not win.overlay.beeping
    assert wait_until(lambda: win.overlay.beeping, timeout=2)

    win.overlay.snooze_ms = 80
    win.overlay.hide_btn.click()
    assert not win.overlay.isVisible() and not win.overlay.beeping
    assert wait_until(lambda: win.overlay.isVisible() and win.overlay.beeping and win.overlay.alert_kind == ALERT_POWER, timeout=2)

    win.overlay.snooze_ms = 30_000
    win.overlay.hide_btn.click()
    assert not win.overlay.isVisible()
    win.power_on_btn.click()
    assert wait_until(lambda: turret.is_connected and win.overlay.showing_restored)
    win.power_off_btn.click()
    assert wait_until(lambda: win.overlay.alert_kind == ALERT_POWER and win.overlay.beeping, timeout=2)
    win.shutdown()
    win.close()


def test_higher_alert_shows_during_lower_snooze(qapp, config, turret, wait_until):
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.show()
    win.overlay.snooze_ms = 30_000
    win._qr_ok_at = time.monotonic() - QR_ALERT_AFTER_S - 1
    win._sync_qr_alert()
    assert win.overlay.alert_kind == ALERT_QR and win.overlay.isVisible()
    win.overlay.hide_btn.click()
    assert not win.overlay.isVisible()

    win.power_off_btn.click()
    assert wait_until(lambda: win.overlay.alert_kind == ALERT_POWER and win.overlay.isVisible() and win.overlay.beeping)
    win.shutdown()
    win.close()


def test_disabled_alerts_skip_card_but_spoofing_still_manual(qapp, config, turret, wait_until):
    config.alert_power = False
    config.alert_qr_read = False
    config.alert_spoofing = False
    config.alert_sound = False
    turret.open(PortIdentity(fake_turret.FAKE_PORT))
    win = MainWindow(config, turret, dev_mode=True)
    win.show()
    win._qr_ok_at = time.monotonic() - 10
    win._sync_qr_alert()
    assert win.overlay.alert_kind is None

    t = time.time()
    win.qr_source.feed(GOOD, t)
    assert wait_until(lambda: win.pill.text() == "TRACKING")
    win.qr_source.feed(JAMMED, t + 0.2)
    assert win.controller.mode is Mode.MANUAL
    assert win.overlay.alert_kind is None

    win.power_off_btn.click()
    assert wait_until(lambda: not turret.is_connected)
    assert not win.overlay.isVisible() and not win.overlay.beeping

    win.config.alert_power = True
    win.config.alert_sound = False
    win._apply_alert_settings()
    assert win.overlay.alert_kind == ALERT_POWER and win.overlay.isVisible() and not win.overlay.beeping
    win.config.alert_sound = True
    win._apply_alert_settings()
    assert win.overlay.beeping
    win.config.alert_power = False
    win._apply_alert_settings()
    assert win.overlay.alert_kind is None and not win.overlay.beeping
    win.shutdown()
    win.close()


def test_settings_groups_declination_crop_and_setup(qapp, config):
    from PySide6.QtWidgets import QLabel, QPushButton

    dlg = SettingsDialog(config)
    labels = [label.text() for label in dlg.findChildren(QLabel)]
    assert "COMPASS CALIBRATION" in labels
    assert "Magnetic declination" in labels
    assert "AIM ARC" in labels
    assert "Arc width" in labels
    assert "QR CAPTURE REGION" in labels
    assert "Frame width" in labels and "Frame height" in labels
    buttons = [button.text() for button in dlg.findChildren(QPushButton)]
    assert any(text.startswith("Run setup again") for text in buttons)
    assert "Save" in buttons and "Cancel" in buttons
    assert "ALERTS" in labels
    checks = [box.text() for box in dlg.findChildren(QCheckBox)]
    assert checks == [
        "Alert when the tracker has no power",
        "Alert when the QR read fails",
        "Alert when spoofing is detected",
        "Play the alarm sound",
    ]
    assert all(box.isChecked() for box in dlg.findChildren(QCheckBox))


def test_position_update_sets_antenna_pose(qapp, config, turret):
    from antenna_tracker.ui.map_view import aim_arc_polygon

    w = MainWindow(config, turret, dev_mode=True)
    calls = []
    w.map._call = lambda fn, *a: calls.append((fn, a))
    w._on_position(100, 95)
    assert any(fn == "setAntennaPose" and a[3:] == (100, 95) for fn, a in calls)
    site = w.controller.site
    assert site is not None
    expected = aim_arc_polygon(site.lat, site.lon, site.ref_az_true, 100, w.config.aim_arc_deg)
    arcs = [a for fn, a in calls if fn == "setAimArc"]
    assert arcs and arcs[-1] == (expected,)
    w.close()


def test_aim_arc_follows_pan_and_coverage_stays_170():
    from antenna_tracker.geo import pointing
    from antenna_tracker.ui.map_view import aim_arc_polygon, sector_polygon

    lat, lon, ref = 32.0, 34.8, 45.0
    coverage = sector_polygon(lat, lon, ref, pointing.PAN_MIN, pointing.PAN_MAX, radius_m=1000.0)
    start = pointing.az_el_dist(lat, lon, 0, coverage[1][0], coverage[1][1], 0)[0]
    end = pointing.az_el_dist(lat, lon, 0, coverage[-1][0], coverage[-1][1], 0)[0]
    assert pointing.wrap180(end - start) == pytest.approx(170, abs=0.05)

    pan, width = 120.0, 10.0
    arc = aim_arc_polygon(lat, lon, ref, pan, width, radius_m=1000.0)
    assert arc[0] == [lat, lon]
    center, _ = pointing.pan_tilt_to_az_el(pan, pointing.TILT_LEVEL, ref)
    edge_az = [
        pointing.az_el_dist(lat, lon, 0, pt[0], pt[1], 0)[0] for pt in arc[1:]
    ]
    assert pointing.wrap180(edge_az[0] - (center - width / 2)) == pytest.approx(0, abs=0.05)
    assert pointing.wrap180(edge_az[-1] - (center + width / 2)) == pytest.approx(0, abs=0.05)
    assert pointing.wrap180(edge_az[-1] - edge_az[0]) == pytest.approx(width, abs=0.05)
    # The old marker sat on mechanical center (pan 90). A pan of 120 must leave that behind.
    assert abs(pointing.wrap180(edge_az[len(edge_az) // 2] - center)) < 0.05
