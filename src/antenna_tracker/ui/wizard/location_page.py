from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWizardPage,
)

from antenna_tracker.config import AppConfig
from antenna_tracker.geo.coords import LatLon, UtmError, utm_input_to_latlon
from antenna_tracker.ui.map_view import MapView

BIG = "font-size: 24px; padding: 6px;"


class LocationPage(QWizardPage):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setTitle("Step 2 of 3: Where is the tracker?")
        self.setSubTitle("Type the UTM grid position (6 + 6 digits) and the height above sea level.")
        self._pos: LatLon | None = None
        six = QRegularExpressionValidator(QRegularExpression(r"\d{0,6}"))
        self.easting = QLineEdit(config.utm_easting, placeholderText="e.g. 667000", styleSheet=BIG)
        self.northing = QLineEdit(config.utm_northing, placeholderText="e.g. 550500", styleSheet=BIG)
        for e in (self.easting, self.northing):
            e.setValidator(six)
            e.setMaxLength(6)
            e.textChanged.connect(self._update)
        self.alt = QDoubleSpinBox(styleSheet=BIG, decimals=0, minimum=-500, maximum=4000, suffix=" m")
        self.alt.setValue(config.antenna_alt_amsl)
        self.message = QLabel(wordWrap=True, styleSheet="font-size: 18px;")
        self.map = MapView()
        self.map.setMinimumHeight(260)

        form = QFormLayout()
        lbl = "font-size: 20px;"
        form.addRow(QLabel("Easting (first 6 digits):", styleSheet=lbl), self.easting)
        form.addRow(QLabel("Northing (last 6 digits):", styleSheet=lbl), self.northing)
        form.addRow(QLabel("Height above sea level:", styleSheet=lbl), self.alt)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self.message)
        lay.addWidget(self.map, 1)
        self._update()

    @property
    def position(self) -> LatLon | None:
        return self._pos

    def _update(self) -> None:
        try:
            self._pos = utm_input_to_latlon(self.easting.text(), self.northing.text())
        except UtmError as e:
            self._pos = None
            self.message.setText(str(e))
            self.message.setStyleSheet("font-size: 18px; color: #c62828;")
        else:
            self.message.setText(f"\u2714 Found it: {self._pos.lat:.5f}, {self._pos.lon:.5f}  (check the map)")
            self.message.setStyleSheet("font-size: 18px; color: #2e7d32; font-weight: bold;")
            self.map.set_antenna(self._pos.lat, self._pos.lon, 15)
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return self._pos is not None

    def validatePage(self) -> bool:
        self.config.utm_easting = self.easting.text()
        self.config.utm_northing = self.northing.text()
        self.config.antenna_alt_amsl = self.alt.value()
        return self._pos is not None
