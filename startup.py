"""
startup.py — Windows registry helpers for auto-start on login.
"""

import os
import sys
import winreg
from pathlib import Path

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_SETTINGS_KEY = r"Software\ClipVault"
_APP_NAME = "ClipVault"

# Install location for the exe — must be outside Dropbox/OneDrive so Windows
# can launch it at boot before any cloud-sync filesystem driver has loaded.
_LOCAL_EXE_DIR = Path(os.environ.get("LOCALAPPDATA", ".")) / "ClipVault"
_LOCAL_EXE = _LOCAL_EXE_DIR / "ClipVault.exe"


def _install_exe_locally() -> bool:
    """Copy the frozen exe to %LOCALAPPDATA%\\ClipVault\\ if running from Dropbox/cloud.
    Returns True on success, False if copy failed."""
    if not getattr(sys, "frozen", False):
        return False
    src = Path(sys.executable)
    if src == _LOCAL_EXE:
        return True  # already running from local install
    try:
        _LOCAL_EXE_DIR.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(src, _LOCAL_EXE)
        return True
    except Exception:
        return False


def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        # Always register the local copy so boot works without Dropbox loaded
        if _LOCAL_EXE.exists() or _install_exe_locally():
            return f'"{_LOCAL_EXE}"'
        return f'"{sys.executable}"'
    main_py = Path(__file__).parent / "main.py"
    return f'"{sys.executable}" "{main_py}"'


def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except OSError:
        return False


def set_startup(enabled: bool):
    if enabled:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_path())
    else:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, _APP_NAME)
        except OSError:
            pass


def _is_first_run() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SETTINGS_KEY) as key:
            winreg.QueryValueEx(key, "first_run_done")
            return False
    except OSError:
        return True


def _mark_first_run_done():
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _SETTINGS_KEY) as key:
        winreg.SetValueEx(key, "first_run_done", 0, winreg.REG_DWORD, 1)


def check_startup_prompt():
    """Show a one-time prompt asking the user about Windows startup."""
    if not _is_first_run():
        return

    from PyQt6.QtWidgets import QMessageBox

    reply = QMessageBox.question(
        None,
        "ClipVault — First Run",
        "Start ClipVault automatically when Windows starts?\n(Recommended)",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    if reply == QMessageBox.StandardButton.Yes:
        set_startup(True)

    _mark_first_run_done()
