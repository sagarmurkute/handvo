"""Unified gesture interaction engine coordinating cursor, pinch, and dwell selection."""

from dataclasses import dataclass
from typing import Optional, Tuple

from app.gestures.cursor import CursorPosition, HandCursorManager
from app.gestures.dwell import DwellResult, DwellSelector
from app.gestures.pinch import PinchDetector, PinchState
from app.vision.landmarks import HandLandmarks


@dataclass
class GestureFrameResult:
    """Consolidated interaction result for a single frame."""
    cursor: CursorPosition
    pinch: PinchState
    dwell: DwellResult
    has_interaction: bool = False


class GestureEngine:
    """High-level facade coordinating hand tracking, cursor motion, pinch clicks, and dwell selections."""

    def __init__(
        self,
        cursor_manager: Optional[HandCursorManager] = None,
        pinch_detector: Optional[PinchDetector] = None,
        dwell_selector: Optional[DwellSelector] = None,
    ) -> None:
        self.cursor_manager = cursor_manager or HandCursorManager()
        self.pinch_detector = pinch_detector or PinchDetector()
        self.dwell_selector = dwell_selector or DwellSelector()

    def update(
        self,
        hand: Optional[HandLandmarks],
        window_width: int,
        window_height: int,
        current_time: Optional[float] = None,
    ) -> GestureFrameResult:
        """Process hand landmarks through cursor, pinch, and dwell pipelines."""
        cursor_pos = self.cursor_manager.update(hand, window_width, window_height)
        pinch_state = self.pinch_detector.detect(hand)
        dwell_result = self.dwell_selector.update(
            cursor_px=(cursor_pos.pixel_x, cursor_pos.pixel_y),
            tracking_valid=cursor_pos.is_valid,
            current_time=current_time,
        )

        return GestureFrameResult(
            cursor=cursor_pos,
            pinch=pinch_state,
            dwell=dwell_result,
            has_interaction=cursor_pos.is_valid,
        )

    def reset(self) -> None:
        self.cursor_manager.reset()
        self.pinch_detector.reset()
        self.dwell_selector.reset()
