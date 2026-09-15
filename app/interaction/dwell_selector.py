"""Gaze Dwell Selection Engine for EYEVO.

Determines when the gaze cursor focuses, dwells, and activates interactive UI elements
with spatial stability checks, hysteresis, and post-selection cooldown.
"""

import enum
import math
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Union


class DwellState(enum.Enum):
    """Lifecycle states of the dwell interaction."""

    IDLE = "IDLE"
    FOCUSING = "FOCUSING"
    DWELLING = "DWELLING"
    SELECTED = "SELECTED"
    COOLDOWN = "COOLDOWN"


@dataclass
class DwellTarget:
    """An interactive UI element registered for gaze dwell selection."""

    target_id: str
    bounds: Union[Tuple[float, float, float, float], Callable[[], Tuple[float, float, float, float]]]
    # bounds format: (x, y, width, height) in pixel window coordinates
    enabled: bool = True
    callback: Optional[Callable[[], None]] = None
    label: str = ""
    hysteresis_px: float = 16.0

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Return the current (x, y, width, height) bounding box."""
        if callable(self.bounds):
            return self.bounds()
        return self.bounds

    def contains(self, px: float, py: float, use_hysteresis: bool = False) -> bool:
        """Check if a coordinate point falls inside target bounds."""
        if not self.enabled:
            return False

        x, y, w, h = self.get_bounds()
        margin = self.hysteresis_px if use_hysteresis else 0.0

        return (x - margin) <= px <= (x + w + margin) and (y - margin) <= py <= (y + h + margin)


@dataclass
class DwellSelectorConfig:
    """Configurable timing and stability thresholds for dwell selection."""

    dwell_time_sec: float = 0.80  # Default 800ms dwell activation
    cooldown_sec: float = 0.60  # Debounce cooldown after successful selection
    stability_radius_px: float = 50.0  # Max gaze dispersion allowed while dwelling
    min_confidence: float = 0.35  # Minimum tracking confidence required


@dataclass
class DwellResult:
    """Result of a single dwell interaction evaluation cycle."""

    target_id: Optional[str] = None
    target: Optional[DwellTarget] = None
    state: DwellState = DwellState.IDLE
    progress: float = 0.0  # 0.0 to 1.0
    remaining_time_sec: float = 0.0
    is_stable: bool = True
    triggered: bool = False


class DwellSelector:
    """Manages dwell state machine, target hit-testing, stability verification, and activation."""

    def __init__(self, config: Optional[DwellSelectorConfig] = None) -> None:
        self.config = config or DwellSelectorConfig()
        self.targets: Dict[str, DwellTarget] = {}

        self.state: DwellState = DwellState.IDLE
        self.active_target_id: Optional[str] = None
        self.dwell_progress: float = 0.0
        self.remaining_time_sec: float = 0.0

        self._dwell_start_time: float = 0.0
        self._last_tick_time: float = 0.0
        self._cooldown_end_time: float = 0.0
        self._cooldown_target_id: Optional[str] = None

        self._dwell_anchor_pos: Optional[Tuple[float, float]] = None
        self._gaze_history: List[Tuple[float, float]] = []

    def register_target(self, target: DwellTarget) -> None:
        """Register an interactive target with the dwell engine."""
        self.targets[target.target_id] = target

    def unregister_target(self, target_id: str) -> None:
        """Remove a target from registration."""
        if target_id in self.targets:
            del self.targets[target_id]
        if self.active_target_id == target_id:
            self._cancel_dwell()

    def clear_targets(self) -> None:
        """Clear all registered targets."""
        self.targets.clear()
        self._cancel_dwell()

    def update(
        self,
        cursor_px: Tuple[float, float],
        tracking_valid: bool = True,
        confidence: float = 1.0,
        current_time: Optional[float] = None,
    ) -> DwellResult:
        """
        Evaluate gaze cursor position against registered targets and advance dwell state.

        Args:
            cursor_px: (pixel_x, pixel_y) in window coordinates.
            tracking_valid: Flag indicating if eye tracking is active.
            confidence: Gaze estimation confidence score (0.0 to 1.0).
            current_time: Optional timestamp for deterministic testing.

        Returns:
            DwellResult containing active target, state, progress, and triggered status.
        """
        t = current_time if current_time is not None else time.perf_counter()
        dt = max(0.001, t - self._last_tick_time) if self._last_tick_time > 0 else 0.033
        self._last_tick_time = t

        px, py = cursor_px
        triggered = False

        # 1. Check Cooldown State
        if self.state == DwellState.COOLDOWN:
            if t >= self._cooldown_end_time:
                self.state = DwellState.IDLE
                self._cooldown_target_id = None
                self.dwell_progress = 0.0
                self.remaining_time_sec = 0.0
            else:
                self.remaining_time_sec = max(0.0, self._cooldown_end_time - t)
                # Keep active target reference during cooldown if still on it
                active_t = self.targets.get(self._cooldown_target_id) if self._cooldown_target_id else None
                return DwellResult(
                    target_id=self._cooldown_target_id,
                    target=active_t,
                    state=DwellState.COOLDOWN,
                    progress=1.0,
                    remaining_time_sec=self.remaining_time_sec,
                    is_stable=True,
                    triggered=False,
                )

        # 2. Tracking Loss / Low Confidence Cancellation
        if not tracking_valid or confidence < self.config.min_confidence or not math.isfinite(px) or not math.isfinite(py):
            self._cancel_dwell()
            return DwellResult(
                target_id=None,
                target=None,
                state=DwellState.IDLE,
                progress=0.0,
                remaining_time_sec=0.0,
                is_stable=False,
                triggered=False,
            )

        # 3. Hit-Testing Against Registered Targets
        hovered_target = self._find_hovered_target(px, py)

        if hovered_target is None:
            # Gaze is in open space -> reset any active dwell
            self._cancel_dwell()
            return DwellResult(
                target_id=None,
                target=None,
                state=DwellState.IDLE,
                progress=0.0,
                remaining_time_sec=0.0,
                is_stable=True,
                triggered=False,
            )

        # 4. Target Transition / New Target Focus
        if self.active_target_id != hovered_target.target_id:
            self.active_target_id = hovered_target.target_id
            self.state = DwellState.FOCUSING
            self._dwell_start_time = t
            self._dwell_anchor_pos = (px, py)
            self._gaze_history = [(px, py)]
            self.dwell_progress = 0.0
            self.remaining_time_sec = self.config.dwell_time_sec

        # 5. Stability Verification
        self._gaze_history.append((px, py))
        if len(self._gaze_history) > 20:
            self._gaze_history.pop(0)

        # Measure displacement from initial anchor position
        is_stable = True
        if self._dwell_anchor_pos is not None:
            dist_from_anchor = math.hypot(px - self._dwell_anchor_pos[0], py - self._dwell_anchor_pos[1])
            if dist_from_anchor > self.config.stability_radius_px:
                # Gaze drifted too far within target -> re-anchor
                self._dwell_anchor_pos = (px, py)
                self._dwell_start_time = t
                self.dwell_progress = 0.0
                is_stable = False

        # 6. Dwell Timer Progression
        elapsed = t - self._dwell_start_time
        dwell_duration = max(0.05, self.config.dwell_time_sec)
        self.dwell_progress = float(min(1.0, max(0.0, elapsed / dwell_duration)))
        self.remaining_time_sec = max(0.0, dwell_duration - elapsed)

        if self.dwell_progress >= 1.0:
            # Dwell Complete -> Trigger Action!
            self.state = DwellState.SELECTED
            triggered = True

            if hovered_target.callback is not None:
                try:
                    hovered_target.callback()
                except Exception:
                    pass

            # Enter post-selection cooldown
            self.state = DwellState.COOLDOWN
            self._cooldown_target_id = hovered_target.target_id
            self._cooldown_end_time = t + self.config.cooldown_sec
            self.active_target_id = None
        else:
            self.state = DwellState.DWELLING

        return DwellResult(
            target_id=hovered_target.target_id,
            target=hovered_target,
            state=self.state,
            progress=self.dwell_progress,
            remaining_time_sec=self.remaining_time_sec,
            is_stable=is_stable,
            triggered=triggered,
        )

    def trigger_target(self, target_id: str, current_time: Optional[float] = None) -> bool:
        """
        Manually activate a target immediately (Keyboard/Mouse fallback for development/testing).
        """
        t = current_time if current_time is not None else time.perf_counter()
        target = self.targets.get(target_id)
        if target is None or not target.enabled:
            return False

        if target.callback is not None:
            try:
                target.callback()
            except Exception:
                pass

        self.state = DwellState.COOLDOWN
        self._cooldown_target_id = target_id
        self._cooldown_end_time = t + self.config.cooldown_sec
        self.active_target_id = None
        return True

    def _find_hovered_target(self, px: float, py: float) -> Optional[DwellTarget]:
        """Find the target under cursor coordinates, applying hysteresis to currently active target."""
        # Check active target first with hysteresis expansion
        if self.active_target_id and self.active_target_id in self.targets:
            curr = self.targets[self.active_target_id]
            if curr.enabled and curr.contains(px, py, use_hysteresis=True):
                return curr

        # Check other registered targets
        for target in self.targets.values():
            if target.enabled and target.contains(px, py, use_hysteresis=False):
                return target

        return None

    def _cancel_dwell(self) -> None:
        """Reset active dwell progress and state to idle."""
        self.state = DwellState.IDLE
        self.active_target_id = None
        self.dwell_progress = 0.0
        self.remaining_time_sec = 0.0
        self._dwell_anchor_pos = None
        self._gaze_history.clear()

    def reset(self) -> None:
        """Full reset of the dwell engine."""
        self._cancel_dwell()
        self._cooldown_target_id = None
        self._cooldown_end_time = 0.0
        self._last_tick_time = 0.0
