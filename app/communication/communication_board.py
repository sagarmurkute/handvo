"""Communication Board data models and pure state management for HANDVO."""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class CommunicationItem:
    """A word, phrase, or action card on the communication board."""
    item_id: str
    label: str
    text: str
    category_id: str
    icon: str = ""
    subtitle: str = ""
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
        """Populate initial 6 categories and rich accessible communication cards."""
        # 1. Common
        common = CommunicationCategory(
            category_id="common",
            name="Common",
            icon="💬",
            accent_color="#38bdf8",
            items=[
                CommunicationItem("comm_yes", "Yes", "Yes", "common", "✅", "Agree", "#22c55e"),
                CommunicationItem("comm_no", "No", "No", "common", "❌", "Disagree", "#ef4444"),
                CommunicationItem("comm_hello", "Hello", "Hello", "common", "👋", "Greetings", "#38bdf8"),
                CommunicationItem("comm_thanks", "Thank You", "Thank you", "common", "🙏", "Gratitude", "#a855f7"),
                CommunicationItem("comm_please", "Please", "Please", "common", "🤲", "Polite request", "#3b82f6"),
                CommunicationItem("comm_help", "Help", "I need help", "common", "🚨", "Urgent assistance", "#f59e0b"),
                CommunicationItem("comm_okay", "I Am Okay", "I am okay", "common", "👍", "Fine status", "#10b981"),
                CommunicationItem("comm_goodbye", "Goodbye", "Goodbye", "common", "👋", "Farewell", "#64748b"),
            ],
        )

        # 2. Needs
        needs = CommunicationCategory(
            category_id="needs",
            name="Needs",
            icon="💧",
            accent_color="#06b6d4",
            items=[
                CommunicationItem("need_water", "Water", "I need water", "needs", "💧", "Drink water", "#06b6d4"),
                CommunicationItem("need_food", "Food", "I need food", "needs", "🍲", "Eat food", "#f97316"),
                CommunicationItem("need_bathroom", "Bathroom", "I need the bathroom", "needs", "🚻", "Restroom", "#8b5cf6"),
                CommunicationItem("need_rest", "Rest", "I want to rest", "needs", "🛌", "Sleep / Lie down", "#6366f1"),
                CommunicationItem("need_glasses", "Glasses", "I need my glasses", "needs", "👓", "Eyewear", "#14b8a6"),
                CommunicationItem("need_medicine", "Medicine", "I need my medicine", "needs", "💊", "Medication", "#ec4899"),
                CommunicationItem("need_blanket", "Blanket", "I need a blanket", "needs", "🧣", "Warmth", "#eab308"),
                CommunicationItem("need_help", "Assistance", "I need assistance", "needs", "🆘", "Caregiver help", "#ef4444"),
            ],
        )

        # 3. Feelings
        feelings = CommunicationCategory(
            category_id="feelings",
            name="Feelings",
            icon="❤️",
            accent_color="#ec4899",
            items=[
                CommunicationItem("feel_happy", "Happy", "I am happy", "feelings", "😄", "Feeling good", "#eab308"),
                CommunicationItem("feel_okay", "Okay", "I am okay", "feelings", "😊", "Normal", "#10b981"),
                CommunicationItem("feel_pain", "In Pain", "I am in pain", "feelings", "😣", "Hurting", "#ef4444"),
                CommunicationItem("feel_tired", "Tired", "I am tired", "feelings", "🥱", "Exhausted", "#64748b"),
                CommunicationItem("feel_sad", "Sad", "I am sad", "feelings", "😢", "Feeling down", "#3b82f6"),
                CommunicationItem("feel_cold", "Cold", "I am cold", "feelings", "🥶", "Chilly", "#06b6d4"),
                CommunicationItem("feel_hot", "Hot", "I am hot", "feelings", "🥵", "Too warm", "#f97316"),
                CommunicationItem("feel_scared", "Scared", "I feel scared", "feelings", "😨", "Worried", "#a855f7"),
            ],
        )

        # 4. People
        people = CommunicationCategory(
            category_id="people",
            name="People",
            icon="👥",
            accent_color="#8b5cf6",
            items=[
                CommunicationItem("ppl_doctor", "Doctor", "Doctor", "people", "👨‍⚕️", "Physician", "#06b6d4"),
                CommunicationItem("ppl_nurse", "Nurse", "Nurse", "people", "👩‍⚕️", "Medical nurse", "#ec4899"),
                CommunicationItem("ppl_family", "Family", "Family", "people", "👨‍👩‍👧", "Loved ones", "#f59e0b"),
                CommunicationItem("ppl_friend", "Friend", "Friend", "people", "🤝", "Companion", "#10b981"),
                CommunicationItem("ppl_caregiver", "Caregiver", "Caregiver", "people", "🧑‍🦽", "Attendant", "#8b5cf6"),
                CommunicationItem("ppl_assistant", "Assistant", "Assistant", "people", "💼", "Helper", "#38bdf8"),
                CommunicationItem("ppl_visitor", "Visitor", "Visitor", "people", "🚪", "Guest", "#14b8a6"),
                CommunicationItem("ppl_everyone", "Everyone", "Everyone", "people", "👥", "All people", "#6366f1"),
            ],
        )

        # 5. Places
        places = CommunicationCategory(
            category_id="places",
            name="Places",
            icon="📍",
            accent_color="#10b981",
            items=[
                CommunicationItem("plc_home", "Home", "Home", "places", "🏠", "My residence", "#10b981"),
                CommunicationItem("plc_hospital", "Hospital", "Hospital", "places", "🏥", "Medical clinic", "#ef4444"),
                CommunicationItem("plc_outside", "Outside", "Outside", "places", "🌳", "Garden / Fresh air", "#22c55e"),
                CommunicationItem("plc_bedroom", "Bedroom", "Bedroom", "places", "🛏️", "Bed room", "#6366f1"),
                CommunicationItem("plc_kitchen", "Kitchen", "Kitchen", "places", "🍽️", "Dining area", "#f97316"),
                CommunicationItem("plc_bathroom", "Bathroom", "Bathroom", "places", "🚿", "Restroom", "#06b6d4"),
                CommunicationItem("plc_livingroom", "Living Room", "Living Room", "places", "🛋️", "Hall / Lounge", "#f59e0b"),
                CommunicationItem("plc_clinic", "Clinic", "Clinic", "places", "🩺", "Doctor office", "#8b5cf6"),
            ],
        )

        # 6. Actions
        actions = CommunicationCategory(
            category_id="actions",
            name="Actions",
            icon="⚡",
            accent_color="#f59e0b",
            items=[
                CommunicationItem("act_come", "Come Here", "Come here", "actions", "👋", "Call nearby", "#38bdf8"),
                CommunicationItem("act_call", "Call Someone", "Call someone", "actions", "📞", "Phone call", "#22c55e"),
                CommunicationItem("act_turn_on", "Turn On", "Turn on", "actions", "💡", "Switch on", "#eab308"),
                CommunicationItem("act_turn_off", "Turn Off", "Turn off", "actions", "🌑", "Switch off", "#64748b"),
                CommunicationItem("act_stop", "Stop", "Stop", "actions", "🛑", "Cease action", "#ef4444"),
                CommunicationItem("act_look", "Look Here", "Look here", "actions", "👀", "Direct visual", "#8b5cf6"),
                CommunicationItem("act_wait", "Wait", "Please wait", "actions", "⏳", "Hold on", "#06b6d4"),
                CommunicationItem("act_open", "Open", "Please open", "actions", "🔓", "Open door / item", "#10b981"),
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
        """Current composed sentence string."""
        return " ".join(t for t in self._message_tokens if t).strip()

    @property
    def message_tokens(self) -> List[str]:
        """List of active phrase tokens."""
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
