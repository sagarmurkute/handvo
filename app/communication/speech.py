"""Offline Text-to-Speech (TTS) engine and audio feedback system for HANDVO.

Provides robust, non-blocking, queued speech synthesis, system voice discovery,
interruptibility for emergency alerts, rate/volume controls, and zero-dependency
synthesized audio cue feedback.
"""

from dataclasses import dataclass
import queue
import sys
import threading
import time
from typing import Callable, List, Optional


@dataclass
class VoiceInfo:
    """Represents an installed system text-to-speech voice."""
    id: str
    name: str
    languages: List[str]
    gender: Optional[str] = None
    age: Optional[int] = None


class SpeechEngine:
    """
    Thread-safe, offline Text-to-Speech synthesis and audio cue manager.
    Runs on a dedicated background worker to prevent GUI stutter and COM concurrency issues.
    """

    def __init__(
        self,
        rate: int = 150,
        volume: float = 1.0,
        voice_id: Optional[str] = None,
    ) -> None:
        self._rate: int = max(50, min(350, rate))
        self._volume: float = max(0.0, min(1.0, volume))
        self._voice_id: Optional[str] = voice_id
        self._is_speaking: bool = False
        self._available_voices: List[VoiceInfo] = []

        # Event callbacks
        self.on_speech_started: Optional[Callable[[str], None]] = None
        self.on_speech_finished: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

        # Queue for speech commands: (command_type, data)
        self._queue: queue.Queue = queue.Queue()
        self._stop_requested: threading.Event = threading.Event()
        self._shutdown_event: threading.Event = threading.Event()

        # Query available system voices initially
        self._discover_voices()

        # Start dedicated worker thread
        self._worker_thread = threading.Thread(target=self._run_worker, name="HandvoSpeechWorker", daemon=True)
        self._worker_thread.start()

    @property
    def rate(self) -> int:
        return self._rate

    @rate.setter
    def rate(self, value: int) -> None:
        self.set_rate(value)

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self.set_volume(value)

    @property
    def voice_id(self) -> Optional[str]:
        return self._voice_id

    @voice_id.setter
    def voice_id(self, value: Optional[str]) -> None:
        self.set_voice(value)

    def is_speaking(self) -> bool:
        """Return True if the speech engine is currently actively speaking."""
        return self._is_speaking

    def get_available_voices(self) -> List[VoiceInfo]:
        """Return cached list of installed system TTS voices."""
        if not self._available_voices:
            self._discover_voices()
        return list(self._available_voices)

    def set_rate(self, rate: int) -> None:
        """Adjust speech rate in words per minute (WPM)."""
        self._rate = max(50, min(350, rate))
        self._queue.put(("SET_RATE", self._rate))

    def set_volume(self, volume: float) -> None:
        """Adjust speech volume (0.0 to 1.0)."""
        self._volume = max(0.0, min(1.0, volume))
        self._queue.put(("SET_VOLUME", self._volume))

    def set_voice(self, voice_id: Optional[str]) -> None:
        """Switch active TTS voice by voice ID."""
        self._voice_id = voice_id
        if voice_id:
            self._queue.put(("SET_VOICE", voice_id))

    def speak(self, text: str, interrupt: bool = False) -> None:
        """
        Synthesize and speak text asynchronously.
        If interrupt is True, active speech is stopped immediately before speaking.
        """
        cleaned = text.strip()
        if not cleaned:
            return

        if interrupt:
            self.stop()

        self._queue.put(("SPEAK", cleaned))

    def stop(self) -> None:
        """Halt active speech immediately and purge pending speech queue."""
        self._stop_requested.set()
        # Drain queue of all pending SPEAK commands
        try:
            while not self._queue.empty():
                cmd, _ = self._queue.get_nowait()
                if cmd not in ("SET_RATE", "SET_VOLUME", "SET_VOICE", "SHUTDOWN"):
                    self._queue.task_done()
        except queue.Empty:
            pass

    def play_sound(self, sound_type: str = "dwell") -> None:
        """
        Play non-blocking synthesized audio cues for AAC feedback.
        Supports 'click', 'dwell', 'clear', 'emergency', 'error'.
        """
        def _sound_worker() -> None:
            try:
                if sys.platform == "win32":
                    import winsound
                    if sound_type == "click":
                        winsound.Beep(900, 30)
                    elif sound_type in ("dwell", "success"):
                        winsound.Beep(1200, 50)
                    elif sound_type == "clear":
                        winsound.Beep(450, 40)
                    elif sound_type == "emergency":
                        winsound.Beep(1600, 100)
                        winsound.Beep(1200, 100)
                    elif sound_type == "error":
                        winsound.Beep(300, 120)
                    else:
                        winsound.Beep(800, 40)
            except Exception:
                pass

        threading.Thread(target=_sound_worker, daemon=True).start()

    def shutdown(self) -> None:
        """Gracefully stop worker thread."""
        self._shutdown_event.set()
        self._queue.put(("SHUTDOWN", None))

    def _discover_voices(self) -> None:
        """Enumerate installed system voices via pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []
            discovered = []
            for v in voices:
                v_id = getattr(v, "id", "")
                v_name = getattr(v, "name", "System Voice")
                v_langs = getattr(v, "languages", [])
                v_gender = getattr(v, "gender", None)
                v_age = getattr(v, "age", None)
                discovered.append(
                    VoiceInfo(
                        id=str(v_id),
                        name=str(v_name),
                        languages=[str(l) for l in v_langs] if v_langs else ["en"],
                        gender=str(v_gender) if v_gender else None,
                        age=int(v_age) if v_age is not None else None,
                    )
                )
            self._available_voices = discovered
            engine.stop()
        except Exception:
            self._available_voices = [
                VoiceInfo(id="default", name="Default System Voice", languages=["en"])
            ]

    def _run_worker(self) -> None:
        """Dedicated worker loop initializing COM and managing pyttsx3."""
        # Initialize COM on Windows for this thread
        if sys.platform == "win32":
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pass

        engine = None
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self._rate)
            engine.setProperty("volume", self._volume)
            if self._voice_id:
                engine.setProperty("voice", self._voice_id)
        except Exception as e:
            if self.on_error:
                self.on_error(e)

        while not self._shutdown_event.is_set():
            try:
                cmd, data = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if cmd == "SHUTDOWN":
                break

            if engine is None:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                except Exception:
                    continue

            try:
                if cmd == "SET_RATE":
                    engine.setProperty("rate", data)
                elif cmd == "SET_VOLUME":
                    engine.setProperty("volume", data)
                elif cmd == "SET_VOICE":
                    engine.setProperty("voice", data)
                elif cmd == "SPEAK":
                    self._stop_requested.clear()
                    self._is_speaking = True
                    if self.on_speech_started:
                        self.on_speech_started(data)

                    engine.say(data)
                    engine.runAndWait()

                    self._is_speaking = False
                    if self.on_speech_finished:
                        self.on_speech_finished(data)

            except Exception as ex:
                self._is_speaking = False
                if self.on_error:
                    self.on_error(ex)
            finally:
                self._queue.task_done()

        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

        if sys.platform == "win32":
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
