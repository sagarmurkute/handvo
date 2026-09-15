"""Gaze calibration session workflow with fixation stability and dwell progress."""

import enum
import math
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

from app.gaze.calibration_model import CalibrationModel


class CalibrationState(enum.Enum):
    """Lifecycle states of the calibration session."""

    IDLE = "IDLE"
    SETTLING = "SETTLING"
    DWELLING = "DWELLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class CalibrationPoint:
    """Target position in normalized window coordinates (0.0 to 1.0)."""

    norm_x: float
    norm_y: float
    label: str


@dataclass
class CalibrationSample:
    """Individual paired gaze-to-target sample."""

    gaze_x: float
    gaze_y: float
    target_x: float
    target_y: float
    timestamp: float = field(default_factory=time.time)


class CalibrationSession:
    """Coordinates 9-point calibration requiring genuine eye fixation stability or manual trigger."""

    DEFAULT_POINTS: List[CalibrationPoint] = [
        CalibrationPoint(0.15, 0.15, "Top-Left"),
        CalibrationPoint(0.50, 0.15, "Top-Center"),
        CalibrationPoint(0.85, 0.15, "Top-Right"),
        CalibrationPoint(0.15, 0.50, "Middle-Left"),
        CalibrationPoint(0.50, 0.50, "Center"),
        CalibrationPoint(0.85, 0.50, "Middle-Right"),
        CalibrationPoint(0.15, 0.85, "Bottom-Left"),
        CalibrationPoint(0.50, 0.85, "Bottom-Center"),
        CalibrationPoint(0.85, 0.85, "Bottom-Right"),
    ]

    def __init__(
        self,
        points: Optional[List[CalibrationPoint]] = None,
        dwell_required_sec: float = 1.0,
        settle_duration_sec: float = 0.50,
    ) -> None:
        self.points = points or list(self.DEFAULT_POINTS)
        self.dwell_required = dwell_required_sec
        self.settle_duration = settle_duration_sec

        self.state = CalibrationState.IDLE
        self.current_point_idx: int = 0
        self.dwell_progress: float = 0.0  # 0.0 to 1.0
        self.samples: List[CalibrationSample] = []
        self._current_gaze_buffer: List[Tuple[float, float]] = []
        self._last_tick_time: float = 0.0
        self._point_start_time: float = 0.0

        self.model = CalibrationModel(degree=2)

    @property
    def current_point(self) -> Optional[CalibrationPoint]:
        """Get the active calibration target point."""
        if 0 <= self.current_point_idx < len(self.points):
            return self.points[self.current_point_idx]
        return None

    def start(self) -> None:
        """Initiate the calibration session."""
        self.state = CalibrationState.SETTLING
        self.current_point_idx = 0
        self.dwell_progress = 0.0
        self.samples.clear()
        self._current_gaze_buffer.clear()
        now = time.perf_counter()
        self._point_start_time = now
        self._last_tick_time = now

    def add_sample(
        self,
        gaze_x: float,
        gaze_y: float,
        tracking_valid: bool = True,
        current_time: Optional[float] = None,
    ) -> CalibrationState:
        """
        Ingest a gaze sample, verify eye fixation stability, and advance dwell progress.
        """
        if self.state not in (CalibrationState.SETTLING, CalibrationState.DWELLING):
            return self.state

        t = current_time if current_time is not None else time.perf_counter()
        dt = max(0.001, t - self._last_tick_time) if self._last_tick_time > 0 else 0.033
        self._last_tick_time = t

        # Settling delay
        if self.state == CalibrationState.SETTLING:
            if (t - self._point_start_time) >= self.settle_duration:
                self.state = CalibrationState.DWELLING
                self.dwell_progress = 0.0
                self._current_gaze_buffer.clear()
            return self.state

        # Active Dwelling / Sampling
        if self.state == CalibrationState.DWELLING:
            if tracking_valid and math.isfinite(gaze_x) and math.isfinite(gaze_y):
                self._current_gaze_buffer.append((gaze_x, gaze_y))
                if len(self._current_gaze_buffer) > 30:
                    self._current_gaze_buffer.pop(0)

                # Check fixation stability: standard deviation of recent gaze points
                if len(self._current_gaze_buffer) >= 5:
                    recent = np.array(self._current_gaze_buffer[-10:])
                    std_dev = float(np.std(recent, axis=0).mean())
                    is_stable = std_dev < 0.12
                else:
                    is_stable = True

                if is_stable:
                    self.dwell_progress = min(1.0, self.dwell_progress + (dt / self.dwell_required))
                else:
                    # Gaze is moving too fast / erratic
                    self.dwell_progress = max(0.0, self.dwell_progress - (dt * 0.5))
            else:
                # Tracking lost -> decay dwell
                self.dwell_progress = max(0.0, self.dwell_progress - (dt * 1.5))

            # Complete point when dwell reaches 100%
            if self.dwell_progress >= 1.0:
                self._capture_current_point()

        return self.state

    def capture_point_manually(self) -> None:
        """Manual trigger (e.g. Spacebar or click) to capture current point immediately."""
        if self.state in (CalibrationState.SETTLING, CalibrationState.DWELLING):
            self._capture_current_point()

    def _capture_current_point(self) -> None:
        """Aggregate buffered samples for current target and advance."""
        pt = self.current_point
        if pt is not None:
            if self._current_gaze_buffer:
                # Use mean centroid of stable fixation
                mean_gx = float(np.median([p[0] for p in self._current_gaze_buffer]))
                mean_gy = float(np.median([p[1] for p in self._current_gaze_buffer]))
            else:
                mean_gx, mean_gy = 0.5, 0.5

            # Store multiple samples around centroid for regression robustness
            for dx, dy in [(0, 0), (-0.01, 0), (0.01, 0), (0, -0.01), (0, 0.01)]:
                self.samples.append(
                    CalibrationSample(
                        gaze_x=float(np.clip(mean_gx + dx, 0.0, 1.0)),
                        gaze_y=float(np.clip(mean_gy + dy, 0.0, 1.0)),
                        target_x=pt.norm_x,
                        target_y=pt.norm_y,
                    )
                )

        self.current_point_idx += 1
        self.dwell_progress = 0.0
        self._current_gaze_buffer.clear()
        self._point_start_time = time.perf_counter()

        if self.current_point_idx >= len(self.points):
            success = self._finalize_calibration()
            self.state = CalibrationState.COMPLETED if success else CalibrationState.FAILED
        else:
            self.state = CalibrationState.SETTLING

    def _finalize_calibration(self) -> bool:
        """Fit model with collected calibration samples."""
        if len(self.samples) < 9:
            return False

        gaze_pts = [(s.gaze_x, s.gaze_y) for s in self.samples]
        target_pts = [(s.target_x, s.target_y) for s in self.samples]

        return self.model.fit(gaze_pts, target_pts)

    def cancel(self) -> None:
        """Cancel and reset session."""
        self.state = CalibrationState.IDLE
        self.current_point_idx = 0
        self.dwell_progress = 0.0
        self.samples.clear()
        self._current_gaze_buffer.clear()
