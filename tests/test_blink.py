"""Unit tests for the Eye Blink Detector state machine and timing logic."""

import unittest
from app.vision.blink_detector import BlinkConfig, BlinkDetector, BlinkState


class TestBlinkDetector(unittest.TestCase):
    """Test suite verifying eye openness state transitions and blink filtering."""

    def setUp(self) -> None:
        self.config = BlinkConfig(
            closed_threshold=0.19,
            open_threshold=0.24,
            min_closed_duration_sec=0.05,
            max_blink_duration_sec=0.40,
            cooldown_sec=0.20,
        )
        self.detector = BlinkDetector(self.config)

    def test_eyes_remain_open_no_blink(self) -> None:
        """Scenario 1: Eyes stay continuously open -> 0 blinks detected."""
        for i in range(10):
            res = self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=i * 0.033)
            self.assertFalse(res.blink_detected)
            self.assertEqual(res.blink_count, 0)
            self.assertEqual(res.state, BlinkState.OPEN)

    def test_intentional_blink_detected(self) -> None:
        """Scenario 2: Eyes briefly close (e.g. 150ms) and reopen -> exactly 1 blink."""
        t = 0.0

        # 1. Open
        res = self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=t)
        self.assertFalse(res.blink_detected)

        # 2. Closing / Closed for 150ms (from t=0.10 to t=0.25)
        t = 0.10
        res = self.detector.update_from_ear(0.12, 0.12, 0.12, current_time=t)
        self.assertEqual(res.state, BlinkState.CLOSING)

        t = 0.15
        res = self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=t)
        self.assertEqual(res.state, BlinkState.CLOSED)

        t = 0.25
        res = self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=t)
        self.assertEqual(res.state, BlinkState.CLOSED)

        # 3. Reopen at t=0.28
        t = 0.28
        res = self.detector.update_from_ear(0.32, 0.32, 0.32, current_time=t)
        self.assertTrue(res.blink_detected)
        self.assertEqual(res.blink_count, 1)
        self.assertEqual(res.state, BlinkState.COMPLETED)

        # 4. Next frame returns to OPEN
        t = 0.31
        res = self.detector.update_from_ear(0.32, 0.32, 0.32, current_time=t)
        self.assertFalse(res.blink_detected)
        self.assertEqual(res.state, BlinkState.OPEN)

    def test_prolonged_eye_closure_no_blink(self) -> None:
        """Scenario 3: Eyes remain closed for too long (> max_blink_duration) -> 0 blinks."""
        # Close eyes at t=1.0
        self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=1.0)
        # Keep closed until t=1.8 (800ms > 400ms max)
        self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=1.8)

        # Reopen eyes at t=1.9
        res = self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=1.9)
        self.assertFalse(res.blink_detected)
        self.assertEqual(res.blink_count, 0)

    def test_noisy_threshold_jitter_no_multiple_blinks(self) -> None:
        """Scenario 4: Rapid noise around threshold (< min_closed_duration) -> 0 blinks."""
        # Single frame drop below threshold (lasting only 10ms < 50ms min)
        self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=1.0)
        self.detector.update_from_ear(0.18, 0.18, 0.18, current_time=1.01)
        res = self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=1.02)
        self.assertFalse(res.blink_detected)
        self.assertEqual(res.blink_count, 0)

    def test_two_distinct_blinks(self) -> None:
        """Scenario 5: Two intentional blinks separated by cooldown -> exactly 2 blinks."""
        # Blink 1 (t=1.0 to 1.15)
        self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=0.9)
        self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=1.0)
        self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=1.1)
        res1 = self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=1.15)
        self.assertTrue(res1.blink_detected)
        self.assertEqual(res1.blink_count, 1)

        # Cooldown interval (300ms)
        self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=1.3)
        self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=1.45)

        # Blink 2 (t=1.50 to 1.65)
        self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=1.50)
        self.detector.update_from_ear(0.10, 0.10, 0.10, current_time=1.60)
        res2 = self.detector.update_from_ear(0.30, 0.30, 0.30, current_time=1.65)
        self.assertTrue(res2.blink_detected)
        self.assertEqual(res2.blink_count, 2)


if __name__ == "__main__":
    unittest.main()
