"""Eye and iris landmark extraction and tracking module."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import cv2
import numpy as np

# MediaPipe 478 Landmark Indices for Eyes & Irises
# Left eye (Anatomical user left / Image right)
LEFT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
LEFT_IRIS_INDICES = [473, 474, 475, 476, 477]  # 473 is center landmark

# Right eye (Anatomical user right / Image left)
RIGHT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_IRIS_INDICES = [468, 469, 470, 471, 472]  # 468 is center landmark


@dataclass
class EyeData:
    """Structured eye and iris tracking coordinates."""

    left_eye_points: List[Tuple[int, int]] = field(default_factory=list)
    right_eye_points: List[Tuple[int, int]] = field(default_factory=list)
    left_iris_points: List[Tuple[int, int]] = field(default_factory=list)
    right_iris_points: List[Tuple[int, int]] = field(default_factory=list)
    left_iris_center: Tuple[float, float] = (0.0, 0.0)
    right_iris_center: Tuple[float, float] = (0.0, 0.0)
    left_iris_center_px: Tuple[int, int] = (0, 0)
    right_iris_center_px: Tuple[int, int] = (0, 0)
    detected: bool = False


class EyeTracker:
    """Extracts eye regions, iris boundaries, and center coordinates from facial landmarks."""

    def __init__(self) -> None:
        pass

    def extract(
        self,
        normalized_landmarks: List[Tuple[float, float]],
        width: int,
        height: int,
    ) -> EyeData:
        """
        Extract eye and iris data from normalized landmark coordinates.

        Args:
            normalized_landmarks: List of (norm_x, norm_y) coordinates for all face landmarks.
            width: Frame width in pixels.
            height: Frame height in pixels.

        Returns:
            Populated EyeData object.
        """
        total_lms = len(normalized_landmarks)
        # We need at least 478 landmarks to have refined iris landmarks (468-477)
        if total_lms < 478 or width <= 0 or height <= 0:
            return EyeData(detected=False)

        def to_px(norm_pt: Tuple[float, float]) -> Tuple[int, int]:
            return (
                int(np.clip(norm_pt[0] * width, 0, width - 1)),
                int(np.clip(norm_pt[1] * height, 0, height - 1)),
            )

        # Extract eye contour points
        left_eye_pts = [to_px(normalized_landmarks[i]) for i in LEFT_EYE_INDICES if i < total_lms]
        right_eye_pts = [to_px(normalized_landmarks[i]) for i in RIGHT_EYE_INDICES if i < total_lms]

        # Extract iris points
        left_iris_pts = [to_px(normalized_landmarks[i]) for i in LEFT_IRIS_INDICES if i < total_lms]
        right_iris_pts = [to_px(normalized_landmarks[i]) for i in RIGHT_IRIS_INDICES if i < total_lms]

        # Compute normalized and pixel iris centers
        # Left Iris (indices 473..477, mean of points for stability)
        left_norm_pts = [normalized_landmarks[i] for i in LEFT_IRIS_INDICES if i < total_lms]
        left_center_norm = (
            float(np.mean([p[0] for p in left_norm_pts])),
            float(np.mean([p[1] for p in left_norm_pts])),
        )
        left_center_px = to_px(left_center_norm)

        # Right Iris (indices 468..472, mean of points for stability)
        right_norm_pts = [normalized_landmarks[i] for i in RIGHT_IRIS_INDICES if i < total_lms]
        right_center_norm = (
            float(np.mean([p[0] for p in right_norm_pts])),
            float(np.mean([p[1] for p in right_norm_pts])),
        )
        right_center_px = to_px(right_center_norm)

        return EyeData(
            left_eye_points=left_eye_pts,
            right_eye_points=right_eye_pts,
            left_iris_points=left_iris_pts,
            right_iris_points=right_iris_pts,
            left_iris_center=left_center_norm,
            right_iris_center=right_center_norm,
            left_iris_center_px=left_center_px,
            right_iris_center_px=right_center_px,
            detected=True,
        )

    def draw_overlay(self, frame: np.ndarray, eye_data: EyeData) -> np.ndarray:
        """
        Draw highlighted eye outlines, iris boundaries, and iris center markers onto the frame.
        """
        if not eye_data.detected or frame is None:
            return frame

        # Draw left and right eye contours (smooth connected polygons)
        if len(eye_data.left_eye_points) > 0:
            left_hull = cv2.convexHull(np.array(eye_data.left_eye_points, dtype=np.int32))
            cv2.polylines(frame, [left_hull], isClosed=True, color=(248, 189, 56), thickness=1, lineType=cv2.LINE_AA)

        if len(eye_data.right_eye_points) > 0:
            right_hull = cv2.convexHull(np.array(eye_data.right_eye_points, dtype=np.int32))
            cv2.polylines(frame, [right_hull], isClosed=True, color=(248, 189, 56), thickness=1, lineType=cv2.LINE_AA)

        # Draw iris circles / outlines
        for iris_pts, center_px in [
            (eye_data.left_iris_points, eye_data.left_iris_center_px),
            (eye_data.right_iris_points, eye_data.right_iris_center_px),
        ]:
            if len(iris_pts) > 0:
                # Estimate radius from points to center
                dists = [np.linalg.norm(np.array(pt) - np.array(center_px)) for pt in iris_pts]
                radius = max(2, int(np.mean(dists))) if dists else 3

                # Iris outline (emerald green)
                cv2.circle(frame, center_px, radius, (34, 197, 94), 1, lineType=cv2.LINE_AA)
                # Iris center crosshair + dot (vibrant magenta/amber)
                cx, cy = center_px
                cv2.line(frame, (cx - 3, cy), (cx + 3, cy), (244, 63, 94), 1, lineType=cv2.LINE_AA)
                cv2.line(frame, (cx, cy - 3), (cx, cy + 3), (244, 63, 94), 1, lineType=cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 2, (255, 255, 255), -1, lineType=cv2.LINE_AA)

        return frame
