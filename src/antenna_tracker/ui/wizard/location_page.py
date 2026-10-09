from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWizardPage,
)

from antenna_tracker.config import AppConfig
from antenna_tracker.geo.coords import LatLon, UtmError, utm_input_to_latlon
from antenna_tracker.i18n import ltr, t
from antenna_tracker.ui.map_view import MapView
from antenna_tracker.ui.theme import MUTED, card, muted

BIG = "font-size: 16px; padding: 7px;"


class LocationPage(QWizardPage):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setTitle(t("Set the tracker location"))
        self.setSubTitle(t("Enter the 12-digit UTM grid reference and verify the position on the map."))
        self._pos: LatLon | None = None
        six = QRegularExpressionValidator(QRegularExpression(r"\d{0,6}"))
        self.easting = QLineEdit(config.utm_easting, placeholderText=t("e.g. 667000"), styleSheet=BIG)
        self.northing = QLineEdit(config.utm_northing, placeholderText=t("e.g. 550500"), styleSheet=BIG)
        for e in (self.easting, self.northing):
            e.setValidator(six)
            e.setMaxLength(6)
            e.textChanged.connect(self._update)
        self.alt = QDoubleSpinBox(styleSheet=BIG, decimals=0, minimum=-500, maximum=4000, suffix=" m")
        self.alt.setValue(config.antenna_alt_amsl)
        self.takeoff_near = QCheckBox(t("Drone takes off next to the antenna"))
        self.takeoff_near.setChecked(config.takeoff_near_antenna)
        self.takeoff_alt = QDoubleSpinBox(styleSheet=BIG, decimals=0, minimum=-500, maximum=4000, suffix=" m")
        self.takeoff_alt.setValue(config.takeoff_alt_amsl)
        self.takeoff_near.toggled.connect(self._update_takeoff)
        self.alt.valueChanged.connect(self._update_takeoff)
        self.message = QLabel(wordWrap=True, styleSheet=f"font-size: 14px; color: {MUTED};")
        self._basemap = config.map_basemap if config.map_basemap in ("osm", "satellite") else "osm"
        self.map = MapView(basemap=self._basemap, zoom_scaled_marker=True)
        self.map.basemap_changed.connect(self._on_basemap)
        self.map.setMinimumHeight(300)
        self.map.setStyleSheet("border: 1px solid #1d2b42; border-radius: 10px;")

        form = QFormLayout()
        form.setSpacing(11)
        form.addRow(QLabel(t("Easting · first 6 digits")), self.easting)
        form.addRow(QLabel(t("Northing · last 6 digits")), self.northing)
        form.addRow(QLabel(t("Site altitude · above sea level")), self.alt)
        form.addRow(self.takeoff_near)
        form.addRow(QLabel(t("Takeoff altitude · above sea level")), self.takeoff_alt)
        location_card, location = card(t("SITE COORDINATES"))
        location.addWidget(muted(t("Use the local six-digit easting and northing values.")))
        location.addLayout(form)
        location.addWidget(self.message)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 8)
        lay.setSpacing(14)
        lay.addWidget(location_card)
        lay.addWidget(self.map, 1)
        self._update_takeoff()
        self._update()

    def _update_takeoff(self) -> None:
        near = self.takeoff_near.isChecked()
        self.takeoff_alt.setEnabled(not near)
        if near:
            self.takeoff_alt.setValue(self.alt.value())

    @property
    def position(self) -> LatLon | None:
        return self._pos

    def _update(self) -> None:
        try:
            self._pos = utm_input_to_latlon(self.easting.text(), self.northing.text())
        except UtmError as e:
            self._pos = None
            self.message.setText(str(e))
            self.message.setStyleSheet("font-size: 14px; color: #ff5d6c;")
        else:
            self.message.setText(
                t("\u2714 Found it: {lat}, {lon}  (check the map)").format(
                    lat=ltr(f"{self._pos.lat:.5f}"), lon=ltr(f"{self._pos.lon:.5f}"),
                )
            )
            self.message.setStyleSheet("font-size: 14px; color: #3ddc84; font-weight: bold;")
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
