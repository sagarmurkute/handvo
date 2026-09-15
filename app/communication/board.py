"""Communication board manager integrating categories, sentence building, prediction, and speech."""

from typing import Dict, List, Optional
from app.communication.categories import CommunicationCategory, CommunicationItem
from app.communication.prediction import PhrasePredictor
from app.communication.sentence import SentenceBuilder
from app.communication.speech import SpeechEngine


class CommunicationBoard:
    """Central state manager for the AAC board."""

    def __init__(self) -> None:
        self.sentence = SentenceBuilder()
        self.speech = SpeechEngine()
        self.predictor = PhrasePredictor()
        self._categories: Dict[str, CommunicationCategory] = {}
        self._active_category_id: str = "common"
        self._init_default_categories()

    def _init_default_categories(self) -> None:
        self._categories = {
            "common": CommunicationCategory("common", "Common", "💬", "#38bdf8", [
                CommunicationItem("c_yes", "✅ Yes", "Yes", "common", "#22c55e"),
                CommunicationItem("c_no", "❌ No", "No", "common", "#ef4444"),
                CommunicationItem("c_hello", "👋 Hello", "Hello", "common", "#38bdf8"),
                CommunicationItem("c_thanks", "🙏 Thank you", "Thank you", "common", "#a855f7"),
                CommunicationItem("c_please", "🤲 Please", "Please", "common", "#3b82f6"),
                CommunicationItem("c_help", "🚨 Help", "Help", "common", "#f59e0b"),
            ]),
            "needs": CommunicationCategory("needs", "Needs", "💧", "#06b6d4", [
                CommunicationItem("n_water", "💧 Water", "I need water", "needs", "#06b6d4"),
                CommunicationItem("n_food", "🍲 Food", "I need food", "needs", "#f97316"),
                CommunicationItem("n_bathroom", "🚻 Bathroom", "I need the bathroom", "needs", "#8b5cf6"),
                CommunicationItem("n_rest", "🛌 Rest", "I want to rest", "needs", "#6366f1"),
            ]),
            "feelings": CommunicationCategory("feelings", "Feelings", "❤️", "#ec4899", [
                CommunicationItem("f_ok", "😊 Okay", "I am okay", "feelings", "#10b981"),
                CommunicationItem("f_pain", "😣 Pain", "I am in pain", "feelings", "#ef4444"),
                CommunicationItem("f_tired", "🥱 Tired", "I am tired", "feelings", "#64748b"),
                CommunicationItem("f_happy", "😄 Happy", "I am happy", "feelings", "#eab308"),
            ]),
            "actions": CommunicationCategory("actions", "Actions", "⚡", "#f59e0b", [
                CommunicationItem("a_come", "👋 Come here", "Come here", "actions", "#38bdf8"),
                CommunicationItem("a_call", "📞 Call someone", "Call someone", "actions", "#22c55e"),
                CommunicationItem("a_stop", "🛑 Stop", "Stop", "actions", "#ef4444"),
            ]),
        }

    @property
    def active_category_id(self) -> str:
        return self._active_category_id

    def set_category(self, category_id: str) -> bool:
        if category_id in self._categories:
            self._active_category_id = category_id
            return True
        return False

    def get_categories(self) -> List[CommunicationCategory]:
        return list(self._categories.values())

    def get_active_items(self) -> List[CommunicationItem]:
        cat = self._categories.get(self._active_category_id)
        return cat.items if cat else []

    def speak_current(self) -> str:
        text = self.sentence.text
        if text:
            self.speech.speak(text)
        return text
