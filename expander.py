"""
expander.py — Global keyboard hook for text expansion.

Listens for shortcode + Space/Tab and replaces with the full expansion.

Implementation notes
--------------------
* Uses pynput Listener (suppress=False) so normal typing is never blocked.
* When expanding, we backspace over the shortcode + trigger character and
  then type the expansion via pynput Controller.
* The _expanding flag prevents the listener from processing key events that
  we inject ourselves during expansion.
* Tab trigger caveat: in apps where Tab moves focus (browser forms), the
  focus change will happen before we can backspace it away.  Space is the
  recommended trigger for reliable cross-app behaviour.
"""

import threading
import time

from pynput import keyboard
from pynput.keyboard import Key, Controller


class TextExpander:
    def __init__(self, db):
        self._db = db
        self._controller = Controller()
        self._buffer: list[str] = []
        self._max_buf = 50
        self._listener: keyboard.Listener | None = None
        self._active = True
        self._expanding = False  # True while injecting keys; ignore our own events

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        self._active = False
        if self._listener:
            self._listener.stop()

    # ------------------------------------------------------------------ #
    # Key handler                                                          #
    # ------------------------------------------------------------------ #

    def _on_press(self, key):
        if not self._active or self._expanding:
            return

        # --- Printable character ---
        try:
            ch = key.char
            if ch:
                self._buffer.append(ch)
                if len(self._buffer) > self._max_buf:
                    self._buffer.pop(0)
            return
        except AttributeError:
            pass

        # --- Special keys ---
        if key == Key.space:
            if not self._check_and_expand():
                # Not a shortcode — keep space in buffer so partial words work
                self._buffer.append(" ")
                if len(self._buffer) > self._max_buf:
                    self._buffer.pop(0)
        elif key == Key.tab:
            # Tab changes context in most apps; just reset the buffer
            self._buffer.clear()
        elif key == Key.backspace:
            if self._buffer:
                self._buffer.pop()
        elif key in (Key.enter, Key.esc, Key.up, Key.down, Key.left, Key.right):
            self._buffer.clear()
        # All other special keys: leave buffer intact

    # ------------------------------------------------------------------ #
    # Expansion logic                                                      #
    # ------------------------------------------------------------------ #

    def _check_and_expand(self) -> bool:
        buf = "".join(self._buffer)
        for code, expansion in self._db.get_shortcodes_dict().items():
            if buf.endswith(code):
                self._buffer.clear()
                self._expanding = True
                threading.Thread(
                    target=self._do_expand,
                    args=(code, expansion),
                    daemon=True,
                ).start()
                return True
        return False

    def _do_expand(self, code: str, expansion: str):
        """Delete shortcode + trigger char, then type the full expansion."""
        try:
            time.sleep(0.05)  # Let trigger key finish registering in the target app

            # Backspace over: shortcode chars + the trigger char (space/tab) = len+1
            delete_count = len(code) + 1
            for _ in range(delete_count):
                self._controller.press(Key.backspace)
                self._controller.release(Key.backspace)
                time.sleep(0.008)

            time.sleep(0.04)
            self._controller.type(expansion)
        except Exception:
            pass
        finally:
            self._expanding = False
