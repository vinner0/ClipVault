"""
main_window.py — Main application window with Clipboard History and Shortcodes tabs.

Thread safety
-------------
on_clipboard_change() is called from the ClipboardMonitor thread.
It emits _signals.refresh via a QObject signal, which Qt automatically
delivers on the main thread (QueuedConnection across threads).
"""

import json

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ui.expander_ui import ShortcodeDialog


# ------------------------------------------------------------------ #
# Signal bridge (emitted on any thread, received on the main thread)  #
# ------------------------------------------------------------------ #

class _Signals(QObject):
    refresh_history = pyqtSignal()


# ------------------------------------------------------------------ #
# Main window                                                          #
# ------------------------------------------------------------------ #

_STYLE = """
QMainWindow, QDialog { background: #1e1e2e; }
QWidget          { background: #1e1e2e; color: #cdd6f4;
                   font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
QTabWidget::pane { border: none; }
QTabBar::tab          { background: #313244; color: #a6adc8;
                        padding: 8px 22px; border: none; margin-right: 2px; }
QTabBar::tab:selected { background: #1e1e2e; color: #cdd6f4;
                        border-bottom: 2px solid #89b4fa; }

QLineEdit { background: #313244; border: 1px solid #45475a; border-radius: 6px;
            padding: 6px 10px; color: #cdd6f4; }
QLineEdit:focus { border-color: #89b4fa; }

QListWidget { background: #181825; border: 1px solid #313244;
              border-radius: 6px; outline: none; }
QListWidget::item          { padding: 3px 10px; border-bottom: 1px solid #2a2a3d; }
QListWidget::item:selected { background: #313244; color: #89b4fa; }
QListWidget::item:hover    { background: #252535; }

QTableWidget { background: #181825; border: 1px solid #313244;
               border-radius: 6px; outline: none; gridline-color: #313244; }
QTableWidget::item          { padding: 6px 8px; }
QTableWidget::item:selected { background: #313244; color: #89b4fa; }
QHeaderView::section { background: #313244; color: #a6adc8;
                       padding: 6px 8px; border: none;
                       border-right: 1px solid #45475a; }

QPushButton { background: #313244; color: #cdd6f4; border: 1px solid #45475a;
              border-radius: 6px; padding: 6px 14px; }
QPushButton:hover   { background: #45475a; border-color: #89b4fa; }
QPushButton:pressed { background: #585b70; }
QPushButton#danger  { color: #f38ba8; border-color: #f38ba8; }
QPushButton#danger:hover { background: #3d1f25; }

QMenu { background: #313244; border: 1px solid #45475a;
        border-radius: 6px; padding: 4px; }
QMenu::item          { padding: 6px 20px; border-radius: 4px; }
QMenu::item:selected { background: #45475a; }

QStatusBar { background: #181825; color: #a6adc8; border-top: 1px solid #313244; }

QTextBrowser { background: #181825; border: 1px solid #313244;
               border-radius: 6px; padding: 8px; }

QScrollBar:vertical           { background: #181825; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical   { background: #45475a; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
"""


_HELP_HTML = """
<style>
  body   { background:#1e1e2e; color:#cdd6f4;
           font-family:'Segoe UI',Arial,sans-serif; font-size:13px;
           margin:0; padding:4px 0; }
  h2     { color:#89b4fa; font-size:15px; margin:18px 0 6px 0;
           border-bottom:1px solid #313244; padding-bottom:4px; }
  h2:first-of-type { margin-top:4px; }
  table  { border-collapse:collapse; width:100%; margin-bottom:4px; }
  td     { padding:5px 8px; vertical-align:top; }
  td.key { color:#cba6f7; font-family:monospace; font-size:13px;
           white-space:nowrap; width:1%; padding-right:18px; }
  td.desc{ color:#cdd6f4; }
  .note  { color:#a6adc8; font-size:12px; margin:2px 0 6px 18px; }
  tr:hover td { background:#252535; }
</style>

<h2>Opening ClipVault</h2>
<table>
  <tr><td class="key">Ctrl+Shift+V</td><td class="desc">Show window from anywhere (global hotkey)</td></tr>
  <tr><td class="key">Tray icon click</td><td class="desc">Show window</td></tr>
  <tr><td class="key">Tray → Open ClipVault</td><td class="desc">Show window via right-click menu</td></tr>
</table>

<h2>Clipboard History</h2>
<p class="note">Every text you copy anywhere in Windows is captured automatically.</p>
<table>
  <tr><td class="key">Click item</td><td class="desc">Copy that entry back to clipboard</td></tr>
  <tr><td class="key">Enter / Return</td><td class="desc">Copy the selected item</td></tr>
  <tr><td class="key">Right-click item</td><td class="desc">Copy &nbsp;•&nbsp; Save as Shortcode &nbsp;•&nbsp; Delete</td></tr>
  <tr><td class="key">Search bar</td><td class="desc">Filter history by keyword</td></tr>
  <tr><td class="key">Clear All</td><td class="desc">Permanently delete all history (asks for confirmation)</td></tr>
</table>

<h2>Text Expander — Shortcodes</h2>
<p class="note">Type a shortcode in any app, then press Space or Tab to expand it.</p>
<table>
  <tr><td class="key">shortcode + Space</td><td class="desc">Expand to full text <em>(recommended trigger)</em></td></tr>
  <tr><td class="key">shortcode + Tab</td><td class="desc">Expand to full text <em>(may move focus in browser forms)</em></td></tr>
  <tr><td class="key">Click row</td><td class="desc">Copy the expansion to clipboard</td></tr>
  <tr><td class="key">Double-click row</td><td class="desc">Edit the shortcode</td></tr>
  <tr><td class="key">+ Add</td><td class="desc">Create a new shortcode</td></tr>
  <tr><td class="key">Edit</td><td class="desc">Edit the selected shortcode</td></tr>
  <tr><td class="key">Delete</td><td class="desc">Delete the selected shortcode</td></tr>
  <tr><td class="key">Export…</td><td class="desc">Save all shortcodes to a JSON file</td></tr>
  <tr><td class="key">Import…</td><td class="desc">Load shortcodes from a JSON file</td></tr>
</table>

<h2>Window Shortcuts</h2>
<table>
  <tr><td class="key">Escape</td><td class="desc">Hide window (app keeps running in tray)</td></tr>
  <tr><td class="key">Enter / Return</td><td class="desc">Copy selected clipboard item</td></tr>
</table>

<h2>Tray Menu</h2>
<table>
  <tr><td class="key">Open ClipVault</td><td class="desc">Show main window</td></tr>
  <tr><td class="key">Clipboard History</td><td class="desc">Open directly on the History tab</td></tr>
  <tr><td class="key">Shortcodes</td><td class="desc">Open directly on the Shortcodes tab</td></tr>
  <tr><td class="key">Settings</td><td class="desc">Toggle launch at Windows startup</td></tr>
  <tr><td class="key">Quit</td><td class="desc">Exit ClipVault completely</td></tr>
</table>

<h2>Tips</h2>
<table>
  <tr><td class="key">Closing the window</td><td class="desc">Hides it — ClipVault keeps running in the background</td></tr>
  <tr><td class="key">Duplicate copies</td><td class="desc">Counted as frequency (×2, ×3…) rather than duplicate entries</td></tr>
  <tr><td class="key">Shortcode trigger</td><td class="desc">Use Space in most apps; avoid Tab in web forms</td></tr>
  <tr><td class="key">Save clipboard as shortcode</td><td class="desc">Right-click any history item → Save as Shortcode</td></tr>
</table>
"""


class MainWindow(QMainWindow):
    def __init__(self, db, monitor=None):
        super().__init__()
        self._db = db
        self._monitor = monitor
        self._signals = _Signals()
        self._signals.refresh_history.connect(self._load_history)
        self._hist_search_timer = QTimer()
        self._hist_search_timer.setSingleShot(True)
        self._hist_search_timer.setInterval(150)
        self._hist_search_timer.timeout.connect(self._load_history)
        self._sc_search_timer = QTimer()
        self._sc_search_timer.setSingleShot(True)
        self._sc_search_timer.setInterval(150)
        self._sc_search_timer.timeout.connect(self._load_shortcodes)

        self._build_ui()
        self._setup_shortcuts()
        self.setStyleSheet(_STYLE)
        self._load_history()
        self._load_shortcodes()

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.setWindowTitle("ClipVault")
        self.setMinimumSize(640, 520)
        self.resize(740, 620)

        # Appear in the taskbar so the app can be pinned
        self.setWindowFlag(Qt.WindowType.Tool, False)

        self._center()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs)

        self._tabs.addTab(self._build_history_tab(), "  Clipboard History  ")
        self._tabs.addTab(self._build_shortcodes_tab(), "  Shortcodes  ")
        self._tabs.addTab(self._build_help_tab(), "  Help  ")

        self.statusBar()  # create status bar

    def _center(self):
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(
            (geo.width() - self.width()) // 2,
            (geo.height() - self.height()) // 2,
        )

    # ---------------------------------------------------------------- #
    # History tab                                                        #
    # ---------------------------------------------------------------- #

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # Search row
        row = QHBoxLayout()
        self._hist_search = QLineEdit()
        self._hist_search.setPlaceholderText("Search clipboard history…")
        self._hist_search.textChanged.connect(self._hist_search_timer.start)
        row.addWidget(self._hist_search)

        clear_btn = QPushButton("Clear All")
        clear_btn.setObjectName("danger")
        clear_btn.setFixedWidth(82)
        clear_btn.clicked.connect(self._clear_history)
        row.addWidget(clear_btn)
        lay.addLayout(row)

        # List
        self._hist_list = QListWidget()
        self._hist_list.setAlternatingRowColors(False)
        self._hist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._hist_list.customContextMenuRequested.connect(self._history_context_menu)
        self._hist_list.itemClicked.connect(self._copy_and_paste_history_item)
        self._hist_list.setToolTip("Click to copy  •  Right-click for options")
        lay.addWidget(self._hist_list)

        return w

    # ---------------------------------------------------------------- #
    # Shortcodes tab                                                     #
    # ---------------------------------------------------------------- #

    def _build_shortcodes_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # Toolbar
        bar = QHBoxLayout()
        self._sc_search = QLineEdit()
        self._sc_search.setPlaceholderText("Search shortcodes…")
        self._sc_search.textChanged.connect(self._sc_search_timer.start)
        bar.addWidget(self._sc_search)

        for label, slot in (
            ("+ Add", self._add_shortcode),
            ("Edit", self._edit_shortcode),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            bar.addWidget(btn)

        del_btn = QPushButton("Delete")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self._delete_shortcode)
        bar.addWidget(del_btn)

        exp_btn = QPushButton("Export…")
        exp_btn.clicked.connect(self._export_shortcodes)
        bar.addWidget(exp_btn)

        imp_btn = QPushButton("Import…")
        imp_btn.clicked.connect(self._import_shortcodes)
        bar.addWidget(imp_btn)

        lay.addLayout(bar)

        # Table
        self._sc_table = QTableWidget(0, 3)
        self._sc_table.setHorizontalHeaderLabels(["Short Code", "Expansion", "Created"])
        hh = self._sc_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._sc_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._sc_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._sc_table.doubleClicked.connect(self._edit_shortcode)
        self._sc_table.cellClicked.connect(self._sc_single_click)
        lay.addWidget(self._sc_table)

        return w

    # ---------------------------------------------------------------- #
    # Help tab                                                          #
    # ---------------------------------------------------------------- #

    def _build_help_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(_HELP_HTML)
        lay.addWidget(browser)
        return w

    # ------------------------------------------------------------------ #
    # Shortcuts                                                            #
    # ------------------------------------------------------------------ #

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Escape"), self, self.hide)
        QShortcut(QKeySequence("Return"), self, self._copy_selected_history)
        QShortcut(QKeySequence("Enter"), self, self._copy_selected_history)

    # ------------------------------------------------------------------ #
    # History operations                                                   #
    # ------------------------------------------------------------------ #

    def _load_history(self):
        search = self._hist_search.text() if hasattr(self, "_hist_search") else ""
        rows = self._db.get_history(search=search)

        self._hist_list.clear()
        for row in rows:
            entry_id, content, copied_at, frequency = (
                row[0], row[1], row[2], row[3],
            )
            first_line = content.split("\n")[0]
            if len(first_line) > 120:
                first_line = first_line[:120] + "…"
            elif len(content) > len(first_line):
                first_line += "…"

            ts = copied_at[:16] if copied_at and len(copied_at) >= 16 else (copied_at or "")
            freq_str = f"  ×{frequency}" if frequency > 1 else ""
            tooltip = content + f"\n\n— {ts}{freq_str}"

            item = QListWidgetItem(first_line)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, content)
            item.setToolTip(tooltip)
            self._hist_list.addItem(item)

    def _copy_history_item(self, item: QListWidgetItem):
        content = item.data(Qt.ItemDataRole.UserRole + 1)
        if content:
            if self._monitor:
                self._monitor.ignore_next_change()
            QApplication.clipboard().setText(content)
            self.statusBar().showMessage("Copied!", 1500)

    def _copy_and_paste_history_item(self, item: QListWidgetItem):
        content = item.data(Qt.ItemDataRole.UserRole + 1)
        if content:
            if self._monitor:
                self._monitor.ignore_next_change()
            QApplication.clipboard().setText(content)
            self.hide()
            QTimer.singleShot(150, self._paste_to_active_window)

    def _paste_to_active_window(self):
        from pynput.keyboard import Controller, Key
        kb = Controller()
        with kb.pressed(Key.ctrl):
            kb.press("v")
            kb.release("v")

    def _copy_selected_history(self):
        selected = self._hist_list.selectedItems()
        if selected:
            self._copy_and_paste_history_item(selected[0])

    def _history_context_menu(self, pos):
        item = self._hist_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        menu.addAction("Copy", lambda: self._copy_history_item(item))
        menu.addAction(
            "Save as Shortcode…", lambda: self._save_as_shortcode(item)
        )
        menu.addSeparator()
        menu.addAction("Delete", lambda: self._delete_history_item(item))
        menu.exec(self._hist_list.mapToGlobal(pos))

    def _delete_history_item(self, item: QListWidgetItem):
        self._db.delete_history_entry(item.data(Qt.ItemDataRole.UserRole))
        self._load_history()

    def _clear_history(self):
        if (
            QMessageBox.question(
                self,
                "Clear History",
                "Delete all clipboard history?  This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self._db.clear_history()
            self._load_history()

    def _save_as_shortcode(self, item: QListWidgetItem):
        content = item.data(Qt.ItemDataRole.UserRole + 1)
        dlg = ShortcodeDialog(self, expansion=content)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            code, expansion = dlg.get_values()
            self._db.add_shortcode(code, expansion)
            self._load_shortcodes()
            self._tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------ #
    # Shortcode operations                                                 #
    # ------------------------------------------------------------------ #

    def _load_shortcodes(self):
        search = self._sc_search.text() if hasattr(self, "_sc_search") else ""
        rows = self._db.get_shortcodes(search=search)

        self._sc_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            sc_id, code, expansion, created_at = row[0], row[1], row[2], row[3]

            code_item = QTableWidgetItem(code)
            code_item.setData(Qt.ItemDataRole.UserRole, sc_id)

            preview = expansion[:100].replace("\n", " ↵ ")
            exp_item = QTableWidgetItem(preview)
            exp_item.setData(Qt.ItemDataRole.UserRole, expansion)  # full text
            exp_item.setToolTip(expansion[:600])

            date_item = QTableWidgetItem(
                (created_at or "")[:10]
            )

            self._sc_table.setItem(i, 0, code_item)
            self._sc_table.setItem(i, 1, exp_item)
            self._sc_table.setItem(i, 2, date_item)

    def _sc_single_click(self, row: int, _col: int):
        """Single-click on shortcode row copies the full expansion."""
        exp_item = self._sc_table.item(row, 1)
        if exp_item:
            full = exp_item.data(Qt.ItemDataRole.UserRole) or exp_item.text()
            QApplication.clipboard().setText(full)
            self.statusBar().showMessage("Expansion copied!", 1500)

    def _selected_sc_row(self) -> int:
        return self._sc_table.currentRow()

    def _add_shortcode(self):
        dlg = ShortcodeDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            code, expansion = dlg.get_values()
            self._db.add_shortcode(code, expansion)
            self._load_shortcodes()

    def _edit_shortcode(self):
        row = self._selected_sc_row()
        if row < 0:
            return
        sc_id = self._sc_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        code = self._sc_table.item(row, 0).text()
        expansion = self._sc_table.item(row, 1).data(Qt.ItemDataRole.UserRole)

        dlg = ShortcodeDialog(self, code=code, expansion=expansion)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_code, new_expansion = dlg.get_values()
            self._db.update_shortcode(sc_id, new_code, new_expansion)
            self._load_shortcodes()

    def _delete_shortcode(self):
        row = self._selected_sc_row()
        if row < 0:
            return
        code = self._sc_table.item(row, 0).text()
        sc_id = self._sc_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        if (
            QMessageBox.question(
                self,
                "Delete Shortcode",
                f'Delete shortcode "{code}"?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self._db.delete_shortcode(sc_id)
            self._load_shortcodes()

    def _export_shortcodes(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Shortcodes", "shortcodes.json", "JSON Files (*.json)"
        )
        if not path:
            return
        rows = self._db.get_shortcodes()
        data = [{"code": r[1], "expansion": r[2]} for r in rows]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        self.statusBar().showMessage(f"Exported {len(data)} shortcodes", 2000)

    def _import_shortcodes(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Shortcodes", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            count = 0
            for item in data:
                if "code" in item and "expansion" in item:
                    self._db.add_shortcode(item["code"], item["expansion"])
                    count += 1
            self._load_shortcodes()
            self.statusBar().showMessage(f"Imported {count} shortcodes", 2000)
        except Exception as exc:
            QMessageBox.warning(self, "Import Error", str(exc))

    # ------------------------------------------------------------------ #
    # Public interface (called from other threads / tray)                 #
    # ------------------------------------------------------------------ #

    def on_clipboard_change(self, text: str, is_new: bool):
        """Called from ClipboardMonitor thread — safe via queued signal."""
        self._signals.refresh_history.emit()

    def show_and_focus(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self._hist_search.setFocus()
        self._hist_search.selectAll()

    def show_tab(self, index: int):
        self.show_and_focus()
        self._tabs.setCurrentIndex(index)

    def show_settings(self):
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self).exec()

    # ------------------------------------------------------------------ #
    # Window events                                                        #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        """Hide to tray instead of quitting."""
        event.ignore()
        self.hide()
