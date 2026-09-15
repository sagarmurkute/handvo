"""Hand cursor management with One-Euro smoothing and window coordinate mapping."""

from dataclasses import dataclass
from typing import Optional, Tuple
from app.gestures.smoothing import OneEuroFilter2D
from app.vision.landmarks import HandLandmarks


@dataclass
class CursorPosition:
    """Represents real-time screen/window cursor coordinates."""
    norm_x: float = 0.5
    norm_y: float = 0.5
    pixel_x: int = 0
    pixel_y: int = 0
    is_valid: bool = False


class HandCursorManager:
    """Manages virtual hand cursor position based on index fingertip tracking."""

    def __init__(self, smooth_filter: Optional[OneEuroFilter2D] = None) -> None:
        self.smoother = smooth_filter or OneEuroFilter2D(min_cutoff=1.5, beta=0.03)
        self.is_enabled = True
        self._last_position = CursorPosition()

    def update(
        self,
        hand: Optional[HandLandmarks],
        window_width: int,
        window_height: int,
    ) -> CursorPosition:
        """Update cursor position from index fingertip coordinates."""
        if not self.is_enabled or hand is None or not hand.is_valid:
            self._last_position = CursorPosition(
                norm_x=self._last_position.norm_x,
                norm_y=self._last_position.norm_y,
                pixel_x=self._last_position.pixel_x,
                pixel_y=self._last_position.pixel_y,
                is_valid=False,
            )
            return self._last_position

        index_tip = hand.index_tip
        if index_tip is None:
            return self._last_position

        # Apply 1-Euro smoothing
        smooth_x, smooth_y = self.smoother.filter(index_tip.x, index_tip.y)

        # Clamp to normalized [0, 1] range
        clamped_x = max(0.0, min(1.0, smooth_x))
        clamped_y = max(0.0, min(1.0, smooth_y))

        px = int(clamped_x * window_width)
        py = int(clamped_y * window_height)

        self._last_position = CursorPosition(
            norm_x=clamped_x,
            norm_y=clamped_y,
            pixel_x=px,
            pixel_y=py,
            is_valid=True,
        )
        return self._last_position

    def reset(self) -> None:
        self.smoother.reset()
        self._last_position = CursorPosition()
