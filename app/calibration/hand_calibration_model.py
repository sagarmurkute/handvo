"""Hand Calibration data structures, calculations, coordinate remapping, and quality assessment."""

from dataclasses import dataclass, field
import math
from typing import Dict, List, Optional, Tuple


@dataclass
class HandCalibrationData:
    """Stores measured hand calibration metrics and thresholds."""
    dominant_hand: str = "Right"
    neutral_x: float = 0.50
    neutral_y: float = 0.50
    range_min_x: float = 0.20
    range_max_x: float = 0.80
    range_min_y: float = 0.20
    range_max_y: float = 0.80
    open_hand_span: float = 0.25
    pinch_contact_dist: float = 0.03
    pinch_threshold: float = 0.05
    pinch_release_threshold: float = 0.08
    dwell_time: float = 0.80
    smoothing_factor: float = 1.50
    quality_score: str = "GOOD"
    quality_pct: float = 85.0
    is_calibrated: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "dominant_hand": self.dominant_hand,
            "neutral_x": round(self.neutral_x, 4),
            "neutral_y": round(self.neutral_y, 4),
            "range_min_x": round(self.range_min_x, 4),
            "range_max_x": round(self.range_max_x, 4),
            "range_min_y": round(self.range_min_y, 4),
            "range_max_y": round(self.range_max_y, 4),
            "open_hand_span": round(self.open_hand_span, 4),
            "pinch_contact_dist": round(self.pinch_contact_dist, 4),
            "pinch_threshold": round(self.pinch_threshold, 4),
            "pinch_release_threshold": round(self.pinch_release_threshold, 4),
            "dwell_time": self.dwell_time,
            "smoothing_factor": self.smoothing_factor,
            "quality_score": self.quality_score,
            "quality_pct": round(self.quality_pct, 1),
            "is_calibrated": self.is_calibrated,
        }


class HandCalibrationEngine:
    """Performs calibration calculations, coordinate scaling, and validation."""

    @staticmethod
    def compute_neutral(samples: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Compute average neutral resting position from collected points."""
        if not samples:
            return (0.50, 0.50)
        avg_x = sum(pt[0] for pt in samples) / len(samples)
        avg_y = sum(pt[1] for pt in samples) / len(samples)
        return (max(0.0, min(1.0, avg_x)), max(0.0, min(1.0, avg_y)))

    @staticmethod
    def compute_range(
        samples: List[Tuple[float, float]],
        margin_pct: float = 0.04,
    ) -> Tuple[float, float, float, float]:
        """
        Compute bounding box of comfortable reach with adaptive padding.
        Returns: (min_x, max_x, min_y, max_y)
        """
        if not samples or len(samples) < 4:
            return (0.20, 0.80, 0.20, 0.80)

        xs = [pt[0] for pt in samples]
        ys = [pt[1] for pt in samples]

        raw_min_x, raw_max_x = min(xs), max(xs)
        raw_min_y, raw_max_y = min(ys), max(ys)

        span_x = max(0.10, raw_max_x - raw_min_x)
        span_y = max(0.10, raw_max_y - raw_min_y)

        # Apply slight margin
        min_x = max(0.02, raw_min_x - span_x * margin_pct)
        max_x = min(0.98, raw_max_x + span_x * margin_pct)
        min_y = max(0.02, raw_min_y - span_y * margin_pct)
        max_y = min(0.98, raw_max_y + span_y * margin_pct)

        return (min_x, max_x, min_y, max_y)

    @staticmethod
    def compute_pinch_thresholds(
        open_span: float,
        pinch_dist: float,
    ) -> Tuple[float, float]:
        """
        Derive optimal pinch trigger & release thresholds with hysteresis.
        Returns: (pinch_threshold, release_threshold)
        """
        open_val = max(0.08, open_span)
        pinch_val = max(0.01, pinch_dist)

        # Pinch trigger at ~35% of separation between pinch contact and open hand
        delta = max(0.02, open_val - pinch_val)
        trigger = pinch_val + delta * 0.35
        release = pinch_val + delta * 0.60

        return (max(0.03, min(0.15, trigger)), max(0.05, min(0.25, release)))

    @staticmethod
    def evaluate_quality(
        neutral: Tuple[float, float],
        reach_bounds: Tuple[float, float, float, float],
        open_span: float,
        pinch_dist: float,
    ) -> Tuple[str, float]:
        """
        Score calibration quality based on range coverage, stability, and pinch delta.
        Returns: (quality_label, percentage)
        """
        min_x, max_x, min_y, max_y = reach_bounds
        span_x = max_x - min_x
        span_y = max_y - min_y

        # Score range coverage (weight 40%)
        coverage_score = min(1.0, (span_x + span_y) / 0.80) * 40.0

        # Score pinch delta separation (weight 40%)
        separation = max(0.0, open_span - pinch_dist)
        pinch_score = min(1.0, separation / 0.12) * 40.0

        # Score neutral centering (weight 20%)
        nx, ny = neutral
        center_dev = math.sqrt((nx - 0.5) ** 2 + (ny - 0.5) ** 2)
        center_score = max(0.0, 1.0 - (center_dev / 0.40)) * 20.0

        total_pct = max(10.0, min(100.0, coverage_score + pinch_score + center_score))

        if total_pct >= 80.0:
            label = "EXCELLENT"
        elif total_pct >= 60.0:
            label = "GOOD"
        else:
            label = "FAIR"

        return (label, total_pct)

    @staticmethod
    def remap_coordinate(
        raw_x: float,
        raw_y: float,
        calib: HandCalibrationData,
    ) -> Tuple[float, float]:
        """
        Remap raw camera landmark (x, y) across calibrated range boundaries to [0.0, 1.0].
        """
        span_x = calib.range_max_x - calib.range_min_x
        span_y = calib.range_max_y - calib.range_min_y

        if span_x < 0.01 or span_y < 0.01:
            return (raw_x, raw_y)

        norm_x = (raw_x - calib.range_min_x) / span_x
        norm_y = (raw_y - calib.range_min_y) / span_y

        clamped_x = max(0.0, min(1.0, norm_x))
        clamped_y = max(0.0, min(1.0, norm_y))

        return (clamped_x, clamped_y)
