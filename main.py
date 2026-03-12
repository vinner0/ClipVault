"""
ClipVault — Clipboard History Manager & Text Expander
======================================================

Install dependencies:
    pip install -r requirements.txt

Run:
    python main.py

Build standalone .exe:
    build.bat
"""

import logging
import os
import sys
from pathlib import Path


# ------------------------------------------------------------------ #
# Logging — errors go to %APPDATA%\ClipVault\clipvault.log            #
# ------------------------------------------------------------------ #

def _setup_logging():
    log_dir = Path(os.environ.get("APPDATA", ".")) / "ClipVault"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_dir / "clipvault.log"),
        level=logging.ERROR,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    )


# ------------------------------------------------------------------ #
# Icon — generate assets/icon.png on first run if missing            #
# ------------------------------------------------------------------ #

def _ensure_icon():
    path = Path("assets") / "icon.png"
    path.parent.mkdir(exist_ok=True)
    if not path.exists():
        from tray import _generate_icon
        _generate_icon()


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def main():
    _setup_logging()
    _ensure_icon()

    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # keep alive when window is hidden
    app.setApplicationName("ClipVault")
    app.setApplicationDisplayName("ClipVault")

    from database import Database
    from clipboard_monitor import ClipboardMonitor
    from expander import TextExpander
    from hotkey import HotkeyListener
    from tray import TrayManager
    from ui.main_window import MainWindow
    from startup import check_startup_prompt

    db = Database()

    # Background clipboard watcher (created before window so we can pass it in)
    monitor = ClipboardMonitor(db)
    window = MainWindow(db, monitor=monitor)
    monitor._on_new_entry = window.on_clipboard_change
    monitor.start()

    # Global text-expander keyboard hook
    expander = TextExpander(db)
    expander.start()

    # Global hotkey  Ctrl+Shift+V → show window
    hotkey = HotkeyListener(on_trigger=window.show_and_focus)
    hotkey.start()

    # System tray (runs in its own daemon thread via run_detached)
    tray = TrayManager(window, app)
    tray.setup()

    # One-time first-run startup prompt (deferred so the event loop is running)
    QTimer.singleShot(800, check_startup_prompt)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
