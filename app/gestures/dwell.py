"""Spatial dwell state machine for hand tracking selections."""

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Dict, Optional, Tuple


class DwellState(Enum):
    IDLE = auto()
    DWELLING = auto()
    TRIGGERED = auto()
    COOLDOWN = auto()


@dataclass
class DwellTarget:
    """A registered UI interaction target with bounding box."""
    target_id: str
    rect: Tuple[int, int, int, int]  # (x, y, width, height)
    on_trigger: Optional[Callable[[], None]] = None
    enabled: bool = True

    def contains(self, px: int, py: int) -> bool:
        x, y, w, h = self.rect
        return self.enabled and (x <= px <= x + w) and (y <= py <= y + h)


@dataclass
class DwellResult:
    """Output state packet from the dwell engine."""
    state: DwellState
    target_id: Optional[str] = None
    progress: float = 0.0
    triggered: bool = False


class DwellSelector:
    """State machine evaluating dwell progress and trigger events."""

    def __init__(self, dwell_time_sec: float = 0.80, cooldown_sec: float = 0.60) -> None:
        self.dwell_time_sec = dwell_time_sec
        self.cooldown_sec = cooldown_sec
        self._targets: Dict[str, DwellTarget] = {}
        self._state = DwellState.IDLE
        self._current_target_id: Optional[str] = None
        self._dwell_start_time: float = 0.0
        self._cooldown_start_time: float = 0.0

    def register_target(self, target: DwellTarget) -> None:
        self._targets[target.target_id] = target

    def unregister_target(self, target_id: str) -> None:
        self._targets.pop(target_id, None)

    def clear_targets(self) -> None:
        self._targets.clear()

    def update(self, cursor_px: Tuple[int, int], tracking_valid: bool, current_time: Optional[float] = None) -> DwellResult:
        now = current_time or time.perf_counter()

        # Handle Cooldown
        if self._state == DwellState.COOLDOWN:
            if now - self._cooldown_start_time >= self.cooldown_sec:
                self._state = DwellState.IDLE
                self._current_target_id = None
            else:
                return DwellResult(state=DwellState.COOLDOWN, target_id=self._current_target_id, progress=0.0)

        if not tracking_valid:
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0)

        px, py = cursor_px
        hit_target_id: Optional[str] = None
        for t_id, target in self._targets.items():
            if target.contains(px, py):
                hit_target_id = t_id
                break

        if hit_target_id is None:
            self._state = DwellState.IDLE
            self._current_target_id = None
            return DwellResult(state=DwellState.IDLE, progress=0.0)

        if self._current_target_id != hit_target_id:
            self._current_target_id = hit_target_id
            self._dwell_start_time = now
            self._state = DwellState.DWELLING
            return DwellResult(state=DwellState.DWELLING, target_id=hit_target_id, progress=0.0)

        elapsed = now - self._dwell_start_time
        progress = min(1.0, elapsed / self.dwell_time_sec) if self.dwell_time_sec > 0 else 1.0

        if progress >= 1.0:
            self._state = DwellState.COOLDOWN
            self._cooldown_start_time = now
            target = self._targets.get(hit_target_id)
            if target and target.on_trigger:
                try:
                    target.on_trigger()
                except Exception:
                    pass
            return DwellResult(state=DwellState.TRIGGERED, target_id=hit_target_id, progress=1.0, triggered=True)

        return DwellResult(state=DwellState.DWELLING, target_id=hit_target_id, progress=progress)

    def reset(self) -> None:
        self._state = DwellState.IDLE
        self._current_target_id = None
