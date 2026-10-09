from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWizard

import PySide6.QtWebEngineWidgets  # noqa: F401  (must be imported before QApplication)

from antenna_tracker.config import AppConfig, load_config, save_config
from antenna_tracker.hardware import fake_turret
from antenna_tracker.hardware.port_finder import PortIdentity
from antenna_tracker.hardware.turret_client import LinkState, TurretClient
from antenna_tracker.ui.main_window import MainWindow
from antenna_tracker.ui.theme import APP_STYLE
from antenna_tracker.ui.wizard import SetupWizard
from antenna_tracker.video.capture import set_video_file_override

DEMO_UTM = ("667000", "550500")  # Tel Aviv area
DEMO_ALT = 30.0


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="antenna-tracker")
    p.add_argument("--dev", action="store_true", help="developer mode: offer the simulated tracker")
    p.add_argument("--demo", action="store_true",
                   help="developer mode, skip the wizard and use the simulated tracker at a demo location")
    p.add_argument("--video-file", metavar="PATH",
                   help="developer: play this recording (looped) instead of the capture device")
    args, _ = p.parse_known_args(argv)
    return args


def demo_config(config: AppConfig) -> AppConfig:
    config.port_device = fake_turret.FAKE_PORT
    config.port_vid, config.port_pid = fake_turret.FAKE_VID, fake_turret.FAKE_PID
    config.port_serial_number = fake_turret.FAKE_SERIAL_NUMBER
    if not (config.utm_easting and config.utm_northing):
        config.utm_easting, config.utm_northing = DEMO_UTM
        config.antenna_alt_amsl = DEMO_ALT
    return config


class App:
    def __init__(self, config: AppConfig, dev_mode: bool) -> None:
        self.config = config
        self.dev_mode = dev_mode
        self.turret = TurretClient()
        self.window: MainWindow | None = None
        self.wizard: SetupWizard | None = None

    def identity(self) -> PortIdentity:
        c = self.config
        return PortIdentity(c.port_device or "", c.port_vid, c.port_pid, c.port_serial_number)

    def run_wizard(self) -> None:
        if self.window is not None:
            self.window.hide()
        self.wizard = SetupWizard(self.config, self.turret, self.dev_mode)
        self.wizard.finished.connect(self._wizard_done)
        self.wizard.show()

    def _wizard_done(self, result: int) -> None:
        if result != QWizard.DialogCode.Accepted:
            if self.window is None:
                QApplication.quit()
            else:
                self.window.show()
            return
        save_config(self.config)
        self.show_main()

    def show_main(self) -> None:
        if self.turret.state is LinkState.DISCONNECTED and self.config.port_device:
            self.turret.open(self.identity())
        if self.window is None:
            self.window = MainWindow(self.config, self.turret, self.dev_mode)
            self.window.rerun_setup.connect(self.run_wizard)
        else:
            self.window.apply_site()
        self.window.show()
        self.window.raise_()

    def shutdown(self) -> None:
        if self.window is not None:
            self.window.shutdown()
        self.turret.close()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    args = parse_args(argv[1:])
    set_video_file_override(args.video_file)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    qapp = QApplication(argv)
    qapp.setApplicationName("Antenna Tracker")
    qapp.setStyleSheet(APP_STYLE)
    config = load_config()
    dev_mode = args.dev or args.demo or config.developer_mode
    app = App(demo_config(config) if args.demo else config, dev_mode)
    qapp.aboutToQuit.connect(app.shutdown)
    if args.demo:
        app.show_main()
    else:
        app.run_wizard()
    return qapp.exec()
