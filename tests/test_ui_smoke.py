import math
import time

import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from antenna_tracker.config import AppConfig  # noqa: E402
from antenna_tracker.hardware import fake_turret  # noqa: E402
from antenna_tracker.hardware.port_finder import PortIdentity  # noqa: E402
from antenna_tracker.hardware.turret_client import TurretClient  # noqa: E402
from antenna_tracker.tracking.controller import Mode, TrackStatus  # noqa: E402
from antenna_tracker.ui.main_window import PILL, SOURCE_QR, SOURCE_SIM, MainWindow, SettingsDialog  # noqa: E402
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
    assert 'data-basemap="osm">Map' in text and 'data-basemap="satellite">Satellite' in text
    assert "setBasemap" in text and "basemapChanged" in text
    assert "maxNativeZoom: 14" in text and "maxZoom: 19" in text
    assert "OpenStreetMap contributors" in text and "https://cloudless.eox.at" in text
    assert (MAP_HTML.parent / "vendor" / "leaflet.js").is_file()
    assert (MAP_HTML.parent / "vendor" / "leaflet.css").is_file()


def test_wizard_constructs_with_fake_port(qapp, config, turret):
    w = SetupWizard(config, turret, dev_mode=True)
    w.show()
    qapp.processEvents()
    page = w.connect_page
    assert any(page.port_combo.itemData(i) == fake_turret.FAKE_PORT for i in range(page.port_combo.count()))
    assert not page.isComplete()
    assert w.location_page.isComplete()
    w.close()


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
    assert not any(b.isEnabled() for b in win.manual.buttons.values())
    win.power_on_btn.click()
    assert wait_until(lambda: turret.is_connected and not win.overlay.beeping)
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


def test_settings_dialog_applies(qapp, config):
    dlg = SettingsDialog(config)
    dlg.declination.setValue(7.5)
    dlg.roi_w.setValue(0.4)
    dlg.roi_h.setValue(0.6)
    dlg.apply(config)
    assert config.declination_deg == 7.5
    assert config.qr_roi == (0.4, 0.6)


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
    assert not win.gps_banner.isHidden()
    assert win.gps_text.text() == "POSSIBLE JAMMING \u2013 aim the antenna manually"
    assert win.qr_source.latest().lat == pytest.approx(32.09)

    win.auto_btn.click()
    assert win.controller.mode is Mode.AUTO
    assert win.gps_banner.isHidden()
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
    assert not win.gps_banner.isHidden()
    assert win.gps_text.text() == "POSSIBLE JAMMING \u2013 aim the antenna manually"
    assert win.sim_source.latest().lat == pytest.approx(pos.lat)

    win.auto_btn.click()
    assert win.controller.mode is Mode.AUTO
    assert win.gps_banner.isHidden()
    win.shutdown()
    win.close()


def test_settings_groups_declination_crop_and_setup(qapp, config):
    from PySide6.QtWidgets import QLabel, QPushButton

    dlg = SettingsDialog(config)
    labels = [label.text() for label in dlg.findChildren(QLabel)]
    assert "COMPASS CALIBRATION" in labels
    assert "Magnetic declination" in labels
    assert "QR CAPTURE REGION" in labels
    assert "Frame width" in labels and "Frame height" in labels
    buttons = [button.text() for button in dlg.findChildren(QPushButton)]
    assert any(text.startswith("Run setup again") for text in buttons)
    assert "Save" in buttons and "Cancel" in buttons
