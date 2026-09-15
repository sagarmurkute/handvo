"""Gaze estimation engine with canthal baseline geometry, head-pose motion fusion, and jitter-free filtering."""

import enum
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

# Landmark Indices for Eyes (Mirrored frame)
# Eye 1 Corner & Iris (Anatomical Left / Screen Left in Mirrored Frame)
L_CORNER_1 = 362
L_CORNER_2 = 263
L_INNER_CORNER = L_CORNER_1
L_OUTER_CORNER = L_CORNER_2
L_TOP_LID = 386
L_BOT_LID = 374
L_IRIS_CENTER = 473

# Eye 2 Corner & Iris (Anatomical Right / Screen Right in Mirrored Frame)
R_CORNER_1 = 33
R_CORNER_2 = 133
R_OUTER_CORNER = R_CORNER_1
R_INNER_CORNER = R_CORNER_2
R_TOP_LID = 159
R_BOT_LID = 145
R_IRIS_CENTER = 468

# Facial Anchors for Head Pose / Motion Tracking
NOSE_TIP = 1
MID_EYES_GLABELLA = 168
CHIN = 152
FACE_LEFT_CHEEK = 234
FACE_RIGHT_CHEEK = 454


class GazeDirection(enum.Enum):
    """Gaze orientation classification."""

    CENTER = "LOOKING_CENTER"
    LEFT = "LOOKING_LEFT"
    RIGHT = "LOOKING_RIGHT"
    UP = "LOOKING_UP"
    DOWN = "LOOKING_DOWN"
    UNKNOWN = "UNKNOWN"


@dataclass
class GazeConfig:
    """Configurable parameters for gaze estimation, sensitivity, and adaptive filtering."""

    # Sensitivity multipliers
    sensitivity_x: float = 1.8
    sensitivity_y: float = 2.4
    # Fusion weight: how much head motion contributes vs pure iris saccades
    head_pose_weight: float = 0.25
    # Velocity-adaptive smoothing
    min_alpha: float = 0.18
    max_alpha: float = 0.85
    velocity_factor: float = 16.0
    deadband_threshold: float = 0.0012
    # Direction classification thresholds
    thresh_left: float = 0.38
    thresh_right: float = 0.62
    thresh_up: float = 0.38
    thresh_down: float = 0.62
    hysteresis: float = 0.04
    # Expected iris dynamic ranges inside eye corners
    min_x_range: float = 0.34
    max_x_range: float = 0.66
    min_y_range: float = 0.35
    max_y_range: float = 0.65
    # Resting center baseline calibration offset
    center_offset_x: float = 0.0
    center_offset_y: float = 0.0


@dataclass
class GazeResult:
    """Gaze estimation result for a single frame."""

    gaze_x: float = 0.5
    gaze_y: float = 0.5
    smoothed_gaze_x: float = 0.5
    smoothed_gaze_y: float = 0.5
    horizontal_direction: str = "CENTER"
    vertical_direction: str = "CENTER"
    overall_direction: str = "LOOKING_CENTER"
    confidence: float = 0.0
    tracking_valid: bool = False


class GazeEstimator:
    """Estimates normalized gaze coordinates combining canthal iris geometry and head motion."""

    SENSITIVITY_PRESETS = {
        "LOW": (1.2, 1.5),
        "NORMAL": (1.8, 2.4),
        "HIGH": (2.4, 3.2),
        "ULTRA": (3.2, 4.2),
    }

    def __init__(self, config: Optional[GazeConfig] = None) -> None:
        self.config = config or GazeConfig()
        self._prev_smoothed_x: Optional[float] = None
        self._prev_smoothed_y: Optional[float] = None
        self._last_raw_x: float = 0.5
        self._last_raw_y: float = 0.5
        self._current_direction: GazeDirection = GazeDirection.CENTER
        self.sensitivity_mode: str = "NORMAL"

    def set_sensitivity_preset(self, preset: str) -> None:
        """Apply a named sensitivity preset (LOW, NORMAL, HIGH, ULTRA)."""
        preset_upper = preset.upper()
        if preset_upper in self.SENSITIVITY_PRESETS:
            self.sensitivity_mode = preset_upper
            sx, sy = self.SENSITIVITY_PRESETS[preset_upper]
            self.config.sensitivity_x = sx
            self.config.sensitivity_y = sy

    def recenter_baseline(self) -> None:
        """Zero out the current raw gaze position as the center baseline."""
        self.config.center_offset_x = self._last_raw_x - 0.5
        self.config.center_offset_y = self._last_raw_y - 0.5

    def estimate(
        self,
        normalized_landmarks: List[Tuple[float, float]],
        eyes_open: bool = True,
    ) -> GazeResult:
        """
        Compute gaze coordinates and direction from normalized face landmarks.

        Args:
            normalized_landmarks: List of (norm_x, norm_y) coordinates.
            eyes_open: Flag indicating if eyes are currently open.

        Returns:
            GazeResult with normalized and smoothed gaze coordinates.
        """
        if not eyes_open or len(normalized_landmarks) < 478:
            return self._create_invalid_result()

        # 1. Left Eye Ratios (Canthal baseline & eyelid geometry)
        left_valid, left_rx, left_ry = self._calc_eye_ratio(
            normalized_landmarks,
            corner_1_idx=L_CORNER_1,
            corner_2_idx=L_CORNER_2,
            top_lid_idx=L_TOP_LID,
            bot_lid_idx=L_BOT_LID,
            iris_center_idx=L_IRIS_CENTER,
        )

        # 2. Right Eye Ratios
        right_valid, right_rx, right_ry = self._calc_eye_ratio(
            normalized_landmarks,
            corner_1_idx=R_CORNER_1,
            corner_2_idx=R_CORNER_2,
            top_lid_idx=R_TOP_LID,
            bot_lid_idx=R_BOT_LID,
            iris_center_idx=R_IRIS_CENTER,
        )

        if not left_valid and not right_valid:
            return self._create_invalid_result()

        # Combine eye measurements
        if left_valid and right_valid:
            iris_rx = (left_rx + right_rx) / 2.0
            iris_ry = (left_ry + right_ry) / 2.0
            confidence = 1.0
        elif left_valid:
            iris_rx, iris_ry = left_rx, left_ry
            confidence = 0.5
        else:
            iris_rx, iris_ry = right_rx, right_ry
            confidence = 0.5

        # 3. Head Motion & Orientation (Pitch & Yaw)
        head_valid, head_yaw, head_pitch = self._calc_head_pose(normalized_landmarks)

        # 4. Multimodal Gaze Fusion (Iris Saccade + Head Motion)
        if head_valid and self.config.head_pose_weight > 0.0:
            hw = self.config.head_pose_weight
            combined_rx = (1.0 - hw) * iris_rx + hw * head_yaw
            combined_ry = (1.0 - hw) * iris_ry + hw * head_pitch
        else:
            combined_rx = iris_rx
            combined_ry = iris_ry

        # Normalize to base range
        base_x = self._normalize_range(combined_rx, self.config.min_x_range, self.config.max_x_range)
        base_y = self._normalize_range(combined_ry, self.config.min_y_range, self.config.max_y_range)

        self._last_raw_x = base_x
        self._last_raw_y = base_y

        # Apply center baseline calibration offset
        centered_x = base_x - self.config.center_offset_x
        centered_y = base_y - self.config.center_offset_y

        # Apply Sensitivity Gain Multiplier centered around 0.5
        gaze_x = 0.5 + (centered_x - 0.5) * self.config.sensitivity_x
        gaze_y = 0.5 + (centered_y - 0.5) * self.config.sensitivity_y

        gaze_x = float(np.clip(gaze_x, 0.0, 1.0))
        gaze_y = float(np.clip(gaze_y, 0.0, 1.0))

        # Velocity-adaptive low-pass smoothing with jitter deadband
        if self._prev_smoothed_x is None or self._prev_smoothed_y is None:
            smoothed_x = gaze_x
            smoothed_y = gaze_y
        else:
            dx = gaze_x - self._prev_smoothed_x
            dy = gaze_y - self._prev_smoothed_y
            dist = math.hypot(dx, dy)

            if dist < self.config.deadband_threshold:
                # Sub-pixel micro-jitter suppressed during steady stare
                smoothed_x = self._prev_smoothed_x
                smoothed_y = self._prev_smoothed_y
            else:
                adaptive_alpha = float(
                    np.clip(
                        self.config.min_alpha + dist * self.config.velocity_factor,
                        self.config.min_alpha,
                        self.config.max_alpha,
                    )
                )
                smoothed_x = adaptive_alpha * gaze_x + (1.0 - adaptive_alpha) * self._prev_smoothed_x
                smoothed_y = adaptive_alpha * gaze_y + (1.0 - adaptive_alpha) * self._prev_smoothed_y

        self._prev_smoothed_x = smoothed_x
        self._prev_smoothed_y = smoothed_y

        # Classify directions with hysteresis
        h_dir, v_dir, overall_dir = self._classify_direction(smoothed_x, smoothed_y)

        return GazeResult(
            gaze_x=gaze_x,
            gaze_y=gaze_y,
            smoothed_gaze_x=float(np.clip(smoothed_x, 0.0, 1.0)),
            smoothed_gaze_y=float(np.clip(smoothed_y, 0.0, 1.0)),
            horizontal_direction=h_dir,
            vertical_direction=v_dir,
            overall_direction=overall_dir,
            confidence=confidence,
            tracking_valid=True,
        )

    def _calc_eye_ratio(
        self,
        lms: List[Tuple[float, float]],
        corner_1_idx: int,
        corner_2_idx: int,
        top_lid_idx: int,
        bot_lid_idx: int,
        iris_center_idx: int,
    ) -> Tuple[bool, float, float]:
        """
        Compute relative iris position inside eye boundaries using canthal geometry.
        Mathematically robust against eyelid flutter and blinking.
        """
        try:
            c1 = lms[corner_1_idx]
            c2 = lms[corner_2_idx]
            top = lms[top_lid_idx]
            bot = lms[bot_lid_idx]
            iris = lms[iris_center_idx]

            x_min = min(c1[0], c2[0])
            x_max = max(c1[0], c2[0])
            eye_width = x_max - x_min

            if eye_width < 1e-4:
                return False, 0.5, 0.5

            # Horizontal ratio: iris X relative to eye corners
            rx = (iris[0] - x_min) / eye_width

            # Vertical ratio: computed relative to canthus baseline (midpoint of c1 and c2)
            # Invariant to eyelid squints and blinks
            mid_y = (c1[1] + c2[1]) / 2.0
            lid_height = abs(bot[1] - top[1])

            # Blend canthus-normalized vertical offset with eyelid ratio for optimal SNR
            canthus_ry = 0.5 + (iris[1] - mid_y) / max(1e-4, eye_width * 0.45)

            if lid_height > 1e-4:
                eyelid_ry = (iris[1] - min(top[1], bot[1])) / lid_height
                # 70% canthal baseline (stable) + 30% eyelid (fine-scale)
                ry = 0.70 * canthus_ry + 0.30 * eyelid_ry
            else:
                ry = canthus_ry

            return True, rx, ry
        except (IndexError, TypeError):
            return False, 0.5, 0.5

    def _calc_head_pose(self, lms: List[Tuple[float, float]]) -> Tuple[bool, float, float]:
        """
        Estimate subtle head yaw and pitch from facial geometry.
        Returns (valid, norm_yaw, norm_pitch).
        """
        try:
            nose = lms[NOSE_TIP]
            glabella = lms[MID_EYES_GLABELLA]
            chin = lms[CHIN]
            left_cheek = lms[FACE_LEFT_CHEEK]
            right_cheek = lms[FACE_RIGHT_CHEEK]

            # Face width & height
            face_w = abs(right_cheek[0] - left_cheek[0])
            face_h = abs(chin[1] - glabella[1])

            if face_w < 1e-3 or face_h < 1e-3:
                return False, 0.5, 0.5

            # Head Yaw: Nose horizontal offset from cheek midpoint
            mid_cheek_x = (left_cheek[0] + right_cheek[0]) / 2.0
            raw_yaw = (nose[0] - mid_cheek_x) / face_w
            norm_yaw = 0.5 + raw_yaw * 2.2

            # Head Pitch: Nose vertical position relative to glabella & chin
            face_mid_y = (glabella[1] + chin[1]) / 2.0
            raw_pitch = (nose[1] - face_mid_y) / face_h
            # In resting face, nose is slightly above face_mid_y
            norm_pitch = 0.5 + (raw_pitch + 0.05) * 2.4

            return True, float(np.clip(norm_yaw, 0.0, 1.0)), float(np.clip(norm_pitch, 0.0, 1.0))
        except (IndexError, TypeError):
            return False, 0.5, 0.5

    @staticmethod
    def _normalize_range(val: float, min_val: float, max_val: float) -> float:
        """Scale value from [min_val, max_val] to [0.0, 1.0]."""
        if max_val <= min_val:
            return 0.5
        norm = (val - min_val) / (max_val - min_val)
        return float(np.clip(norm, 0.0, 1.0))

    def _classify_direction(self, sx: float, sy: float) -> Tuple[str, str, str]:
        """Classify gaze orientation with hysteresis."""
        h = self.config.hysteresis

        # Horizontal classification
        if sx < self.config.thresh_left - h:
            h_dir = "LEFT"
        elif sx > self.config.thresh_right + h:
            h_dir = "RIGHT"
        elif (self.config.thresh_left + h) <= sx <= (self.config.thresh_right - h):
            h_dir = "CENTER"
        else:
            h_dir = "CENTER"

        # Vertical classification
        if sy < self.config.thresh_up - h:
            v_dir = "UP"
        elif sy > self.config.thresh_down + h:
            v_dir = "DOWN"
        elif (self.config.thresh_up + h) <= sy <= (self.config.thresh_down - h):
            v_dir = "CENTER"
        else:
            v_dir = "CENTER"

        # Overall primary direction
        dx = abs(sx - 0.5)
        dy = abs(sy - 0.5)

        if h_dir == "CENTER" and v_dir == "CENTER":
            overall = "LOOKING_CENTER"
        elif dx >= dy:
            overall = f"LOOKING_{h_dir}"
        else:
            overall = f"LOOKING_{v_dir}"

        return h_dir, v_dir, overall

    def _create_invalid_result(self) -> GazeResult:
        """Generate a fallback result when gaze tracking is unavailable."""
        return GazeResult(
            gaze_x=0.5,
            gaze_y=0.5,
            smoothed_gaze_x=self._prev_smoothed_x if self._prev_smoothed_x is not None else 0.5,
            smoothed_gaze_y=self._prev_smoothed_y if self._prev_smoothed_y is not None else 0.5,
            horizontal_direction="UNKNOWN",
            vertical_direction="UNKNOWN",
            overall_direction="UNKNOWN",
            confidence=0.0,
            tracking_valid=False,
        )

    def reset(self) -> None:
        """Clear filter history and state."""
        self._prev_smoothed_x = None
        self._prev_smoothed_y = None
        self._current_direction = GazeDirection.CENTER
