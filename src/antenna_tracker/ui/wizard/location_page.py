from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtCore import QObject, QRegularExpression, Qt, QTimer
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget, QWizardPage,
)

from antenna_tracker.config import AppConfig
from antenna_tracker.geo.computer_location import ComputerLocation
from antenna_tracker.geo.coords import (
    LatLon, UtmError, format_utm_fields, utm_fields_for_latlon, utm_input_to_latlon,
)
from antenna_tracker.i18n import ltr, t
from antenna_tracker.ui.map_view import MapView
from antenna_tracker.ui.theme import AMBER, BORDER, GREEN, MUTED, RED, TEXT, card, muted

BIG = "font-size: 16px; padding: 7px;"


class LocationPage(QWizardPage):
    def __init__(self, config: AppConfig, parent=None,
                 location_source: Callable[[QObject], QObject] | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._location_source = ComputerLocation if location_source is None else location_source
        self._lookup = None
        self._accept_computer_fix = False
        self._from_computer = False
        self._coords_touched = False
        self._alt_touched = False
        self._applying = False
        self._suggested_easting = ""
        self._suggested_northing = ""
        self.setTitle(t("Set the tracker location"))
        self.setSubTitle(t(
            "Enter the 12-digit UTM grid reference and verify the position on the map. "
            "An empty grid starts from this computer's location."
        ))
        self._pos: LatLon | None = None
        # Digits only. A Hebrew "e.g." prefix is right-to-left, so Qt draws the
        # example number off the left edge once the field grows (maximized window).
        self.easting = QLineEdit(config.utm_easting, placeholderText="667000", styleSheet=BIG)
        self.northing = QLineEdit(config.utm_northing, placeholderText="550500", styleSheet=BIG)
        digits = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignVCenter
        for e in (self.easting, self.northing):
            e.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,6}")))
            e.setMaxLength(6)
            e.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            e.setAlignment(digits)
            e.textChanged.connect(self._update)
        self._easting_prev = self.easting.text()
        self.easting.textEdited.connect(self._on_easting_edited)
        self.northing.textEdited.connect(self._on_coords_edited)
        # Israeli northings are 3xxxxxx. The millions digit is fixed and stays outside the field.
        self.northing_prefix = QLabel("3")
        self.northing_prefix.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.northing_prefix.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.northing_prefix.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {TEXT}; background: transparent; border: none;"
        )
        self.alt = QDoubleSpinBox(styleSheet=BIG, decimals=0, minimum=-500, maximum=4000, suffix=" m")
        self.alt.setValue(config.antenna_alt_amsl)
        self.takeoff_near = QCheckBox(t("Drone takes off next to the antenna"))
        self.takeoff_near.setChecked(config.takeoff_near_antenna)
        self.takeoff_alt = QDoubleSpinBox(styleSheet=BIG, decimals=0, minimum=-500, maximum=4000, suffix=" m")
        self.takeoff_alt.setValue(config.takeoff_alt_amsl)
        self.takeoff_near.toggled.connect(self._update_takeoff)
        self.alt.valueChanged.connect(self._update_takeoff)
        self.alt.valueChanged.connect(self._on_alt_changed)
        self.message = QLabel(wordWrap=True, styleSheet=f"font-size: 14px; color: {MUTED};")
        self._basemap = config.map_basemap if config.map_basemap in ("osm", "satellite") else "osm"
        self.map = MapView(basemap=self._basemap, zoom_scaled_marker=True)
        self.map.basemap_changed.connect(self._on_basemap)
        self.map.setMinimumHeight(300)
        self.map.setStyleSheet(f"border: 1px solid {BORDER}; border-radius: 10px;")

        form = QFormLayout()
        form.setSpacing(11)
        form.addRow(self._coordinate_row())
        form.addRow(QLabel(t("Site altitude · above sea level")), self.alt)
        form.addRow(self.takeoff_near)
        form.addRow(QLabel(t("Takeoff altitude · above sea level")), self.takeoff_alt)
        self.locate_btn = QPushButton(t("Use this computer's position"), styleSheet=BIG)
        self.locate_btn.setProperty("primary", True)
        self.locate_btn.clicked.connect(self._on_locate_clicked)
        location_card, location = card(t("SITE COORDINATES"))
        location.addWidget(muted(t("Use the local six-digit easting and northing values.")))
        location.addWidget(self.locate_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        location.addLayout(form)
        location.addWidget(self.message)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 8)
        lay.setSpacing(14)
        lay.addWidget(location_card)
        lay.addWidget(self.map, 1)
        self._update_takeoff()
        self._update()

    def _coordinate_row(self) -> QWidget:
        """East on the left, north on the right, in both Hebrew and English layouts."""
        host = QWidget()
        host.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        label_align = (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignBottom
        )
        east_label = QLabel(t("Easting · first 6 digits"), alignment=label_align, wordWrap=True)
        north_label = QLabel(t("Northing · last 6 digits"), alignment=label_align, wordWrap=True)
        for label in (east_label, north_label):
            label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(0)
        grid.setVerticalSpacing(4)
        prefix_host = QWidget()
        prefix_host.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        prefix_row = QHBoxLayout(prefix_host)
        prefix_row.setContentsMargins(16, 0, 6, 0)
        prefix_row.setSpacing(0)
        prefix_row.addWidget(self.northing_prefix)
        grid.addWidget(east_label, 0, 0)
        grid.addWidget(north_label, 0, 2)
        grid.addWidget(self.easting, 1, 0)
        grid.addWidget(prefix_host, 1, 1)
        grid.addWidget(self.northing, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        return host

    def _on_easting_edited(self, text: str) -> None:
        self._on_coords_edited(text)
        completed = len(text) == 6 and len(self._easting_prev) < 6
        self._easting_prev = text
        if completed:
            QTimer.singleShot(0, self._focus_northing)

    def _on_coords_edited(self, _text: str = "") -> None:
        self._coords_touched = True
        self._from_computer = False

    def _on_alt_changed(self, _value: float) -> None:
        if not self._applying:
            self._alt_touched = True

    def initializePage(self) -> None:
        super().initializePage()
        self._suggest_from_computer()

    def cleanupPage(self) -> None:
        self._stop_location_lookup()
        super().cleanupPage()

    def _stop_location_lookup(self) -> None:
        if self._lookup is not None:
            self._lookup.stop()

    def _on_locate_clicked(self) -> None:
        """The button asks for a fresh fix and uses it in place of the current grid."""
        self._coords_touched = False
        self._alt_touched = False
        self._accept_computer_fix = True
        self.locate_btn.setEnabled(False)
        self._set_status(t("Waiting for this computer's location. Allow it if the system asks."), MUTED)
        self._ensure_lookup()
        self._lookup.request()

    def _ensure_lookup(self) -> None:
        if self._lookup is not None:
            return
        self._lookup = self._location_source(self)
        self._lookup.found.connect(self._apply_computer_fix)
        self._lookup.unavailable.connect(self._computer_fix_unavailable)

    def _suggest_from_computer(self) -> None:
        if self._coords_touched or self.easting.text().strip() or self.northing.text().strip():
            return
        self._ensure_lookup()
        self._set_status(t("Waiting for this computer's location. Allow it if the system asks."), MUTED)
        self._lookup.request()

    def _apply_computer_fix(self, lat: float, lon: float, alt: float) -> None:
        accept = self._accept_computer_fix
        self._accept_computer_fix = False
        self.locate_btn.setEnabled(True)
        if self._coords_touched and not accept:
            return
        try:
            easting, northing = utm_fields_for_latlon(lat, lon)
        except UtmError:
            if accept or not (self.easting.text().strip() or self.northing.text().strip()):
                self._set_status(
                    t("This computer is outside the operating area. Enter the site grid."),
                    RED,
                )
            return
        self._applying = True
        self._from_computer = True
        self._suggested_easting = easting
        self._suggested_northing = northing
        try:
            self.easting.setText(easting)
            self._easting_prev = self.easting.text()
            self.northing.setText(northing)
            if (accept or not self._alt_touched) and math.isfinite(alt):
                self.alt.setValue(round(alt))
        finally:
            self._applying = False

    def _computer_fix_unavailable(self) -> None:
        accept = self._accept_computer_fix
        self._accept_computer_fix = False
        self.locate_btn.setEnabled(True)
        if not accept and (
            self._coords_touched
            or self._from_computer
            or self.easting.text().strip()
            or self.northing.text().strip()
        ):
            return
        reason = getattr(self._lookup, "failure", "")
        if reason in ("denied", "blocked"):
            text = t("Location is blocked. Allow antenaa in system settings, then try again.")
        else:
            text = t("Could not read this computer's location. Enter the site grid.")
        self._set_status(text, RED)

    def _set_status(self, text: str, color: str, *, bold: bool = False) -> None:
        weight = " font-weight: bold;" if bold else ""
        self.message.setText(text)
        self.message.setStyleSheet(f"font-size: 14px; color: {color};{weight}")

    def _focus_northing(self) -> None:
        if len(self.easting.text()) != 6:
            return
        self.northing.setFocus()
        self.northing.setCursorPosition(len(self.northing.text()))

    def _update_takeoff(self) -> None:
        near = self.takeoff_near.isChecked()
        self.takeoff_alt.setEnabled(not near)
        if near:
            self.takeoff_alt.setValue(self.alt.value())

    @property
    def position(self) -> LatLon | None:
        return self._pos

    def _note_coord_edit(self) -> None:
        if self._applying:
            return
        if (
            self.easting.text() != self._suggested_easting
            or self.northing.text() != self._suggested_northing
        ):
            self._coords_touched = True
            self._from_computer = False

    def _update(self) -> None:
        self._note_coord_edit()
        try:
            self._pos = utm_input_to_latlon(self.easting.text(), self.northing.text())
        except UtmError as e:
            self._pos = None
            self._set_status(str(e), RED)
        else:
            utm = ltr(format_utm_fields(self.easting.text(), self.northing.text()))
            if self._from_computer:
                text = t("Suggested from this computer: {utm}. Check the map.").format(utm=utm)
                color = AMBER
            else:
                text = t("\u2714 Found it: {utm}  (check the map)").format(utm=utm)
                color = GREEN
            self._set_status(text, color, bold=True)
            self.map.set_antenna(self._pos.lat, self._pos.lon, 15)
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._pos is not None

    def _on_basemap(self, name: str) -> None:
        if name in ("osm", "satellite"):
            self._basemap = name

    def validatePage(self) -> bool:
        self.config.utm_easting = self.easting.text()
        self.config.utm_northing = self.northing.text()
        self.config.antenna_alt_amsl = self.alt.value()
        self.config.takeoff_near_antenna = self.takeoff_near.isChecked()
        self.config.takeoff_alt_amsl = self.takeoff_alt.value()
        self.config.map_basemap = self._basemap
        return self._pos is not None
