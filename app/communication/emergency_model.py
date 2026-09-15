"""Emergency domain management and audio dispatch for HANDVO."""

from typing import Callable, List, Optional
from app.communication.speech import SpeechEngine
from app.database.database import Database
from app.database.models import EmergencyAction
from app.database.profile_repository import ProfileRepository


class EmergencyManager:
    """Manages high-priority emergency phrases, offline speech dispatch, and event listeners."""

    def __init__(
        self,
        repository: Optional[ProfileRepository] = None,
        speech_engine: Optional[SpeechEngine] = None,
    ) -> None:
        self.repo = repository or ProfileRepository(Database())
        self.speech = speech_engine or SpeechEngine(rate=140, volume=1.0)
        self.last_spoken: Optional[str] = None
        self._listeners: List[Callable[[EmergencyAction], None]] = []

    def load_actions(self, enabled_only: bool = True) -> List[EmergencyAction]:
        """Fetch configured emergency actions from SQLite."""
        return self.repo.get_emergency_actions(enabled_only=enabled_only)

    def trigger_action(self, action: EmergencyAction) -> str:
        """
        Execute emergency action: Speak text through offline TTS engine
        and notify UI listeners.
        """
        spoken = action.speech_text.strip() or action.label.strip()
        self.last_spoken = spoken
        self.speech.speak(spoken)

        for listener in self._listeners:
            try:
                listener(action)
            except Exception:
                pass

        return spoken

    def add_listener(self, listener: Callable[[EmergencyAction], None]) -> None:
        """Register callback for emergency triggers."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[EmergencyAction], None]) -> None:
        """Unregister callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def save_action(self, action: EmergencyAction) -> EmergencyAction:
        """Save new or edited emergency action."""
        return self.repo.save_emergency_action(action)

    def delete_action(self, action_id: int) -> bool:
        """Delete an emergency action."""
        return self.repo.delete_emergency_action(action_id)

    def reset_defaults(self) -> List[EmergencyAction]:
        """Reset emergency actions to defaults."""
        return self.repo.reset_emergency_actions()
