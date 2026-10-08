from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QSlider, QSplitter, QVBoxLayout, QWidget,
)

from antenna_tracker.config import AppConfig, save_config
from antenna_tracker.geo import pointing
from antenna_tracker.geo.coords import utm_input_to_latlon
from antenna_tracker.geo.pointing import Solution
from antenna_tracker.hardware import fake_turret
from antenna_tracker.hardware.turret_client import TurretClient
from antenna_tracker.sources.simulated import SimulatedSource
from antenna_tracker.tracking.controller import AntennaSite, Mode, TrackingController, TrackStatus
from antenna_tracker.ui.alerts import PowerOverlay
from antenna_tracker.ui.gauges import CompassGauge, ElevationGauge
from antenna_tracker.ui.manual_panel import ManualPanel
from antenna_tracker.ui.map_view import MapView
from antenna_tracker.video.capture import VideoPreview

PILL = {
    TrackStatus.TRACKING: ("TRACKING", "#2e7d32"),
    TrackStatus.MANUAL: ("MANUAL", "#ef6c00"),
    TrackStatus.OUT_OF_RANGE: ("OUT OF RANGE", "#d84315"),
    TrackStatus.NO_POSITION: ("NO DRONE POSITION", "#616161"),
    TrackStatus.STALE: ("NO FRESH DRONE POSITION", "#616161"),
    TrackStatus.NO_POWER: ("NO POWER", "#c62828"),
}
ACTUAL_LINE_M = 2000.0
DEFAULT_DRONE_DIST_M = 1000.0
DEFAULT_DRONE_HEIGHT_M = 100.0


class SettingsDialog(QDialog):
    RERUN_SETUP = 2

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setStyleSheet("QLabel, QDoubleSpinBox, QCheckBox, QPushButton { font-size: 18px; }")
        self.interval = QDoubleSpinBox(minimum=0.2, maximum=30, singleStep=0.5, suffix=" s", value=config.update_interval_s)
        self.declination = QDoubleSpinBox(minimum=-30, maximum=30, singleStep=0.5, suffix="\u00b0", value=config.declination_deg)
        self.stale = QDoubleSpinBox(minimum=1, maximum=120, singleStep=1, suffix=" s", value=config.stale_timeout_s)
        self.dev = QCheckBox("Developer mode (simulated tracker)", checked=config.developer_mode)
        form = QFormLayout()
        form.addRow("Update every:", self.interval)
        form.addRow("Magnetic declination:", self.declination)
        form.addRow("Drone position too old after:", self.stale)
        form.addRow(self.dev)
        rerun = QPushButton("Run setup again\u2026")
        rerun.clicked.connect(lambda: self.done(self.RERUN_SETUP))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(rerun)
        lay.addWidget(buttons)

    def apply(self, config: AppConfig) -> None:
        config.update_interval_s = self.interval.value()
        config.declination_deg = self.declination.value()
        config.stale_timeout_s = self.stale.value()
        config.developer_mode = self.dev.isChecked()


class MainWindow(QMainWindow):
    rerun_setup = Signal()

    def __init__(self, config: AppConfig, turret: TurretClient, dev_mode: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.config, self.turret, self.dev_mode = config, turret, dev_mode
        self.setWindowTitle("Antenna Tracker")
        self.source = SimulatedSource(self)
        self.controller = TrackingController(
            turret, None, self.source, self,
            interval_s=config.update_interval_s, stale_timeout_s=config.stale_timeout_s)
        self._solution: Solution | None = None
        self._build()
        self._wire()
        self._sim_heartbeat = QTimer(self, interval=1000)
        self._sim_heartbeat.timeout.connect(self._refresh_sim_drone)
        self._sim_heartbeat.start()
        self.apply_site()
        self.controller.start()

    # ---------- layout ----------
    def _build(self) -> None:
        self.map = MapView()

        drone_bar = QHBoxLayout()
        drone_bar.addWidget(QLabel("Drone height:", styleSheet="font-size: 18px;"))
        self.alt_slider = QSlider(Qt.Orientation.Horizontal, minimum=-200, maximum=3000, singleStep=10)
        self.alt_label = QLabel(styleSheet="font-size: 18px; min-width: 110px;")
        self.circle_btn = QPushButton("Fly a circle", checkable=True, styleSheet="font-size: 18px; padding: 8px;")
        drone_bar.addWidget(self.alt_slider, 1)
        drone_bar.addWidget(self.alt_label)
        drone_bar.addWidget(self.circle_btn)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.map, 1)
        lv.addLayout(drone_bar)

        self.pill = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.pill.setMinimumHeight(70)
        self.info = QLabel(alignment=Qt.AlignmentFlag.AlignCenter, wordWrap=True, styleSheet="font-size: 17px; color: #444;")

        self.auto_btn = QPushButton("AUTO", checkable=True)
        self.manual_btn = QPushButton("MANUAL", checkable=True)
        self.mode_group = QButtonGroup(self)
        for b, color in ((self.auto_btn, "#2e7d32"), (self.manual_btn, "#ef6c00")):
            b.setMinimumHeight(70)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setStyleSheet(
                "QPushButton { font-size: 30px; font-weight: bold; border: 2px solid #999; background: #eee; color: #555; }"
                f"QPushButton:checked {{ background: {color}; color: white; border-color: {color}; }}")
            self.mode_group.addButton(b)
        self.auto_btn.setChecked(True)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        mode_row.addWidget(self.auto_btn)
        mode_row.addWidget(self.manual_btn)

        self.video = VideoPreview()
        self.video.setMinimumHeight(140)
        self.compass = CompassGauge()
        self.elevation = ElevationGauge()
        gauges = QHBoxLayout()
        gauges.addWidget(self.compass)
        gauges.addWidget(self.elevation)
        self.manual = ManualPanel(self.controller)
        self.manual_frame = QFrame(frameShape=QFrame.Shape.StyledPanel)
        mf = QVBoxLayout(self.manual_frame)
        mf.addWidget(self.manual)

        self.gear = QPushButton("\u2699 Settings", styleSheet="font-size: 18px; padding: 8px;")
        top = QHBoxLayout()
        top.addWidget(self.pill, 1)
        top.addWidget(self.gear)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.addLayout(top)
        rv.addWidget(self.info)
        rv.addLayout(mode_row)
        rv.addWidget(self.video, 1)
        rv.addLayout(gauges, 1)
        rv.addWidget(self.manual_frame)

        if self.dev_mode:
            dev = QHBoxLayout()
            dev.addWidget(QLabel("Developer:", styleSheet="font-size: 15px; color: #6a1b9a; font-weight: bold;"))
            self.power_off_btn = QPushButton("Simulate power OFF")
            self.power_on_btn = QPushButton("Simulate power ON")
            for b in (self.power_off_btn, self.power_on_btn):
                b.setStyleSheet("font-size: 15px; padding: 6px;")
                dev.addWidget(b)
            self.power_off_btn.clicked.connect(fake_turret.DEFAULT_DEVICE.power_off)
            self.power_on_btn.clicked.connect(fake_turret.DEFAULT_DEVICE.power_on)
            rv.addLayout(dev)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        self.setCentralWidget(split)
        self.overlay = PowerOverlay(split)
        screen = self.screen().availableGeometry()
        self.resize(min(1400, screen.width()), min(900, screen.height() - 30))

        for key, name in ((Qt.Key.Key_Up, "up"), (Qt.Key.Key_Down, "down"),
                          (Qt.Key.Key_Left, "left"), (Qt.Key.Key_Right, "right")):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda n=name: self.manual.buttons[n].isEnabled() and self.manual.nudge(n))

    def _wire(self) -> None:
        c, t = self.controller, self.turret
        c.recommendation.connect(self._on_recommendation)
        c.status_changed.connect(self._on_status)
        c.mode_changed.connect(self._on_mode)
        c.command_sent.connect(lambda *_: self.manual.refresh())
        t.position.connect(self._on_position)
        t.power_lost.connect(self._on_power_lost)
        t.power_restored.connect(self._on_power_restored)
        t.state_changed.connect(lambda *_: (self.manual.refresh(), c.tick()))
        self.auto_btn.clicked.connect(lambda: c.set_mode(Mode.AUTO))
        self.manual_btn.clicked.connect(lambda: c.set_mode(Mode.MANUAL))
        self.manual.back_to_auto.connect(lambda: c.set_mode(Mode.AUTO))
        self.map.drone_moved.connect(self._on_drone_dragged)
        self.source.position_changed.connect(self._on_drone_position)
        self.alt_slider.valueChanged.connect(self._on_alt)
        self.circle_btn.toggled.connect(self._on_circle)
        self.gear.clicked.connect(self.open_settings)
        self._on_status((c.status or TrackStatus.NO_POSITION).value)
        self._on_mode(c.mode.value)

    # ---------- site / drone ----------
    def apply_site(self) -> None:
        cfg = self.config
        self.controller.set_interval(cfg.update_interval_s)
        self.controller.stale_timeout_s = cfg.stale_timeout_s
        try:
            p = utm_input_to_latlon(cfg.utm_easting, cfg.utm_northing)
        except ValueError:
            return
        site = AntennaSite(p.lat, p.lon, cfg.antenna_alt_amsl, cfg.ref_azimuth_true)
        self.controller.set_site(site)
        self.map.set_antenna(p.lat, p.lon, 14)
        self.map.set_sector(p.lat, p.lon, site.ref_az_true)
        self.video.set_device(cfg.video_device_id)
        if self.source.latest() is None:
            lat, lon = pointing.destination(p.lat, p.lon, site.ref_az_true, DEFAULT_DRONE_DIST_M)
            alt = cfg.antenna_alt_amsl + DEFAULT_DRONE_HEIGHT_M
            self.alt_slider.setValue(int(alt))
            self.source.set_position(lat, lon, alt)
        self._on_alt(self.alt_slider.value())
        self.controller.tick()

    def _refresh_sim_drone(self) -> None:
        if not self.source.circling and self.source.latest() is not None:
            self.source.set_altitude(float(self.alt_slider.value()))

    def _on_drone_dragged(self, lat: float, lon: float) -> None:
        if self.circle_btn.isChecked():
            self.circle_btn.setChecked(False)
        self.source.set_position(lat, lon)

    def _on_drone_position(self, pos) -> None:
        self.map.set_drone(pos.lat, pos.lon, True)

    def _on_alt(self, value: int) -> None:
        site = self.controller.site
        above = f" ({value - site.alt_amsl:+.0f})" if site else ""
        self.alt_label.setText(f"{value} m{above}")
        self.source.set_altitude(float(value))

    def _on_circle(self, on: bool) -> None:
        site = self.controller.site
        if on and site is not None:
            self.source.start_circle(site.lat, site.lon, DEFAULT_DRONE_DIST_M, 90.0)
        else:
            self.source.stop_circle()

    # ---------- tracking feedback ----------
    def _on_recommendation(self, sol: Solution | None) -> None:
        self._solution = sol
        site = self.controller.site
        if sol is None or site is None:
            self.map.set_recommended(None)
            self.info.setText("")
        else:
            end = pointing.destination(site.lat, site.lon, sol.azimuth, sol.distance_m)
            self.map.set_recommended([[site.lat, site.lon], list(end)])
            self.info.setText(self._explain(sol))
        self._update_gauges()
        self.manual.refresh()

    def _explain(self, sol: Solution) -> str:
        base = f"Drone is {sol.distance_m / 1000:.2f} km away, {sol.azimuth:.0f}\u00b0, {sol.elevation:+.0f}\u00b0 up."
        if sol.status is pointing.PointingStatus.AZIMUTH_OUT_OF_COVERAGE:
            return base + " It is outside the area the tracker can turn to."
        if sol.status is pointing.PointingStatus.ELEVATION_LIMITED:
            return base + " The tracker cannot tilt that far here; it points as close as it can."
        return base

    def _on_position(self, pan: int, tilt: int) -> None:
        site = self.controller.site
        if site is not None:
            az, _ = pointing.pan_tilt_to_az_el(pan, tilt, site.ref_az_true)
            end = pointing.destination(site.lat, site.lon, az, ACTUAL_LINE_M)
            self.map.set_actual([[site.lat, site.lon], list(end)])
        self._update_gauges()
        self.manual.refresh()

    def _update_gauges(self) -> None:
        site = self.controller.site
        act_az = act_el = None
        pos = self.turret.last_position
        if pos is not None and site is not None:
            act_az, act_el = pointing.pan_tilt_to_az_el(pos[0], pos[1], site.ref_az_true)
        sol = self._solution
        self.compass.set_values(sol.azimuth if sol else None, act_az)
        self.elevation.set_values(sol.elevation if sol else None, act_el)

    def _on_status(self, value: str) -> None:
        text, color = PILL[TrackStatus(value)]
        self.pill.setText(text)
        self.pill.setStyleSheet(
            f"background: {color}; color: white; font-size: 34px; font-weight: bold; border-radius: 35px; padding: 6px 20px;")

    def _on_mode(self, value: str) -> None:
        manual = value == Mode.MANUAL.value
        (self.manual_btn if manual else self.auto_btn).setChecked(True)
        self.manual.auto_btn.setVisible(manual)
        self.manual.refresh()

    def _on_power_lost(self, reason: str) -> None:
        self.overlay.show_lost(reason)
        self.controller.tick()

    def _on_power_restored(self) -> None:
        self.overlay.show_restored()
        self.controller.reset_last_command()
        self.controller.tick()

    # ---------- settings ----------
    def open_settings(self) -> None:
        dlg = SettingsDialog(self.config, self)
        result = dlg.exec()
        if result == QDialog.DialogCode.Rejected:
            return
        dlg.apply(self.config)
        save_config(self.config)
        self.apply_site()
        if result == SettingsDialog.RERUN_SETUP:
            self.rerun_setup.emit()

    def shutdown(self) -> None:
        self.controller.stop()
        self.source.stop()
        self.video.stop()

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
