"""
hotkey.py — Global hotkey listener (Ctrl+Shift+V) via pynput.

pynput fires the callback on its own thread; marshal back to Qt main
thread using QTimer.singleShot(0, fn) — same pattern as tray.py.
"""

from pynput import keyboard
from PyQt6.QtCore import QTimer


class HotkeyListener:
    def __init__(self, on_trigger):
        self._on_trigger = on_trigger
        self._listener: keyboard.GlobalHotKeys | None = None

    def _fire(self):
        QTimer.singleShot(0, self._on_trigger)

    def start(self):
        self._listener = keyboard.GlobalHotKeys(
            {"<ctrl>+<shift>+v": self._fire}
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
