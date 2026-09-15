"""Real-time MediaPipe Face Landmark detection module."""

from pathlib import Path
from typing import Any, List, Optional, Tuple
import cv2
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "models"
MODEL_PATH = MODEL_DIR / "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"


class FaceDetector:
    """Manages MediaPipe Face Landmarker for real-time face detection and visualization."""

    def __init__(self, model_path: Optional[Path] = None) -> None:
        self.model_path = model_path or MODEL_PATH
        self._landmarker: Any = None
        self._initialized = False
        self._init_detector()

    def _ensure_model_exists(self) -> bool:
        """Verify model file existence, downloading if missing."""
        if self.model_path.exists() and self.model_path.stat().st_size > 0:
            return True
        try:
            import urllib.request
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(MODEL_URL, str(self.model_path))
            return self.model_path.exists() and self.model_path.stat().st_size > 0
        except Exception:
            return False

    def _init_detector(self) -> None:
        """Initialize MediaPipe FaceLandmarker."""
        if not self._ensure_model_exists():
            return

        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=str(self.model_path))
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
            )
            self._landmarker = vision.FaceLandmarker.create_from_options(options)
            self._initialized = True
        except Exception:
            self._landmarker = None
            self._initialized = False

    def process_frame(
        self,
        frame: np.ndarray,
    ) -> Tuple[bool, np.ndarray, List[Tuple[int, int]], List[Tuple[float, float]]]:
        """
        Process a BGR frame, detect face landmarks, and draw subtle face mesh overlay.

        Returns:
            (face_detected, annotated_frame, pixel_landmarks, normalized_landmarks)
        """
        if not self._initialized or self._landmarker is None or frame is None:
            return False, frame, [], []

        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        annotated_frame = frame.copy()
        pixel_landmarks: List[Tuple[int, int]] = []
        normalized_landmarks: List[Tuple[float, float]] = []

        try:
            import mediapipe as mp
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = self._landmarker.detect(mp_image)

            if result.face_landmarks and len(result.face_landmarks) > 0:
                for lm in result.face_landmarks[0]:
                    normalized_landmarks.append((float(lm.x), float(lm.y)))
                    x = max(0, min(w - 1, int(lm.x * w)))
                    y = max(0, min(h - 1, int(lm.y * h)))
                    pixel_landmarks.append((x, y))
        except Exception:
            pixel_landmarks = []
            normalized_landmarks = []

        face_detected = len(pixel_landmarks) > 0

        if face_detected:
            # Draw subtle facial landmark points (face mesh structure)
            for x, y in pixel_landmarks:
                cv2.circle(annotated_frame, (x, y), 1, (100, 116, 139), -1, lineType=cv2.LINE_AA)

        return face_detected, annotated_frame, pixel_landmarks, normalized_landmarks

    def close(self) -> None:
        """Release MediaPipe model resources."""
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None
        self._initialized = False
