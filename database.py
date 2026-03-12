"""
database.py — Thread-safe SQLite operations for ClipVault.
All public methods acquire a lock and use per-thread connections.
"""

import sqlite3
import threading
import os
from pathlib import Path


def _data_dir() -> Path:
    base = Path(os.environ.get("APPDATA", "."))
    d = base / "ClipVault"
    d.mkdir(parents=True, exist_ok=True)
    return d


class Database:
    def __init__(self):
        self._db_path = str(_data_dir() / "clipvault.db")
        self._lock = threading.Lock()
        self._local = threading.local()
        self._init_db()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        with self._lock:
            c = self._conn()
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS clipboard_history (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    content    TEXT    NOT NULL,
                    copied_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                    frequency  INTEGER  DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS shortcodes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    code       TEXT UNIQUE NOT NULL,
                    expansion  TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            c.commit()

    # ------------------------------------------------------------------ #
    # Clipboard history                                                    #
    # ------------------------------------------------------------------ #

    def add_clipboard_entry(self, content: str) -> bool:
        """Insert or update an entry.  Returns True if it was a new entry."""
        with self._lock:
            c = self._conn()
            row = c.execute(
                "SELECT id FROM clipboard_history WHERE content = ?", (content,)
            ).fetchone()
            if row:
                c.execute(
                    "UPDATE clipboard_history "
                    "SET copied_at = CURRENT_TIMESTAMP, frequency = frequency + 1 "
                    "WHERE id = ?",
                    (row[0],),
                )
                c.commit()
                return False
            c.execute(
                "INSERT INTO clipboard_history (content) VALUES (?)", (content,)
            )
            c.commit()
            return True

    def get_history(self, search: str = "", limit: int = 500):
        with self._lock:
            c = self._conn()
            if search:
                return c.execute(
                    "SELECT id, content, copied_at, frequency "
                    "FROM clipboard_history "
                    "WHERE content LIKE ? "
                    "ORDER BY copied_at DESC LIMIT ?",
                    (f"%{search}%", limit),
                ).fetchall()
            return c.execute(
                "SELECT id, content, copied_at, frequency "
                "FROM clipboard_history "
                "ORDER BY copied_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def delete_history_entry(self, entry_id: int):
        with self._lock:
            c = self._conn()
            c.execute("DELETE FROM clipboard_history WHERE id = ?", (entry_id,))
            c.commit()

    def clear_history(self):
        with self._lock:
            c = self._conn()
            c.execute("DELETE FROM clipboard_history")
            c.commit()

    # ------------------------------------------------------------------ #
    # Shortcodes                                                           #
    # ------------------------------------------------------------------ #

    def add_shortcode(self, code: str, expansion: str):
        with self._lock:
            c = self._conn()
            c.execute(
                "INSERT OR REPLACE INTO shortcodes (code, expansion) VALUES (?, ?)",
                (code.strip().lower(), expansion),
            )
            c.commit()

    def update_shortcode(self, sc_id: int, code: str, expansion: str):
        with self._lock:
            c = self._conn()
            c.execute(
                "UPDATE shortcodes SET code = ?, expansion = ? WHERE id = ?",
                (code.strip().lower(), expansion, sc_id),
            )
            c.commit()

    def delete_shortcode(self, sc_id: int):
        with self._lock:
            c = self._conn()
            c.execute("DELETE FROM shortcodes WHERE id = ?", (sc_id,))
            c.commit()

    def get_shortcodes(self, search: str = ""):
        with self._lock:
            c = self._conn()
            if search:
                return c.execute(
                    "SELECT id, code, expansion, created_at FROM shortcodes "
                    "WHERE code LIKE ? OR expansion LIKE ? ORDER BY code",
                    (f"%{search}%", f"%{search}%"),
                ).fetchall()
            return c.execute(
                "SELECT id, code, expansion, created_at FROM shortcodes ORDER BY code"
            ).fetchall()

    def get_shortcodes_dict(self) -> dict:
        """Returns {code: expansion} for use by the text expander."""
        with self._lock:
            c = self._conn()
            rows = c.execute("SELECT code, expansion FROM shortcodes").fetchall()
            return {row[0]: row[1] for row in rows}
