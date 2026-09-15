"""Eye blink detection engine using Eye Aspect Ratio (EAR) and state machine."""

import enum
import math
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

# MediaPipe Eye Landmark Indices for EAR Calculation
# Left Eye (Anatomical Left / Image Right)
LEFT_HORIZ = (362, 263)
LEFT_VERT_1 = (385, 380)
LEFT_VERT_2 = (387, 373)

# Right Eye (Anatomical Right / Image Left)
RIGHT_HORIZ = (33, 133)
RIGHT_VERT_1 = (160, 144)
RIGHT_VERT_2 = (158, 153)


class BlinkState(enum.Enum):
    """Blink lifecycle states."""

    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    OPENING = "OPENING"
    COMPLETED = "COMPLETED"


@dataclass
class BlinkConfig:
    """Configurable thresholds for eye openness and blink timing."""

    closed_threshold: float = 0.19  # EAR below this is considered closed
    open_threshold: float = 0.24  # EAR above this is considered fully open
    min_closed_duration_sec: float = 0.04  # Minimum closed duration (~40ms)
    max_blink_duration_sec: float = 0.45  # Maximum duration for valid blink (~450ms)
    cooldown_sec: float = 0.20  # Minimum delay between distinct blinks


@dataclass
class BlinkResult:
    """Detection result for a single processed frame."""

    left_ear: float = 0.0
    right_ear: float = 0.0
    avg_ear: float = 0.0
    left_open: bool = True
    right_open: bool = True
    state: BlinkState = BlinkState.OPEN
    blink_detected: bool = False
    blink_count: int = 0


class BlinkDetector:
    """Real-time eye openness measurement and blink state machine."""

    def __init__(self, config: Optional[BlinkConfig] = None) -> None:
        self.config = config or BlinkConfig()
        self.state: BlinkState = BlinkState.OPEN
        self.blink_count: int = 0
        self._closed_start_time: Optional[float] = None
        self._last_blink_time: float = 0.0
        self._exceeded_max_duration: bool = False

    @staticmethod
    def _dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate 2D Euclidean distance between two normalized points."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def calculate_ear(
        self,
        landmarks: List[Tuple[float, float]],
        horiz_idx: Tuple[int, int],
        vert1_idx: Tuple[int, int],
        vert2_idx: Tuple[int, int],
    ) -> float:
        """Compute Eye Aspect Ratio (EAR) for given landmark indices."""
        total = len(landmarks)
        needed = [horiz_idx[0], horiz_idx[1], vert1_idx[0], vert1_idx[1], vert2_idx[0], vert2_idx[1]]
        if any(idx >= total for idx in needed):
            return 0.0

        p_h1, p_h2 = landmarks[horiz_idx[0]], landmarks[horiz_idx[1]]
        p_v1_top, p_v1_bot = landmarks[vert1_idx[0]], landmarks[vert1_idx[1]]
        p_v2_top, p_v2_bot = landmarks[vert2_idx[0]], landmarks[vert2_idx[1]]

        horiz_dist = self._dist(p_h1, p_h2)
        if horiz_dist <= 1e-6:
            return 0.0

        vert1_dist = self._dist(p_v1_top, p_v1_bot)
        vert2_dist = self._dist(p_v2_top, p_v2_bot)

        return (vert1_dist + vert2_dist) / (2.0 * horiz_dist)

    def process(
        self,
        normalized_landmarks: List[Tuple[float, float]],
        current_time: Optional[float] = None,
    ) -> BlinkResult:
        """
        Process normalized face landmarks and update the blink state machine.

        Args:
            normalized_landmarks: List of (norm_x, norm_y) for face landmarks.
            current_time: Timestamp in seconds (uses time.perf_counter() if None).

        Returns:
            BlinkResult with current EAR, eye states, and blink event flag.
        """
        t = current_time if current_time is not None else time.perf_counter()

        if len(normalized_landmarks) < 468:
            return BlinkResult(
                state=BlinkState.OPEN,
                blink_detected=False,
                blink_count=self.blink_count,
            )

        left_ear = self.calculate_ear(normalized_landmarks, LEFT_HORIZ, LEFT_VERT_1, LEFT_VERT_2)
        right_ear = self.calculate_ear(normalized_landmarks, RIGHT_HORIZ, RIGHT_VERT_1, RIGHT_VERT_2)
        avg_ear = (left_ear + right_ear) / 2.0

        return self.update_from_ear(left_ear, right_ear, avg_ear, current_time=t)

    def update_from_ear(
        self,
        left_ear: float,
        right_ear: float,
        avg_ear: float,
        current_time: Optional[float] = None,
    ) -> BlinkResult:
        """
        Directly update state machine from computed EAR values (useful for testing & processing).
        """
        t = current_time if current_time is not None else time.perf_counter()
        blink_detected = False

        left_open = left_ear > self.config.closed_threshold
        right_open = right_ear > self.config.closed_threshold
        both_closed = avg_ear <= self.config.closed_threshold
        both_open = avg_ear >= self.config.open_threshold

        # Reset completed state on next tick
        if self.state == BlinkState.COMPLETED:
            self.state = BlinkState.OPEN

        if both_closed:
            if self.state in (BlinkState.OPEN, BlinkState.OPENING):
                self.state = BlinkState.CLOSING
                self._closed_start_time = t
                self._exceeded_max_duration = False
            elif self.state == BlinkState.CLOSING:
                self.state = BlinkState.CLOSED

            # Check for prolonged eye closure
            if self._closed_start_time is not None:
                duration = t - self._closed_start_time
                if duration > self.config.max_blink_duration_sec:
                    self._exceeded_max_duration = True
        else:
            if both_open:
                if self.state in (BlinkState.CLOSING, BlinkState.CLOSED):
                    self.state = BlinkState.OPENING
                    if (
                        self._closed_start_time is not None
                        and not self._exceeded_max_duration
                    ):
                        duration = t - self._closed_start_time
                        time_since_last_blink = t - self._last_blink_time

                        if (
                            duration >= self.config.min_closed_duration_sec
                            and duration <= self.config.max_blink_duration_sec
                            and time_since_last_blink >= self.config.cooldown_sec
                        ):
                            blink_detected = True
                            self.blink_count += 1
                            self._last_blink_time = t
                            self.state = BlinkState.COMPLETED

                    self._closed_start_time = None
                    self._exceeded_max_duration = False
                elif self.state == BlinkState.OPENING:
                    self.state = BlinkState.OPEN

        return BlinkResult(
            left_ear=left_ear,
            right_ear=right_ear,
            avg_ear=avg_ear,
            left_open=left_open,
            right_open=right_open,
            state=self.state,
            blink_detected=blink_detected,
            blink_count=self.blink_count,
        )

    def reset(self) -> None:
        """Reset state machine and counters."""
        self.state = BlinkState.OPEN
        self.blink_count = 0
        self._closed_start_time = None
        self._last_blink_time = 0.0
        self._exceeded_max_duration = False
