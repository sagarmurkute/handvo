"""Repository pattern for managing multi-user profiles, calibration, custom phrases, and learned frequencies."""

import json
from typing import Any, Dict, List, Optional, Tuple

from app.database.database import Database
from app.database.models import CustomPhrase, EmergencyAction, UserProfile


class ProfileRepository:
    """Handles CRUD operations for user profiles, calibration data, and prediction learning."""

    def __init__(self, database: Optional[Database] = None) -> None:
        self.db = database or Database()

    def _row_to_profile(self, row: Tuple[Any, ...]) -> UserProfile:
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
            is_archived=bool(row[15]) if len(row) > 15 and row[15] is not None else False,
            is_active=bool(row[16]) if len(row) > 16 and row[16] is not None else False,
            language=row[17] if len(row) > 17 and row[17] else "en",
            tts_rate=int(row[18]) if len(row) > 18 and row[18] is not None else 150,
            tts_volume=float(row[19]) if len(row) > 19 and row[19] is not None else 1.0,
            dwell_sound=bool(row[20]) if len(row) > 20 and row[20] is not None else True,
            high_contrast=bool(row[21]) if len(row) > 21 and row[21] is not None else False,
            theme=row[22] if len(row) > 22 and row[22] else "dark",
            ui_scale=row[23] if len(row) > 23 and row[23] else "medium",
            cooldown_time=float(row[24] if len(row) > 24 and row[24] is not None else 0.60),
            cursor_size=row[25] if len(row) > 25 and row[25] is not None else 14,
            cursor_color=row[26] if len(row) > 26 and row[26] else "#38bdf8",
            reduced_motion=bool(row[27]) if len(row) > 27 and row[27] is not None else False,
            voice_id=row[28] if len(row) > 28 and row[28] else None,
        )

    def _select_columns_sql(self) -> str:
        return """
            SELECT id, name, dominant_hand, neutral_x, neutral_y,
                   range_min_x, range_max_x, range_min_y, range_max_y,
                   open_hand_span, pinch_threshold, pinch_release_threshold,
                   dwell_time, smoothing_factor, calibration_quality,
                   is_archived, is_active, language, tts_rate, tts_volume,
                   dwell_sound, high_contrast, theme, ui_scale,
                   cooldown_time, cursor_size, cursor_color, reduced_motion,
                   voice_id
            FROM profiles
        """

    def get_or_create_default(self) -> UserProfile:
        return self.get_active_profile()

    def get_active_profile(self) -> UserProfile:
        """Fetch the currently active profile, or activate the first non-archived profile."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(f"{self._select_columns_sql()} WHERE is_active = 1 AND is_archived = 0 LIMIT 1;")
            row = cursor.fetchone()
            if row:
                return self._row_to_profile(row)

            # Check for any non-archived profile
            cursor.execute(f"{self._select_columns_sql()} WHERE is_archived = 0 ORDER BY id ASC LIMIT 1;")
            row = cursor.fetchone()
            if row:
                prof = self._row_to_profile(row)
                cursor.execute("UPDATE profiles SET is_active = 1 WHERE id = ?;", (prof.id,))
                prof.is_active = True
                return prof

            # Create brand new default profile
            cursor.execute(
                """
                INSERT INTO profiles (
                    name, dominant_hand, neutral_x, neutral_y,
                    range_min_x, range_max_x, range_min_y, range_max_y,
                    open_hand_span, pinch_threshold, pinch_release_threshold,
                    dwell_time, smoothing_factor, calibration_quality,
                    is_archived, is_active, language, tts_rate, tts_volume,
                    dwell_sound, high_contrast, theme, ui_scale,
                    cooldown_time, cursor_size, cursor_color, reduced_motion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 'en', 150, 1.0, 1, 0, 'dark', 'medium', 0.60, 14, '#38bdf8', 0);
                """,
                ("Default User", "Right", 0.50, 0.50, 0.20, 0.80, 0.20, 0.80, 0.25, 0.05, 0.08, 0.80, 1.50, "GOOD"),
            )
            prof_id = cursor.lastrowid
            return UserProfile(id=prof_id, name="Default User", is_active=True)

    def set_active_profile(self, profile_id: int) -> Optional[UserProfile]:
        """Switch active profile by ID."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE profiles SET is_active = 0;")
            cursor.execute("UPDATE profiles SET is_active = 1, is_archived = 0 WHERE id = ?;", (profile_id,))
            cursor.execute(f"{self._select_columns_sql()} WHERE id = ?;", (profile_id,))
            row = cursor.fetchone()
            return self._row_to_profile(row) if row else None

    def get_profile_by_id(self, profile_id: int) -> Optional[UserProfile]:
        """Fetch profile by ID."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(f"{self._select_columns_sql()} WHERE id = ?;", (profile_id,))
            row = cursor.fetchone()
            return self._row_to_profile(row) if row else None

    def get_all_profiles(self, include_archived: bool = False) -> List[UserProfile]:
        """Retrieve list of user profiles."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            query = self._select_columns_sql()
            if not include_archived:
                query += " WHERE is_archived = 0"
            query += " ORDER BY is_active DESC, is_archived ASC, id ASC;"

            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_profile(r) for r in rows]

    def create_profile(self, profile: UserProfile) -> UserProfile:
        """Create new profile."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO profiles (
                    name, dominant_hand, neutral_x, neutral_y,
                    range_min_x, range_max_x, range_min_y, range_max_y,
                    open_hand_span, pinch_threshold, pinch_release_threshold,
                    dwell_time, smoothing_factor, calibration_quality,
                    is_archived, is_active, language, tts_rate, tts_volume,
                    dwell_sound, high_contrast, theme, ui_scale,
                    cooldown_time, cursor_size, cursor_color, reduced_motion,
                    voice_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                    1 if profile.is_archived else 0,
                    1 if profile.is_active else 0,
                    profile.language,
                    profile.tts_rate,
                    profile.tts_volume,
                    1 if profile.dwell_sound else 0,
                    1 if profile.high_contrast else 0,
                    profile.theme,
                    profile.ui_scale,
                    profile.cooldown_time,
                    profile.cursor_size,
                    profile.cursor_color,
                    1 if profile.reduced_motion else 0,
                    profile.voice_id,
                ),
            )
            profile.id = cursor.lastrowid
            return profile

    def save_calibration(self, profile: UserProfile) -> bool:
        """Save or update user profile with calibrated metrics and accessibility settings."""
        return self.save_profile(profile)

    def save_profile(self, profile: UserProfile) -> bool:
        """Update existing profile settings."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            if profile.id is None:
                self.create_profile(profile)
                return True

            cursor.execute(
                """
                UPDATE profiles SET
                    name = ?,
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
                    calibration_quality = ?,
                    is_archived = ?,
                    is_active = ?,
                    language = ?,
                    tts_rate = ?,
                    tts_volume = ?,
                    dwell_sound = ?,
                    high_contrast = ?,
                    theme = ?,
                    ui_scale = ?,
                    cooldown_time = ?,
                    cursor_size = ?,
                    cursor_color = ?,
                    reduced_motion = ?,
                    voice_id = ?
                WHERE id = ?;
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
                    1 if profile.is_archived else 0,
                    1 if profile.is_active else 0,
                    profile.language,
                    profile.tts_rate,
                    profile.tts_volume,
                    1 if profile.dwell_sound else 0,
                    1 if profile.high_contrast else 0,
                    profile.theme,
                    profile.ui_scale,
                    profile.cooldown_time,
                    profile.cursor_size,
                    profile.cursor_color,
                    1 if profile.reduced_motion else 0,
                    profile.voice_id,
                    profile.id,
                ),
            )
            return True

    def duplicate_profile(self, profile_id: int, new_name: str) -> Optional[UserProfile]:
        """Clone an existing profile with all calibration, custom phrases, and prediction history."""
        source = self.get_profile_by_id(profile_id)
        if not source:
            return None

        # Create cloned profile
        cloned = UserProfile(
            name=new_name,
            dominant_hand=source.dominant_hand,
            neutral_x=source.neutral_x,
            neutral_y=source.neutral_y,
            range_min_x=source.range_min_x,
            range_max_x=source.range_max_x,
            range_min_y=source.range_min_y,
            range_max_y=source.range_max_y,
            open_hand_span=source.open_hand_span,
            pinch_threshold=source.pinch_threshold,
            pinch_release_threshold=source.pinch_release_threshold,
            dwell_time=source.dwell_time,
            smoothing_factor=source.smoothing_factor,
            calibration_quality=source.calibration_quality,
            is_archived=False,
            is_active=False,
            language=source.language,
            tts_rate=source.tts_rate,
            tts_volume=source.tts_volume,
            dwell_sound=source.dwell_sound,
            high_contrast=source.high_contrast,
            theme=source.theme,
            ui_scale=source.ui_scale,
            cooldown_time=source.cooldown_time,
            cursor_size=source.cursor_size,
            cursor_color=source.cursor_color,
            reduced_motion=source.reduced_motion,
            voice_id=source.voice_id,
        )
        new_prof = self.create_profile(cloned)
        new_id = new_prof.id

        # Copy custom phrases
        phrases = self.get_custom_phrases(profile_id)
        for p in phrases:
            cp = CustomPhrase(
                profile_id=new_id,
                category=p.category,
                label=p.label,
                text=p.text,
                icon=p.icon,
                accent_color=p.accent_color,
                sort_order=p.sort_order,
            )
            self.save_custom_phrase(cp)

        # Copy phrase frequencies
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO phrase_frequencies (profile_id, prev_token, next_token, category_id, frequency, last_used)
                SELECT ?, prev_token, next_token, category_id, frequency, last_used
                FROM phrase_frequencies
                WHERE profile_id = ?;
                """,
                (new_id, profile_id),
            )

        return new_prof

    def archive_profile(self, profile_id: int, archived: bool = True) -> bool:
        """Archive or unarchive a profile. If active profile is archived, switches active to another."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE profiles SET is_archived = ?, is_active = CASE WHEN ? = 1 THEN 0 ELSE is_active END WHERE id = ?;",
                (1 if archived else 0, 1 if archived else 0, profile_id),
            )
        # Ensure there is always an active profile
        self.get_active_profile()
        return True

    def delete_profile(self, profile_id: int) -> bool:
        """Delete profile, custom phrases, and isolated phrase frequencies."""
        target = self.get_profile_by_id(profile_id)
        if not target:
            return False

        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM phrase_frequencies WHERE profile_id = ?;", (profile_id,))
            cursor.execute("DELETE FROM custom_phrases WHERE profile_id = ?;", (profile_id,))
            cursor.execute("DELETE FROM profiles WHERE id = ?;", (profile_id,))

        self.get_active_profile()
        return True

    # -------------------------------------------------------------
    # JSON Profile Export & Import (Offline Caregiver Backup)
    # -------------------------------------------------------------
    def export_profile_json(self, profile_id: int) -> str:
        """Export full profile configuration, phrases, and prediction learning as JSON string."""
        profile = self.get_profile_by_id(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found.")

        phrases = self.get_custom_phrases(profile_id)
        phrases_data = [
            {
                "category": p.category,
                "label": p.label,
                "text": p.text,
                "icon": p.icon,
                "accent_color": p.accent_color,
                "sort_order": p.sort_order,
            }
            for p in phrases
        ]

        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT prev_token, next_token, category_id, frequency, last_used
                FROM phrase_frequencies WHERE profile_id = ?;
                """,
                (profile_id,),
            )
            freq_rows = cursor.fetchall()
            frequencies_data = [
                {
                    "prev_token": r[0],
                    "next_token": r[1],
                    "category_id": r[2],
                    "frequency": r[3],
                    "last_used": r[4],
                }
                for r in freq_rows
            ]

        data = {
            "handvo_profile_version": "1.0",
            "name": profile.name,
            "dominant_hand": profile.dominant_hand,
            "neutral_x": profile.neutral_x,
            "neutral_y": profile.neutral_y,
            "range_min_x": profile.range_min_x,
            "range_max_x": profile.range_max_x,
            "range_min_y": profile.range_min_y,
            "range_max_y": profile.range_max_y,
            "open_hand_span": profile.open_hand_span,
            "pinch_threshold": profile.pinch_threshold,
            "pinch_release_threshold": profile.pinch_release_threshold,
            "dwell_time": profile.dwell_time,
            "smoothing_factor": profile.smoothing_factor,
            "calibration_quality": profile.calibration_quality,
            "language": profile.language,
            "tts_rate": profile.tts_rate,
            "tts_volume": profile.tts_volume,
            "dwell_sound": profile.dwell_sound,
            "high_contrast": profile.high_contrast,
            "theme": profile.theme,
            "ui_scale": profile.ui_scale,
            "cooldown_time": profile.cooldown_time,
            "cursor_size": profile.cursor_size,
            "cursor_color": profile.cursor_color,
            "reduced_motion": profile.reduced_motion,
            "voice_id": profile.voice_id,
            "custom_phrases": phrases_data,
            "phrase_frequencies": frequencies_data,
        }
        return json.dumps(data, indent=2)

    def import_profile_json(self, json_str: str) -> UserProfile:
        """Import profile from JSON string, creating a new profile entry."""
        data = json.loads(json_str)

        name = data.get("name", "Imported User")
        profile = UserProfile(
            name=name,
            dominant_hand=data.get("dominant_hand", "Right"),
            neutral_x=float(data.get("neutral_x", 0.50)),
            neutral_y=float(data.get("neutral_y", 0.50)),
            range_min_x=float(data.get("range_min_x", 0.20)),
            range_max_x=float(data.get("range_max_x", 0.80)),
            range_min_y=float(data.get("range_min_y", 0.20)),
            range_max_y=float(data.get("range_max_y", 0.80)),
            open_hand_span=float(data.get("open_hand_span", 0.25)),
            pinch_threshold=float(data.get("pinch_threshold", 0.05)),
            pinch_release_threshold=float(data.get("pinch_release_threshold", 0.08)),
            dwell_time=float(data.get("dwell_time", 0.80)),
            smoothing_factor=float(data.get("smoothing_factor", 1.50)),
            calibration_quality=data.get("calibration_quality", "GOOD"),
            language=data.get("language", "en"),
            tts_rate=int(data.get("tts_rate", 150)),
            tts_volume=float(data.get("tts_volume", 1.0)),
            dwell_sound=bool(data.get("dwell_sound", True)),
            high_contrast=bool(data.get("high_contrast", False)),
            theme=data.get("theme", "dark"),
            ui_scale=data.get("ui_scale", "medium"),
            cooldown_time=float(data.get("cooldown_time", 0.60)),
            cursor_size=data.get("cursor_size", 14),
            cursor_color=data.get("cursor_color", "#38bdf8"),
            reduced_motion=bool(data.get("reduced_motion", False)),
            voice_id=data.get("voice_id"),
            is_active=False,
            is_archived=False,
        )

        created = self.create_profile(profile)
        new_id = created.id

        # Import custom phrases
        for p in data.get("custom_phrases", []):
            cp = CustomPhrase(
                profile_id=new_id,
                category=p.get("category", "common"),
                label=p.get("label", ""),
                text=p.get("text", ""),
                icon=p.get("icon", "💬"),
                accent_color=p.get("accent_color", "#38bdf8"),
                sort_order=p.get("sort_order", 0),
            )
            self.save_custom_phrase(cp)

        # Import phrase frequencies
        for f in data.get("phrase_frequencies", []):
            with self.db.session() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO phrase_frequencies (profile_id, prev_token, next_token, category_id, frequency, last_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(profile_id, prev_token, next_token) DO UPDATE SET
                        frequency = frequency + excluded.frequency,
                        last_used = excluded.last_used;
                    """,
                    (
                        new_id,
                        f.get("prev_token", "").strip().lower(),
                        f.get("next_token", "").strip(),
                        f.get("category_id", "common"),
                        int(f.get("frequency", 1)),
                        f.get("last_used"),
                    ),
                )

        return created

    # -------------------------------------------------------------
    # Custom Phrases Management
    # -------------------------------------------------------------
    def get_custom_phrases(self, profile_id: int, category: Optional[str] = None) -> List[CustomPhrase]:
        """Retrieve custom phrases for given profile."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, profile_id, category, label, text, icon, accent_color, sort_order
                FROM custom_phrases
                WHERE profile_id = ?
            """
            params: List[Any] = [profile_id]
            if category:
                query += " AND category = ?"
                params.append(category)
            query += " ORDER BY sort_order ASC, id ASC;"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                CustomPhrase(
                    id=r[0],
                    profile_id=r[1],
                    category=r[2],
                    label=r[3],
                    text=r[4],
                    icon=r[5] or "💬",
                    accent_color=r[6] or "#38bdf8",
                    sort_order=r[7] or 0,
                )
                for r in rows
            ]

    def save_custom_phrase(self, phrase: CustomPhrase) -> CustomPhrase:
        """Create or update a custom phrase."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            if phrase.id is not None:
                cursor.execute(
                    """
                    UPDATE custom_phrases
                    SET category = ?, label = ?, text = ?, icon = ?, accent_color = ?, sort_order = ?
                    WHERE id = ?;
                    """,
                    (phrase.category, phrase.label, phrase.text, phrase.icon, phrase.accent_color, phrase.sort_order, phrase.id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO custom_phrases (profile_id, category, label, text, icon, accent_color, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (phrase.profile_id, phrase.category, phrase.label, phrase.text, phrase.icon, phrase.accent_color, phrase.sort_order),
                )
                phrase.id = cursor.lastrowid
            return phrase

    def delete_custom_phrase(self, phrase_id: int) -> bool:
        """Delete custom phrase by ID."""
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_phrases WHERE id = ?;", (phrase_id,))
            return cursor.rowcount > 0

    # -------------------------------------------------------------
    # Learned Prediction Frequencies (Profile Isolated)
    # -------------------------------------------------------------
    def record_phrase_usage(
        self,
        prev_token: str,
        next_token: str,
        category_id: str = "common",
        profile_id: int = 1,
    ) -> None:
        """Increment learned selection frequency for (prev_token -> next_token) pair in SQLite per profile."""
        p_clean = prev_token.strip().lower()
        n_clean = next_token.strip()
        if not n_clean:
            return

        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO phrase_frequencies (profile_id, prev_token, next_token, category_id, frequency, last_used)
                VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(profile_id, prev_token, next_token) DO UPDATE SET
                    frequency = frequency + 1,
                    last_used = CURRENT_TIMESTAMP;
                """,
                (profile_id, p_clean, n_clean, category_id),
            )

    def get_top_predictions(self, prev_token: str, limit: int = 5, profile_id: int = 1) -> List[Tuple[str, int]]:
        """Retrieve most frequent next tokens for given prefix context for this profile."""
        p_clean = prev_token.strip().lower()
        with self.db.session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT next_token, frequency
                FROM phrase_frequencies
                WHERE profile_id = ? AND prev_token = ?
                ORDER BY frequency DESC, last_used DESC
                LIMIT ?;
                """,
                (profile_id, p_clean, limit),
            )
            return cursor.fetchall()

    # -------------------------------------------------------------
    # Emergency Actions
    # -------------------------------------------------------------
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


