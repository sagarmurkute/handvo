"""Database data models for user profiles and calibration settings."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProfile:
    """User preferences, speech parameters, accessibility, and calibration profile."""
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
    cooldown_time: float = 0.60
    cursor_size: int | str = 14
    cursor_color: str = "#38bdf8"
    smoothing_factor: float = 1.50
    calibration_quality: str = "GOOD"
    is_archived: bool = False
    is_active: bool = False
    language: str = "en"
    tts_rate: int = 150
    tts_volume: float = 1.0
    dwell_sound: bool = True
    high_contrast: bool = False
    theme: str = "dark"
    ui_scale: str = "medium"
    reduced_motion: bool = False
    voice_id: Optional[str] = None

    @property
    def speech_rate(self) -> int:
        return self.tts_rate

    @speech_rate.setter
    def speech_rate(self, val: int) -> None:
        self.tts_rate = val

    @property
    def speech_volume(self) -> float:
        return self.tts_volume

    @speech_volume.setter
    def speech_volume(self, val: float) -> None:
        self.tts_volume = val

    @property
    def button_size(self) -> str:
        return self.ui_scale

    @button_size.setter
    def button_size(self, val: str) -> None:
        self.ui_scale = val

    @property
    def smoothing_strength(self) -> float:
        return self.smoothing_factor

    @smoothing_strength.setter
    def smoothing_strength(self, val: float) -> None:
        self.smoothing_factor = val



@dataclass
class CustomPhrase:
    """Caregiver or user configured phrase item within a category."""
    id: Optional[int] = None
    profile_id: int = 1
    category: str = "common"
    label: str = ""
    text: str = ""
    icon: str = "💬"
    accent_color: str = "#38bdf8"
    sort_order: int = 0



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

