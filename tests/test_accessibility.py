"""Unit tests for HANDVO Accessibility & Personalization Backend Models."""

import os
import tempfile
import pytest

from app.communication.communication_board import CommunicationBoardModel
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


def test_profile_accessibility_fields_persistence(temp_db):
    """Verify that all new accessibility settings persist in SQLite database."""
    repo = ProfileRepository(temp_db)
    profile = repo.get_active_profile()

    # Modify all accessibility settings
    profile.dwell_time = 1.40
    profile.cooldown_time = 0.85
    profile.cursor_size = "large"
    profile.cursor_color = "#f43f5e"
    profile.theme = "light"
    profile.high_contrast = False
    profile.reduced_motion = True
    profile.button_size = "large"
    profile.smoothing_strength = 0.85
    profile.pinch_threshold = 0.04
    profile.speech_rate = 140
    profile.speech_volume = 0.80
    profile.language = "hi"
    profile.dominant_hand = "left"

    repo.save_profile(profile)

    # Reload profile from database
    loaded = repo.get_profile_by_id(profile.id)
    assert loaded is not None
    assert loaded.dwell_time == 1.40
    assert loaded.cooldown_time == 0.85
    assert loaded.cursor_size == "large"
    assert loaded.cursor_color == "#f43f5e"
    assert loaded.theme == "light"
    assert loaded.high_contrast is False
    assert loaded.reduced_motion is True
    assert loaded.button_size == "large"
    assert loaded.smoothing_strength == 0.85
    assert loaded.pinch_threshold == 0.04
    assert loaded.speech_rate == 140
    assert loaded.speech_volume == 0.80
    assert loaded.language == "hi"
    assert loaded.dominant_hand == "left"


def test_profile_export_import_with_accessibility(temp_db):
    """Verify JSON export and import faithfully maintain accessibility settings."""
    repo = ProfileRepository(temp_db)
    new_prof = UserProfile(
        name="Custom Access User",
        cursor_size=24,
        cursor_color="#eab308",
        theme="high_contrast",
        reduced_motion=True,
        language="mr",
    )
    profile = repo.create_profile(new_prof)

    json_str = repo.export_profile_json(profile.id)
    assert '"cursor_size": 24' in json_str or '"cursor_size": "24"' in json_str or '"cursor_size": "large"' in json_str or '"cursor_size": 24' in json_str
    assert '"cursor_color": "#eab308"' in json_str
    assert '"theme": "high_contrast"' in json_str
    assert '"reduced_motion": true' in json_str
    assert '"language": "mr"' in json_str

    imported = repo.import_profile_json(json_str)
    assert "Custom Access User" in imported.name
    assert imported.cursor_color == "#eab308"
    assert imported.theme == "high_contrast"
    assert imported.reduced_motion is True
    assert imported.language == "mr"


def test_multilingual_aac_vocabularies():
    """Verify AAC categories and items switch properly between English, Hindi, and Marathi."""
    model = CommunicationBoardModel()

    # English
    model.set_language("en")
    en_categories = model.get_categories()
    assert len(en_categories) >= 6
    needs_cat = [c for c in en_categories if c.category_id == "needs"][0]
    assert "Needs" in needs_cat.name
    assert any(item.label == "Water" for item in needs_cat.items)

    # Hindi
    model.set_language("hi")
    hi_categories = model.get_categories()
    assert len(hi_categories) >= 6
    hi_needs_cat = [c for c in hi_categories if c.category_id == "needs"][0]
    assert "ज़रूरतें" in hi_needs_cat.name
    assert any("पानी" in item.label for item in hi_needs_cat.items)

    # Marathi
    model.set_language("mr")
    mr_categories = model.get_categories()
    assert len(mr_categories) >= 6
    mr_needs_cat = [c for c in mr_categories if c.category_id == "needs"][0]
    assert "गरजा" in mr_needs_cat.name
    assert any("पाणी" in item.label for item in mr_needs_cat.items)
