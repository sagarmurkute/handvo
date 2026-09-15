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
    def thumb_ip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[3] if self.is_valid else None

    @property
    def thumb_mcp(self) -> Optional[LandmarkPoint]:
        return self.landmarks[2] if self.is_valid else None

    @property
    def thumb_cmc(self) -> Optional[LandmarkPoint]:
        return self.landmarks[1] if self.is_valid else None

    @property
    def index_tip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[8] if self.is_valid else None

    @property
    def index_pip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[6] if self.is_valid else None

    @property
    def index_mcp(self) -> Optional[LandmarkPoint]:
        return self.landmarks[5] if self.is_valid else None

    @property
    def middle_tip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[12] if self.is_valid else None

    @property
    def middle_pip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[10] if self.is_valid else None

    @property
    def middle_mcp(self) -> Optional[LandmarkPoint]:
        return self.landmarks[9] if self.is_valid else None

    @property
    def ring_tip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[16] if self.is_valid else None

    @property
    def ring_pip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[14] if self.is_valid else None

    @property
    def ring_mcp(self) -> Optional[LandmarkPoint]:
        return self.landmarks[13] if self.is_valid else None

    @property
    def pinky_tip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[20] if self.is_valid else None

    @property
    def pinky_pip(self) -> Optional[LandmarkPoint]:
        return self.landmarks[18] if self.is_valid else None

    @property
    def pinky_mcp(self) -> Optional[LandmarkPoint]:
        return self.landmarks[17] if self.is_valid else None
