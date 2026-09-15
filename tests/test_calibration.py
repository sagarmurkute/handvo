"""Unit tests for the Gaze Calibration System, regression models, and persistence."""

import os
import tempfile
import unittest
from pathlib import Path
from app.gaze.calibration import (
    CalibrationPoint,
    CalibrationSample,
    CalibrationSession,
    CalibrationState,
)
from app.gaze.calibration_model import CalibrationModel, ModelMetrics


class TestGazeCalibration(unittest.TestCase):
    """Test suite for 9-point calibration workflow and polynomial model fitting."""

    def test_default_calibration_points(self) -> None:
        """Scenario 1: 9-point grid generation."""
        session = CalibrationSession()
        self.assertEqual(len(session.points), 9)
        labels = [p.label for p in session.points]
        self.assertIn("Top-Left", labels)
        self.assertIn("Center", labels)
        self.assertIn("Bottom-Right", labels)

        # Check bounds are within inset margins (0.10 to 0.90)
        for pt in session.points:
            self.assertGreaterEqual(pt.norm_x, 0.10)
            self.assertLessEqual(pt.norm_x, 0.90)
            self.assertGreaterEqual(pt.norm_y, 0.10)
            self.assertLessEqual(pt.norm_y, 0.90)

    def test_sample_validation_and_dwell(self) -> None:
        """Scenario 2: Dwell progress and sample validation."""
        session = CalibrationSession(dwell_required_sec=0.1, settle_duration_sec=0.0)
        session.start()
        session.state = CalibrationState.DWELLING

        # Ingest invalid sample -> dwell decays or stays 0
        session.add_sample(0.5, 0.5, tracking_valid=False, current_time=1.0)
        self.assertEqual(session.dwell_progress, 0.0)

        # Ingest valid sample -> dwell increases
        session.add_sample(0.5, 0.5, tracking_valid=True, current_time=1.05)
        self.assertGreater(session.dwell_progress, 0.0)

    def test_manual_point_capture(self) -> None:
        """Scenario 3: Manual point capture (spacebar/click) stores sample and advances."""
        session = CalibrationSession()
        session.start()
        session.state = CalibrationState.DWELLING
        session._current_gaze_buffer = [(0.2, 0.3)]

        self.assertEqual(session.current_point_idx, 0)
        session.capture_point_manually()
        self.assertEqual(session.current_point_idx, 1)
        self.assertGreater(len(session.samples), 0)

    def test_insufficient_samples_handling(self) -> None:
        """Scenario 4: Model fails gracefully when samples are insufficient."""
        model = CalibrationModel()
        fitted = model.fit([(0.5, 0.5)], [(0.5, 0.5)])
        self.assertFalse(fitted)
        self.assertFalse(model.is_trained)

        # Predict with untrained model returns fallback
        pred_x, pred_y = model.predict(0.3, 0.7)
        self.assertEqual(pred_x, 0.3)
        self.assertEqual(pred_y, 0.7)

    def test_model_training_and_prediction(self) -> None:
        """Scenario 5: Fit synthetic calibration data and check prediction accuracy."""
        model = CalibrationModel(degree=2)

        gaze_samples = []
        target_samples = []

        grid_coords = [(0.15, 0.15), (0.50, 0.15), (0.85, 0.15),
                       (0.15, 0.50), (0.50, 0.50), (0.85, 0.50),
                       (0.15, 0.85), (0.50, 0.85), (0.85, 0.85)]

        for gx, gy in grid_coords:
            for _ in range(10):
                gaze_samples.append((gx + 0.01, gy - 0.01))
                target_samples.append((gx, gy))

        success = model.fit(gaze_samples, target_samples)
        self.assertTrue(success)
        self.assertTrue(model.is_trained)
        self.assertIn(model.metrics.quality, ("EXCELLENT", "GOOD"))

        px, py = model.predict(0.51, 0.49)
        self.assertAlmostEqual(px, 0.50, delta=0.08)
        self.assertAlmostEqual(py, 0.50, delta=0.08)

        pix_x, pix_y = model.predict(0.51, 0.49, screen_w=1000, screen_h=800)
        self.assertAlmostEqual(pix_x, 500, delta=80)
        self.assertAlmostEqual(pix_y, 400, delta=80)

    def test_model_json_serialization(self) -> None:
        """Scenario 6: Save and reload model from JSON."""
        model = CalibrationModel(degree=2)
        grid_coords = [(0.2, 0.2), (0.5, 0.2), (0.8, 0.2),
                       (0.2, 0.5), (0.5, 0.5), (0.8, 0.5),
                       (0.2, 0.8), (0.5, 0.8), (0.8, 0.8)]
        model.fit(grid_coords, grid_coords)

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "calib_test.json"
            saved = model.save_to_json(file_path)
            self.assertTrue(saved)
            self.assertTrue(file_path.exists())

            loaded_model = CalibrationModel()
            loaded = loaded_model.load_from_json(file_path)
            self.assertTrue(loaded)
            self.assertTrue(loaded_model.is_trained)
            self.assertEqual(loaded_model.metrics.quality, model.metrics.quality)

            p1 = model.predict(0.4, 0.6)
            p2 = loaded_model.predict(0.4, 0.6)
            self.assertAlmostEqual(p1[0], p2[0], places=5)
            self.assertAlmostEqual(p1[1], p2[1], places=5)

    def test_session_lifecycle_and_cancellation(self) -> None:
        """Scenario 7: Start, run, and cancel session."""
        session = CalibrationSession(settle_duration_sec=0.0)
        session.start()
        self.assertEqual(session.state, CalibrationState.SETTLING)

        session.cancel()
        self.assertEqual(session.state, CalibrationState.IDLE)
        self.assertEqual(len(session.samples), 0)


if __name__ == "__main__":
    unittest.main()
