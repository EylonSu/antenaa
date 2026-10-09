from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWizard

from antenna_tracker.config import AppConfig
from antenna_tracker.hardware.turret_client import TurretClient
from antenna_tracker.i18n import t
from antenna_tracker.ui.theme import BORDER, MUTED, TEXT, language_row
from antenna_tracker.ui.wizard.alignment_page import AlignmentPage
from antenna_tracker.ui.wizard.connect_page import ConnectPage
from antenna_tracker.ui.wizard.location_page import LocationPage


class SetupWizard(QWizard):
    """Connect -> Location -> Align. Edits `config` in place; opens `turret` after step 1."""

    language_restart = Signal(str)

    def __init__(self, config: AppConfig, turret: TurretClient, dev_mode: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("antenaa - " + t("Setup"))
        # ClassicStyle renders the title on the page background. ModernStyle
        # paints its own white banner, which clashes with the dark theme.
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#05080e"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
        pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
        pal.setColor(QPalette.ColorRole.Mid, QColor(BORDER))
        self.setPalette(pal)
        self.setStyleSheet(f"""
            QWizard {{ background: #05080e; border: none; }}
            QWizardPage {{ background: #05080e; border: none; }}
            QLabel#qt_wizard_title {{
                color: {TEXT}; font-size: 22px; font-weight: 800; background: transparent; border: none;
            }}
            QLabel#qt_wizard_subtitle {{
                color: {MUTED}; font-size: 14px; background: transparent; border: none;
            }}
            QWizard QFrame {{ border: none; }}
            QWizard QPushButton {{ min-width: 100px; padding: 10px 22px; }}
        """)
        self.connect_page = ConnectPage(config, turret, dev_mode)
        self.location_page = LocationPage(config)
        self.alignment_page = AlignmentPage(config, turret)
        for p in (self.connect_page, self.location_page, self.alignment_page):
            self.addPage(p)
            lay = p.layout()
            if lay is not None:
                lay.insertWidget(0, language_row(config.language, self._on_language))
        self.setButtonText(QWizard.WizardButton.NextButton, t("Continue"))
        self.setButtonText(QWizard.WizardButton.BackButton, t("Back"))
        self.setButtonText(QWizard.WizardButton.CancelButton, t("Cancel"))
        self.setButtonText(QWizard.WizardButton.FinishButton, t("Finish"))
        self.resize(1050, 760)

    def _on_language(self, code: str) -> None:
        current = "en" if self.config.language == "en" else "he"
        if code == current:
            return
        self.language_restart.emit(code)
