from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWizard

import PySide6.QtWebEngineWidgets  # noqa: F401  (must be imported before QApplication)

from antenna_tracker.config import AppConfig, load_config, save_config
from antenna_tracker.hardware import fake_turret
from antenna_tracker.hardware.port_finder import PortIdentity
from antenna_tracker.hardware.turret_client import LinkState, TurretClient
from antenna_tracker.i18n import is_rtl, set_language, t
from antenna_tracker.ui.main_window import MainWindow
from antenna_tracker.ui.theme import app_style
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


def relaunch_command() -> tuple[str, list[str]]:
    """Same process, so a language change picks up direction, stylesheet, and labels.

    Frozen builds relaunch the executable. ``python -m antenna_tracker`` must stay a
    module launch; a direct path to ``__main__.py`` is not a valid program on its own.
    """
    args = list(sys.argv[1:])
    if getattr(sys, "frozen", False):
        return sys.executable, args
    invoked = sys.argv[0] if sys.argv else ""
    if invoked in ("-m", "") or Path(invoked).name == "__main__.py":
        return sys.executable, ["-m", "antenna_tracker", *args]
    return sys.executable, [invoked, *args]


class App:
    def __init__(self, config: AppConfig, dev_mode: bool) -> None:
        self.config = config
        self.dev_mode = dev_mode
        self.turret = TurretClient()
        self.window: MainWindow | None = None
        self.wizard: SetupWizard | None = None
        self._restarting = False
        self._did_shutdown = False

    def identity(self) -> PortIdentity:
        c = self.config
        return PortIdentity(c.port_device or "", c.port_vid, c.port_pid, c.port_serial_number)

    def run_wizard(self) -> None:
        if self.window is not None:
            self.window.hide()
        self.wizard = SetupWizard(self.config, self.turret, self.dev_mode)
        self.wizard.finished.connect(self._wizard_done)
        self.wizard.language_restart.connect(self.restart_in_language)
        self.wizard.show()

    def _wizard_done(self, result: int) -> None:
        if self._restarting:
            return
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
            self.window.language_restart.connect(self.restart_in_language)
        else:
            self.window.apply_site()
        self.window.show()
        self.window.raise_()

    def restart_in_language(self, language: str) -> None:
        """Save the language, release the turret port, then start the same command."""
        if self._restarting:
            return
        self._restarting = True
        self.config.language = "en" if language == "en" else "he"
        save_config(self.config)
        self.shutdown()
        program, args = relaunch_command()
        QProcess.startDetached(program, args)
        QApplication.quit()

    def shutdown(self) -> None:
        if self._did_shutdown:
            return
        self._did_shutdown = True
        if self.window is not None:
            self.window.shutdown()
        self.turret.close()

ICON_PATH = Path(__file__).resolve().parent / "assets" / "icon.png"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    args = parse_args(argv[1:])
    set_video_file_override(args.video_file)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    qapp = QApplication(argv)
    config = load_config()
    set_language(config.language)
    qapp.setLayoutDirection(
        Qt.LayoutDirection.RightToLeft if is_rtl() else Qt.LayoutDirection.LeftToRight)
    qapp.setStyleSheet(app_style(is_rtl()))
    qapp.setApplicationName("antenaa")
    qapp.setWindowIcon(QIcon(str(ICON_PATH)))
    dev_mode = args.dev or args.demo or config.developer_mode
    app = App(demo_config(config) if args.demo else config, dev_mode)
    qapp.aboutToQuit.connect(app.shutdown)
    if args.demo:
        app.show_main()
    else:
        app.run_wizard()
    return qapp.exec()
