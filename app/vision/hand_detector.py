"""MediaPipe HandLandmarker wrapper for real-time 21-hand landmark extraction."""

from pathlib import Path
from typing import Any, List, Optional, Tuple
import cv2
import numpy as np

from app.vision.landmarks import HandLandmarks, LandmarkPoint

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "models"
HAND_MODEL_PATH = MODEL_DIR / "hand_landmarker.task"
HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

# Standard Hand Connections (21 Landmarks)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
    (0, 17)                                # Palm base
]


class HandDetector:
    """Detects 21 3D hand landmarks using MediaPipe HandLandmarker."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = model_path or HAND_MODEL_PATH
        self._landmarker: Any = None
        self._initialized = False
        self._init_detector()

    def _ensure_model_exists(self) -> bool:
        """Download hand landmarker task file if missing."""
        if self.model_path.exists() and self.model_path.stat().st_size > 0:
            return True
        try:
            import urllib.request
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(HAND_MODEL_URL, str(self.model_path))
            return self.model_path.exists() and self.model_path.stat().st_size > 0
        except Exception:
            return False

    def _init_detector(self) -> None:
        """Initialize MediaPipe HandLandmarker."""
        if not self._ensure_model_exists():
            return

        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=str(self.model_path))
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_hands=2,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._landmarker = vision.HandLandmarker.create_from_options(options)
            self._initialized = True
        except Exception:
            self._landmarker = None
            self._initialized = False

    def detect(self, rgb_frame: np.ndarray) -> List[HandLandmarks]:
        """Detect hands and return list of HandLandmarks dataclasses."""
        if not self._initialized or self._landmarker is None or rgb_frame is None:
            return []

        results: List[HandLandmarks] = []
        try:
            import mediapipe as mp
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self._landmarker.detect(mp_image)

            if detection_result.hand_landmarks:
                for idx, hand in enumerate(detection_result.hand_landmarks):
                    handedness = "Right"
                    if detection_result.handedness and idx < len(detection_result.handedness):
                        handedness = detection_result.handedness[idx][0].category_name

                    landmarks_list = [
                        LandmarkPoint(x=float(lm.x), y=float(lm.y), z=float(lm.z))
                        for lm in hand
                    ]
                    results.append(HandLandmarks(landmarks=landmarks_list, handedness=handedness, confidence=0.9))
        except Exception:
            results = []

        return results

    def draw_skeleton(self, frame: np.ndarray, hands: List[HandLandmarks]) -> np.ndarray:
        """Draw hand skeletal connections and landmarks on frame."""
        h, w = frame.shape[:2]
        annotated = frame.copy()

        for hand in hands:
            if not hand.is_valid:
                continue

            pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand.landmarks]

            # Draw bones
            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx < len(pts) and end_idx < len(pts):
                    cv2.line(annotated, pts[start_idx], pts[end_idx], (14, 165, 233), 2, cv2.LINE_AA)

            # Draw joint points
            for idx, (x, y) in enumerate(pts):
                # Accentuate index tip and thumb tip
                if idx in (4, 8):
                    cv2.circle(annotated, (x, y), 6, (34, 197, 94), -1, cv2.LINE_AA)
                    cv2.circle(annotated, (x, y), 8, (255, 255, 255), 1, cv2.LINE_AA)
                else:
                    cv2.circle(annotated, (x, y), 3, (56, 189, 248), -1, cv2.LINE_AA)

        return annotated

    def close(self) -> None:
        """Release MediaPipe model resources."""
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None
        self._initialized = False
