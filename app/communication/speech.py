"""Offline Text-to-Speech engine using pyttsx3."""

import threading
from typing import Optional


class SpeechEngine:
    """Provides non-blocking, offline text-to-speech synthesis."""

    def __init__(self, rate: int = 150, volume: float = 1.0) -> None:
        self.rate = rate
        self.volume = volume
        self._engine = None
        self._init_engine()

    def _init_engine(self) -> None:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)
        except Exception:
            self._engine = None

    def speak(self, text: str) -> None:
        """Speak text in a non-blocking background thread."""
        if not text.strip():
            return

        def _worker() -> None:
            try:
                import pyttsx3
                local_engine = pyttsx3.init()
                local_engine.setProperty("rate", self.rate)
                local_engine.setProperty("volume", self.volume)
                local_engine.say(text)
                local_engine.runAndWait()
                local_engine.stop()
            except Exception:
                pass

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
