"""Pinch gesture detection between thumb tip and index tip."""

import math
from dataclasses import dataclass
from typing import Optional
from app.vision.landmarks import HandLandmarks


@dataclass
class PinchState:
    """Represents real-time pinch state metrics."""
    is_pinched: bool = False
    pinch_distance: float = 1.0
    normalized_distance: float = 1.0
    is_new_pinch: bool = False  # Trigger event edge


class PinchDetector:
    """Detects pinch contact gestures between thumb tip (4) and index tip (8)."""

    def __init__(self, pinch_threshold: float = 0.06, release_threshold: float = 0.08) -> None:
        self.pinch_threshold = pinch_threshold
        self.release_threshold = release_threshold
        self._was_pinched = False

    def detect(self, hand: Optional[HandLandmarks]) -> PinchState:
        """Calculate normalized pinch distance and trigger states."""
        if hand is None or not hand.is_valid:
            self._was_pinched = False
            return PinchState(is_pinched=False, pinch_distance=1.0, normalized_distance=1.0, is_new_pinch=False)

        thumb = hand.thumb_tip
        index = hand.index_tip
        wrist = hand.wrist
        middle_mcp = hand.middle_mcp

        if thumb is None or index is None or wrist is None or middle_mcp is None:
            self._was_pinched = False
            return PinchState(is_pinched=False, pinch_distance=1.0, normalized_distance=1.0, is_new_pinch=False)

        # Euclidean distance between Thumb Tip and Index Tip
        dx = thumb.x - index.x
        dy = thumb.y - index.y
        dz = thumb.z - index.z
        raw_dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        # Scale normalization by palm scale (distance between wrist and middle MCP)
        pdx = middle_mcp.x - wrist.x
        pdy = middle_mcp.y - wrist.y
        pdz = middle_mcp.z - wrist.z
        palm_scale = math.sqrt(pdx * pdx + pdy * pdy + pdz * pdz)
        norm_dist = raw_dist / palm_scale if palm_scale > 0.001 else raw_dist

        # Hysteresis thresholding
        if self._was_pinched:
            is_pinched = norm_dist < self.release_threshold
        else:
            is_pinched = norm_dist < self.pinch_threshold

        is_new_pinch = is_pinched and not self._was_pinched
        self._was_pinched = is_pinched

        return PinchState(
            is_pinched=is_pinched,
            pinch_distance=raw_dist,
            normalized_distance=norm_dist,
            is_new_pinch=is_new_pinch,
        )

    def reset(self) -> None:
        self._was_pinched = False
