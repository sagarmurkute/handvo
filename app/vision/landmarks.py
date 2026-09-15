"""Hand landmark data structures and normalization utilities."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class LandmarkPoint:
    """A 3D normalized landmark point."""
    x: float
    y: float
    z: float = 0.0


@dataclass
class HandLandmarks:
    """Represents detected landmarks for a single hand."""
    landmarks: List[LandmarkPoint] = field(default_factory=list)
    handedness: str = "Right"
    confidence: float = 0.0

    @property
    def is_valid(self) -> bool:
        return len(self.landmarks) >= 21

    @property
    def wrist(self) -> Optional[LandmarkPoint]:
        return self.landmarks[0] if self.is_valid else None

    @property
    def thumb_tip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[4] if self.is_valid else None

    @property
    def index_tip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[8] if self.is_valid else None

    @property
    def middle_mcp(self) -> Optional[LandmarkPoint]:
        return self.landmarks[9] if self.is_valid else None
