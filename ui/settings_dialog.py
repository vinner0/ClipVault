"""
settings_dialog.py — Application settings window.
"""

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
)
import startup


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ClipVault — Settings")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)

        # -- Startup group --
        grp = QGroupBox("Windows Startup")
        grp_layout = QVBoxLayout(grp)

        self._startup_cb = QCheckBox("Start ClipVault automatically with Windows")
        self._startup_cb.setChecked(startup.is_startup_enabled())
        self._startup_cb.toggled.connect(startup.set_startup)
        grp_layout.addWidget(self._startup_cb)

        layout.addWidget(grp)
        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
