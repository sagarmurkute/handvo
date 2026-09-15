"""SQLite local persistence engine for HANDVO profiles, calibration, phrases, and learned frequencies."""

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

            # Learned phrase transition frequency table for smart predictions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS phrase_frequencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prev_token TEXT NOT NULL,
                    next_token TEXT NOT NULL,
                    category_id TEXT DEFAULT 'common',
                    frequency INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(prev_token, next_token)
                );
                """
            )

            # High-priority emergency actions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS emergency_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    speech_text TEXT NOT NULL,
                    icon TEXT DEFAULT '🚨',
                    accent_color TEXT DEFAULT '#ef4444',
                    sort_order INTEGER DEFAULT 0,
                    is_enabled BOOLEAN DEFAULT 1
                );
                """
            )

            # Seed default emergency actions if none exist
            cursor.execute("SELECT COUNT(*) FROM emergency_actions;")
            if cursor.fetchone()[0] == 0:
                defaults = [
                    ("Call Help", "Emergency! Please help me immediately!", "🚨", "#ef4444", 0),
                    ("I Need a Doctor", "I need a doctor right now!", "👨‍⚕️", "#dc2626", 1),
                    ("I'm in Pain", "I am experiencing severe pain!", "⚡", "#f97316", 2),
                    ("I Can't Breathe", "I cannot breathe, please help me quickly!", "🫁", "#b91c1c", 3),
                    ("Yes", "Yes", "✅", "#22c55e", 4),
                    ("No", "No", "❌", "#64748b", 5),
                ]
                cursor.executemany(
                    """
                    INSERT INTO emergency_actions (label, speech_text, icon, accent_color, sort_order, is_enabled)
                    VALUES (?, ?, ?, ?, ?, 1);
                    """,
                    defaults,
                )
