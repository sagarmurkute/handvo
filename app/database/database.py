"""SQLite local persistence engine for profiles, settings, and custom phrase boards."""

from pathlib import Path
import sqlite3
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "handvo.db"


class Database:
    """Manages SQLite database connection and schema initialization."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    dwell_time REAL DEFAULT 0.80,
                    pinch_threshold REAL DEFAULT 0.05,
                    smoothing_factor REAL DEFAULT 1.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_phrases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    category TEXT NOT NULL,
                    label TEXT NOT NULL,
                    text TEXT NOT NULL,
                    accent_color TEXT DEFAULT '#38bdf8',
                    FOREIGN KEY (profile_id) REFERENCES profiles(id)
                );
                """
            )
            conn.commit()
