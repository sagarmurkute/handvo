"""Unit tests for GazeEstimator math, direction classification, sensitivity presets, and adaptive smoothing."""

import unittest
from typing import List, Tuple
from app.vision.gaze_estimator import (
    L_BOT_LID,
    L_INNER_CORNER,
    L_IRIS_CENTER,
    L_OUTER_CORNER,
    L_TOP_LID,
    R_BOT_LID,
    R_INNER_CORNER,
    R_IRIS_CENTER,
    R_OUTER_CORNER,
    R_TOP_LID,
    GazeConfig,
    GazeEstimator,
)


def create_synthetic_landmarks(
    left_rx: float = 0.50,
    left_ry: float = 0.50,
    right_rx: float = 0.50,
    right_ry: float = 0.50,
) -> List[Tuple[float, float]]:
    """Build a mock 478-point landmark array with configured iris positions inside eye bounds."""
    lms = [(0.5, 0.5)] * 478

    # Left Eye Bounds (Image coordinates)
    lms[L_INNER_CORNER] = (0.55, 0.50)
    lms[L_OUTER_CORNER] = (0.65, 0.50)
    lms[L_TOP_LID] = (0.60, 0.45)
    lms[L_BOT_LID] = (0.60, 0.55)
    lms[L_IRIS_CENTER] = (0.55 + left_rx * 0.10, 0.45 + left_ry * 0.10)

    # Right Eye Bounds (Image coordinates)
    lms[R_OUTER_CORNER] = (0.35, 0.50)
    lms[R_INNER_CORNER] = (0.45, 0.50)
    lms[R_TOP_LID] = (0.40, 0.45)
    lms[R_BOT_LID] = (0.40, 0.55)
    lms[R_IRIS_CENTER] = (0.35 + right_rx * 0.10, 0.45 + right_ry * 0.10)

    return lms


class TestGazeEstimator(unittest.TestCase):
    """Test suite for GazeEstimator."""

    def setUp(self) -> None:
        self.config = GazeConfig(min_alpha=1.0, max_alpha=1.0)
        self.estimator = GazeEstimator(self.config)

    def test_center_gaze(self) -> None:
        """Scenario 1: Center iris position -> LOOKING_CENTER."""
        lms = create_synthetic_landmarks(0.50, 0.50, 0.50, 0.50)
        res = self.estimator.estimate(lms, eyes_open=True)

        self.assertTrue(res.tracking_valid)
        self.assertAlmostEqual(res.gaze_x, 0.50, delta=0.08)
        self.assertAlmostEqual(res.gaze_y, 0.50, delta=0.08)
        self.assertEqual(res.overall_direction, "LOOKING_CENTER")

    def test_looking_left(self) -> None:
        """Scenario 2: Iris shifted to user's left -> LOOKING_LEFT."""
        lms = create_synthetic_landmarks(0.30, 0.50, 0.30, 0.50)
        res = self.estimator.estimate(lms, eyes_open=True)

        self.assertTrue(res.tracking_valid)
        self.assertLess(res.gaze_x, 0.38)
        self.assertEqual(res.horizontal_direction, "LEFT")
        self.assertEqual(res.overall_direction, "LOOKING_LEFT")

    def test_looking_right(self) -> None:
        """Scenario 3: Iris shifted to user's right -> LOOKING_RIGHT."""
        lms = create_synthetic_landmarks(0.70, 0.50, 0.70, 0.50)
        res = self.estimator.estimate(lms, eyes_open=True)

        self.assertTrue(res.tracking_valid)
        self.assertGreater(res.gaze_x, 0.62)
        self.assertEqual(res.horizontal_direction, "RIGHT")
        self.assertEqual(res.overall_direction, "LOOKING_RIGHT")

    def test_looking_up(self) -> None:
        """Scenario 4: Iris shifted upward -> LOOKING_UP."""
        lms = create_synthetic_landmarks(0.50, 0.30, 0.50, 0.30)
        res = self.estimator.estimate(lms, eyes_open=True)

        self.assertTrue(res.tracking_valid)
        self.assertLess(res.gaze_y, 0.38)
        self.assertEqual(res.vertical_direction, "UP")
        self.assertEqual(res.overall_direction, "LOOKING_UP")

    def test_looking_down(self) -> None:
        """Scenario 5: Iris shifted downward -> LOOKING_DOWN."""
        lms = create_synthetic_landmarks(0.50, 0.70, 0.50, 0.70)
        res = self.estimator.estimate(lms, eyes_open=True)

        self.assertTrue(res.tracking_valid)
        self.assertGreater(res.gaze_y, 0.62)
        self.assertEqual(res.vertical_direction, "DOWN")
        self.assertEqual(res.overall_direction, "LOOKING_DOWN")

    def test_sensitivity_presets(self) -> None:
        """Scenario 6: Sensitivity presets modify multipliers."""
        self.estimator.set_sensitivity_preset("ULTRA")
        self.assertEqual(self.estimator.sensitivity_mode, "ULTRA")
        self.assertGreater(self.estimator.config.sensitivity_x, 2.5)

        self.estimator.set_sensitivity_preset("LOW")
        self.assertEqual(self.estimator.sensitivity_mode, "LOW")
        self.assertLess(self.estimator.config.sensitivity_x, 1.5)

    def test_recenter_baseline(self) -> None:
        """Scenario 7: Re-zeroing center offsets baseline."""
        lms = create_synthetic_landmarks(0.55, 0.55, 0.55, 0.55)
        self.estimator.estimate(lms, eyes_open=True)
        self.estimator.recenter_baseline()

        # After recenter, same position should produce ~0.50
        res_recentered = self.estimator.estimate(lms, eyes_open=True)
        self.assertAlmostEqual(res_recentered.gaze_x, 0.50, delta=0.05)
        self.assertAlmostEqual(res_recentered.gaze_y, 0.50, delta=0.05)

    def test_eyelid_flutter_stability(self) -> None:
        """Scenario 8: Eyelid squints/flutter do not collapse vertical gaze metric."""
        lms = create_synthetic_landmarks(0.50, 0.50, 0.50, 0.50)
        # Narrow eyelid gap (squint)
        lms[L_TOP_LID] = (0.60, 0.49)
        lms[L_BOT_LID] = (0.60, 0.51)
        res = self.estimator.estimate(lms, eyes_open=True)
        self.assertTrue(res.tracking_valid)
        self.assertAlmostEqual(res.gaze_y, 0.50, delta=0.10)


if __name__ == "__main__":
    unittest.main()
