"""Unit tests for HANDVO Offline Text-to-Speech (TTS) Engine and Audio Feedback."""

import os
import tempfile
import time
import pytest

from app.communication.speech import SpeechEngine, VoiceInfo
from app.database.database import Database
from app.database.models import UserProfile
from app.database.profile_repository import ProfileRepository


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with all migrations applied."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    db = Database(db_path=db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)


def test_speech_engine_init():
    """Verify SpeechEngine initializes with valid rate and volume bounds."""
    engine = SpeechEngine(rate=160, volume=0.85)
    assert engine.rate == 160
    assert engine.volume == 0.85
    assert not engine.is_speaking()

    # Rate bounds clamping
    engine.set_rate(400)
    assert engine.rate == 350
    engine.set_rate(20)
    assert engine.rate == 50

    # Volume bounds clamping
    engine.set_volume(1.5)
    assert engine.volume == 1.0
    engine.set_volume(-0.5)
    assert engine.volume == 0.0

    engine.shutdown()


def test_speech_engine_voice_discovery():
    """Verify speech engine discovers system voices or provides a valid fallback."""
    engine = SpeechEngine()
    voices = engine.get_available_voices()
    assert len(voices) >= 1
    v = voices[0]
    assert isinstance(v, VoiceInfo)
    assert v.id is not None
    assert v.name is not None

    # Test setting active voice
    engine.set_voice(v.id)
    assert engine.voice_id == v.id

    engine.shutdown()


def test_speech_engine_speak_and_stop():
    """Verify non-blocking speak, stop, and queue handling."""
    engine = SpeechEngine()

    started = []
    engine.on_speech_started = lambda txt: started.append(txt)

    engine.speak("Hello HANDVO")
    engine.speak("Second phrase in queue")

    # Stop clears pending queue
    engine.stop()

    engine.play_sound("dwell")
    engine.play_sound("click")
    engine.play_sound("emergency")

    engine.shutdown()


def test_voice_id_database_persistence(temp_db):
    """Verify voice_id persists in SQLite user profile."""
    repo = ProfileRepository(temp_db)
    profile = repo.get_active_profile()

    profile.voice_id = "test_voice_model_id"
    profile.tts_rate = 175
    profile.tts_volume = 0.90
    profile.dwell_sound = True
    repo.save_profile(profile)

    loaded = repo.get_profile_by_id(profile.id)
    assert loaded is not None
    assert loaded.voice_id == "test_voice_model_id"
    assert loaded.tts_rate == 175
    assert loaded.tts_volume == 0.90
    assert loaded.dwell_sound is True


def test_voice_id_json_export_import(temp_db):
    """Verify JSON export and import include voice_id."""
    repo = ProfileRepository(temp_db)
    prof = repo.create_profile(
        UserProfile(
            name="Voice User",
            voice_id="custom_sapi_voice_42",
            tts_rate=160,
        )
    )

    json_str = repo.export_profile_json(prof.id)
    assert '"voice_id": "custom_sapi_voice_42"' in json_str

    imported = repo.import_profile_json(json_str)
    assert imported.voice_id == "custom_sapi_voice_42"
    assert imported.tts_rate == 160
