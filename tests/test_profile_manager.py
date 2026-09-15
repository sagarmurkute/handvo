"""Unit tests for HANDVO Multi-User Profiles & Caregiver System."""

import json
from pathlib import Path
import tempfile
import unittest

from app.communication.prediction import SmartPredictionEngine
from app.database.database import Database
from app.database.models import CustomPhrase, UserProfile
from app.database.profile_repository import ProfileRepository


class TestProfileManager(unittest.TestCase):
    """Tests for multi-user profile lifecycle, duplication, JSON import/export, and isolation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_profiles.db"
        self.database = Database(db_path=self.db_path)
        self.repo = ProfileRepository(database=self.database)
        self.prediction_engine = SmartPredictionEngine(repository=self.repo)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_profile_creation_and_activation(self) -> None:
        active = self.repo.get_active_profile()
        self.assertIsNotNone(active.id)
        self.assertTrue(active.is_active)
        self.assertFalse(active.is_archived)
        self.assertEqual(active.dominant_hand, "Right")

    def test_create_and_switch_profile(self) -> None:
        new_prof = UserProfile(
            name="Alice",
            dominant_hand="Left",
            dwell_time=0.60,
            calibration_quality="EXCELLENT",
        )
        created = self.repo.create_profile(new_prof)
        self.assertIsNotNone(created.id)

        # Switch active
        switched = self.repo.set_active_profile(created.id)
        self.assertIsNotNone(switched)
        self.assertEqual(switched.name, "Alice")
        self.assertTrue(switched.is_active)

        # Confirm database state
        all_profs = self.repo.get_all_profiles(include_archived=False)
        active_profs = [p for p in all_profs if p.is_active]
        self.assertEqual(len(active_profs), 1)
        self.assertEqual(active_profs[0].id, created.id)

    def test_duplicate_profile(self) -> None:
        # Create base profile with phrases and prediction frequencies
        p1 = self.repo.create_profile(UserProfile(name="Bob", dominant_hand="Right", dwell_time=0.75))
        self.repo.save_custom_phrase(CustomPhrase(profile_id=p1.id, category="needs", label="Juice", text="I want apple juice"))
        self.repo.record_phrase_usage("i want", "apple juice", category_id="needs", profile_id=p1.id)

        # Duplicate
        cloned = self.repo.duplicate_profile(p1.id, new_name="Bob (Cloned)")
        self.assertIsNotNone(cloned)
        self.assertEqual(cloned.name, "Bob (Cloned)")
        self.assertEqual(cloned.dwell_time, 0.75)
        self.assertNotEqual(cloned.id, p1.id)

        # Verify cloned phrases and predictions
        cloned_phrases = self.repo.get_custom_phrases(cloned.id)
        self.assertEqual(len(cloned_phrases), 1)
        self.assertEqual(cloned_phrases[0].label, "Juice")

        cloned_preds = self.repo.get_top_predictions("i want", profile_id=cloned.id)
        self.assertEqual(len(cloned_preds), 1)
        self.assertEqual(cloned_preds[0][0], "apple juice")

    def test_archive_and_unarchive_profile(self) -> None:
        p1 = self.repo.get_active_profile()
        p2 = self.repo.create_profile(UserProfile(name="Charlie"))

        # Archive Charlie
        self.repo.archive_profile(p2.id, archived=True)
        active_list = self.repo.get_all_profiles(include_archived=False)
        self.assertFalse(any(p.id == p2.id for p in active_list))

        all_list = self.repo.get_all_profiles(include_archived=True)
        self.assertTrue(any(p.id == p2.id and p.is_archived for p in all_list))

        # Unarchive Charlie
        self.repo.archive_profile(p2.id, archived=False)
        active_list2 = self.repo.get_all_profiles(include_archived=False)
        self.assertTrue(any(p.id == p2.id for p in active_list2))

    def test_delete_profile(self) -> None:
        p1 = self.repo.get_active_profile()
        p2 = self.repo.create_profile(UserProfile(name="Temporary"))
        self.repo.save_custom_phrase(CustomPhrase(profile_id=p2.id, category="common", label="Test", text="Test text"))

        deleted = self.repo.delete_profile(p2.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get_profile_by_id(p2.id))
        self.assertEqual(len(self.repo.get_custom_phrases(p2.id)), 0)

    def test_json_export_and_import_roundtrip(self) -> None:
        # Create profile with custom settings, phrases, and prediction histories
        p = self.repo.create_profile(
            UserProfile(
                name="Diana",
                dominant_hand="Left",
                dwell_time=0.65,
                tts_rate=160,
                tts_volume=0.9,
                calibration_quality="EXCELLENT",
                high_contrast=True,
            )
        )
        self.repo.save_custom_phrase(
            CustomPhrase(profile_id=p.id, category="actions", label="Music", text="Please play music", icon="🎵")
        )
        self.repo.record_phrase_usage("please", "play music", category_id="actions", profile_id=p.id)

        # Export to JSON
        json_str = self.repo.export_profile_json(p.id)
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["name"], "Diana")
        self.assertEqual(parsed["dominant_hand"], "Left")
        self.assertEqual(len(parsed["custom_phrases"]), 1)
        self.assertEqual(parsed["custom_phrases"][0]["icon"], "🎵")

        # Import as new profile
        imported = self.repo.import_profile_json(json_str)
        self.assertIsNotNone(imported.id)
        self.assertNotEqual(imported.id, p.id)
        self.assertEqual(imported.name, "Diana")
        self.assertEqual(imported.dwell_time, 0.65)
        self.assertTrue(imported.high_contrast)

        # Verify imported custom phrases and prediction learning
        imp_phrases = self.repo.get_custom_phrases(imported.id)
        self.assertEqual(len(imp_phrases), 1)
        self.assertEqual(imp_phrases[0].label, "Music")

        imp_preds = self.repo.get_top_predictions("please", profile_id=imported.id)
        self.assertEqual(len(imp_preds), 1)
        self.assertEqual(imp_preds[0][0], "play music")

    def test_profile_isolated_predictions(self) -> None:
        p1 = self.repo.create_profile(UserProfile(name="User 1"))
        p2 = self.repo.create_profile(UserProfile(name="User 2"))

        # User 1 repeatedly selects "warm blanket"
        for _ in range(4):
            self.prediction_engine.learn_selection(
                prev_sentence="I need",
                selected_phrase="warm blanket",
                category_id="needs",
                profile_id=p1.id,
            )

        # User 1 should have "warm blanket" boosted to top
        preds_u1 = self.prediction_engine.get_predictions("I need", active_category_id="needs", profile_id=p1.id)
        self.assertEqual(preds_u1[0].text, "warm blanket")

        # User 2 should NOT have "warm blanket" boosted
        preds_u2 = self.prediction_engine.get_predictions("I need", active_category_id="needs", profile_id=p2.id)
        self.assertNotEqual(preds_u2[0].text, "warm blanket")


if __name__ == "__main__":
    unittest.main()
