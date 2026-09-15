"""Unit tests for EYEVO configuration, camera, face detector, and eye tracker modules."""

import unittest
from app.config import CONFIG
import app


class TestAppFoundation(unittest.TestCase):
    def test_foundation(self) -> None:
        self.assertEqual(app.__app_name__, "EYEVO")
        self.assertEqual(CONFIG.app_name, "EYEVO")
        self.assertEqual(CONFIG.app_subtitle, "Eye-Gaze Assistive Communication")
        self.assertEqual(CONFIG.window_title, "EYEVO")

    def test_camera_module(self) -> None:
        try:
            from app.vision.camera import Camera
            cam = Camera(device_index=999)
            self.assertFalse(cam.is_opened())
            opened = cam.open()
            if not opened:
                self.assertFalse(cam.is_opened())
                success, frame = cam.read_frame()
                self.assertFalse(success)
                self.assertIsNone(frame)
            cam.release()
            self.assertFalse(cam.is_opened())
        except ImportError:
            pass

    def test_face_detector_module(self) -> None:
        try:
            from app.vision.face_detector import FaceDetector
            detector = FaceDetector()
            self.assertTrue(detector._initialized)
            detector.close()
            self.assertFalse(detector._initialized)
        except ImportError:
            pass

    def test_eye_tracker_module(self) -> None:
        try:
            from app.vision.eye_tracker import EyeTracker, EyeData
            import numpy as np

            tracker = EyeTracker()
            # Test insufficient landmarks
            empty_data = tracker.extract([], 640, 480)
            self.assertFalse(empty_data.detected)

            # Test synthetic 478 landmarks
            mock_landmarks = [(0.5 + 0.001 * i, 0.5 + 0.001 * i) for i in range(478)]
            eye_data = tracker.extract(mock_landmarks, 640, 480)
            self.assertTrue(eye_data.detected)
            self.assertGreater(len(eye_data.left_eye_points), 0)
            self.assertGreater(len(eye_data.right_eye_points), 0)
            self.assertGreater(len(eye_data.left_iris_points), 0)
            self.assertGreater(len(eye_data.right_iris_points), 0)
            self.assertIsInstance(eye_data.left_iris_center, tuple)
            self.assertIsInstance(eye_data.right_iris_center, tuple)

            # Test overlay drawing
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            annotated = tracker.draw_overlay(frame, eye_data)
            self.assertEqual(annotated.shape, (480, 640, 3))
        except ImportError:
            pass


if __name__ == "__main__":
    unittest.main()
