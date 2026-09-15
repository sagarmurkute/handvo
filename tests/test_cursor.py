"""Unit tests for Gaze Cursor position manager, smoothing, clamping, and tracking state."""

import unittest
from app.gaze.calibration_model import CalibrationModel
from app.gaze.gaze_cursor import CursorConfig, CursorPosition, GazeCursorManager


class TestGazeCursor(unittest.TestCase):
    """Test suite for GazeCursorManager coordinate mapping and boundary clamping."""

    def setUp(self) -> None:
        self.config = CursorConfig(
            min_smoothing=1.0,
            max_smoothing=1.0,
            cursor_size=32,
            margin_px=20,
            jitter_threshold_px=0.0,
        )
        self.manager = GazeCursorManager(self.config)

    def test_gaze_to_window_coordinates(self) -> None:
        """Scenario 1: Map normalized center (0.5, 0.5) to window pixel coordinates."""
        pos = self.manager.update(
            gaze_x=0.5,
            gaze_y=0.5,
            tracking_valid=True,
            calibration_model=None,
            window_w=1000,
            window_h=800,
        )
        self.assertTrue(pos.is_valid)
        self.assertAlmostEqual(pos.pixel_x, 500.0, delta=1.0)
        self.assertAlmostEqual(pos.pixel_y, 400.0, delta=1.0)

    def test_boundary_clamping(self) -> None:
        """Scenario 2: Out-of-bounds coordinates are clamped to window margins."""
        # Far top-left (-0.5, -0.5) -> clamped to margin (20, 20)
        pos_tl = self.manager.update(
            gaze_x=-0.5,
            gaze_y=-0.5,
            tracking_valid=True,
            calibration_model=None,
            window_w=1000,
            window_h=800,
        )
        self.assertEqual(pos_tl.pixel_x, 20.0)
        self.assertEqual(pos_tl.pixel_y, 20.0)

        # Far bottom-right (1.5, 1.5) -> clamped to (980, 780)
        pos_br = self.manager.update(
            gaze_x=1.5,
            gaze_y=1.5,
            tracking_valid=True,
            calibration_model=None,
            window_w=1000,
            window_h=800,
        )
        self.assertEqual(pos_br.pixel_x, 980.0)
        self.assertEqual(pos_br.pixel_y, 780.0)

    def test_cursor_smoothing(self) -> None:
        """Scenario 3: Smoothing adapts to movement."""
        smooth_manager = GazeCursorManager(CursorConfig(min_smoothing=0.5, max_smoothing=0.5, margin_px=0, jitter_threshold_px=0.0))

        # Frame 1: Position at 200px
        pos1 = smooth_manager.update(0.2, 0.2, True, None, 1000, 1000)
        self.assertAlmostEqual(pos1.pixel_x, 200.0, delta=1.0)

        # Frame 2: Move to 600px
        pos2 = smooth_manager.update(0.6, 0.6, True, None, 1000, 1000)
        self.assertAlmostEqual(pos2.pixel_x, 400.0, delta=1.0)
        self.assertAlmostEqual(pos2.pixel_y, 400.0, delta=1.0)

    def test_tracking_lost_freezes_position(self) -> None:
        """Scenario 4: When tracking is lost, cursor retains last valid position without random jumps."""
        self.manager.update(0.4, 0.4, True, None, 1000, 1000)

        # Lost tracking frame
        lost_pos = self.manager.update(0.9, 0.9, False, None, 1000, 1000)
        self.assertFalse(lost_pos.is_valid)
        self.assertAlmostEqual(lost_pos.pixel_x, 400.0, delta=1.0)
        self.assertAlmostEqual(lost_pos.pixel_y, 400.0, delta=1.0)

    def test_window_resizing_updates_bounds(self) -> None:
        """Scenario 5: Window resize recalculates coordinates accurately."""
        pos1 = self.manager.update(0.5, 0.5, True, None, 800, 600)
        self.assertAlmostEqual(pos1.pixel_x, 400.0, delta=1.0)
        self.assertAlmostEqual(pos1.pixel_y, 300.0, delta=1.0)

        pos2 = self.manager.update(0.5, 0.5, True, None, 1200, 900)
        self.assertAlmostEqual(pos2.pixel_x, 600.0, delta=1.0)
        self.assertAlmostEqual(pos2.pixel_y, 450.0, delta=1.0)

    def test_invalid_input_handling(self) -> None:
        """Scenario 6: NaN or Inf gaze values do not crash and mark position invalid."""
        pos = self.manager.update(float("nan"), float("inf"), True, None, 1000, 800)
        self.assertFalse(pos.is_valid)

    def test_toggle_visibility(self) -> None:
        """Scenario 7: Cursor visibility toggle."""
        self.manager.set_enabled(False)
        pos = self.manager.update(0.5, 0.5, True, None, 1000, 800)
        self.assertFalse(pos.is_visible)

        self.manager.set_enabled(True)
        pos2 = self.manager.update(0.5, 0.5, True, None, 1000, 800)
        self.assertTrue(pos2.is_visible)


if __name__ == "__main__":
    unittest.main()
