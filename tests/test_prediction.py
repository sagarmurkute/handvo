"""Unit tests for HANDVO Smart Prediction Engine and SQLite frequency learning."""

from pathlib import Path
import tempfile
import unittest

from app.communication.prediction import PredictionCandidate, SmartPredictionEngine
from app.database.database import Database
from app.database.profile_repository import ProfileRepository


class TestSmartPredictionEngine(unittest.TestCase):
    """Tests for n-gram suggestions, category priors, and SQLite frequency learning."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_pred.db"
        self.database = Database(db_path=self.db_path)
        self.repo = ProfileRepository(database=self.database)
        self.engine = SmartPredictionEngine(repository=self.repo)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_empty_sentence_predictions(self) -> None:
        preds = self.engine.get_predictions(current_sentence="", active_category_id="common", limit=5)
        self.assertGreaterEqual(len(preds), 3)
        self.assertLessEqual(len(preds), 5)
        texts = [p.text for p in preds]
        self.assertIn("Yes", texts)
        self.assertIn("Hello", texts)

    def test_prefix_matching_i_need(self) -> None:
        preds = self.engine.get_predictions(current_sentence="I need", active_category_id="needs", limit=5)
        texts = [p.text for p in preds]
        self.assertIn("water", texts)
        self.assertIn("food", texts)

    def test_prefix_matching_i_am(self) -> None:
        preds = self.engine.get_predictions(current_sentence="I am", active_category_id="feelings", limit=5)
        texts = [p.text for p in preds]
        self.assertIn("okay", texts)
        self.assertIn("tired", texts)

    def test_category_context_priors(self) -> None:
        preds = self.engine.get_predictions(current_sentence="", active_category_id="actions", limit=5)
        texts = [p.text for p in preds]
        # Should include action category defaults
        self.assertTrue(any(t in ("Come here", "Call someone", "Turn on", "Stop") for t in texts))

    def test_frequency_learning_boosts_candidate(self) -> None:
        # Initially, "the bathroom" may not be top 1
        self.engine.learn_selection(prev_sentence="I need", selected_phrase="the bathroom", category_id="needs")
        self.engine.learn_selection(prev_sentence="I need", selected_phrase="the bathroom", category_id="needs")
        self.engine.learn_selection(prev_sentence="I need", selected_phrase="the bathroom", category_id="needs")

        preds = self.engine.get_predictions(current_sentence="I need", active_category_id="needs", limit=5)
        # "the bathroom" should be boosted to top 1 position due to 3 selections
        self.assertEqual(preds[0].text, "the bathroom")


if __name__ == "__main__":
    unittest.main()
