"""Unit tests for HANDVO Hand Calibration calculations, coordinate remapping, and SQLite persistence."""

import os
from pathlib import Path
import tempfile
import unittest

from app.calibration.hand_calibration_model import (
    HandCalibrationData,
    HandCalibrationEngine,
)
from app.database.database import Database
from app.database.models import UserProfile
from app.database.profile_repository import ProfileRepository


class TestHandCalibrationEngine(unittest.TestCase):
    """Tests for mathematical algorithms in HandCalibrationEngine."""

    def test_compute_neutral_centroid(self) -> None:
        samples = [(0.48, 0.52), (0.50, 0.50), (0.52, 0.48)]
        nx, ny = HandCalibrationEngine.compute_neutral(samples)
        self.assertAlmostEqual(nx, 0.50, places=2)
        self.assertAlmostEqual(ny, 0.50, places=2)

    def test_compute_range_extents(self) -> None:
        samples = [
            (0.20, 0.20),
            (0.80, 0.20),
            (0.20, 0.80),
            (0.80, 0.80),
            (0.50, 0.50),
        ]
        min_x, max_x, min_y, max_y = HandCalibrationEngine.compute_range(samples, margin_pct=0.0)
        self.assertAlmostEqual(min_x, 0.20, places=2)
        self.assertAlmostEqual(max_x, 0.80, places=2)
        self.assertAlmostEqual(min_y, 0.20, places=2)
        self.assertAlmostEqual(max_y, 0.80, places=2)

    def test_compute_pinch_thresholds(self) -> None:
        open_span = 0.25
        pinch_contact = 0.03
        trig, rel = HandCalibrationEngine.compute_pinch_thresholds(open_span, pinch_contact)
        # Trigger should be strictly less than release for proper hysteresis debouncing
        self.assertLess(trig, rel)
        self.assertGreater(trig, pinch_contact)
        self.assertLess(rel, open_span)

    def test_evaluate_quality_excellent(self) -> None:
        neutral = (0.50, 0.50)
        reach = (0.15, 0.85, 0.15, 0.85)
        open_span = 0.28
        pinch_dist = 0.02
        label, pct = HandCalibrationEngine.evaluate_quality(neutral, reach, open_span, pinch_dist)
        self.assertEqual(label, "EXCELLENT")
        self.assertGreaterEqual(pct, 80.0)

    def test_evaluate_quality_fair(self) -> None:
        neutral = (0.10, 0.10)
        reach = (0.45, 0.55, 0.45, 0.55)  # Very narrow range
        open_span = 0.06
        pinch_dist = 0.05  # Almost no pinch delta
        label, pct = HandCalibrationEngine.evaluate_quality(neutral, reach, open_span, pinch_dist)
        self.assertEqual(label, "FAIR")
        self.assertLess(pct, 60.0)

    def test_remap_coordinate(self) -> None:
        calib = HandCalibrationData(
            range_min_x=0.20,
            range_max_x=0.80,
            range_min_y=0.20,
            range_max_y=0.80,
        )
        # Center should map to (0.5, 0.5)
        cx, cy = HandCalibrationEngine.remap_coordinate(0.50, 0.50, calib)
        self.assertAlmostEqual(cx, 0.50, places=2)
        self.assertAlmostEqual(cy, 0.50, places=2)

        # Min bounds should map to (0.0, 0.0)
        cx, cy = HandCalibrationEngine.remap_coordinate(0.20, 0.20, calib)
        self.assertAlmostEqual(cx, 0.0, places=2)
        self.assertAlmostEqual(cy, 0.0, places=2)

        # Max bounds should map to (1.0, 1.0)
        cx, cy = HandCalibrationEngine.remap_coordinate(0.80, 0.80, calib)
        self.assertAlmostEqual(cx, 1.0, places=2)
        self.assertAlmostEqual(cy, 1.0, places=2)


class TestHandCalibrationDatabasePersistence(unittest.TestCase):
    """Tests for saving and loading calibration data to SQLite profiles table."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_handvo.db"
        self.database = Database(db_path=self.db_path)
        self.repo = ProfileRepository(database=self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_and_load_calibration_profile(self) -> None:
        profile = self.repo.get_or_create_default()
        self.assertIsNotNone(profile.id)

        # Update calibration parameters
        profile.dominant_hand = "Left"
        profile.neutral_x = 0.45
        profile.neutral_y = 0.55
        profile.range_min_x = 0.18
        profile.range_max_x = 0.82
        profile.range_min_y = 0.15
        profile.range_max_y = 0.85
        profile.open_hand_span = 0.26
        profile.pinch_threshold = 0.045
        profile.pinch_release_threshold = 0.075
        profile.calibration_quality = "EXCELLENT"

        success = self.repo.save_calibration(profile)
        self.assertTrue(success)

        # Reload from fresh repo instance
        reloaded_repo = ProfileRepository(database=Database(db_path=self.db_path))
        loaded_profile = reloaded_repo.get_or_create_default()

        self.assertEqual(loaded_profile.dominant_hand, "Left")
        self.assertAlmostEqual(loaded_profile.neutral_x, 0.45, places=2)
        self.assertAlmostEqual(loaded_profile.neutral_y, 0.55, places=2)
        self.assertAlmostEqual(loaded_profile.range_min_x, 0.18, places=2)
        self.assertAlmostEqual(loaded_profile.range_max_x, 0.82, places=2)
        self.assertAlmostEqual(loaded_profile.open_hand_span, 0.26, places=2)
        self.assertAlmostEqual(loaded_profile.pinch_threshold, 0.045, places=3)
        self.assertAlmostEqual(loaded_profile.pinch_release_threshold, 0.075, places=3)
        self.assertEqual(loaded_profile.calibration_quality, "EXCELLENT")


if __name__ == "__main__":
    unittest.main()
