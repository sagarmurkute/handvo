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
    Maintains composed message words, active category, language, and fires change notifications.
    """

    def __init__(self, language: str = "en") -> None:
        self._language: str = language
        self._message_tokens: List[str] = []
        self._active_category_id: str = "common"
        self._categories: Dict[str, CommunicationCategory] = {}
        self._on_message_changed_listeners: List[Callable[[str], None]] = []
        self._on_category_changed_listeners: List[Callable[[str], None]] = []
        self._on_speak_requested_listeners: List[Callable[[str], None]] = []

        self._init_content_for_language(self._language)

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language_code: str) -> None:
        """Update language (en, hi, mr) and rebuild AAC category cards."""
        if language_code in ("en", "hi", "mr") and language_code != self._language:
            self._language = language_code
            self._init_content_for_language(self._language)
            self._notify_category_changed()

    def _init_default_content(self) -> None:
        self._init_content_for_language(self._language)

    def _init_content_for_language(self, lang: str) -> None:
        """Populate localized 6 categories and accessible communication cards."""
        if lang == "hi":
            self._categories = self._build_hindi_categories()
        elif lang == "mr":
            self._categories = self._build_marathi_categories()
        else:
            self._categories = self._build_english_categories()

    def _build_english_categories(self) -> Dict[str, CommunicationCategory]:
        return {
            "common": CommunicationCategory(
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
            ),
            "needs": CommunicationCategory(
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
            ),
            "feelings": CommunicationCategory(
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
            ),
            "people": CommunicationCategory(
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
            ),
            "places": CommunicationCategory(
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
            ),
            "actions": CommunicationCategory(
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
            ),
        }

    def _build_hindi_categories(self) -> Dict[str, CommunicationCategory]:
        return {
            "common": CommunicationCategory(
                category_id="common",
                name="सामान्य (Common)",
                icon="💬",
                accent_color="#38bdf8",
                items=[
                    CommunicationItem("comm_yes", "हाँ", "हाँ", "common", "✅", "स्वीकार", "#22c55e"),
                    CommunicationItem("comm_no", "नहीं", "नहीं", "common", "❌", "अस्वीकार", "#ef4444"),
                    CommunicationItem("comm_hello", "नमस्ते", "नमस्ते", "common", "👋", "अभिवादन", "#38bdf8"),
                    CommunicationItem("comm_thanks", "धन्यवाद", "धन्यवाद", "common", "🙏", "आभार", "#a855f7"),
                    CommunicationItem("comm_please", "कृपया", "कृपया", "common", "🤲", "विनम्र अनुरोध", "#3b82f6"),
                    CommunicationItem("comm_help", "मदद", "मुझे मदद चाहिए", "common", "🚨", "आपातकालीन सहायता", "#f59e0b"),
                    CommunicationItem("comm_okay", "मैं ठीक हूँ", "मैं ठीक हूँ", "common", "👍", "स्थिति ठीक है", "#10b981"),
                    CommunicationItem("comm_goodbye", "अलविदा", "अलविदा", "common", "👋", "विदा", "#64748b"),
                ],
            ),
            "needs": CommunicationCategory(
                category_id="needs",
                name="ज़रूरतें (Needs)",
                icon="💧",
                accent_color="#06b6d4",
                items=[
                    CommunicationItem("need_water", "पानी", "मुझे पानी चाहिए", "needs", "💧", "पानी पीना है", "#06b6d4"),
                    CommunicationItem("need_food", "खाना", "मुझे खाना चाहिए", "needs", "🍲", "खाना खाना है", "#f97316"),
                    CommunicationItem("need_bathroom", "शौचालय", "मुझे शौचालय जाना है", "needs", "🚻", "शौचालय", "#8b5cf6"),
                    CommunicationItem("need_rest", "आराम", "मुझे आराम करना है", "needs", "🛌", "सोना / लेटना", "#6366f1"),
                    CommunicationItem("need_glasses", "चश्मा", "मुझे मेरा चश्मा चाहिए", "needs", "👓", "चश्मा", "#14b8a6"),
                    CommunicationItem("need_medicine", "दवा", "मुझे मेरी दवा चाहिए", "needs", "💊", "दवाई", "#ec4899"),
                    CommunicationItem("need_blanket", "कंबल", "मुझे कंबल चाहिए", "needs", "🧣", "ठंड लग रही है", "#eab308"),
                    CommunicationItem("need_help", "सहायता", "मुझे सहायता चाहिए", "needs", "🆘", "सहायक बुलाएं", "#ef4444"),
                ],
            ),
            "feelings": CommunicationCategory(
                category_id="feelings",
                name="भावनाएं (Feelings)",
                icon="❤️",
                accent_color="#ec4899",
                items=[
                    CommunicationItem("feel_happy", "खुश", "मैं खुश हूँ", "feelings", "😄", "अच्छा लग रहा है", "#eab308"),
                    CommunicationItem("feel_okay", "ठीक हूँ", "मैं ठीक हूँ", "feelings", "😊", "सामान्य", "#10b981"),
                    CommunicationItem("feel_pain", "दर्द में हूँ", "मुझे दर्द हो रहा है", "feelings", "😣", "दर्द", "#ef4444"),
                    CommunicationItem("feel_tired", "थका हुआ", "मैं थका हुआ हूँ", "feelings", "🥱", "थकान", "#64748b"),
                    CommunicationItem("feel_sad", "उदास", "मैं उदास हूँ", "feelings", "😢", "उदास", "#3b82f6"),
                    CommunicationItem("feel_cold", "ठंड", "मुझे ठंड लग रही है", "feelings", "🥶", "ठंडा", "#06b6d4"),
                    CommunicationItem("feel_hot", "गर्मी", "मुझे गर्मी लग रही है", "feelings", "🥵", "गर्म", "#f97316"),
                    CommunicationItem("feel_scared", "डरा हुआ", "मुझे डर लग रहा है", "feelings", "😨", "चिंता", "#a855f7"),
                ],
            ),
            "people": CommunicationCategory(
                category_id="people",
                name="लोग (People)",
                icon="👥",
                accent_color="#8b5cf6",
                items=[
                    CommunicationItem("ppl_doctor", "डॉक्टर", "डॉक्टर", "people", "👨‍⚕️", "चिकित्सक", "#06b6d4"),
                    CommunicationItem("ppl_nurse", "नर्स", "नर्स", "people", "👩‍⚕️", "परिचारिका", "#ec4899"),
                    CommunicationItem("ppl_family", "परिवार", "परिवार", "people", "👨‍👩‍👧", "अपने लोग", "#f59e0b"),
                    CommunicationItem("ppl_friend", "दोस्त", "दोस्त", "people", "🤝", "मित्र", "#10b981"),
                    CommunicationItem("ppl_caregiver", "देखभालकर्ता", "देखभालकर्ता", "people", "🧑‍🦽", "सहायक", "#8b5cf6"),
                    CommunicationItem("ppl_assistant", "सहायक", "सहायक", "people", "💼", "मददगार", "#38bdf8"),
                    CommunicationItem("ppl_visitor", "आगंतुक", "आगंतुक", "people", "🚪", "मेहमान", "#14b8a6"),
                    CommunicationItem("ppl_everyone", "सभी लोग", "सभी लोग", "people", "👥", "सब", "#6366f1"),
                ],
            ),
            "places": CommunicationCategory(
                category_id="places",
                name="स्थान (Places)",
                icon="📍",
                accent_color="#10b981",
                items=[
                    CommunicationItem("plc_home", "घर", "घर", "places", "🏠", "मेरा घर", "#10b981"),
                    CommunicationItem("plc_hospital", "अस्पताल", "अस्पताल", "places", "🏥", "अस्पताल", "#ef4444"),
                    CommunicationItem("plc_outside", "बाहर", "बाहर", "places", "🌳", "बगीचा / बाहर", "#22c55e"),
                    CommunicationItem("plc_bedroom", "शयनकक्ष", "शयनकक्ष", "places", "🛏️", "सोने का कमरा", "#6366f1"),
                    CommunicationItem("plc_kitchen", "रसोई", "रसोई", "places", "🍽️", "भोजन कक्ष", "#f97316"),
                    CommunicationItem("plc_bathroom", "स्नानघर", "स्नानघर", "places", "🚿", "शौचालय", "#06b6d4"),
                    CommunicationItem("plc_livingroom", "बैठक", "बैठक", "places", "🛋️", "हॉल", "#f59e0b"),
                    CommunicationItem("plc_clinic", "क्लिनिक", "क्लिनिक", "places", "🩺", "डॉक्टर का कमरा", "#8b5cf6"),
                ],
            ),
            "actions": CommunicationCategory(
                category_id="actions",
                name="क्रियाएं (Actions)",
                icon="⚡",
                accent_color="#f59e0b",
                items=[
                    CommunicationItem("act_come", "यहाँ आओ", "यहाँ आओ", "actions", "👋", "पास बुलाएं", "#38bdf8"),
                    CommunicationItem("act_call", "कॉल करो", "किसी को बुलाओ", "actions", "📞", "फोन करो", "#22c55e"),
                    CommunicationItem("act_turn_on", "चालू करो", "चालू करो", "actions", "💡", "स्विच ऑन", "#eab308"),
                    CommunicationItem("act_turn_off", "बंद करो", "बंद करो", "actions", "🌑", "स्विच ऑफ", "#64748b"),
                    CommunicationItem("act_stop", "रुको", "रुको", "actions", "🛑", "कार्य रोकें", "#ef4444"),
                    CommunicationItem("act_look", "यहाँ देखो", "यहाँ देखो", "actions", "👀", "ध्यान दें", "#8b5cf6"),
                    CommunicationItem("act_wait", "प्रतीक्षा करो", "कृपया प्रतीक्षा करें", "actions", "⏳", "रुकें", "#06b6d4"),
                    CommunicationItem("act_open", "खोलो", "कृपया खोलो", "actions", "🔓", "दरवाजा खोलो", "#10b981"),
                ],
            ),
        }

    def _build_marathi_categories(self) -> Dict[str, CommunicationCategory]:
        return {
            "common": CommunicationCategory(
                category_id="common",
                name="सामान्य (Common)",
                icon="💬",
                accent_color="#38bdf8",
                items=[
                    CommunicationItem("comm_yes", "हो", "हो", "common", "✅", "संमती", "#22c55e"),
                    CommunicationItem("comm_no", "नाही", "नाही", "common", "❌", "असंमती", "#ef4444"),
                    CommunicationItem("comm_hello", "नमस्कार", "नमस्कार", "common", "👋", "अभिवादन", "#38bdf8"),
                    CommunicationItem("comm_thanks", "धन्यवाद", "धन्यवाद", "common", "🙏", "आभार", "#a855f7"),
                    CommunicationItem("comm_please", "कृपया", "कृपया", "common", "🤲", "नम्र विनंती", "#3b82f6"),
                    CommunicationItem("comm_help", "मदत", "मला मदत हवी आहे", "common", "🚨", "तातडीची मदत", "#f59e0b"),
                    CommunicationItem("comm_okay", "मी ठीक आहे", "मी ठीक आहे", "common", "👍", "स्थिती ठीक", "#10b981"),
                    CommunicationItem("comm_goodbye", "पुन्हा भेटू", "पुन्हा भेटू", "common", "👋", "निरोप", "#64748b"),
                ],
            ),
            "needs": CommunicationCategory(
                category_id="needs",
                name="गरजा (Needs)",
                icon="💧",
                accent_color="#06b6d4",
                items=[
                    CommunicationItem("need_water", "पाणी", "मला पाणी हवे आहे", "needs", "💧", "पाणी प्यायचे आहे", "#06b6d4"),
                    CommunicationItem("need_food", "जेवण", "मला जेवण हवे आहे", "needs", "🍲", "जेवायचे आहे", "#f97316"),
                    CommunicationItem("need_bathroom", "स्वच्छतागृह", "मला स्वच्छतागृहात जायचे आहे", "needs", "🚻", "टॉयलेट", "#8b5cf6"),
                    CommunicationItem("need_rest", "विश्रांती", "मला विश्रांती हवी आहे", "needs", "🛌", "झोपणे / विश्रांती", "#6366f1"),
                    CommunicationItem("need_glasses", "चष्मा", "मला माझा चष्मा हवा आहे", "needs", "👓", "चष्मा", "#14b8a6"),
                    CommunicationItem("need_medicine", "औषध", "मला माझे औषध हवे आहे", "needs", "💊", "औषधे", "#ec4899"),
                    CommunicationItem("need_blanket", "घोंगडी", "मला चादर/घोंगडी हवी आहे", "needs", "🧣", "थंडी वाजते", "#eab308"),
                    CommunicationItem("need_help", "साहाय्य", "मला साहाय्य हवे आहे", "needs", "🆘", "मदतनीस", "#ef4444"),
                ],
            ),
            "feelings": CommunicationCategory(
                category_id="feelings",
                name="भावना (Feelings)",
                icon="❤️",
                accent_color="#ec4899",
                items=[
                    CommunicationItem("feel_happy", "आनंदी", "मी आनंदी आहे", "feelings", "😄", "छान वाटते", "#eab308"),
                    CommunicationItem("feel_okay", "ठीक आहे", "मी ठीक आहे", "feelings", "😊", "सामान्य", "#10b981"),
                    CommunicationItem("feel_pain", "दुखत आहे", "मला खूप दुखत आहे", "feelings", "😣", "वेदना", "#ef4444"),
                    CommunicationItem("feel_tired", "थकलो आहे", "मी खूप थकलो आहे", "feelings", "🥱", "थकवा", "#64748b"),
                    CommunicationItem("feel_sad", "उदास", "मला वाईट वाटत आहे", "feelings", "😢", "उदास", "#3b82f6"),
                    CommunicationItem("feel_cold", "थंडी", "मला थंडी वाजते आहे", "feelings", "🥶", "गारठा", "#06b6d4"),
                    CommunicationItem("feel_hot", "गरम", "मला गरम होत आहे", "feelings", "🥵", "उकाडा", "#f97316"),
                    CommunicationItem("feel_scared", "भीती", "मला भीती वाटते आहे", "feelings", "😨", "काळजी", "#a855f7"),
                ],
            ),
            "people": CommunicationCategory(
                category_id="people",
                name="व्यक्ती (People)",
                icon="👥",
                accent_color="#8b5cf6",
                items=[
                    CommunicationItem("ppl_doctor", "डॉक्टर", "डॉक्टर", "people", "👨‍⚕️", "वैद्यकीय डॉक्टर", "#06b6d4"),
                    CommunicationItem("ppl_nurse", "परिचारिका", "परिचारिका", "people", "👩‍⚕️", "नर्स", "#ec4899"),
                    CommunicationItem("ppl_family", "कुटुंब", "कुटुंब", "people", "👨‍👩‍👧", "घरचे लोक", "#f59e0b"),
                    CommunicationItem("ppl_friend", "मित्र", "मित्र", "people", "🤝", "सोबती", "#10b981"),
                    CommunicationItem("ppl_caregiver", "देखभालदार", "देखभालदार", "people", "🧑‍🦽", "मदतनीस", "#8b5cf6"),
                    CommunicationItem("ppl_assistant", "सहायक", "सहायक", "people", "💼", "मदतीसाठी", "#38bdf8"),
                    CommunicationItem("ppl_visitor", "पाहुणे", "पाहुणे", "people", "🚪", "भेटणारे", "#14b8a6"),
                    CommunicationItem("ppl_everyone", "सर्वजण", "सर्वजण", "people", "👥", "सगळे", "#6366f1"),
                ],
            ),
            "places": CommunicationCategory(
                category_id="places",
                name="ठिकाणे (Places)",
                icon="📍",
                accent_color="#10b981",
                items=[
                    CommunicationItem("plc_home", "घर", "घर", "places", "🏠", "माझे घर", "#10b981"),
                    CommunicationItem("plc_hospital", "रुग्णालय", "रुग्णालय", "places", "🏥", "हॉस्पिटल", "#ef4444"),
                    CommunicationItem("plc_outside", "बाहेर", "बाहेर", "places", "🌳", "बागेत / बाहेर", "#22c55e"),
                    CommunicationItem("plc_bedroom", "बेडरूम", "बेडरूम", "places", "🛏️", "झोपण्याची खोली", "#6366f1"),
                    CommunicationItem("plc_kitchen", "स्वयंपाकघर", "स्वयंपाकघर", "places", "🍽️", "जेवणाची जागा", "#f97316"),
                    CommunicationItem("plc_bathroom", "बाथरूम", "बाथरूम", "places", "🚿", "शौचालय", "#06b6d4"),
                    CommunicationItem("plc_livingroom", "दिवाणखाना", "दिवाणखाना", "places", "🛋️", "हॉल", "#f59e0b"),
                    CommunicationItem("plc_clinic", "दवाखाना", "दवाखाना", "places", "🩺", "क्लिनिक", "#8b5cf6"),
                ],
            ),
            "actions": CommunicationCategory(
                category_id="actions",
                name="कृती (Actions)",
                icon="⚡",
                accent_color="#f59e0b",
                items=[
                    CommunicationItem("act_come", "इथे या", "इथे या", "actions", "👋", "जवळ बोलावणे", "#38bdf8"),
                    CommunicationItem("act_call", "फोन करा", "कोणालातरी बोलवा", "actions", "📞", "कॉल करा", "#22c55e"),
                    CommunicationItem("act_turn_on", "सुरू करा", "सुरू करा", "actions", "💡", "स्विच ऑन", "#eab308"),
                    CommunicationItem("act_turn_off", "बंद करा", "बंद करा", "actions", "🌑", "स्विच ऑफ", "#64748b"),
                    CommunicationItem("act_stop", "थांबा", "थांबा", "actions", "🛑", "थांबवा", "#ef4444"),
                    CommunicationItem("act_look", "इथे पहा", "इथे पहा", "actions", "👀", "लक्ष द्या", "#8b5cf6"),
                    CommunicationItem("act_wait", "वाट पहा", "कृपया थोडी वाट पहा", "actions", "⏳", "थांबा जरा", "#06b6d4"),
                    CommunicationItem("act_open", "उघडा", "कृपया उघडा", "actions", "🔓", "दरवाजा उघडा", "#10b981"),
                ],
            ),
        }

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
