"""SQLite local persistence engine for HANDVO profiles, calibration, and settings."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator, Optional

DB_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "handvo.db"


class Database:
    """Manages SQLite database connection, table schemas, and migrations."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_PATH
        self._init_db()

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that automatically commits transactions and closes connection."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    dominant_hand TEXT DEFAULT 'Right',
                    neutral_x REAL DEFAULT 0.50,
                    neutral_y REAL DEFAULT 0.50,
                    range_min_x REAL DEFAULT 0.20,
                    range_max_x REAL DEFAULT 0.80,
                    range_min_y REAL DEFAULT 0.20,
                    range_max_y REAL DEFAULT 0.80,
                    open_hand_span REAL DEFAULT 0.25,
                    pinch_threshold REAL DEFAULT 0.05,
                    pinch_release_threshold REAL DEFAULT 0.08,
                    dwell_time REAL DEFAULT 0.80,
                    smoothing_factor REAL DEFAULT 1.50,
                    calibration_quality TEXT DEFAULT 'GOOD',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Ensure any missing columns are added for older schemas
            columns_to_ensure = [
                ("dominant_hand", "TEXT DEFAULT 'Right'"),
                ("neutral_x", "REAL DEFAULT 0.50"),
                ("neutral_y", "REAL DEFAULT 0.50"),
                ("range_min_x", "REAL DEFAULT 0.20"),
                ("range_max_x", "REAL DEFAULT 0.80"),
                ("range_min_y", "REAL DEFAULT 0.20"),
                ("range_max_y", "REAL DEFAULT 0.80"),
                ("open_hand_span", "REAL DEFAULT 0.25"),
                ("pinch_release_threshold", "REAL DEFAULT 0.08"),
                ("calibration_quality", "TEXT DEFAULT 'GOOD'"),
            ]
            cursor.execute("PRAGMA table_info(profiles);")
            existing_cols = {col[1] for col in cursor.fetchall()}
            for col_name, col_type in columns_to_ensure:
                if col_name not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE profiles ADD COLUMN {col_name} {col_type};")
                    except Exception:
                        pass

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
