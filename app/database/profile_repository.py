"""Repository pattern for managing user profile and calibration persistence."""

from typing import List, Optional
from app.database.database import Database
from app.database.models import UserProfile


class ProfileRepository:
    """Handles CRUD operations for user profiles and calibration data."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self.db = database or Database()

    def get_or_create_default(self) -> UserProfile:
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, dominant_hand, neutral_x, neutral_y,
                       range_min_x, range_max_x, range_min_y, range_max_y,
                       open_hand_span, pinch_threshold, pinch_release_threshold,
                       dwell_time, smoothing_factor, calibration_quality
                FROM profiles LIMIT 1;
                """
            )
            row = cursor.fetchone()
            if row:
                return UserProfile(
                    id=row[0],
                    name=row[1] or "Default User",
                    dominant_hand=row[2] or "Right",
                    neutral_x=float(row[3] if row[3] is not None else 0.50),
                    neutral_y=float(row[4] if row[4] is not None else 0.50),
                    range_min_x=float(row[5] if row[5] is not None else 0.20),
                    range_max_x=float(row[6] if row[6] is not None else 0.80),
                    range_min_y=float(row[7] if row[7] is not None else 0.20),
                    range_max_y=float(row[8] if row[8] is not None else 0.80),
                    open_hand_span=float(row[9] if row[9] is not None else 0.25),
                    pinch_threshold=float(row[10] if row[10] is not None else 0.05),
                    pinch_release_threshold=float(row[11] if row[11] is not None else 0.08),
                    dwell_time=float(row[12] if row[12] is not None else 0.80),
                    smoothing_factor=float(row[13] if row[13] is not None else 1.50),
                    calibration_quality=row[14] or "GOOD",
                )

            cursor.execute(
                """
                INSERT INTO profiles (
                    name, dominant_hand, neutral_x, neutral_y,
                    range_min_x, range_max_x, range_min_y, range_max_y,
                    open_hand_span, pinch_threshold, pinch_release_threshold,
                    dwell_time, smoothing_factor, calibration_quality
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                ("Default User", "Right", 0.50, 0.50, 0.20, 0.80, 0.20, 0.80, 0.25, 0.05, 0.08, 0.80, 1.50, "GOOD"),
            )
            return UserProfile(id=cursor.lastrowid)

    def save_calibration(self, profile: UserProfile) -> bool:
        """Save or update user profile with calibrated metrics."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            if profile.id is not None:
                cursor.execute(
                    """
                    UPDATE profiles SET
                        dominant_hand = ?,
                        neutral_x = ?,
                        neutral_y = ?,
                        range_min_x = ?,
                        range_max_x = ?,
                        range_min_y = ?,
                        range_max_y = ?,
                        open_hand_span = ?,
                        pinch_threshold = ?,
                        pinch_release_threshold = ?,
                        dwell_time = ?,
                        smoothing_factor = ?,
                        calibration_quality = ?
                    WHERE id = ?;
                    """,
                    (
                        profile.dominant_hand,
                        profile.neutral_x,
                        profile.neutral_y,
                        profile.range_min_x,
                        profile.range_max_x,
                        profile.range_min_y,
                        profile.range_max_y,
                        profile.open_hand_span,
                        profile.pinch_threshold,
                        profile.pinch_release_threshold,
                        profile.dwell_time,
                        profile.smoothing_factor,
                        profile.calibration_quality,
                        profile.id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO profiles (
                        name, dominant_hand, neutral_x, neutral_y,
                        range_min_x, range_max_x, range_min_y, range_max_y,
                        open_hand_span, pinch_threshold, pinch_release_threshold,
                        dwell_time, smoothing_factor, calibration_quality
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        profile.name,
                        profile.dominant_hand,
                        profile.neutral_x,
                        profile.neutral_y,
                        profile.range_min_x,
                        profile.range_max_x,
                        profile.range_min_y,
                        profile.range_max_y,
                        profile.open_hand_span,
                        profile.pinch_threshold,
                        profile.pinch_release_threshold,
                        profile.dwell_time,
                        profile.smoothing_factor,
                        profile.calibration_quality,
                    ),
                )
                profile.id = cursor.lastrowid
            return True
