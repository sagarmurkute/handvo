"""Hand Gesture Dwell Selection Engine for HANDVO.

Evaluates index fingertip hover / cursor dwell on registered UI bounding boxes.
"""

import math
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, Optional, Tuple


class DwellState(Enum):
    IDLE = auto()
    FOCUSING = auto()
    DWELLING = auto()
    TRIGGERED = auto()
    COOLDOWN = auto()


@dataclass
class DwellSelectorConfig:
    dwell_time_sec: float = 0.80
    cooldown_sec: float = 0.60
    stability_radius_px: float = 40.0
    min_confidence: float = 0.40


@dataclass
class DwellTarget:
    target_id: str
    rect: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    bounds: Optional[Tuple[float, float, float, float]] = None
    on_trigger: Optional[Callable[[], None]] = None
    callback: Optional[Callable[[], None]] = None
    label: str = ""
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.bounds is not None:
            self.rect = self.bounds
        if self.callback is not None:
            self.on_trigger = self.callback

    def contains(self, px: float, py: float) -> bool:
        if math.isnan(px) or math.isnan(py) or math.isinf(px) or math.isinf(py):
            return False
        x, y, w, h = self.rect
        return self.enabled and (x <= px <= x + w) and (y <= py <= y + h)


@dataclass
class DwellResult:
    state: DwellState
    target_id: Optional[str] = None
    progress: float = 0.0
    elapsed_time: float = 0.0
    triggered: bool = False
    is_stable: bool = True


class DwellSelector:
    """Manages dwell state machine and hit-testing on interactive targets."""

    def __init__(self, config: Optional[DwellSelectorConfig] = None) -> None:
        self.config = config or DwellSelectorConfig()
        self._targets: Dict[str, DwellTarget] = {}
        self._state = DwellState.IDLE
        self._current_target_id: Optional[str] = None
        self._dwell_start_time: float = 0.0
        self._cooldown_start_time: float = 0.0

    @property
    def state(self) -> DwellState:
        return self._state

    def register_target(self, target: DwellTarget) -> None:
        self._targets[target.target_id] = target

    def unregister_target(self, target_id: str) -> None:
        self._targets.pop(target_id, None)

    def clear_targets(self) -> None:
        self._targets.clear()

    def trigger_target(self, target_id: str, current_time: Optional[float] = None) -> bool:
        now = current_time or time.perf_counter()
        target = self._targets.get(target_id)
        if target and target.enabled:
            self._state = DwellState.COOLDOWN
            self._cooldown_start_time = now
            self._current_target_id = target_id
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
        now = current_time or time.perf_counter()

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

        if not tracking_valid or confidence < self.config.min_confidence:
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0, is_stable=False)

        px, py = cursor_px
        if math.isnan(px) or math.isnan(py) or math.isinf(px) or math.isinf(py):
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0, is_stable=False)

        hit_target_id: Optional[str] = None
        for t_id, target in self._targets.items():
            if target.contains(px, py):
                hit_target_id = t_id
                break

        if hit_target_id is None:
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0, is_stable=True)

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

        elapsed = now - self._dwell_start_time
        progress = min(1.0, elapsed / self.config.dwell_time_sec) if self.config.dwell_time_sec > 0 else 1.0

        if progress >= 1.0:
            self._state = DwellState.COOLDOWN
            self._cooldown_start_time = now
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

        self._state = DwellState.DWELLING
        return DwellResult(
            state=DwellState.DWELLING,
            target_id=hit_target_id,
            progress=progress,
            elapsed_time=elapsed,
            is_stable=True,
        )

    def reset(self) -> None:
        self._state = DwellState.IDLE
        self._current_target_id = None
