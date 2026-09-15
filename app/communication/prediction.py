"""Next-word and quick phrase prediction helper for AAC communication."""

from typing import Dict, List


class PhrasePredictor:
    """Predicts relevant completion phrases based on active tokens and frequency."""

    COMMON_FOLLOWUPS: Dict[str, List[str]] = {
        "I need": ["water", "food", "help", "rest", "the bathroom", "my glasses"],
        "I want": ["to rest", "to go outside", "to speak", "to eat"],
        "I am": ["okay", "tired", "in pain", "happy", "cold", "hot"],
        "Please": ["help me", "call someone", "come here", "wait"],
    }

    def predict_next(self, current_sentence: str) -> List[str]:
        cleaned = current_sentence.strip()
        for prefix, suggestions in self.COMMON_FOLLOWUPS.items():
            if cleaned.endswith(prefix) or cleaned == prefix:
                return suggestions
        return []
