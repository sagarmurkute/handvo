"""Database data models for user profiles and calibration settings."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProfile:
    """User preferences and calibration profile."""
    id: Optional[int] = None
    name: str = "Default User"
    dominant_hand: str = "Right"
    neutral_x: float = 0.50
    neutral_y: float = 0.50
    range_min_x: float = 0.20
    range_max_x: float = 0.80
    range_min_y: float = 0.20
    range_max_y: float = 0.80
    open_hand_span: float = 0.25
    pinch_threshold: float = 0.05
    pinch_release_threshold: float = 0.08
    dwell_time: float = 0.80
    smoothing_factor: float = 1.50
    calibration_quality: str = "GOOD"


@dataclass
class EmergencyAction:
    """Configurable emergency action phrase and button definition."""
    id: Optional[int] = None
    label: str = ""
    speech_text: str = ""
    icon: str = "🚨"
    accent_color: str = "#ef4444"
    sort_order: int = 0
    is_enabled: bool = True

