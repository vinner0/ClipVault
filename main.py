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
import traceback
from datetime import datetime
from pathlib import Path


def get_app_dir() -> Path:
    """Return the directory containing the application files.

    - Frozen (PyInstaller --onefile): sys._MEIPASS (temp extraction dir)
    - Frozen (PyInstaller --onedir):  directory of sys.executable
    - Development:                    directory of this script
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).parent


def get_assets_dir() -> Path:
    """Return the path to the assets directory, creating it if needed."""
    d = get_app_dir() / "assets"
    d.mkdir(parents=True, exist_ok=True)
    return d


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

    # Capture any unhandled exception to the log file (critical for --noconsole builds)
    def _excepthook(exc_type, exc_value, exc_tb):
        logging.error(
            "Unhandled exception — app crashed",
            exc_info=(exc_type, exc_value, exc_tb),
        )

    sys.excepthook = _excepthook

    # Write a startup marker so we can confirm the exe ran even if it crashes early
    try:
        with open(log_dir / "startup.log", "a") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] ClipVault starting (PID {os.getpid()})\n")
    except Exception:
        pass


# ------------------------------------------------------------------ #
# Icon — generate assets/icon.png on first run if missing            #
# ------------------------------------------------------------------ #

def _ensure_icon():
    path = get_assets_dir() / "icon.png"
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
    try:
        expander.start()
    except Exception:
        logging.error("TextExpander failed to start", exc_info=True)

    # Global hotkey  Ctrl+Shift+V → show window
    hotkey = HotkeyListener(on_trigger=window.show_and_focus)
    try:
        hotkey.start()
    except Exception:
        logging.error("HotkeyListener failed to start", exc_info=True)

    # System tray (runs in its own daemon thread via run_detached)
    tray = TrayManager(window, app)
    tray.setup()

    # One-time first-run startup prompt (deferred so the event loop is running)
    QTimer.singleShot(800, check_startup_prompt)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
