"""Advanced Multi-Gesture Classifier for HANDVO.

Recognizes static and dynamic hand postures from MediaPipe 21 3D landmarks:
- Pointing (Index only)
- Pinch (Thumb + Index contact)
- Open Palm (All fingers extended)
- Fist (All fingers curled)
- Thumbs Up (Thumb up, fingers curled)
- Thumbs Down (Thumb down, fingers curled)
- Peace Sign / V-Sign (Index + Middle extended)
- Swipe Left / Swipe Right (Rapid hand velocity displacement)
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional, Tuple
from collections import deque

from app.vision.landmarks import HandLandmarks


class GestureType(str, Enum):
    """Recognized gesture categories."""
    NONE = "none"
    POINTING = "pointing"
    PINCH = "pinch"
    OPEN_PALM = "open_palm"
    FIST = "fist"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    PEACE_SIGN = "peace_sign"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"


@dataclass
class GestureClassificationResult:
    """Consolidated classification output for a single video frame."""
    gesture: GestureType = GestureType.NONE
    confidence: float = 0.0
    is_pinch: bool = False
    pinch_distance: float = 1.0
    finger_states: Dict[str, bool] = field(default_factory=dict)  # is_extended per finger
    swipe_event: Optional[str] = None  # "left" or "right" when triggered
    raw_gesture_name: str = "none"


class HandGestureClassifier:
    """Robust heuristic classifier identifying assistive AAC postures with temporal hysteresis."""

    def __init__(
        self,
        pinch_threshold: float = 0.065,
        release_threshold: float = 0.085,
        swipe_velocity_threshold: float = 1.2,  # screen widths per second
        swipe_history_len: int = 10,
    ) -> None:
        self.pinch_threshold = pinch_threshold
        self.release_threshold = release_threshold
        self.swipe_velocity_threshold = swipe_velocity_threshold

        self._was_pinched = False
        self._history: Deque[Tuple[float, float, float]] = deque(maxlen=swipe_history_len)
        self._last_swipe_time = -999.0
        self._swipe_cooldown = 0.8  # seconds

    def _is_finger_extended(self, tip_y: float, pip_y: float, mcp_y: float, is_thumb: bool = False, tip_x: float = 0, ip_x: float = 0, mcp_x: float = 0) -> bool:
        """Check if a finger is extended based on joint vertical/horizontal displacements."""
        if is_thumb:
            # Thumb moves primarily laterally
            return abs(tip_x - mcp_x) > abs(ip_x - mcp_x) and tip_y < mcp_y + 0.05
        # Standard fingers: tip is higher up (smaller y in image space) than PIP and MCP
        return tip_y < pip_y and pip_y < mcp_y

    def classify(self, hand: Optional[HandLandmarks], current_time: Optional[float] = None) -> GestureClassificationResult:
        """Classify current hand posture and check dynamic swipe events."""
        now = current_time if current_time is not None else time.time()

        if hand is None or not hand.is_valid:
            self._was_pinched = False
            self._history.clear()
            return GestureClassificationResult()

        wrist = hand.wrist
        thumb = hand.thumb_tip
        index = hand.index_tip
        middle = hand.middle_tip
        ring = hand.ring_tip
        pinky = hand.pinky_tip

        if not all([wrist, thumb, index, middle, ring, pinky]):
            return GestureClassificationResult()

        # 1. Determine Extension State of each finger
        # Thumb
        t_extended = False
        if hand.thumb_ip and hand.thumb_mcp:
            dx_tip = abs(thumb.x - wrist.x)
            dx_mcp = abs(hand.thumb_mcp.x - wrist.x)
            t_extended = dx_tip > dx_mcp and thumb.y < wrist.y + 0.1

        # Index
        i_extended = False
        if hand.index_pip and hand.index_mcp:
            i_extended = index.y < hand.index_pip.y and hand.index_pip.y < hand.index_mcp.y

        # Middle
        m_extended = False
        if hand.middle_pip and hand.middle_mcp:
            m_extended = middle.y < hand.middle_pip.y and hand.middle_pip.y < hand.middle_mcp.y

        # Ring
        r_extended = False
        if hand.ring_pip and hand.ring_mcp:
            r_extended = ring.y < hand.ring_pip.y and hand.ring_pip.y < hand.ring_mcp.y

        # Pinky
        p_extended = False
        if hand.pinky_pip and hand.pinky_mcp:
            p_extended = pinky.y < hand.pinky_pip.y and hand.pinky_pip.y < hand.pinky_mcp.y

        finger_states = {
            "thumb": t_extended,
            "index": i_extended,
            "middle": m_extended,
            "ring": r_extended,
            "pinky": p_extended,
        }

        # 2. Pinch Distance Calculation
        dx = thumb.x - index.x
        dy = thumb.y - index.y
        dz = thumb.z - index.z
        raw_pinch_dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        # Scale by palm size
        palm_dx = hand.middle_mcp.x - wrist.x
        palm_dy = hand.middle_mcp.y - wrist.y
        palm_dz = hand.middle_mcp.z - wrist.z
        palm_scale = math.sqrt(palm_dx * palm_dx + palm_dy * palm_dy + palm_dz * palm_dz)
        norm_pinch_dist = raw_pinch_dist / palm_scale if palm_scale > 0.001 else raw_pinch_dist

        if self._was_pinched:
            is_pinched = norm_pinch_dist < self.release_threshold
        else:
            is_pinched = norm_pinch_dist < self.pinch_threshold
        self._was_pinched = is_pinched

        # 3. Dynamic Swipe Gesture Detection
        swipe_event: Optional[str] = None
        self._history.append((now, wrist.x, wrist.y))
        if len(self._history) >= 4 and (now - self._last_swipe_time) > self._swipe_cooldown:
            t0, x0, _ = self._history[0]
            dt = now - t0
            dx_swipe = wrist.x - x0
            if dt > 0.05:
                vel_x = dx_swipe / dt
                if vel_x > self.swipe_velocity_threshold:
                    swipe_event = "right"
                    self._last_swipe_time = now
                    self._history.clear()
                elif vel_x < -self.swipe_velocity_threshold:
                    swipe_event = "left"
                    self._last_swipe_time = now
                    self._history.clear()

        # 4. Posture Classification Decision Tree
        active_gesture = GestureType.NONE
        confidence = 0.85

        if swipe_event == "left":
            active_gesture = GestureType.SWIPE_LEFT
            confidence = 0.95
        elif swipe_event == "right":
            active_gesture = GestureType.SWIPE_RIGHT
            confidence = 0.95
        elif is_pinched:
            active_gesture = GestureType.PINCH
            confidence = 0.95
        # Thumbs Up: Thumb pointing UP (y well above wrist and MCP), others folded
        elif thumb.y < wrist.y - 0.12 and not i_extended and not m_extended and not r_extended and not p_extended:
            active_gesture = GestureType.THUMBS_UP
            confidence = 0.92
        # Thumbs Down: Thumb pointing DOWN (y well below wrist and MCP), others folded
        elif thumb.y > wrist.y + 0.12 and not i_extended and not m_extended and not r_extended and not p_extended:
            active_gesture = GestureType.THUMBS_DOWN
            confidence = 0.92
        # Open Palm: All 4 main fingers extended + thumb out
        elif i_extended and m_extended and r_extended and p_extended:
            active_gesture = GestureType.OPEN_PALM
            confidence = 0.95
        # Fist: None of the main 4 fingers extended, thumb not pointing high up
        elif not i_extended and not m_extended and not r_extended and not p_extended and not (thumb.y < wrist.y - 0.10):
            active_gesture = GestureType.FIST
            confidence = 0.90
        # Peace Sign (V): Index & Middle extended, Ring & Pinky folded
        elif i_extended and m_extended and not r_extended and not p_extended:
            active_gesture = GestureType.PEACE_SIGN
            confidence = 0.93
        # Pointing: Only Index extended, Middle/Ring/Pinky folded
        elif i_extended and not m_extended and not r_extended and not p_extended:
            active_gesture = GestureType.POINTING
            confidence = 0.90

        return GestureClassificationResult(
            gesture=active_gesture,
            confidence=confidence,
            is_pinch=is_pinched,
            pinch_distance=norm_pinch_dist,
            finger_states=finger_states,
            swipe_event=swipe_event,
            raw_gesture_name=active_gesture.value,
        )

    def reset(self) -> None:
        """Reset internal filter states and histories."""
        self._was_pinched = False
        self._history.clear()
        self._last_swipe_time = -999.0
