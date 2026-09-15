"""One-Euro filter implementation for adaptive jitter-free coordinate smoothing."""

import math
import time
from typing import Optional, Tuple


class LowPassFilter:
    """Standard exponential smoothing filter."""

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha
        self.last_value: Optional[float] = None

    def filter(self, value: float, alpha: Optional[float] = None) -> float:
        if alpha is not None:
            self.alpha = alpha
        if self.last_value is None:
            self.last_value = value
            return value
        filtered = self.alpha * value + (1.0 - self.alpha) * self.last_value
        self.last_value = filtered
        return filtered

    def reset(self) -> None:
        self.last_value = None


class OneEuroFilter:
    """Adaptive 1-Euro filter for low-latency, jitter-free cursor tracking."""

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.05,
        d_cutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_filt = LowPassFilter()
        self.dx_filt = LowPassFilter()
        self.last_time: Optional[float] = None

    def _alpha(self, rate: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / rate if rate > 0 else 0.016
        return 1.0 / (1.0 + tau / te)

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        t = timestamp or time.perf_counter()
        if self.last_time is None:
            self.last_time = t
            return self.x_filt.filter(x)

        dt = t - self.last_time
        self.last_time = t
        rate = 1.0 / dt if dt > 0.0001 else 30.0

        prev_x = self.x_filt.last_value if self.x_filt.last_value is not None else x
        dx = (x - prev_x) * rate
        edx = self.dx_filt.filter(dx, self._alpha(rate, self.d_cutoff))

        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filt.filter(x, self._alpha(rate, cutoff))

    def reset(self) -> None:
        self.x_filt.reset()
        self.dx_filt.reset()
        self.last_time = None


class OneEuroFilter2D:
    """Pair of 1-Euro filters for 2D (X, Y) coordinate points."""

    def __init__(self, min_cutoff: float = 1.2, beta: float = 0.04) -> None:
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)

    def filter(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        return (
            self.filter_x.filter(x, timestamp),
            self.filter_y.filter(y, timestamp),
        )

    def reset(self) -> None:
        self.filter_x.reset()
        self.filter_y.reset()
