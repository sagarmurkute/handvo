"""Unit tests for DwellSelector state machine, spatial stability, dwell timing, and cooldowns."""

import unittest
from app.interaction.dwell_selector import (
    DwellResult,
    DwellSelector,
    DwellSelectorConfig,
    DwellState,
    DwellTarget,
)


class TestDwellSelector(unittest.TestCase):
    """Comprehensive test suite for the Gaze Dwell Interaction Engine."""

    def setUp(self) -> None:
        self.config = DwellSelectorConfig(
            dwell_time_sec=0.80,
            cooldown_sec=0.50,
            stability_radius_px=40.0,
            min_confidence=0.35,
        )
        self.selector = DwellSelector(self.config)

        self.callback_count = 0

        def dummy_callback():
            self.callback_count += 1

        self.target_a = DwellTarget(
            target_id="btn_a",
            bounds=(100.0, 100.0, 120.0, 60.0),
            enabled=True,
            callback=dummy_callback,
            label="Button A",
        )

        self.target_b = DwellTarget(
            target_id="btn_b",
            bounds=(300.0, 100.0, 120.0, 60.0),
            enabled=True,
            callback=None,
            label="Button B",
        )

        self.selector.register_target(self.target_a)
        self.selector.register_target(self.target_b)

    def test_entering_target_starts_focus(self) -> None:
        """Scenario 1: Moving gaze inside target enters FOCUSING/DWELLING state."""
        res = self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.0)

        self.assertEqual(res.target_id, "btn_a")
        self.assertIn(res.state, (DwellState.FOCUSING, DwellState.DWELLING))
        self.assertEqual(res.progress, 0.0)
        self.assertFalse(res.triggered)
        self.assertEqual(self.callback_count, 0)

    def test_stable_gaze_progression(self) -> None:
        """Scenario 2: Holding gaze on target steadily advances dwell progress."""
        # Start dwell at t=1.0
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.0)

        # Advance by 0.40s (halfway through 0.80s dwell)
        res = self.selector.update((152.0, 131.0), tracking_valid=True, current_time=1.40)

        self.assertEqual(res.target_id, "btn_a")
        self.assertEqual(res.state, DwellState.DWELLING)
        self.assertAlmostEqual(res.progress, 0.50, delta=0.05)
        self.assertFalse(res.triggered)

    def test_successful_selection_and_cooldown(self) -> None:
        """Scenario 3: Completing 100% dwell triggers callback and enters COOLDOWN."""
        # Start dwell at t=1.0
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.0)

        # Reach 100% dwell duration at t=1.85 (0.85s >= 0.80s)
        res = self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.85)

        self.assertTrue(res.triggered)
        self.assertEqual(self.callback_count, 1)
        self.assertEqual(res.state, DwellState.COOLDOWN)

        # Frame immediately after is in cooldown (does not re-trigger)
        res_cool = self.selector.update((150.0, 130.0), tracking_valid=True, current_time=2.0)
        self.assertEqual(res_cool.state, DwellState.COOLDOWN)
        self.assertEqual(self.callback_count, 1)

    def test_leaving_before_completion_cancels_dwell(self) -> None:
        """Scenario 4: Moving gaze away before dwell completes cancels progress."""
        # Focus at t=1.0
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.0)
        # Advance to 50% at t=1.40
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.40)

        # Move to empty space outside targets at t=1.50
        res_exit = self.selector.update((50.0, 50.0), tracking_valid=True, current_time=1.50)

        self.assertIsNone(res_exit.target_id)
        self.assertEqual(res_exit.state, DwellState.IDLE)
        self.assertEqual(res_exit.progress, 0.0)
        self.assertEqual(self.callback_count, 0)

    def test_repeated_gaze_after_cooldown_expires(self) -> None:
        """Scenario 5: After cooldown expires, gazing again initiates a fresh dwell cycle."""
        # 1. Trigger selection at t=1.0 -> t=1.85
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.0)
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.85)
        self.assertEqual(self.callback_count, 1)

        # 2. Advance time past cooldown duration (cooldown is 0.50s, so t=2.40 >= 1.85 + 0.50)
        res_after = self.selector.update((150.0, 130.0), tracking_valid=True, current_time=2.45)
        self.assertEqual(res_after.target_id, "btn_a")
        self.assertIn(res_after.state, (DwellState.FOCUSING, DwellState.DWELLING))

        # 3. Complete second dwell at t=3.30
        res_second = self.selector.update((150.0, 130.0), tracking_valid=True, current_time=3.30)
        self.assertTrue(res_second.triggered)
        self.assertEqual(self.callback_count, 2)

    def test_tracking_loss_cancels_dwell(self) -> None:
        """Scenario 6: Gaze tracking loss immediately cancels active dwell."""
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.0)
        self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.40)

        # Tracking lost
        res_lost = self.selector.update((150.0, 130.0), tracking_valid=False, current_time=1.50)
        self.assertIsNone(res_lost.target_id)
        self.assertEqual(res_lost.state, DwellState.IDLE)
        self.assertEqual(res_lost.progress, 0.0)
        self.assertFalse(res_lost.is_stable)

    def test_disabled_target_is_ignored(self) -> None:
        """Scenario 7: Disabled targets cannot be focused or triggered."""
        self.target_a.enabled = False

        res = self.selector.update((150.0, 130.0), tracking_valid=True, current_time=1.0)
        self.assertIsNone(res.target_id)
        self.assertEqual(res.state, DwellState.IDLE)
        self.assertEqual(self.callback_count, 0)

    def test_invalid_coordinates_handled_gracefully(self) -> None:
        """Scenario 8: NaN or Inf coordinates are safely handled."""
        res = self.selector.update((float("nan"), float("inf")), tracking_valid=True, current_time=1.0)
        self.assertIsNone(res.target_id)
        self.assertEqual(res.state, DwellState.IDLE)

    def test_manual_trigger_fallback(self) -> None:
        """Scenario 9: Keyboard/Mouse fallback manually triggers target immediately."""
        success = self.selector.trigger_target("btn_a", current_time=1.0)

        self.assertTrue(success)
        self.assertEqual(self.callback_count, 1)
        self.assertEqual(self.selector.state, DwellState.COOLDOWN)


if __name__ == "__main__":
    unittest.main()
