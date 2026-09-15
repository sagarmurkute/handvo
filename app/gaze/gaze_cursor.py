"""Gaze cursor manager for coordinate transformation, velocity smoothing, and boundary clamping."""

import math
from dataclasses import dataclass
from typing import Optional, Tuple
from app.gaze.calibration_model import CalibrationModel


@dataclass
class CursorConfig:
    """Configurable settings for cursor smoothing, size, and boundaries."""

    min_smoothing: float = 0.20  # Alpha during stillness/fixation
    max_smoothing: float = 0.85  # Alpha during fast eye saccades
    cursor_size: int = 32  # Diameter in pixels
    margin_px: int = 16  # Inset margin from window boundaries
    jitter_threshold_px: float = 1.0  # Subpixel movement suppression threshold


@dataclass
class CursorPosition:
    """Current cursor state and coordinates."""

    pixel_x: float = 0.0
    pixel_y: float = 0.0
    norm_x: float = 0.5
    norm_y: float = 0.5
    is_valid: bool = False
    is_visible: bool = True


class GazeCursorManager:
    """Manages virtual gaze cursor position, responsive smoothing, and window boundary clamping."""

    def __init__(self, config: Optional[CursorConfig] = None) -> None:
        self.config = config or CursorConfig()
        self.is_enabled: bool = True
        self._current_x: Optional[float] = None
        self._current_y: Optional[float] = None
        self._last_position = CursorPosition()

    def update(
        self,
        gaze_x: float,
        gaze_y: float,
        tracking_valid: bool,
        calibration_model: Optional[CalibrationModel],
        window_w: int,
        window_h: int,
    ) -> CursorPosition:
        """
        Process a gaze sample and compute smoothed, clamped window cursor coordinates.

        Args:
            gaze_x: Normalized horizontal gaze (0.0 to 1.0).
            gaze_y: Normalized vertical gaze (0.0 to 1.0).
            tracking_valid: True if valid eye/face tracking is currently available.
            calibration_model: Optional fitted calibration model for gaze-to-screen mapping.
            window_w: Active application window width in pixels.
            window_h: Active application window height in pixels.

        Returns:
            CursorPosition with clamped pixel coordinates and tracking status.
        """
        if window_w <= 0 or window_h <= 0:
            return CursorPosition(is_valid=False, is_visible=self.is_enabled)

        # Handle lost tracking -> preserve last position without jittering
        if not tracking_valid or not math.isfinite(gaze_x) or not math.isfinite(gaze_y):
            self._last_position = CursorPosition(
                pixel_x=self._current_x if self._current_x is not None else window_w / 2.0,
                pixel_y=self._current_y if self._current_y is not None else window_h / 2.0,
                norm_x=(self._current_x / window_w) if self._current_x is not None else 0.5,
                norm_y=(self._current_y / window_h) if self._current_y is not None else 0.5,
                is_valid=False,
                is_visible=self.is_enabled,
            )
            return self._last_position

        # 1. Map normalized gaze to calibrated screen position
        if calibration_model is not None and calibration_model.is_trained:
            norm_screen_x, norm_screen_y = calibration_model.predict(gaze_x, gaze_y)
        else:
            norm_screen_x, norm_screen_y = gaze_x, gaze_y

        target_px = norm_screen_x * window_w
        target_py = norm_screen_y * window_h

        # 2. Clamp coordinates within usable window boundaries
        margin = self.config.margin_px
        clamped_px = max(margin, min(target_px, window_w - margin))
        clamped_py = max(margin, min(target_py, window_h - margin))

        # 3. Apply velocity-adaptive smoothing
        if self._current_x is None or self._current_y is None:
            self._current_x = clamped_px
            self._current_y = clamped_py
        else:
            dist = math.hypot(clamped_px - self._current_x, clamped_py - self._current_y)
            if dist >= self.config.jitter_threshold_px:
                # Fast movements adapt to higher alpha for snappy responsiveness
                speed_ratio = min(1.0, dist / 80.0)
                alpha = self.config.min_smoothing + speed_ratio * (self.config.max_smoothing - self.config.min_smoothing)

                self._current_x = alpha * clamped_px + (1.0 - alpha) * self._current_x
                self._current_y = alpha * clamped_py + (1.0 - alpha) * self._current_y

        self._last_position = CursorPosition(
            pixel_x=self._current_x,
            pixel_y=self._current_y,
            norm_x=self._current_x / window_w,
            norm_y=self._current_y / window_h,
            is_valid=True,
            is_visible=self.is_enabled,
        )
        return self._last_position

    def set_enabled(self, enabled: bool) -> None:
        """Toggle cursor visibility."""
        self.is_enabled = enabled
        self._last_position.is_visible = enabled

    def reset(self) -> None:
        """Reset cursor smoothing history."""
        self._current_x = None
        self._current_y = None
        self._last_position = CursorPosition(is_valid=False, is_visible=self.is_enabled)
