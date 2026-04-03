"""
tray.py — System-tray icon and menu via pystray.

pystray is run via icon.run_detached() which starts its own daemon thread,
keeping it isolated from the PyQt6 main-thread event loop.

Tray callbacks arrive on pystray's thread; we marshal them back to Qt using
QTimer.singleShot(0, fn), which is thread-safe and executes fn in the main thread.
"""

from pathlib import Path

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem, Menu
from PyQt6.QtCore import QTimer


class TrayManager:
    def __init__(self, main_window, app):
        self._window = main_window
        self._app = app
        self._icon: pystray.Icon | None = None

    # ------------------------------------------------------------------ #
    # Setup                                                                #
    # ------------------------------------------------------------------ #

    def setup(self):
        image = self._load_or_generate_icon()

        menu = Menu(
            MenuItem("Open ClipVault", self._show_window, default=True),
            Menu.SEPARATOR,
            MenuItem("Clipboard History", self._show_history),
            MenuItem("Shortcodes", self._show_shortcodes),
            Menu.SEPARATOR,
            MenuItem("Settings", self._show_settings),
            MenuItem("Help", self._show_help),
            Menu.SEPARATOR,
            MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon("ClipVault", image, "ClipVault", menu=menu)
        self._icon.run_detached()

    def stop(self):
        if self._icon:
            self._icon.stop()

    # ------------------------------------------------------------------ #
    # Icon helpers                                                         #
    # ------------------------------------------------------------------ #

    def _load_or_generate_icon(self) -> Image.Image:
        from main import get_assets_dir
        path = get_assets_dir() / "icon.png"
        if path.exists():
            return Image.open(path)
        return _generate_icon()

    # ------------------------------------------------------------------ #
    # Menu callbacks (run on pystray thread → marshal to Qt main thread)  #
    # ------------------------------------------------------------------ #

    def _qt(self, fn):
        """Schedule fn() to run in the Qt main thread."""
        QTimer.singleShot(0, fn)

    def _show_window(self, icon=None, item=None):
        self._qt(self._window.show_and_focus)

    def _show_history(self, icon=None, item=None):
        self._qt(lambda: self._window.show_tab(0))

    def _show_shortcodes(self, icon=None, item=None):
        self._qt(lambda: self._window.show_tab(1))

    def _show_settings(self, icon=None, item=None):
        self._qt(self._window.show_settings)

    def _show_help(self, icon=None, item=None):
        self._qt(lambda: self._window.show_tab(2))

    def _quit(self, icon=None, item=None):
        self._icon.stop()
        self._qt(self._app.quit)


# ------------------------------------------------------------------ #
# Icon generation (used if assets/icon.png is missing)               #
# ------------------------------------------------------------------ #

def _generate_icon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue circle background
    draw.ellipse([1, 1, size - 2, size - 2], fill="#1565C0")

    # Clipboard body
    draw.rectangle([14, 18, 50, 56], fill="#E3F2FD", outline="#90CAF9", width=1)

    # Clip at top
    draw.rectangle([24, 13, 40, 23], fill="#90CAF9", outline="#64B5F6", width=1)
    draw.ellipse([28, 10, 36, 18], fill="#1565C0")  # hole in clip

    # Text lines
    for y in (28, 34, 40, 46):
        draw.rectangle([20, y, 44, y + 2], fill="#1976D2")

    # Save for future runs
    from main import get_assets_dir
    path = get_assets_dir() / "icon.png"
    img.save(str(path))
    return img
