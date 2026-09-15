"""Unit tests for CommunicationBoardModel state management, actions, and category navigation."""

import unittest
from app.communication.communication_board import (
    CommunicationBoardModel,
    CommunicationCategory,
    CommunicationItem,
)


class TestCommunicationBoard(unittest.TestCase):
    """Test suite for CommunicationBoardModel."""

    def setUp(self) -> None:
        self.model = CommunicationBoardModel()
        self.message_updates = []
        self.category_updates = []
        self.speak_calls = []

        self.model.on_message_changed(lambda msg: self.message_updates.append(msg))
        self.model.on_category_changed(lambda cat: self.category_updates.append(cat))
        self.model.on_speak_requested(lambda msg: self.speak_calls.append(msg))

    def test_initial_state(self) -> None:
        """Scenario 1: Initial message is empty and default category is common."""
        self.assertEqual(self.model.current_message, "")
        self.assertEqual(self.model.active_category_id, "common")
        self.assertGreater(len(self.model.get_categories()), 0)
        self.assertGreater(len(self.model.get_active_items()), 0)

    def test_add_item_builds_message(self) -> None:
        """Scenario 2: Adding phrases builds composed message string."""
        item1 = CommunicationItem("test_1", "Hello", "Hello", "common")
        item2 = CommunicationItem("test_2", "Help", "I need help", "common")

        self.model.add_item(item1)
        self.assertEqual(self.model.current_message, "Hello")

        self.model.add_item(item2)
        self.assertEqual(self.model.current_message, "Hello I need help")
        self.assertEqual(len(self.message_updates), 2)

    def test_delete_last_token(self) -> None:
        """Scenario 3: Delete last removes the most recent phrase token."""
        item1 = CommunicationItem("test_1", "Yes", "Yes", "common")
        item2 = CommunicationItem("test_2", "Water", "I need water", "needs")

        self.model.add_item(item1)
        self.model.add_item(item2)
        self.assertEqual(self.model.current_message, "Yes I need water")

        deleted = self.model.delete_last()
        self.assertTrue(deleted)
        self.assertEqual(self.model.current_message, "Yes")

        self.model.delete_last()
        self.assertEqual(self.model.current_message, "")

        # Calling delete on empty returns False
        empty_del = self.model.delete_last()
        self.assertFalse(empty_del)

    def test_clear_message(self) -> None:
        """Scenario 4: Clear removes all words."""
        self.model.add_text("Hello")
        self.model.add_text("Doctor")
        self.assertEqual(self.model.current_message, "Hello Doctor")

        self.model.clear_message()
        self.assertEqual(self.model.current_message, "")
        self.assertEqual(self.model.message_tokens, [])

    def test_switch_categories(self) -> None:
        """Scenario 5: Category switching updates active items and fires notifications."""
        self.assertEqual(self.model.active_category_id, "common")

        success = self.model.set_category("needs")
        self.assertTrue(success)
        self.assertEqual(self.model.active_category_id, "needs")
        self.assertIn("needs", self.category_updates)

        # Active items should now be needs items
        items = self.model.get_active_items()
        item_ids = [it.item_id for it in items]
        self.assertIn("need_water", item_ids)

    def test_message_persists_across_category_switches(self) -> None:
        """Scenario 6: Composed message is retained while navigating between categories."""
        # Add item from Common
        item_yes = self.model.get_active_items()[0]
        self.model.add_item(item_yes)

        # Switch to Needs
        self.model.set_category("needs")
        item_water = self.model.get_active_items()[0]
        self.model.add_item(item_water)

        # Switch to Feelings
        self.model.set_category("feelings")
        item_feeling = self.model.get_active_items()[0]
        self.model.add_item(item_feeling)

        # Verify combined sentence
        expected = f"{item_yes.text} {item_water.text} {item_feeling.text}"
        self.assertEqual(self.model.current_message, expected)

    def test_speak_request_hook(self) -> None:
        """Scenario 7: Speak request fires listeners with current message."""
        self.model.add_text("I need urgent help")
        spoken = self.model.request_speak()

        self.assertEqual(spoken, "I need urgent help")
        self.assertEqual(self.speak_calls, ["I need urgent help"])

    def test_all_categories_accessible(self) -> None:
        """Scenario 8: All standard categories exist with valid items."""
        required = ["common", "needs", "feelings", "people", "places", "actions"]
        for cat_id in required:
            cat = self.model.get_category(cat_id)
            self.assertIsNotNone(cat)
            self.assertGreater(len(cat.items), 0)


if __name__ == "__main__":
    unittest.main()
