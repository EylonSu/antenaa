import pytest

pytest.importorskip("PySide6.QtWebEngineWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from antenna_tracker.config import AppConfig  # noqa: E402
from antenna_tracker.hardware import fake_turret  # noqa: E402
from antenna_tracker.hardware.port_finder import PortIdentity  # noqa: E402
from antenna_tracker.hardware.turret_client import TurretClient  # noqa: E402
from antenna_tracker.tracking.controller import Mode  # noqa: E402
from antenna_tracker.ui.main_window import MainWindow, SettingsDialog  # noqa: E402
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
    dlg.interval.setValue(2.5)
    dlg.apply(config)
    assert config.update_interval_s == 2.5
