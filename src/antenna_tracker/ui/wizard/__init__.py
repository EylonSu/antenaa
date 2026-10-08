from __future__ import annotations

from PySide6.QtWidgets import QWizard

from antenna_tracker.config import AppConfig
from antenna_tracker.hardware.turret_client import TurretClient
from antenna_tracker.ui.wizard.alignment_page import AlignmentPage
from antenna_tracker.ui.wizard.connect_page import ConnectPage
from antenna_tracker.ui.wizard.location_page import LocationPage


class SetupWizard(QWizard):
    """Connect -> Location -> Align. Edits `config` in place; opens `turret` after step 1."""

    def __init__(self, config: AppConfig, turret: TurretClient, dev_mode: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Antenna Tracker - Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)
        self.setStyleSheet("QWizard QPushButton { font-size: 20px; padding: 10px 24px; }")
        self.connect_page = ConnectPage(config, turret, dev_mode)
        self.location_page = LocationPage(config)
        self.alignment_page = AlignmentPage(config, turret)
        for p in (self.connect_page, self.location_page, self.alignment_page):
            self.addPage(p)
        self.setButtonText(QWizard.WizardButton.NextButton, "Next \u25b6")
        self.setButtonText(QWizard.WizardButton.BackButton, "\u25c0 Back")
        self.resize(900, 760)
