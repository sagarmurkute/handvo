"""Production-ready Hand Dwell Selection Engine for HANDVO.

Evaluates hand cursor pointing, dwell timers, hit-testing, progress calculation, and cooldown debouncing.
"""

import math
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, Optional, Tuple, Union


class DwellState(Enum):
    """Lifecycle states of the Dwell Selection Engine."""
    IDLE = auto()
    FOCUSING = auto()
    DWELLING = auto()
    TRIGGERED = auto()
    COOLDOWN = auto()


@dataclass
class DwellSelectorConfig:
    """Configuration parameters for dwell timing, cooldown, and stability."""
    dwell_time_sec: float = 0.80
    cooldown_sec: float = 0.60
    stability_radius_px: float = 40.0
    min_confidence: float = 0.35
    audio_feedback: bool = True


@dataclass
class DwellTarget:
    """An interactive UI target supporting static rectangles or dynamic callable bounds."""
    target_id: str
    rect: Union[Tuple[float, float, float, float], Callable[[], Tuple[float, float, float, float]]] = (0.0, 0.0, 0.0, 0.0)
    bounds: Optional[Union[Tuple[float, float, float, float], Callable[[], Tuple[float, float, float, float]]]] = None
    on_trigger: Optional[Callable[[], None]] = None
    callback: Optional[Callable[[], None]] = None
    label: str = ""
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.bounds is not None:
            self.rect = self.bounds
        if self.callback is not None:
            self.on_trigger = self.callback

    def get_current_rect(self) -> Tuple[float, float, float, float]:
        """Resolve current window coordinates dynamically if bound to a callable."""
        if callable(self.rect):
            try:
                return self.rect()
            except Exception:
                return (-1000.0, -1000.0, 0.0, 0.0)
        return self.rect

    def contains(self, px: float, py: float) -> bool:
        """Perform exact point-in-rectangle collision testing."""
        if math.isnan(px) or math.isnan(py) or math.isinf(px) or math.isinf(py):
            return False
        x, y, w, h = self.get_current_rect()
        return self.enabled and (x <= px <= x + w) and (y <= py <= y + h)


@dataclass
class DwellResult:
    """Output state packet emitted every frame by the dwell selector."""
    state: DwellState
    target_id: Optional[str] = None
    progress: float = 0.0
    elapsed_time: float = 0.0
    triggered: bool = False
    is_stable: bool = True


class DwellSelector:
    """
    State machine evaluating cursor dwell progression, enter/exit events,
    cancellation, and single-trigger execution with cooldown protection.
    """

    def __init__(
        self,
        config: Optional[DwellSelectorConfig] = None,
        dwell_time_sec: Optional[float] = None,
        cooldown_sec: Optional[float] = None,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = DwellSelectorConfig(
                dwell_time_sec=dwell_time_sec if dwell_time_sec is not None else 0.80,
                cooldown_sec=cooldown_sec if cooldown_sec is not None else 0.60,
            )

        self._targets: Dict[str, DwellTarget] = {}
        self._state = DwellState.IDLE
        self._current_target_id: Optional[str] = None
        self._dwell_start_time: float = 0.0
        self._cooldown_start_time: float = 0.0

    @property
    def state(self) -> DwellState:
        return self._state

    def register_target(self, target: DwellTarget) -> None:
        """Register a new interactive dwell target."""
        self._targets[target.target_id] = target

    def unregister_target(self, target_id: str) -> None:
        """Unregister an existing dwell target."""
        self._targets.pop(target_id, None)

    def clear_targets(self) -> None:
        """Clear all registered targets."""
        self._targets.clear()

    def play_feedback_cue(self) -> None:
        """Play non-blocking subtle audio chime/click on successful dwell trigger."""
        if not self.config.audio_feedback:
            return
        if sys.platform.startswith("win"):
            try:
                import winsound
                winsound.Beep(880, 70)  # 880 Hz subtle 70ms chime
            except Exception:
                pass

    def trigger_target(self, target_id: str, current_time: Optional[float] = None) -> bool:
        """Manually trigger a target (e.g. from pinch gesture or hotkey fallback)."""
        now = current_time or time.perf_counter()
        target = self._targets.get(target_id)
        if target and target.enabled:
            self._state = DwellState.COOLDOWN
            self._cooldown_start_time = now
            self._current_target_id = target_id
            self.play_feedback_cue()
            if target.on_trigger:
                try:
                    target.on_trigger()
                except Exception:
                    pass
            return True
        return False

    def update(
        self,
        cursor_px: Tuple[float, float],
        tracking_valid: bool = True,
        confidence: float = 1.0,
        current_time: Optional[float] = None,
    ) -> DwellResult:
        """
        Process current frame cursor coordinate and update dwell progression.
        """
        now = current_time or time.perf_counter()

        # 1. Handle Cooldown debouncing
        if self._state == DwellState.COOLDOWN:
            if now - self._cooldown_start_time >= self.config.cooldown_sec:
                self._state = DwellState.IDLE
                self._current_target_id = None
            else:
                return DwellResult(
                    state=DwellState.COOLDOWN,
                    target_id=self._current_target_id,
                    progress=0.0,
                    elapsed_time=now - self._cooldown_start_time,
                    is_stable=tracking_valid,
                )

        # 2. Tracking loss / low confidence immediately cancels dwell
        if not tracking_valid or confidence < self.config.min_confidence:
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0, is_stable=False)

        px, py = cursor_px
        if math.isnan(px) or math.isnan(py) or math.isinf(px) or math.isinf(py):
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0, is_stable=False)

        # 3. Hit-testing against registered targets
        hit_target_id: Optional[str] = None
        for t_id, target in self._targets.items():
            if target.contains(px, py):
                hit_target_id = t_id
                break

        # 4. Cursor outside all targets cancels focus
        if hit_target_id is None:
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0, is_stable=True)

        # 5. Cursor entered a new target: initiate FOCUSING state
        if self._current_target_id != hit_target_id:
            self._current_target_id = hit_target_id
            self._dwell_start_time = now
            self._state = DwellState.FOCUSING
            return DwellResult(
                state=DwellState.FOCUSING,
                target_id=hit_target_id,
                progress=0.0,
                elapsed_time=0.0,
                is_stable=True,
            )

        # 6. Cursor continuing dwell on active target: calculate progress
        elapsed = now - self._dwell_start_time
        progress = min(1.0, elapsed / self.config.dwell_time_sec) if self.config.dwell_time_sec > 0 else 1.0

        # 7. Completed dwell (100%): fire trigger action and enter cooldown
        if progress >= 1.0:
            self._state = DwellState.COOLDOWN
            self._cooldown_start_time = now
            self.play_feedback_cue()
            target = self._targets.get(hit_target_id)
            if target and target.on_trigger:
                try:
                    target.on_trigger()
                except Exception:
                    pass
            return DwellResult(
                state=DwellState.COOLDOWN,
                target_id=hit_target_id,
                progress=1.0,
                elapsed_time=elapsed,
                triggered=True,
                is_stable=True,
            )

        # 8. Ongoing active dwell progression
        self._state = DwellState.DWELLING
        return DwellResult(
            state=DwellState.DWELLING,
            target_id=hit_target_id,
            progress=progress,
            elapsed_time=elapsed,
            is_stable=True,
        )

    def reset(self) -> None:
        """Reset state machine to IDLE."""
        self._state = DwellState.IDLE
        self._current_target_id = None
