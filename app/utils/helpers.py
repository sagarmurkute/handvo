"""Common mathematical and geometric helper functions."""

import math
from typing import Tuple

def euclidean_distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """Calculate Euclidean distance between two 3D points."""
    return math.sqrt(
        (p1[0] - p2[0]) ** 2 +
        (p1[1] - p2[1]) ** 2 +
        (p1[2] - p2[2]) ** 2
    )

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max bounds."""
    return max(min_val, min(max_val, value))
