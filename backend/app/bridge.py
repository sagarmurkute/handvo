"""Frontend-Backend Communication Layer Bridge for HANDVO.

Defines the event contracts, data schemas, and bidirectional dispatchers
connecting the Python backend engine with the HTML/CSS/JS frontend interface.
"""

from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class BridgeEvent(str, Enum):
    """Event names for Frontend-Backend communication contract."""
    # Vision & Cursor
    CURSOR_UPDATE = "cursor:update"
    HAND_DETECTED = "hand:detected"
    HAND_LOST = "hand:lost"
    PINCH_TRIGGERED = "pinch:triggered"
    CAMERA_STATE_CHANGED = "camera:state_changed"

    # Dwell & Selection
    DWELL_START = "dwell:start"
    DWELL_PROGRESS = "dwell:progress"
    DWELL_COMPLETE = "dwell:complete"
    DWELL_CANCEL = "dwell:cancel"

    # AAC Communication
    PHRASE_SELECTED = "aac:phrase_selected"
    SENTENCE_UPDATED = "aac:sentence_updated"
    CATEGORY_CHANGED = "aac:category_changed"

    # Speech Synthesis
    SPEECH_REQUEST = "speech:speak"
    SPEECH_STOP = "speech:stop"
    SPEECH_STARTED = "speech:started"
    SPEECH_FINISHED = "speech:finished"

    # Smart Predictions
    PREDICTION_REQUEST = "prediction:request"
    PREDICTION_LEARN = "prediction:learn"
    PREDICTIONS_UPDATED = "prediction:updated"

    # Settings & Profiles
    PROFILE_ACTIVE_CHANGED = "profile:active_changed"
    PROFILE_LIST_UPDATED = "profile:list_updated"
    SETTINGS_SAVED = "settings:saved"

    # Emergency Mode
    EMERGENCY_TRIGGERED = "emergency:triggered"
    EMERGENCY_EXITED = "emergency:exited"

    # Calibration
    CALIBRATION_STEP = "calibration:step"
    CALIBRATION_SAMPLE = "calibration:sample"
    CALIBRATION_COMPLETED = "calibration:completed"


@dataclass
class CursorUpdatePacket:
    """Cursor position and hand gesture tracking telemetry packet."""
    camera_active: bool
    tracking_valid: bool
    norm_x: float = 0.5
    norm_y: float = 0.5
    raw_x: float = 960.0
    raw_y: float = 540.0
    is_pinched: bool = False
    pinch_distance: float = 0.0
    handedness: str = "Right"
    landmarks: List[Dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class SpeechRequestPacket:
    """TTS speech synthesis request packet."""
    text: str
    interrupt: bool = False
    voice_id: Optional[str] = None
    rate: Optional[int] = None
    volume: Optional[float] = None


@dataclass
class PredictionRequestPacket:
    """Smart next-phrase prediction query packet."""
    sentence: str
    category: str = "common"
    limit: int = 5


@dataclass
class PredictionLearnPacket:
    """User phrase selection learning packet."""
    prev_sentence: str
    selected_phrase: str
    category_id: str = "common"
    profile_id: int = 1


@dataclass
class EmergencyTriggerPacket:
    """Emergency alert trigger packet."""
    action_id: int
    label: str
    speech_text: str
    icon: str = "🚨"


class CommunicationBridge:
    """Universal Communication Bridge coordinating backend events and frontend clients."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Register an event callback listener."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Unregister an event callback listener."""
        if event_name in self._subscribers and callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)

    def dispatch(self, event_name: str, payload: Any = None) -> None:
        """Broadcast an event to all subscribed listeners."""
        for cb in self._subscribers.get(event_name, []):
            try:
                cb(payload)
            except Exception as e:
                print(f"[Bridge] Error dispatching event {event_name}: {e}")


# Singleton bridge instance for application runtime
bridge = CommunicationBridge()
