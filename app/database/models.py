"""Database data models for user profiles and settings."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProfile:
    """User preferences profile."""
    id: Optional[int] = None
    name: str = "Default User"
    dwell_time: float = 0.80
    pinch_threshold: float = 0.05
    smoothing_factor: float = 1.5
