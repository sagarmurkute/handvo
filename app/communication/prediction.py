"""100% Offline Smart Prediction Engine for HANDVO.

Predicts next words/phrases using n-gram grammar models, active category context,
and SQLite-backed user frequency learning.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from app.database.database import Database
from app.database.profile_repository import ProfileRepository


@dataclass
class PredictionCandidate:
    """Represents a predicted phrase suggestion chip."""
    text: str
    label: str
    icon: str = "💡"
    accent_color: str = "#38bdf8"
    score: float = 1.0


class SmartPredictionEngine:
    """
    Offline statistical and contextual prediction engine that learns
    from user selection history over time.
    """

    # Pre-seeded linguistic collocations and AAC communication transition maps
    PREFIX_MAP: Dict[str, List[Tuple[str, str, str]]] = {
        "": [
            ("Yes", "✅", "#22c55e"),
            ("No", "❌", "#ef4444"),
            ("Hello", "👋", "#38bdf8"),
            ("Thank you", "🙏", "#a855f7"),
            ("I need help", "🚨", "#f59e0b"),
            ("I am okay", "👍", "#10b981"),
        ],
        "i need": [
            ("water", "💧", "#06b6d4"),
            ("food", "🍲", "#f97316"),
            ("the bathroom", "🚻", "#8b5cf6"),
            ("rest", "🛌", "#6366f1"),
            ("medicine", "💊", "#ec4899"),
            ("my glasses", "👓", "#14b8a6"),
            ("help", "🆘", "#ef4444"),
        ],
        "need": [
            ("water", "💧", "#06b6d4"),
            ("food", "🍲", "#f97316"),
            ("the bathroom", "🚻", "#8b5cf6"),
            ("rest", "🛌", "#6366f1"),
            ("assistance", "🆘", "#ef4444"),
        ],
        "i want": [
            ("to rest", "🛌", "#6366f1"),
            ("to eat", "🍽️", "#f97316"),
            ("water", "💧", "#06b6d4"),
            ("to go outside", "🌳", "#22c55e"),
            ("to sleep", "🛏️", "#8b5cf6"),
        ],
        "want": [
            ("water", "💧", "#06b6d4"),
            ("food", "🍲", "#f97316"),
            ("to rest", "🛌", "#6366f1"),
            ("to speak", "💬", "#38bdf8"),
        ],
        "i am": [
            ("okay", "😊", "#10b981"),
            ("in pain", "😣", "#ef4444"),
            ("tired", "🥱", "#64748b"),
            ("happy", "😄", "#eab308"),
            ("cold", "🥶", "#06b6d4"),
            ("hot", "🥵", "#f97316"),
            ("sad", "😢", "#3b82f6"),
        ],
        "feel": [
            ("okay", "😊", "#10b981"),
            ("pain", "😣", "#ef4444"),
            ("tired", "🥱", "#64748b"),
            ("happy", "😄", "#eab308"),
            ("cold", "🥶", "#06b6d4"),
        ],
        "please": [
            ("help me", "🚨", "#f59e0b"),
            ("come here", "👋", "#38bdf8"),
            ("call someone", "📞", "#22c55e"),
            ("wait", "⏳", "#06b6d4"),
            ("open", "🔓", "#10b981"),
        ],
        "doctor": [
            ("help me", "🚨", "#f59e0b"),
            ("I am in pain", "😣", "#ef4444"),
            ("medicine", "💊", "#ec4899"),
        ],
        "nurse": [
            ("water", "💧", "#06b6d4"),
            ("medicine", "💊", "#ec4899"),
            ("bathroom", "🚻", "#8b5cf6"),
        ],
    }

    # Category defaults fallback
    CATEGORY_DEFAULTS: Dict[str, List[Tuple[str, str, str]]] = {
        "common": [
            ("Yes", "✅", "#22c55e"),
            ("No", "❌", "#ef4444"),
            ("Hello", "👋", "#38bdf8"),
            ("Thank you", "🙏", "#a855f7"),
            ("Please", "🤲", "#3b82f6"),
        ],
        "needs": [
            ("I need water", "💧", "#06b6d4"),
            ("I need food", "🍲", "#f97316"),
            ("I need the bathroom", "🚻", "#8b5cf6"),
            ("I want to rest", "🛌", "#6366f1"),
        ],
        "feelings": [
            ("I am okay", "😊", "#10b981"),
            ("I am in pain", "😣", "#ef4444"),
            ("I am tired", "🥱", "#64748b"),
            ("I am happy", "😄", "#eab308"),
        ],
        "people": [
            ("Doctor", "👨‍⚕️", "#06b6d4"),
            ("Nurse", "👩‍⚕️", "#ec4899"),
            ("Family", "👨‍👩‍👧", "#f59e0b"),
            ("Caregiver", "🧑‍🦽", "#8b5cf6"),
        ],
        "places": [
            ("Home", "🏠", "#10b981"),
            ("Hospital", "🏥", "#ef4444"),
            ("Outside", "🌳", "#22c55e"),
            ("Bathroom", "🚿", "#06b6d4"),
        ],
        "actions": [
            ("Come here", "👋", "#38bdf8"),
            ("Call someone", "📞", "#22c55e"),
            ("Turn on", "💡", "#eab308"),
            ("Stop", "🛑", "#ef4444"),
        ],
    }

    def __init__(self, repository: Optional[ProfileRepository] = None) -> None:
        self.repo = repository or ProfileRepository(Database())

    def get_predictions(
        self,
        current_sentence: str,
        active_category_id: str = "common",
        limit: int = 5,
    ) -> List[PredictionCandidate]:
        """
        Generate top 3–5 contextual suggestions by combining n-grams,
        category priors, and SQLite-learned user frequencies.
        """
        raw_text = current_sentence.strip()
        lower_text = raw_text.lower()
        candidates_dict: Dict[str, PredictionCandidate] = {}

        # 1. Suffix Prefix and N-gram Matching
        matched_prefix = ""
        matched_items: List[Tuple[str, str, str]] = []

        if not lower_text:
            matched_prefix = ""
            if active_category_id == "common":
                matched_items = self.PREFIX_MAP.get("", [])
        else:
            for prefix, items in self.PREFIX_MAP.items():
                if prefix and (lower_text == prefix or lower_text.endswith(" " + prefix)):
                    matched_prefix = prefix
                    matched_items = items
                    break

            if not matched_items and " " in lower_text:
                last_word = lower_text.split()[-1]
                if last_word in self.PREFIX_MAP:
                    matched_prefix = last_word
                    matched_items = self.PREFIX_MAP[last_word]

        for text, icon, color in matched_items:
            candidates_dict[text] = PredictionCandidate(
                text=text,
                label=f"{icon} {text}",
                icon=icon,
                accent_color=color,
                score=25.0,
            )

        # 2. Query SQLite Learned Frequencies for this prefix
        try:
            freq_rows = self.repo.get_top_predictions(matched_prefix, limit=limit)
            for next_tok, freq in freq_rows:
                if next_tok in candidates_dict:
                    candidates_dict[next_tok].score += freq * 10.0
                else:
                    candidates_dict[next_tok] = PredictionCandidate(
                        text=next_tok,
                        label=f"⭐ {next_tok}",
                        icon="⭐",
                        accent_color="#38bdf8",
                        score=20.0 + freq * 10.0,
                    )
        except Exception:
            pass

        # 3. Category Context Priors
        cat_items = self.CATEGORY_DEFAULTS.get(active_category_id, self.CATEGORY_DEFAULTS["common"])
        cat_score = 25.0 if not lower_text and active_category_id != "common" else 5.0
        for text, icon, color in cat_items:
            if text not in candidates_dict:
                candidates_dict[text] = PredictionCandidate(
                    text=text,
                    label=f"{icon} {text}",
                    icon=icon,
                    accent_color=color,
                    score=cat_score,
                )
            else:
                if not lower_text and active_category_id != "common":
                    candidates_dict[text].score = max(candidates_dict[text].score, cat_score)

        # Fallback to general common items if we still don't have enough candidates
        if len(candidates_dict) < limit:
            for text, icon, color in self.PREFIX_MAP.get("", []):
                if text not in candidates_dict:
                    candidates_dict[text] = PredictionCandidate(
                        text=text,
                        label=f"{icon} {text}",
                        icon=icon,
                        accent_color=color,
                        score=2.0,
                    )

        # Sort by score descending and return top `limit`
        sorted_candidates = sorted(candidates_dict.values(), key=lambda c: c.score, reverse=True)
        return sorted_candidates[:limit]

    def learn_selection(
        self,
        prev_sentence: str,
        selected_phrase: str,
        category_id: str = "common",
    ) -> None:
        """Record selection pair into SQLite to adaptively boost future rankings."""
        lower = prev_sentence.strip().lower()
        prefix = ""
        for p in self.PREFIX_MAP.keys():
            if p and (lower == p or lower.endswith(" " + p)):
                prefix = p
                break
        if not prefix and lower:
            prefix = lower.split()[-1]

        try:
            self.repo.record_phrase_usage(prefix, selected_phrase, category_id)
        except Exception:
            pass


PhrasePredictor = SmartPredictionEngine
