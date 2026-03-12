"""
expander_ui.py — ShortcodeDialog: add / edit a single shortcode entry.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)


class ShortcodeDialog(QDialog):
    def __init__(self, parent=None, *, code: str = "", expansion: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Edit Shortcode" if code else "Add Shortcode")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._code_edit = QLineEdit(code)
        self._code_edit.setPlaceholderText("e.g.  addr  sig  myemail")
        form.addRow("Short Code:", self._code_edit)

        self._expansion_edit = QTextEdit()
        self._expansion_edit.setPlainText(expansion)
        self._expansion_edit.setPlaceholderText("Full expansion text…")
        self._expansion_edit.setMinimumHeight(120)
        form.addRow("Expansion:", self._expansion_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._code_edit.setFocus()

    def _validate_and_accept(self):
        if not self._code_edit.text().strip():
            QMessageBox.warning(self, "Validation", "Short code cannot be empty.")
            return
        if not self._expansion_edit.toPlainText().strip():
            QMessageBox.warning(self, "Validation", "Expansion text cannot be empty.")
            return
        self.accept()

    def get_values(self) -> tuple[str, str]:
        return (
            self._code_edit.text().strip().lower(),
            self._expansion_edit.toPlainText(),
        )
