"""Repository pattern for managing user profile, calibration, and learned phrase frequencies."""

from typing import List, Optional, Tuple
from app.database.database import Database
from app.database.models import EmergencyAction, UserProfile


class ProfileRepository:
    """Handles CRUD operations for user profiles, calibration data, and prediction learning."""

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

    def record_phrase_usage(self, prev_token: str, next_token: str, category_id: str = "common") -> None:
        """Increment learned selection frequency for (prev_token -> next_token) pair in SQLite."""
        p_clean = prev_token.strip().lower()
        n_clean = next_token.strip()
        if not n_clean:
            return

        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO phrase_frequencies (prev_token, next_token, category_id, frequency, last_used)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(prev_token, next_token) DO UPDATE SET
                    frequency = frequency + 1,
                    last_used = CURRENT_TIMESTAMP;
                """,
                (p_clean, n_clean, category_id),
            )

    def get_top_predictions(self, prev_token: str, limit: int = 5) -> List[Tuple[str, int]]:
        """Retrieve most frequent next tokens for given prefix context."""
        p_clean = prev_token.strip().lower()
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT next_token, frequency
                FROM phrase_frequencies
                WHERE prev_token = ?
                ORDER BY frequency DESC, last_used DESC
                LIMIT ?;
                """,
                (p_clean, limit),
            )
            return cursor.fetchall()

    def get_emergency_actions(self, enabled_only: bool = True) -> List[EmergencyAction]:
        """Retrieve configured emergency actions ordered by sort_order."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, label, speech_text, icon, accent_color, sort_order, is_enabled
                FROM emergency_actions
            """
            if enabled_only:
                query += " WHERE is_enabled = 1"
            query += " ORDER BY sort_order ASC, id ASC;"

            cursor.execute(query)
            rows = cursor.fetchall()
            return [
                EmergencyAction(
                    id=row[0],
                    label=row[1],
                    speech_text=row[2],
                    icon=row[3] or "🚨",
                    accent_color=row[4] or "#ef4444",
                    sort_order=row[5] or 0,
                    is_enabled=bool(row[6]),
                )
                for row in rows
            ]

    def save_emergency_action(self, action: EmergencyAction) -> EmergencyAction:
        """Create or update an emergency action in the database."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            if action.id is not None:
                cursor.execute(
                    """
                    UPDATE emergency_actions
                    SET label = ?, speech_text = ?, icon = ?, accent_color = ?, sort_order = ?, is_enabled = ?
                    WHERE id = ?;
                    """,
                    (
                        action.label,
                        action.speech_text,
                        action.icon,
                        action.accent_color,
                        action.sort_order,
                        1 if action.is_enabled else 0,
                        action.id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO emergency_actions (label, speech_text, icon, accent_color, sort_order, is_enabled)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        action.label,
                        action.speech_text,
                        action.icon,
                        action.accent_color,
                        action.sort_order,
                        1 if action.is_enabled else 0,
                    ),
                )
                action.id = cursor.lastrowid
            return action

    def delete_emergency_action(self, action_id: int) -> bool:
        """Delete an emergency action by ID."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM emergency_actions WHERE id = ?;", (action_id,))
            return cursor.rowcount > 0

    def reset_emergency_actions(self) -> List[EmergencyAction]:
        """Reset emergency actions to default predefined set."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM emergency_actions;")
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
        return self.get_emergency_actions(enabled_only=False)

