"""Repository pattern for managing user profile persistence."""

from typing import List, Optional
from app.database.database import Database
from app.database.models import UserProfile


class ProfileRepository:
    """Handles CRUD operations for user profiles."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self.db = database or Database()

    def get_or_create_default(self) -> UserProfile:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, dwell_time, pinch_threshold, smoothing_factor FROM profiles LIMIT 1;")
            row = cursor.fetchone()
            if row:
                return UserProfile(id=row[0], name=row[1], dwell_time=row[2], pinch_threshold=row[3], smoothing_factor=row[4])

            cursor.execute(
                "INSERT INTO profiles (name, dwell_time, pinch_threshold, smoothing_factor) VALUES (?, ?, ?, ?);",
                ("Default", 0.80, 0.05, 1.5),
            )
            conn.commit()
            return UserProfile(id=cursor.lastrowid, name="Default", dwell_time=0.80, pinch_threshold=0.05, smoothing_factor=1.5)
