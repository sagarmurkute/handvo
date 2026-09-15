"""Communication Board data models and pure state management for HANDVO."""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class CommunicationItem:
    """A word, phrase, or action item on the communication board."""

    item_id: str
    label: str
    text: str
    category_id: str
    accent_color: str = "#38bdf8"
    enabled: bool = True


@dataclass
class CommunicationCategory:
    """A collection of related communication items."""

    category_id: str
    name: str
    icon: str
    accent_color: str
    items: List[CommunicationItem] = field(default_factory=list)


class CommunicationBoardModel:
    """
    Pure state management for the HANDVO Communication Board.
    Maintains composed message words, active category, and fires change notifications.
    """

    def __init__(self) -> None:
        self._message_tokens: List[str] = []
        self._active_category_id: str = "common"
        self._categories: Dict[str, CommunicationCategory] = {}
        self._on_message_changed_listeners: List[Callable[[str], None]] = []
        self._on_category_changed_listeners: List[Callable[[str], None]] = []
        self._on_speak_requested_listeners: List[Callable[[str], None]] = []

        self._init_default_content()

    def _init_default_content(self) -> None:
        """Populate initial categories and accessible communication items."""
        common = CommunicationCategory(
            category_id="common",
            name="Common",
            icon="💬",
            accent_color="#38bdf8",
            items=[
                CommunicationItem("comm_yes", "✅ Yes", "Yes", "common", "#22c55e"),
                CommunicationItem("comm_no", "❌ No", "No", "common", "#ef4444"),
                CommunicationItem("comm_hello", "👋 Hello", "Hello", "common", "#38bdf8"),
                CommunicationItem("comm_thanks", "🙏 Thank you", "Thank you", "common", "#a855f7"),
                CommunicationItem("comm_please", "🤲 Please", "Please", "common", "#3b82f6"),
                CommunicationItem("comm_help", "🚨 Help", "Help", "common", "#f59e0b"),
                CommunicationItem("comm_okay", "👍 I am okay", "I am okay", "common", "#10b981"),
                CommunicationItem("comm_goodbye", "👋 Goodbye", "Goodbye", "common", "#64748b"),
            ],
        )

        needs = CommunicationCategory(
            category_id="needs",
            name="Needs",
            icon="💧",
            accent_color="#06b6d4",
            items=[
                CommunicationItem("need_water", "💧 Water", "I need water", "needs", "#06b6d4"),
                CommunicationItem("need_food", "🍲 Food", "I need food", "needs", "#f97316"),
                CommunicationItem("need_bathroom", "🚻 Bathroom", "I need the bathroom", "needs", "#8b5cf6"),
                CommunicationItem("need_help", "🆘 I need help", "I need help", "needs", "#ef4444"),
                CommunicationItem("need_rest", "🛌 Rest / Sleep", "I want to rest", "needs", "#6366f1"),
                CommunicationItem("need_glasses", "👓 Glasses", "I need my glasses", "needs", "#14b8a6"),
            ],
        )

        feelings = CommunicationCategory(
            category_id="feelings",
            name="Feelings",
            icon="❤️",
            accent_color="#ec4899",
            items=[
                CommunicationItem("feel_okay", "😊 I am okay", "I am okay", "feelings", "#10b981"),
                CommunicationItem("feel_tired", "🥱 I am tired", "I am tired", "feelings", "#64748b"),
                CommunicationItem("feel_pain", "😣 I am in pain", "I am in pain", "feelings", "#ef4444"),
                CommunicationItem("feel_happy", "😄 I am happy", "I am happy", "feelings", "#eab308"),
                CommunicationItem("feel_sad", "😢 I am sad", "I am sad", "feelings", "#3b82f6"),
                CommunicationItem("feel_cold", "🥶 I am cold", "I am cold", "feelings", "#06b6d4"),
                CommunicationItem("feel_hot", "🥵 I am hot", "I am hot", "feelings", "#f97316"),
            ],
        )

        people = CommunicationCategory(
            category_id="people",
            name="People",
            icon="👥",
            accent_color="#8b5cf6",
            items=[
                CommunicationItem("ppl_doctor", "👨‍⚕️ Doctor", "Doctor", "people", "#06b6d4"),
                CommunicationItem("ppl_nurse", "👩‍⚕️ Nurse", "Nurse", "people", "#ec4899"),
                CommunicationItem("ppl_family", "👨‍👩‍👧 Family", "Family", "people", "#f59e0b"),
                CommunicationItem("ppl_friend", "🤝 Friend", "Friend", "people", "#10b981"),
                CommunicationItem("ppl_caregiver", "🧑‍🦽 Caregiver", "Caregiver", "people", "#8b5cf6"),
                CommunicationItem("ppl_assistant", "💼 Assistant", "Assistant", "people", "#38bdf8"),
            ],
        )

        places = CommunicationCategory(
            category_id="places",
            name="Places",
            icon="📍",
            accent_color="#10b981",
            items=[
                CommunicationItem("plc_home", "🏠 Home", "Home", "places", "#10b981"),
                CommunicationItem("plc_hospital", "🏥 Hospital", "Hospital", "places", "#ef4444"),
                CommunicationItem("plc_outside", "🌳 Outside", "Outside", "places", "#22c55e"),
                CommunicationItem("plc_bedroom", "🛏️ Bedroom", "Bedroom", "places", "#6366f1"),
                CommunicationItem("plc_kitchen", "🍽️ Kitchen", "Kitchen", "places", "#f97316"),
                CommunicationItem("plc_bathroom", "🚿 Bathroom", "Bathroom", "places", "#06b6d4"),
            ],
        )

        actions = CommunicationCategory(
            category_id="actions",
            name="Actions",
            icon="⚡",
            accent_color="#f59e0b",
            items=[
                CommunicationItem("act_come", "👋 Come here", "Come here", "actions", "#38bdf8"),
                CommunicationItem("act_call", "📞 Call someone", "Call someone", "actions", "#22c55e"),
                CommunicationItem("act_turn_on", "💡 Turn on", "Turn on", "actions", "#eab308"),
                CommunicationItem("act_turn_off", "🌑 Turn off", "Turn off", "actions", "#64748b"),
                CommunicationItem("act_stop", "🛑 Stop", "Stop", "actions", "#ef4444"),
                CommunicationItem("act_look", "👀 Look here", "Look here", "actions", "#8b5cf6"),
            ],
        )

        self._categories = {
            "common": common,
            "needs": needs,
            "feelings": feelings,
            "people": people,
            "places": places,
            "actions": actions,
        }

    @property
    def current_message(self) -> str:
        return " ".join(self._message_tokens).strip()

    @property
    def message_tokens(self) -> List[str]:
        return list(self._message_tokens)

    @property
    def active_category_id(self) -> str:
        return self._active_category_id

    def get_categories(self) -> List[CommunicationCategory]:
        return list(self._categories.values())

    def get_category(self, category_id: str) -> Optional[CommunicationCategory]:
        return self._categories.get(category_id)

    def get_active_items(self) -> List[CommunicationItem]:
        cat = self._categories.get(self._active_category_id)
        return cat.items if cat else []

    def set_category(self, category_id: str) -> bool:
        if category_id in self._categories and category_id != self._active_category_id:
            self._active_category_id = category_id
            self._notify_category_changed()
            return True
        return False

    def add_item(self, item: CommunicationItem) -> None:
        if item.text:
            self._message_tokens.append(item.text)
            self._notify_message_changed()

    def add_text(self, text: str) -> None:
        if text.strip():
            self._message_tokens.append(text.strip())
            self._notify_message_changed()

    def add_space(self) -> None:
        self._message_tokens.append("")
        self._notify_message_changed()

    def delete_last(self) -> bool:
        if self._message_tokens:
            self._message_tokens.pop()
            self._notify_message_changed()
            return True
        return False

    def clear_message(self) -> None:
        if self._message_tokens:
            self._message_tokens.clear()
            self._notify_message_changed()

    def request_speak(self) -> str:
        msg = self.current_message
        for listener in self._on_speak_requested_listeners:
            try:
                listener(msg)
            except Exception:
                pass
        return msg

    def on_message_changed(self, callback: Callable[[str], None]) -> None:
        self._on_message_changed_listeners.append(callback)

    def on_category_changed(self, callback: Callable[[str], None]) -> None:
        self._on_category_changed_listeners.append(callback)

    def on_speak_requested(self, callback: Callable[[str], None]) -> None:
        self._on_speak_requested_listeners.append(callback)

    def _notify_message_changed(self) -> None:
        msg = self.current_message
        for listener in self._on_message_changed_listeners:
            try:
                listener(msg)
            except Exception:
                pass

    def _notify_category_changed(self) -> None:
        cat_id = self._active_category_id
        for listener in self._on_category_changed_listeners:
            try:
                listener(cat_id)
            except Exception:
                pass
