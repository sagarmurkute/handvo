"""Dedicated Accessibility & Personalization Settings Dialog for HANDVO.

Provides live tuning for dwell timings, cursor appearance, theme mode, high contrast,
sound feedback, speech synthesis speed/volume, multilingual AAC vocabularies, and reduced motion.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.communication.speech import SpeechEngine
from app.database.models import UserProfile
from app.database.profile_repository import ProfileRepository


class AccessibilityDialog(QDialog):
    """
    Full-featured Accessibility & Personalization Settings experience.
    Automatically persists settings to SQLite and notifies live application listeners.
    """

    settings_updated = Signal(UserProfile)
    settings_changed = settings_updated

    def __init__(
        self,
        profile: UserProfile,
        repository: ProfileRepository,
        speech_engine: Optional[SpeechEngine] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.repo = repository
        self.speech_engine = speech_engine or SpeechEngine(rate=profile.tts_rate, volume=profile.tts_volume)
        self._cursor_color = self.profile.cursor_color or "#38bdf8"

        self.setWindowTitle("Accessibility & Personalization Settings — HANDVO")
        self.resize(760, 580)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            """
            QDialog { background-color: #0b0f19; color: #f8fafc; }
            QTabWidget::pane { border: 1px solid #1e293b; background-color: #0f172a; border-radius: 8px; }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 13px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected { background-color: #0284c7; color: #ffffff; }
            QFrame#cardGroup {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel { color: #cbd5e1; font-size: 13px; }
            QLabel#sectionHeader { color: #38bdf8; font-size: 14px; font-weight: bold; }
            QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 6px 10px;
                font-size: 13px;
            }
            QSlider::groove:horizontal { height: 6px; background: #1e293b; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #0284c7; border-radius: 3px; }
            QSlider::handle:horizontal {
                background: #38bdf8;
                border: 2px solid #0284c7;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QCheckBox, QRadioButton { color: #e2e8f0; font-size: 13px; }
            QPushButton {
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                border: none;
            }
            QPushButton#btnPrimary { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnPrimary:hover { background-color: #0369a1; }
            QPushButton#btnSecondary { background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; }
            QPushButton#btnSecondary:hover { background-color: #334155; }
            QPushButton#btnReset { background-color: #334155; color: #cbd5e1; }
            QPushButton#btnReset:hover { background-color: #475569; }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # Header
        header = QVBoxLayout()
        lbl_title = QLabel("⚙️ Accessibility & Personalization Suite")
        lbl_title.setStyleSheet("color: #38bdf8; font-size: 20px; font-weight: bold;")
        lbl_sub = QLabel(f"Personalizing settings for: {self.profile.name} (Changes apply live and save automatically)")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        header.addWidget(lbl_title)
        header.addWidget(lbl_sub)
        root.addLayout(header)

        # Tab Widget
        tabs = QTabWidget()

        # -------------------------------------------------------------
        # Tab 1: 🎯 Interaction & Dwell Control
        # -------------------------------------------------------------
        tab_interact = QWidget()
        layout_interact = QVBoxLayout(tab_interact)
        layout_interact.setContentsMargins(14, 14, 14, 14)
        layout_interact.setSpacing(12)

        card_interact = QFrame()
        card_interact.setObjectName("cardGroup")
        grid_i = QGridLayout(card_interact)
        grid_i.setSpacing(12)

        # Dwell Duration
        grid_i.addWidget(QLabel("Dwell Duration (seconds):"), 0, 0)
        self.slider_dwell = QSlider(Qt.Orientation.Horizontal)
        self.slider_dwell.setRange(30, 300)  # 0.30s - 3.00s
        self.slider_dwell.setValue(int(self.profile.dwell_time * 100))
        self.lbl_dwell_val = QLabel(f"{self.profile.dwell_time:.2f}s")
        self.lbl_dwell_val.setFixedWidth(50)
        self.slider_dwell.valueChanged.connect(self._on_dwell_slider_changed)
        grid_i.addWidget(self.slider_dwell, 0, 1)
        grid_i.addWidget(self.lbl_dwell_val, 0, 2)

        # Cooldown Time
        grid_i.addWidget(QLabel("Cooldown Duration (seconds):"), 1, 0)
        self.slider_cooldown = QSlider(Qt.Orientation.Horizontal)
        self.slider_cooldown.setRange(20, 200)  # 0.20s - 2.00s
        self.slider_cooldown.setValue(int(self.profile.cooldown_time * 100))
        self.lbl_cooldown_val = QLabel(f"{self.profile.cooldown_time:.2f}s")
        self.lbl_cooldown_val.setFixedWidth(50)
        self.slider_cooldown.valueChanged.connect(self._on_cooldown_slider_changed)
        grid_i.addWidget(self.slider_cooldown, 1, 1)
        grid_i.addWidget(self.lbl_cooldown_val, 1, 2)

        # Smoothing Strength
        grid_i.addWidget(QLabel("Cursor Smoothing Strength:"), 2, 0)
        self.slider_smooth = QSlider(Qt.Orientation.Horizontal)
        self.slider_smooth.setRange(5, 30)  # 0.5 - 3.0
        self.slider_smooth.setValue(int(self.profile.smoothing_factor * 10))
        self.lbl_smooth_val = QLabel(f"{self.profile.smoothing_factor:.1f}x")
        self.lbl_smooth_val.setFixedWidth(50)
        self.slider_smooth.valueChanged.connect(self._on_smooth_slider_changed)
        grid_i.addWidget(self.slider_smooth, 2, 1)
        grid_i.addWidget(self.lbl_smooth_val, 2, 2)

        # Dominant Hand
        grid_i.addWidget(QLabel("Dominant Hand:"), 3, 0)
        self.combo_hand = QComboBox()
        self.combo_hand.addItems(["Right", "Left"])
        self.combo_hand.setCurrentText(self.profile.dominant_hand)
        self.combo_hand.currentTextChanged.connect(self._on_hand_changed)
        grid_i.addWidget(self.combo_hand, 3, 1)

        layout_interact.addWidget(card_interact)
        layout_interact.addStretch()
        tabs.addTab(tab_interact, "🎯 Interaction & Dwell")

        # -------------------------------------------------------------
        # Tab 2: 👁️ Visuals, Cursor & Themes
        # -------------------------------------------------------------
        tab_visuals = QWidget()
        layout_visuals = QVBoxLayout(tab_visuals)
        layout_visuals.setContentsMargins(14, 14, 14, 14)
        layout_visuals.setSpacing(12)

        card_v = QFrame()
        card_v.setObjectName("cardGroup")
        grid_v = QGridLayout(card_v)
        grid_v.setSpacing(12)

        # Cursor Size
        grid_v.addWidget(QLabel("Cursor Size:"), 0, 0)
        self.slider_csize = QSlider(Qt.Orientation.Horizontal)
        self.slider_csize.setRange(10, 32)
        self.slider_csize.setValue(self.profile.cursor_size)
        self.lbl_csize_val = QLabel(f"{self.profile.cursor_size}px")
        self.lbl_csize_val.setFixedWidth(50)
        self.slider_csize.valueChanged.connect(self._on_csize_changed)
        grid_v.addWidget(self.slider_csize, 0, 1)
        grid_v.addWidget(self.lbl_csize_val, 0, 2)

        # Cursor Color
        grid_v.addWidget(QLabel("Cursor Color:"), 1, 0)
        color_row = QHBoxLayout()
        color_row.setSpacing(6)

        self.btn_color_pick = QPushButton("🎨 Pick Color")
        self.btn_color_pick.setObjectName("btnSecondary")
        self.btn_color_pick.clicked.connect(self._choose_color)
        color_row.addWidget(self.btn_color_pick)

        # Preset Color chips
        for c in ["#38bdf8", "#22c55e", "#f59e0b", "#ec4899", "#ffffff", "#ffff00"]:
            btn_chip = QPushButton("●")
            btn_chip.setFixedSize(28, 28)
            btn_chip.setStyleSheet(f"background-color: {c}; color: {c}; border-radius: 14px;")
            btn_chip.clicked.connect(lambda _, col=c: self._set_cursor_color(col))
            color_row.addWidget(btn_chip)

        color_row.addStretch()
        grid_v.addLayout(color_row, 1, 1, 1, 2)

        # Theme Selector
        grid_v.addWidget(QLabel("Theme Mode:"), 2, 0)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light", "high_contrast"])
        self.combo_theme.setCurrentText(self.profile.theme)
        self.combo_theme.currentTextChanged.connect(self._on_theme_changed)
        grid_v.addWidget(self.combo_theme, 2, 1)

        # UI Scale
        grid_v.addWidget(QLabel("Button / UI Scale:"), 3, 0)
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["compact", "medium", "large"])
        self.combo_scale.setCurrentText(self.profile.ui_scale)
        self.combo_scale.currentTextChanged.connect(self._on_scale_changed)
        grid_v.addWidget(self.combo_scale, 3, 1)

        # High Contrast & Reduced Motion Toggles
        grid_v.addWidget(QLabel("Accessibility Toggles:"), 4, 0)
        toggles_row = QHBoxLayout()
        self.chk_contrast = QCheckBox("High-Contrast Mode")
        self.chk_contrast.setChecked(self.profile.high_contrast)
        self.chk_contrast.stateChanged.connect(self._on_contrast_changed)

        self.chk_motion = QCheckBox("Reduced Motion")
        self.chk_motion.setChecked(self.profile.reduced_motion)
        self.chk_motion.stateChanged.connect(self._on_motion_changed)

        toggles_row.addWidget(self.chk_contrast)
        toggles_row.addWidget(self.chk_motion)
        grid_v.addLayout(toggles_row, 4, 1, 1, 2)

        layout_visuals.addWidget(card_v)
        layout_visuals.addStretch()
        tabs.addTab(tab_visuals, "👁️ Visuals & Themes")

        # -------------------------------------------------------------
        # Tab 3: 🔊 Voice & Sound Feedback
        # -------------------------------------------------------------
        tab_voice = QWidget()
        layout_voice = QVBoxLayout(tab_voice)
        layout_voice.setContentsMargins(14, 14, 14, 14)
        layout_voice.setSpacing(12)

        card_voice = QFrame()
        card_voice.setObjectName("cardGroup")
        grid_voice = QGridLayout(card_voice)
        grid_voice.setSpacing(12)

        # Voice Speech Rate (WPM)
        grid_voice.addWidget(QLabel("Speech Rate (WPM):"), 0, 0)
        self.slider_rate = QSlider(Qt.Orientation.Horizontal)
        self.slider_rate.setRange(80, 260)
        self.slider_rate.setValue(self.profile.tts_rate)
        self.lbl_rate_val = QLabel(f"{self.profile.tts_rate} WPM")
        self.lbl_rate_val.setFixedWidth(60)
        self.slider_rate.valueChanged.connect(self._on_rate_changed)
        grid_voice.addWidget(self.slider_rate, 0, 1)
        grid_voice.addWidget(self.lbl_rate_val, 0, 2)

        # Voice Volume
        grid_voice.addWidget(QLabel("Speech Volume:"), 1, 0)
        self.slider_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vol.setRange(10, 100)
        self.slider_vol.setValue(int(self.profile.tts_volume * 100))
        self.lbl_vol_val = QLabel(f"{int(self.profile.tts_volume * 100)}%")
        self.lbl_vol_val.setFixedWidth(60)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        grid_voice.addWidget(self.slider_vol, 1, 1)
        grid_voice.addWidget(self.lbl_vol_val, 1, 2)

        # Selection Sound Feedback Toggle
        grid_voice.addWidget(QLabel("Audio Feedback:"), 2, 0)
        self.chk_sound = QCheckBox("Play Audio Sound on Dwell Selection")
        self.chk_sound.setChecked(self.profile.dwell_sound)
        self.chk_sound.stateChanged.connect(self._on_sound_toggle_changed)
        grid_voice.addWidget(self.chk_sound, 2, 1, 1, 2)

        # Voice Test Button
        btn_test_speech = QPushButton("🔊 Test Spoken Voice")
        btn_test_speech.setObjectName("btnPrimary")
        btn_test_speech.clicked.connect(self._test_spoken_voice)
        grid_voice.addWidget(btn_test_speech, 3, 1)

        layout_voice.addWidget(card_voice)
        layout_voice.addStretch()
        tabs.addTab(tab_voice, "🔊 Speech & Sound")

        # -------------------------------------------------------------
        # Tab 4: 🌐 Language & Localization
        # -------------------------------------------------------------
        tab_lang = QWidget()
        layout_lang = QVBoxLayout(tab_lang)
        layout_lang.setContentsMargins(14, 14, 14, 14)
        layout_lang.setSpacing(12)

        card_lang = QFrame()
        card_lang.setObjectName("cardGroup")
        grid_l = QGridLayout(card_lang)
        grid_l.setSpacing(12)

        grid_l.addWidget(QLabel("Application Language:"), 0, 0)
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("English (English)", "en")
        self.combo_lang.addItem("हिंदी (Hindi)", "hi")
        self.combo_lang.addItem("मराठी (Marathi)", "mr")

        cur_idx = self.combo_lang.findData(self.profile.language)
        if cur_idx >= 0:
            self.combo_lang.setCurrentIndex(cur_idx)
        self.combo_lang.currentIndexChanged.connect(self._on_language_changed)
        grid_l.addWidget(self.combo_lang, 0, 1)

        self.lbl_lang_info = QLabel(
            "Selected language translates all AAC categories, communication phrases, and prediction hints immediately."
        )
        self.lbl_lang_info.setStyleSheet("color: #94a3b8; font-size: 12px;")
        grid_l.addWidget(self.lbl_lang_info, 1, 0, 1, 2)

        layout_lang.addWidget(card_lang)
        layout_lang.addStretch()
        tabs.addTab(tab_lang, "🌐 Language (भाषा)")

        root.addWidget(tabs, stretch=1)

        # Bottom Buttons
        bottom_row = QHBoxLayout()
        btn_reset_defs = QPushButton("↺ Reset to Defaults")
        btn_reset_defs.setObjectName("btnReset")
        btn_reset_defs.clicked.connect(self._reset_to_defaults)

        btn_done = QPushButton("Done")
        btn_done.setObjectName("btnPrimary")
        btn_done.clicked.connect(self.accept)

        bottom_row.addWidget(btn_reset_defs)
        bottom_row.addStretch()
        bottom_row.addWidget(btn_done)
        root.addLayout(bottom_row)

    # -------------------------------------------------------------
    # Live Handlers & Auto-Save
    # -------------------------------------------------------------
    def _save_and_emit(self) -> None:
        self.repo.save_profile(self.profile)
        self.settings_updated.emit(self.profile)

    def _on_dwell_slider_changed(self, val: int) -> None:
        sec = val / 100.0
        self.profile.dwell_time = sec
        self.lbl_dwell_val.setText(f"{sec:.2f}s")
        self._save_and_emit()

    def _on_cooldown_slider_changed(self, val: int) -> None:
        sec = val / 100.0
        self.profile.cooldown_time = sec
        self.lbl_cooldown_val.setText(f"{sec:.2f}s")
        self._save_and_emit()

    def _on_smooth_slider_changed(self, val: int) -> None:
        factor = val / 10.0
        self.profile.smoothing_factor = factor
        self.lbl_smooth_val.setText(f"{factor:.1f}x")
        self._save_and_emit()

    def _on_hand_changed(self, hand: str) -> None:
        self.profile.dominant_hand = hand
        self._save_and_emit()

    def _on_csize_changed(self, val: int) -> None:
        self.profile.cursor_size = val
        self.lbl_csize_val.setText(f"{val}px")
        self._save_and_emit()

    def _set_cursor_color(self, color_hex: str) -> None:
        self._cursor_color = color_hex
        self.profile.cursor_color = color_hex
        self._save_and_emit()

    def _choose_color(self) -> None:
        c = QColorDialog.getColor(QColor(self._cursor_color), self, "Select Cursor Color")
        if c.isValid():
            self._set_cursor_color(c.name())

    def _on_theme_changed(self, theme_name: str) -> None:
        self.profile.theme = theme_name
        self._save_and_emit()

    def _on_scale_changed(self, scale_name: str) -> None:
        self.profile.ui_scale = scale_name
        self._save_and_emit()

    def _on_contrast_changed(self) -> None:
        self.profile.high_contrast = self.chk_contrast.isChecked()
        self._save_and_emit()

    def _on_motion_changed(self) -> None:
        self.profile.reduced_motion = self.chk_motion.isChecked()
        self._save_and_emit()

    def _on_rate_changed(self, val: int) -> None:
        self.profile.tts_rate = val
        self.lbl_rate_val.setText(f"{val} WPM")
        self.speech_engine.rate = val
        self._save_and_emit()

    def _on_volume_changed(self, val: int) -> None:
        vol = val / 100.0
        self.profile.tts_volume = vol
        self.lbl_vol_val.setText(f"{val}%")
        self.speech_engine.volume = vol
        self._save_and_emit()

    def _on_sound_toggle_changed(self) -> None:
        self.profile.dwell_sound = self.chk_sound.isChecked()
        self._save_and_emit()

    def _on_language_changed(self) -> None:
        lang_code = self.combo_lang.currentData()
        self.profile.language = lang_code
        self._save_and_emit()

    def _test_spoken_voice(self) -> None:
        sample_texts = {
            "en": "Hello, HANDVO speech synthesis is working properly.",
            "hi": "नमस्ते, हैंडवो वाक् संश्लेषण ठीक से काम कर रहा है।",
            "mr": "नमस्कार, हँडव्हो आवाज प्रणाली व्यवस्थित सुरू आहे.",
        }
        text = sample_texts.get(self.profile.language, sample_texts["en"])
        self.speech_engine.speak(text)

    def _reset_to_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all accessibility and personalization settings to factory defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.profile.dwell_time = 0.80
            self.profile.cooldown_time = 0.60
            self.profile.cursor_size = 14
            self.profile.cursor_color = "#38bdf8"
            self.profile.smoothing_factor = 1.50
            self.profile.dominant_hand = "Right"
            self.profile.language = "en"
            self.profile.tts_rate = 150
            self.profile.tts_volume = 1.0
            self.profile.dwell_sound = True
            self.profile.high_contrast = False
            self.profile.theme = "dark"
            self.profile.ui_scale = "medium"
            self.profile.reduced_motion = False

            self._save_and_emit()
            self.accept()
