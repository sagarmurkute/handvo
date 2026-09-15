"""Test suite for Advanced Multi-Gesture Classifier."""

import unittest
from app.gestures.gesture_classifier import GestureType, HandGestureClassifier
from app.vision.landmarks import HandLandmarks, LandmarkPoint


class TestHandGestureClassifier(unittest.TestCase):
    """Unit tests for static and dynamic hand gesture recognition."""

    def setUp(self) -> None:
        self.classifier = HandGestureClassifier()

    def _build_hand(self, tip_y_offsets=(0.2, 0.2, 0.2, 0.2, 0.2), wrist_y=0.7) -> HandLandmarks:
        """Create a mock 21-point hand landmark set."""
        pts = []
        # 0: Wrist
        pts.append(LandmarkPoint(x=0.5, y=wrist_y, z=0.0))
        # 1-4: Thumb (CMC, MCP, IP, Tip)
        pts.append(LandmarkPoint(x=0.45, y=wrist_y - 0.1, z=0.0))
        pts.append(LandmarkPoint(x=0.42, y=wrist_y - 0.15, z=0.0))
        pts.append(LandmarkPoint(x=0.40, y=wrist_y - 0.2, z=0.0))
        pts.append(LandmarkPoint(x=0.38, y=tip_y_offsets[0], z=0.0))

        # 5-8: Index (MCP, PIP, DIP, Tip)
        pts.append(LandmarkPoint(x=0.48, y=wrist_y - 0.25, z=0.0))
        pts.append(LandmarkPoint(x=0.48, y=wrist_y - 0.35, z=0.0))
        pts.append(LandmarkPoint(x=0.48, y=wrist_y - 0.45, z=0.0))
        pts.append(LandmarkPoint(x=0.48, y=tip_y_offsets[1], z=0.0))

        # 9-12: Middle (MCP, PIP, DIP, Tip)
        pts.append(LandmarkPoint(x=0.52, y=wrist_y - 0.25, z=0.0))
        pts.append(LandmarkPoint(x=0.52, y=wrist_y - 0.35, z=0.0))
        pts.append(LandmarkPoint(x=0.52, y=wrist_y - 0.45, z=0.0))
        pts.append(LandmarkPoint(x=0.52, y=tip_y_offsets[2], z=0.0))

        # 13-16: Ring (MCP, PIP, DIP, Tip)
        pts.append(LandmarkPoint(x=0.55, y=wrist_y - 0.23, z=0.0))
        pts.append(LandmarkPoint(x=0.55, y=wrist_y - 0.33, z=0.0))
        pts.append(LandmarkPoint(x=0.55, y=wrist_y - 0.43, z=0.0))
        pts.append(LandmarkPoint(x=0.55, y=tip_y_offsets[3], z=0.0))

        # 17-20: Pinky (MCP, PIP, DIP, Tip)
        pts.append(LandmarkPoint(x=0.58, y=wrist_y - 0.20, z=0.0))
        pts.append(LandmarkPoint(x=0.58, y=wrist_y - 0.30, z=0.0))
        pts.append(LandmarkPoint(x=0.58, y=wrist_y - 0.40, z=0.0))
        pts.append(LandmarkPoint(x=0.58, y=tip_y_offsets[4], z=0.0))

        return HandLandmarks(landmarks=pts, handedness="Right", confidence=0.9)

    def test_open_palm_gesture(self) -> None:
        """Scenario 1: All 5 fingers extended outward."""
        hand = self._build_hand(tip_y_offsets=(0.3, 0.15, 0.12, 0.15, 0.20), wrist_y=0.7)
        res = self.classifier.classify(hand)
        self.assertEqual(res.gesture, GestureType.OPEN_PALM)
        self.assertTrue(res.finger_states["index"])
        self.assertTrue(res.finger_states["middle"])

    def test_fist_gesture(self) -> None:
        """Scenario 2: All fingers folded/curled inward."""
        hand = self._build_hand(tip_y_offsets=(0.75, 0.72, 0.73, 0.72, 0.74), wrist_y=0.7)
        res = self.classifier.classify(hand)
        self.assertEqual(res.gesture, GestureType.FIST)
        self.assertFalse(res.finger_states["index"])
        self.assertFalse(res.finger_states["middle"])

    def test_peace_sign_gesture(self) -> None:
        """Scenario 3: Index & Middle extended up, Ring & Pinky folded."""
        hand = self._build_hand(tip_y_offsets=(0.75, 0.15, 0.12, 0.72, 0.74), wrist_y=0.7)
        res = self.classifier.classify(hand)
        self.assertEqual(res.gesture, GestureType.PEACE_SIGN)

    def test_pointing_gesture(self) -> None:
        """Scenario 4: Only Index extended."""
        hand = self._build_hand(tip_y_offsets=(0.75, 0.15, 0.73, 0.72, 0.74), wrist_y=0.7)
        res = self.classifier.classify(hand)
        self.assertEqual(res.gesture, GestureType.POINTING)

    def test_thumbs_up_gesture(self) -> None:
        """Scenario 5: Thumb extended high above wrist, fingers folded."""
        hand = self._build_hand(tip_y_offsets=(0.4, 0.72, 0.73, 0.72, 0.74), wrist_y=0.7)
        res = self.classifier.classify(hand)
        self.assertEqual(res.gesture, GestureType.THUMBS_UP)

    def test_dynamic_swipe_gesture(self) -> None:
        """Scenario 6: Rapid lateral movement triggers swipe event."""
        # Frame 1 at t=0.0, x=0.2
        h1 = self._build_hand(wrist_y=0.7)
        h1.landmarks[0].x = 0.2
        self.classifier.classify(h1, current_time=0.0)

        # Frame 2 at t=0.05, x=0.35
        h2 = self._build_hand(wrist_y=0.7)
        h2.landmarks[0].x = 0.35
        self.classifier.classify(h2, current_time=0.05)

        # Frame 3 at t=0.10, x=0.55
        h3 = self._build_hand(wrist_y=0.7)
        h3.landmarks[0].x = 0.55
        self.classifier.classify(h3, current_time=0.10)

        # Frame 4 at t=0.15, x=0.75 (speed = (0.75 - 0.2) / 0.15 = 3.66 > 1.2 threshold)
        h4 = self._build_hand(wrist_y=0.7)
        h4.landmarks[0].x = 0.75
        res = self.classifier.classify(h4, current_time=0.15)

        self.assertEqual(res.swipe_event, "right")
        self.assertEqual(res.gesture, GestureType.SWIPE_RIGHT)
