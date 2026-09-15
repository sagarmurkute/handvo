"""Sentence buffer and token composition for AAC communication."""

from typing import Callable, List


class SentenceBuilder:
    """Manages active phrase composition, space insertion, and token backspacing."""

    def __init__(self) -> None:
        self._tokens: List[str] = []
        self._listeners: List[Callable[[str], None]] = []

    @property
    def text(self) -> str:
        return " ".join(t for t in self._tokens if t).strip()

    @property
    def tokens(self) -> List[str]:
        return list(self._tokens)

    def add_token(self, token: str) -> None:
        if token:
            self._tokens.append(token.strip())
            self._notify()

    def add_space(self) -> None:
        self._tokens.append("")
        self._notify()

    def delete_last(self) -> bool:
        if self._tokens:
            self._tokens.pop()
            self._notify()
            return True
        return False

    def clear(self) -> None:
        if self._tokens:
            self._tokens.clear()
            self._notify()

    def on_change(self, callback: Callable[[str], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        t = self.text
        for cb in self._listeners:
            try:
                cb(t)
            except Exception:
                pass
