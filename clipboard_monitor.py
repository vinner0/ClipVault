"""
clipboard_monitor.py — Background thread that polls the clipboard every 500 ms.
Uses win32clipboard when available, falls back to pyperclip.
"""

import threading
import time

try:
    import win32clipboard
    import win32con

    _USE_WIN32 = True
except ImportError:
    import pyperclip  # type: ignore

    _USE_WIN32 = False


class ClipboardMonitor(threading.Thread):
    def __init__(self, db, on_new_entry=None):
        """
        on_new_entry(text: str, is_new: bool) is called on the monitor thread
        whenever the clipboard changes.  Use Qt signals to marshal to the UI thread.
        """
        super().__init__(daemon=True, name="ClipboardMonitor")
        self._db = db
        self._on_new_entry = on_new_entry
        self._last_text: str | None = None
        self._running = True
        self._ignore_once = False  # set before programmatic clipboard writes

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def ignore_next_change(self):
        """Suppress the next clipboard-change event (called before we set
        the clipboard ourselves so the monitor does not re-add our write)."""
        self._ignore_once = True

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------ #
    # Thread body                                                          #
    # ------------------------------------------------------------------ #

    def run(self):
        while self._running:
            try:
                text = self._read_clipboard()
                if text and text != self._last_text:
                    self._last_text = text
                    if self._ignore_once:
                        self._ignore_once = False
                    else:
                        is_new = self._db.add_clipboard_entry(text)
                        if self._on_new_entry:
                            self._on_new_entry(text, is_new)
            except Exception:
                pass
            time.sleep(0.5)

    # ------------------------------------------------------------------ #
    # Clipboard read helpers                                               #
    # ------------------------------------------------------------------ #

    def _read_clipboard(self) -> str | None:
        if _USE_WIN32:
            return self._read_win32()
        return self._read_pyperclip()

    @staticmethod
    def _read_win32() -> str | None:
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                stripped = text.strip() if text else ""
                return stripped or None
            return None
        except Exception:
            return None
        finally:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

    @staticmethod
    def _read_pyperclip() -> str | None:
        try:
            text = pyperclip.paste()
            stripped = text.strip() if text else ""
            return stripped or None
        except Exception:
            return None
