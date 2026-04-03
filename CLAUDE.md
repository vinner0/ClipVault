# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py

# Build standalone .exe
build.bat
```

## Architecture

ClipVault is a Windows-only system-tray utility with two features: clipboard history and text expansion.

### Threading model

| Thread | Runs | Communicates with UI via |
|--------|------|--------------------------|
| Qt main thread | PyQt6 event loop | — |
| `ClipboardMonitor` (daemon) | polls clipboard every 500 ms | `pyqtSignal` on `_Signals` QObject |
| `TextExpander` (daemon) | `pynput.keyboard.Listener` | n/a (uses pynput `Controller` to inject keys) |
| `HotkeyListener` (daemon) | `pynput.keyboard.GlobalHotKeys` | `QTimer.singleShot(0, fn)` |
| pystray (daemon) | `icon.run_detached()` — Win32 msg loop | `QTimer.singleShot(0, fn)` |

`QTimer.singleShot(0, fn)` is the standard pattern to safely call Qt methods from non-Qt threads — it queues `fn` to run on the main thread.

### Key files

- **`main.py`** — wires all components together; no logic
- **`database.py`** — `Database` class; all public methods hold `self._lock` and use per-thread `sqlite3.Connection` objects (`threading.local`) for thread safety
- **`clipboard_monitor.py`** — prefers `win32clipboard`; falls back to `pyperclip`; calls `monitor.ignore_next_change()` before programmatic clipboard writes to avoid self-loops
- **`expander.py`** — builds a rolling character buffer; on Space/Tab checks the buffer tail against all shortcodes via `db.get_shortcodes_dict()`; if matched, sends Backspace×(len+1) then `controller.type(expansion)`. The `_expanding` flag prevents re-entrancy while injecting keys.
- **`tray.py`** — `TrayManager`; also contains `_generate_icon()` which creates `assets/icon.png` via Pillow if missing
- **`startup.py`** — reads/writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`; copies exe to `%LOCALAPPDATA%\ClipVault\ClipVault.exe` before registering, so Windows can launch it at boot before Dropbox's filesystem driver loads (Dropbox `ReparsePoint` files silently fail at boot)
- **`ui/main_window.py`** — `QMainWindow` with two tabs; `closeEvent` hides instead of quitting; `on_clipboard_change()` emits `_signals.refresh_history` (pyqtSignal, safe cross-thread)
- **`ui/expander_ui.py`** — `ShortcodeDialog` (add/edit)
- **`ui/settings_dialog.py`** — Settings window (Windows startup toggle)

### Database (SQLite, stored in `%APPDATA%\ClipVault\clipvault.db`)

```
clipboard_history  id, content, copied_at, frequency
shortcodes         id, code (unique, lowercase), expansion, created_at
```

Duplicate clipboard entries increment `frequency` rather than inserting a new row.

### Window visibility

The window is hidden on startup (`window.show()` is never called during init). It appears only via tray left-click, tray menu, or `Ctrl+Shift+V`. `Qt.WindowType.Tool` keeps it out of the taskbar. `closeEvent` hides rather than closes so the app stays alive in the tray.
