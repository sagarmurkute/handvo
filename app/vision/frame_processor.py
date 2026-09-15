"""Vision pipeline frame processor coordinating camera capture and hand landmark detection."""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import cv2
import numpy as np

from app.vision.camera import Camera
from app.vision.hand_detector import HandDetector
from app.vision.landmarks import HandLandmarks


@dataclass
class VisionFrameResult:
    """Output packet from vision frame processing."""
    frame: np.ndarray
    annotated_frame: np.ndarray
    hands: List[HandLandmarks]
    has_hands: bool = False
    primary_hand: Optional[HandLandmarks] = None


class FrameProcessor:
    """Processes camera frames through the computer vision pipeline."""

    def __init__(self, camera: Camera, hand_detector: HandDetector) -> None:
        self.camera = camera
        self.hand_detector = hand_detector

    def process_next_frame(self) -> Tuple[bool, Optional[VisionFrameResult]]:
        """Read and process next camera frame."""
        success, frame = self.camera.read_frame()
        if not success or frame is None:
            return False, None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands = self.hand_detector.detect(rgb)
        annotated = self.hand_detector.draw_skeleton(frame, hands)

        primary_hand = hands[0] if len(hands) > 0 else None

        result = VisionFrameResult(
            frame=frame,
            annotated_frame=annotated,
            hands=hands,
            has_hands=len(hands) > 0,
            primary_hand=primary_hand,
        )
        return True, result
