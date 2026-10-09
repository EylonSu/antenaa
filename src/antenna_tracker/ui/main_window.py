from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QSlider, QSplitter, QVBoxLayout, QWidget,
)

from antenna_tracker.config import AppConfig, save_config
from antenna_tracker.geo import pointing
from antenna_tracker.geo.coords import utm_input_to_latlon
from antenna_tracker.geo.pointing import Solution
from antenna_tracker.hardware import fake_turret
from antenna_tracker.hardware.turret_client import TurretClient
from antenna_tracker.sources.qr_video import QrVideoSource
from antenna_tracker.sources.simulated import SimulatedSource
from antenna_tracker.tracking.controller import AntennaSite, Mode, TrackingController, TrackStatus
from antenna_tracker.ui.alerts import PowerOverlay
from antenna_tracker.ui.gauges import CompassGauge, ElevationGauge
from antenna_tracker.ui.manual_panel import ManualPanel
from antenna_tracker.ui.map_view import MapView
from antenna_tracker.ui.theme import ACCENT, AMBER, BORDER, GREEN, MUTED, RED, SURFACE, SURFACE_2, TEXT, card, muted, repolish, title
from antenna_tracker.video.capture import VideoPreview
from antenna_tracker.video.qr_decoder import QrDecoder, Roi

PILL = {
    TrackStatus.TRACKING: ("TRACKING", "#63e63b"),
    TrackStatus.MANUAL: ("MANUAL", "#f5b942"),
    TrackStatus.OUT_OF_RANGE: ("OUT OF RANGE", "#d84315"),
    TrackStatus.NO_POSITION: ("NO DRONE POSITION", "#616161"),
    TrackStatus.STALE: ("NO FRESH DRONE POSITION", "#616161"),
    TrackStatus.NO_POWER: ("NO POWER", "#c62828"),
    TrackStatus.NO_GPS: ("NO DRONE GPS", "#e65100"),
}
SOURCE_QR, SOURCE_SIM = "qr", "sim"
NO_GPS_STYLE = "background: #4a3410; color: #ffd57b; border: 1px solid #8d6724; border-radius: 8px;"
GPS_BACK_STYLE = "background: #123c2b; color: #7ce8ad; border: 1px solid #286b4d; border-radius: 8px;"
JAM_STYLE = "background: #4b1f2a; color: #ff9daa; border: 1px solid #8b394b; border-radius: 8px;"
QR_OK_STYLE = "font-size: 11px; font-weight: 800; color: #6ee7a4; background: #123c2b; padding: 4px 8px; border: 1px solid #286b4d; border-radius: 9px;"
QR_BAD_STYLE = "font-size: 11px; font-weight: 800; color: #ff9daa; background: #4b1f2a; padding: 4px 8px; border: 1px solid #8b394b; border-radius: 9px;"
ACTUAL_LINE_M = 2000.0
DEFAULT_DRONE_DIST_M = 1000.0
DEFAULT_DRONE_HEIGHT_M = 100.0


class SettingsDialog(QDialog):
    RERUN_SETUP = 2

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tracker settings")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.declination = QDoubleSpinBox(minimum=-30, maximum=30, singleStep=0.5, suffix="\u00b0", value=config.declination_deg)
        self.roi_w = QDoubleSpinBox(minimum=0.05, maximum=1.0, singleStep=0.05, value=config.qr_roi[0])
        self.roi_h = QDoubleSpinBox(minimum=0.05, maximum=1.0, singleStep=0.05, value=config.qr_roi[1])
        for spin in (self.declination, self.roi_w, self.roi_h):
            spin.setMinimumHeight(38)

        heading = title("Tracker settings", 24)
        intro = muted("Fine-tune calibration and QR capture. Hardware and location are managed by setup.", True)

        compass_card, compass = card("COMPASS CALIBRATION")
        compass_form = QFormLayout()
        compass_form.setSpacing(12)
        compass_form.addRow("Magnetic declination", self.declination)
        compass.addLayout(compass_form)
        compass.addWidget(muted("Applied only when the alignment direction was measured with a compass.", True))

        qr_card, qr = card("QR CAPTURE REGION")
        qr_form = QFormLayout()
        qr_form.setSpacing(12)
        qr_form.addRow("Frame width", self.roi_w)
        qr_form.addRow("Frame height", self.roi_h)
        qr.addLayout(qr_form)
        qr.addWidget(muted("Fraction of the video frame scanned from the top-left corner (0.05–1.00).", True))

        rerun = QPushButton("Run setup again")
        rerun.setProperty("danger", True)
        rerun.clicked.connect(lambda: self.done(self.RERUN_SETUP))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        save.setProperty("primary", True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(14)
        lay.addWidget(heading)
        lay.addWidget(intro)
        lay.addWidget(compass_card)
        lay.addWidget(qr_card)
        lay.addWidget(rerun)
        lay.addWidget(buttons)

    def apply(self, config: AppConfig) -> None:
        config.declination_deg = self.declination.value()
        config.qr_roi = (self.roi_w.value(), self.roi_h.value())


class MainWindow(QMainWindow):
    rerun_setup = Signal()

    def __init__(self, config: AppConfig, turret: TurretClient, dev_mode: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.config, self.turret, self.dev_mode = config, turret, dev_mode
        self.setWindowTitle("Antenna Tracker")
        self.sim_source = SimulatedSource(self)
        self.qr_source = QrVideoSource.from_config(config, self)
        self.decoder = QrDecoder(config.qr_decode_fps, Roi(*config.qr_roi), parent=self)
        self.source_kind = SOURCE_QR
        self.source = self.qr_source
        self.controller = TrackingController(
            turret, None, self.source, self,
            interval_s=config.update_interval_s, stale_timeout_s=config.stale_timeout_s)
        self._solution: Solution | None = None
        self._qr_rate = 0.0
        self._build()
        self._wire()
        self._sim_heartbeat = QTimer(self, interval=1000)
        self._sim_heartbeat.timeout.connect(self._refresh_sim_drone)
        self._sim_heartbeat.start()
        self.apply_site()
        self.set_source_kind(SOURCE_QR)
        self.controller.start()

    # ---------- layout ----------
    def _build(self) -> None:
        self.map = MapView(basemap=self.config.map_basemap)

        self.sim_bar = QWidget()
        drone_bar = QHBoxLayout(self.sim_bar)
        drone_bar.setContentsMargins(14, 9, 14, 9)
        drone_bar.addWidget(QLabel("SIMULATED ALTITUDE", styleSheet=f"color: {MUTED}; font-size: 11px; font-weight: 700;"))
        self.alt_slider = QSlider(Qt.Orientation.Horizontal, minimum=-200, maximum=3000, singleStep=10)
        self.alt_label = QLabel(styleSheet="font-size: 15px; font-weight: 700; min-width: 100px;")
        self.circle_btn = QPushButton("Orbit site", checkable=True)
        drone_bar.addWidget(self.alt_slider, 1)
        drone_bar.addWidget(self.alt_label)
        drone_bar.addWidget(self.circle_btn)
        self.sim_bar.setStyleSheet(f"background: {SURFACE}; border-top: 1px solid {BORDER};")
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        lv.addWidget(self.map, 1)
        lv.addWidget(self.sim_bar)

        self.pill = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.pill.setMinimumHeight(36)

        self.auto_btn = QPushButton("AUTO", checkable=True)
        self.manual_btn = QPushButton("MANUAL", checkable=True)
        self.mode_group = QButtonGroup(self)
        for b, color in ((self.auto_btn, GREEN), (self.manual_btn, AMBER)):
            b.setMinimumHeight(42)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setStyleSheet(
                f"QPushButton {{ font-size: 13px; font-weight: 800; border: 1px solid {BORDER}; "
                f"background: #0a1525; color: {MUTED}; border-radius: 7px; }}"
                f"QPushButton:checked {{ background: {color}; color: #06131b; border-color: {color}; }}")
            self.mode_group.addButton(b)
        self.auto_btn.setChecked(True)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_row.addWidget(self.auto_btn)
        mode_row.addWidget(self.manual_btn)

        self.video = VideoPreview(self, show_preview=False)
        self.serial_label = QLabel("\u2014", styleSheet="font-size: 14px; font-weight: 700;")
        self.altitude_value = QLabel("\u2014")
        self.home_value = QLabel("\u2014")
        self.heading_value = QLabel("\u2014")
        self.qr_rate_value = QLabel("0/s")
        for value in (self.altitude_value, self.home_value, self.heading_value, self.qr_rate_value):
            value.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.qr_indicator = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._set_qr_indicator(0.0)
        self.drone_info = QLabel("Height \u2014   Home \u2014   Heading \u2014",
                                 alignment=Qt.AlignmentFlag.AlignLeft, styleSheet=f"font-size: 13px; color: {MUTED};")
        self.drone_info.hide()
        qr_row = QHBoxLayout()
        qr_row.setSpacing(10)
        qr_row.addWidget(self.qr_indicator)
        qr_row.addStretch(1)
        metrics = QGridLayout()
        metrics.setHorizontalSpacing(18)
        metrics.setVerticalSpacing(5)
        metric_data = (
            ("DRONE", self.serial_label, 0, 0),
            ("ALTITUDE", self.altitude_value, 0, 1),
            ("HEADING", self.heading_value, 0, 2),
            ("HOME DISTANCE", self.home_value, 2, 0),
            ("QR RATE", self.qr_rate_value, 2, 1),
        )
        for label_text, value, row, col in metric_data:
            label = QLabel(label_text)
            label.setStyleSheet(f"font-size: 9px; font-weight: 800; color: {MUTED};")
            metrics.addWidget(label, row, col)
            metrics.addWidget(value, row + 1, col)
        self.qr_widget = QWidget()
        qv = QVBoxLayout(self.qr_widget)
        qv.setContentsMargins(0, 0, 0, 0)
        qv.setSpacing(10)
        qv.addLayout(qr_row)
        qv.addLayout(metrics)
        qv.addWidget(self.drone_info)

        self.gps_banner = QFrame()
        self.gps_banner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.gps_text = QLabel(alignment=Qt.AlignmentFlag.AlignCenter, wordWrap=True,
                               styleSheet="font-size: 16px; font-weight: 800; background: transparent; border: none;")
        gb = QHBoxLayout(self.gps_banner)
        gb.setContentsMargins(16, 10, 16, 10)
        gb.addWidget(self.gps_text, 1)
        self.gps_banner.hide()
        self.compass = CompassGauge()
        self.elevation = ElevationGauge()
        gauges = QHBoxLayout()
        gauges.setSpacing(8)
        gauges.addWidget(self.compass)
        gauges.addWidget(self.elevation)
        self.manual = ManualPanel(self.controller)
        self.manual_frame, mf = card("MANUAL CONTROL")
        mf.addWidget(self.manual)

        self.gear = QPushButton("Settings")
        self.gear.setToolTip("Tracker settings")
        brand_row = QHBoxLayout()
        brand = QLabel("ANTENNA TRACKER")
        brand.setStyleSheet(f"font-size: 17px; font-weight: 900; color: {TEXT}; letter-spacing: 1px;")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        brand_row.addWidget(QLabel("OPERATIONS", styleSheet=f"font-size: 9px; font-weight: 800; color: {ACCENT};"))
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(self.pill, 1)
        top.addWidget(self.gear)

        telemetry_card, telemetry = card("DRONE LINK")
        telemetry.addWidget(self.qr_widget)
        pointing_card, pointing = card("POINTING SOLUTION")
        pointing.addLayout(gauges)

        right = QWidget()
        right.setMinimumWidth(430)
        right.setMaximumWidth(590)
        right.setStyleSheet(f"background: #0b1524; border-left: 1px solid {BORDER};")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(12, 10, 12, 10)
        rv.setSpacing(8)
        rv.addLayout(brand_row)
        rv.addLayout(top)
        rv.addLayout(mode_row)
        rv.addWidget(telemetry_card)
        rv.addWidget(pointing_card, 1)
        rv.addWidget(self.manual_frame)

        if self.dev_mode:
            dev_card, dev = card("SIMULATION & DEVELOPER")
            dev_row = QHBoxLayout()
            dev_row.addWidget(QLabel("DEV", styleSheet=f"font-size: 9px; color: {ACCENT}; font-weight: 800;"))
            self.power_off_btn = QPushButton("Simulate power OFF")
            self.power_on_btn = QPushButton("Simulate power ON")
            for b in (self.power_off_btn, self.power_on_btn):
                dev_row.addWidget(b)
            self.source_combo = QComboBox()
            self.source_combo.addItem("Drone position: Video QR", SOURCE_QR)
            self.source_combo.addItem("Drone position: Simulated", SOURCE_SIM)
            dev_row.addWidget(self.source_combo)
            self.power_off_btn.clicked.connect(fake_turret.DEFAULT_DEVICE.power_off)
            self.power_on_btn.clicked.connect(fake_turret.DEFAULT_DEVICE.power_on)
            dev.addLayout(dev_row)
            rv.addWidget(dev_card)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 3)
        central = QWidget()
        cv = QVBoxLayout(central)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.addWidget(self.gps_banner)
        cv.addWidget(split, 1)
        self.setCentralWidget(central)
        self.overlay = PowerOverlay(split)
        screen = self.screen().availableGeometry()
        self.resize(min(1500, screen.width()), min(940, screen.height() - 30))

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
        self.map.drone_moved.connect(self._on_drone_dragged)
        self.map.basemap_changed.connect(self._on_basemap_changed)
        self.sim_source.position_changed.connect(self._on_sim_position)
        self.qr_source.position_changed.connect(self._on_qr_position)
        self.qr_source.telemetry.connect(self._on_telemetry)
        self.qr_source.gps_lost.connect(self._on_gps_lost)
        self.qr_source.gps_restored.connect(self._on_gps_restored)
        self.qr_source.possible_jamming.connect(lambda: self._on_possible_jamming(SOURCE_QR))
        self.sim_source.possible_jamming.connect(lambda: self._on_possible_jamming(SOURCE_SIM))
        self.video.frame_ready.connect(self.decoder.submit_frame)
        self.decoder.decoded.connect(self.qr_source.feed)
        self.decoder.stats.connect(self._set_qr_indicator)
        if self.dev_mode:
            self.source_combo.currentIndexChanged.connect(
                lambda _: self.set_source_kind(self.source_combo.currentData()))
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
        self.map.set_basemap(cfg.map_basemap)
        try:
            p = utm_input_to_latlon(cfg.utm_easting, cfg.utm_northing)
        except ValueError:
            return
        site = AntennaSite(p.lat, p.lon, cfg.antenna_alt_amsl, cfg.ref_azimuth_true)
        self.controller.set_site(site)
        self.map.set_antenna(p.lat, p.lon, 14)
        self.map.set_sector(p.lat, p.lon, site.ref_az_true)
        self.video.set_device(cfg.video_device_id)
        self.qr_source.fields = cfg.qr_fields
        self.decoder.roi = Roi(*cfg.qr_roi)
        self.decoder.max_fps = cfg.qr_decode_fps
        self.qr_source.set_takeoff_alt(cfg.effective_takeoff_alt_amsl)
        if self.sim_source.latest() is None:
            lat, lon = pointing.destination(p.lat, p.lon, site.ref_az_true, DEFAULT_DRONE_DIST_M)
            alt = cfg.antenna_alt_amsl + DEFAULT_DRONE_HEIGHT_M
            self.alt_slider.setValue(int(alt))
            self.sim_source.set_position(lat, lon, alt)
        self._on_alt(self.alt_slider.value())
        self.controller.tick()

    def _on_basemap_changed(self, name: str) -> None:
        if name not in ("osm", "satellite"):
            return
        self.config.map_basemap = name
        save_config(self.config)

    def set_source_kind(self, kind: str) -> None:
        if kind == SOURCE_SIM and not self.dev_mode:
            kind = SOURCE_QR
        self.source_kind = kind
        sim = kind == SOURCE_SIM
        self.source = self.sim_source if sim else self.qr_source
        self.controller.set_source(self.source)
        self.sim_bar.setVisible(sim)
        if self.dev_mode and self.source_combo.currentData() != kind:
            self.source_combo.setCurrentIndex(self.source_combo.findData(kind))
        if sim:
            self.gps_banner.hide()
            self.map.set_drone_last_known(False)
            self.controller.set_drone_gps(True)
        else:
            self.sim_source.stop_circle()
            self.circle_btn.setChecked(False)
            self.controller.set_drone_gps(self.qr_source.gps_ok)
        pos = self.source.latest()
        if pos is not None:
            self.map.set_drone(pos.lat, pos.lon, sim)
        self.controller.tick()

    def _refresh_sim_drone(self) -> None:
        if not self.sim_source.circling and self.sim_source.latest() is not None:
            self.sim_source.set_altitude(float(self.alt_slider.value()))

    def _on_drone_dragged(self, lat: float, lon: float) -> None:
        if self.source_kind != SOURCE_SIM:
            return
        if self.circle_btn.isChecked():
            self.circle_btn.setChecked(False)
        self.sim_source.set_position(lat, lon)

    def _on_sim_position(self, pos) -> None:
        if self.source_kind == SOURCE_SIM:
            self.map.set_drone(pos.lat, pos.lon, True)

    def _on_qr_position(self, pos) -> None:
        if self.source_kind == SOURCE_QR:
            self.map.set_drone(pos.lat, pos.lon, False)

    # ---------- video / QR ----------
    def _set_qr_indicator(self, rate: float) -> None:
        self._qr_rate = rate
        if hasattr(self, "qr_rate_value"):
            self.qr_rate_value.setText(f"{rate:.0f}/s")
        if rate > 0:
            self.qr_indicator.setText("QR LINK ACTIVE")
            self.qr_indicator.setStyleSheet(QR_OK_STYLE)
        else:
            self.qr_indicator.setText("NO QR CODE DETECTED")
            self.qr_indicator.setStyleSheet(QR_BAD_STYLE)

    def _on_telemetry(self, tel) -> None:
        self.serial_label.setText(tel.serial or "\u2014")
        home = f"{tel.home_dist / 1000:.2f} km" if tel.home_dist is not None and tel.home_dist >= 0 else "\u2014"
        heading = f"{tel.heading:.0f}\u00b0" if tel.heading is not None else "\u2014"
        self.altitude_value.setText(f"{tel.rel_alt:+.0f} m")
        self.home_value.setText(home)
        self.heading_value.setText(heading)
        self.drone_info.setText(f"Height {tel.rel_alt:+.0f} m   Home {home}   Heading {heading}")

    def _on_gps_lost(self) -> None:
        if self.source_kind != SOURCE_QR:
            return
        self.gps_banner.setStyleSheet(NO_GPS_STYLE)
        self.gps_text.setText("DRONE HAS NO GPS \u2013 aim the antenna manually")
        self.gps_banner.show()
        self.map.set_drone_last_known(True)
        self.controller.on_gps_lost()

    def _on_gps_restored(self) -> None:
        if self.source_kind != SOURCE_QR:
            return
        self.gps_banner.setStyleSheet(GPS_BACK_STYLE)
        self.gps_text.setText("Drone GPS is back")
        self.gps_banner.show()
        self.map.set_drone_last_known(False)
        self.controller.on_gps_restored()

    def _on_possible_jamming(self, kind: str) -> None:
        if self.source_kind != kind:
            return
        if kind == SOURCE_SIM and not self.dev_mode:
            return
        self.gps_banner.setStyleSheet(JAM_STYLE)
        self.gps_text.setText("POSSIBLE JAMMING \u2013 aim the antenna manually")
        self.gps_banner.show()
        self.controller.set_mode(Mode.MANUAL)
        if kind == SOURCE_SIM:
            pos = self.sim_source.latest()
            if pos is not None:
                self.map.set_drone(pos.lat, pos.lon, True)

    def _on_alt(self, value: int) -> None:
        site = self.controller.site
        above = f" ({value - site.alt_amsl:+.0f})" if site else ""
        self.alt_label.setText(f"{value} m{above}")
        self.sim_source.set_altitude(float(value))

    def _on_circle(self, on: bool) -> None:
        site = self.controller.site
        if on and site is not None and self.source_kind == SOURCE_SIM:
            self.sim_source.start_circle(site.lat, site.lon, DEFAULT_DRONE_DIST_M, 90.0)
        else:
            self.sim_source.stop_circle()

    # ---------- tracking feedback ----------
    def _on_recommendation(self, sol: Solution | None) -> None:
        self._solution = sol
        site = self.controller.site
        if sol is None or site is None:
            self.map.set_recommended(None)
        else:
            end = pointing.destination(site.lat, site.lon, sol.azimuth, sol.distance_m)
            self.map.set_recommended([[site.lat, site.lon], list(end)])
        self._update_gauges()
        self.manual.refresh()

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
        foreground = "#06131b" if TrackStatus(value) in (TrackStatus.TRACKING, TrackStatus.MANUAL) else "white"
        self.pill.setStyleSheet(
            f"background: {color}; color: {foreground}; font-size: 13px; font-weight: 800; "
            "letter-spacing: 1px; border-radius: 8px; padding: 7px 14px;")

    def _on_mode(self, value: str) -> None:
        manual = value == Mode.MANUAL.value
        (self.manual_btn if manual else self.auto_btn).setChecked(True)
        if not manual and self.controller.drone_gps_ok:
            self.gps_banner.hide()
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
        self.sim_source.stop()
        self.qr_source.stop()
        self.video.stop()
        self.decoder.shutdown()

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
