"""Unit tests for HANDVO Emergency Mode domain, persistence, and speech triggering."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

from app.communication.emergency_model import EmergencyManager
from app.database.database import Database
from app.database.models import EmergencyAction
from app.database.profile_repository import ProfileRepository
from app.gestures.dwell import DwellSelector


class TestEmergencyMode(unittest.TestCase):
    """Tests for emergency actions, SQLite repository, speech synthesis, and dwell targets."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_emergency.db"
        self.database = Database(db_path=self.db_path)
        self.repo = ProfileRepository(database=self.database)
        self.mock_speech = MagicMock()
        self.manager = EmergencyManager(repository=self.repo, speech_engine=self.mock_speech)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_emergency_actions_seeded(self) -> None:
        actions = self.manager.load_actions(enabled_only=True)
        self.assertGreaterEqual(len(actions), 6)
        labels = [a.label for a in actions]
        self.assertIn("Call Help", labels)
        self.assertIn("I Need a Doctor", labels)
        self.assertIn("I'm in Pain", labels)
        self.assertIn("I Can't Breathe", labels)
        self.assertIn("Yes", labels)
        self.assertIn("No", labels)

    def test_emergency_manager_trigger_and_listener(self) -> None:
        action = EmergencyAction(
            id=99,
            label="Severe Emergency",
            speech_text="Alert! Severe allergic reaction!",
            icon="🚨",
            accent_color="#ef4444",
        )
        received_actions = []
        self.manager.add_listener(lambda a: received_actions.append(a))

        spoken = self.manager.trigger_action(action)
        self.assertEqual(spoken, "Alert! Severe allergic reaction!")
        self.mock_speech.speak.assert_called_once_with("Alert! Severe allergic reaction!", interrupt=True)
        self.assertEqual(len(received_actions), 1)
        self.assertEqual(received_actions[0].label, "Severe Emergency")

    def test_emergency_manager_save_and_delete_action(self) -> None:
        new_act = EmergencyAction(
            label="Choking",
            speech_text="I am choking! Help!",
            icon="🫁",
            accent_color="#dc2626",
            sort_order=10,
            is_enabled=True,
        )
        saved = self.manager.save_action(new_act)
        self.assertIsNotNone(saved.id)

        actions = self.manager.load_actions(enabled_only=False)
        self.assertTrue(any(a.label == "Choking" for a in actions))

        # Delete it
        deleted = self.manager.delete_action(saved.id)
        self.assertTrue(deleted)
        actions_after = self.manager.load_actions(enabled_only=False)
        self.assertFalse(any(a.label == "Choking" for a in actions_after))

    def test_emergency_manager_reset_defaults(self) -> None:
        # Delete an action or modify
        actions = self.manager.load_actions()
        first_id = actions[0].id
        self.manager.delete_action(first_id)
        self.assertEqual(len(self.manager.load_actions()), len(actions) - 1)

        # Reset to defaults
        reset_actions = self.manager.reset_defaults()
        self.assertEqual(len(reset_actions), 6)
        labels = [a.label for a in reset_actions]
        self.assertIn("Call Help", labels)


if __name__ == "__main__":
    unittest.main()
