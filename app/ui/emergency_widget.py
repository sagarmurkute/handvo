"""High-contrast Emergency Mode interface for HANDVO with large accessible action cards."""

from typing import Callable, Dict, List, Optional
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.communication.emergency_model import EmergencyManager
from app.database.models import EmergencyAction
from app.gestures.dwell import DwellSelector
from app.ui.emergency_settings_dialog import EmergencySettingsDialog
from app.ui.gaze_button import GazeButton


class EmergencyWidget(QWidget):
    """
    Dedicated high-contrast, high-priority emergency AAC interface.
    Features giant cards, live offline speech dispatch, dwell support, and caregiver settings.
    """

    exit_requested = Signal()

    def __init__(
        self,
        emergency_mgr: Optional[EmergencyManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.emergency_mgr = emergency_mgr or EmergencyManager()
        self._dwell_selector: Optional[DwellSelector] = None
        self._root_window: Optional[QWidget] = None

        self.action_buttons: List[GazeButton] = []
        self._button_map: Dict[str, GazeButton] = {}

        self.emergency_mgr.add_listener(self._on_action_triggered)

        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background-color: #0b0f19;
                color: #f8fafc;
            }
            QFrame#alertBanner {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7f1d1d, stop:0.5 #991b1b, stop:1 #7f1d1d);
                border: 2px solid #ef4444;
                border-radius: 12px;
                padding: 12px 18px;
            }
            QLabel#alertTitle {
                color: #fef2f2;
                font-size: 22px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QLabel#alertSub {
                color: #fecaca;
                font-size: 13px;
                font-weight: 500;
            }
            QFrame#spokenCard {
                background-color: #111827;
                border: 2px solid #ef4444;
                border-radius: 10px;
                padding: 8px 14px;
            }
            QLabel#spokenLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }
            """
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        # 1. Top Alert Header
        header_card = QFrame()
        header_card.setObjectName("alertBanner")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(14)

        icon_alert = QLabel("🚨")
        icon_alert.setFont(QFont("Segoe UI Emoji", 32))
        header_layout.addWidget(icon_alert)

        header_text = QVBoxLayout()
        lbl_title = QLabel("EMERGENCY MODE ACTIVE")
        lbl_title.setObjectName("alertTitle")
        lbl_sub = QLabel("Point hand cursor or pinch to trigger high-priority assistance immediately")
        lbl_sub.setObjectName("alertSub")
        header_text.addWidget(lbl_title)
        header_text.addWidget(lbl_sub)
        header_layout.addLayout(header_text)

        header_layout.addStretch()

        # Caregiver Settings & Exit Action Buttons
        self.btn_settings = GazeButton(
            target_id="emg_caregiver_settings",
            text="⚙️ Settings",
            accent_color="#64748b",
            callback=self._open_caregiver_settings,
        )
        self.btn_settings.setMinimumHeight(44)
        self._button_map[self.btn_settings.target_id] = self.btn_settings

        self.btn_exit = GazeButton(
            target_id="emg_exit_mode",
            text="🔙 Exit Emergency",
            accent_color="#334155",
            callback=self.exit_requested.emit,
        )
        self.btn_exit.setMinimumHeight(44)
        self._button_map[self.btn_exit.target_id] = self.btn_exit

        header_layout.addWidget(self.btn_settings)
        header_layout.addWidget(self.btn_exit)
        root_layout.addWidget(header_card)

        # 2. Live Spoken Phrase Banner
        self.spoken_card = QFrame()
        self.spoken_card.setObjectName("spokenCard")
        spoken_layout = QHBoxLayout(self.spoken_card)
        spoken_layout.setContentsMargins(12, 6, 12, 6)
        spoken_layout.setSpacing(10)

        lbl_mic = QLabel("📢")
        lbl_mic.setFont(QFont("Segoe UI Emoji", 16))
        spoken_layout.addWidget(lbl_mic)

        self.lbl_spoken = QLabel("Ready — Hover cursor over any emergency card to speak immediately.")
        self.lbl_spoken.setObjectName("spokenLabel")
        spoken_layout.addWidget(self.lbl_spoken, stretch=1)

        root_layout.addWidget(self.spoken_card)

        # 3. Large High-Priority Action Cards Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 4, 0, 4)
        self.cards_grid.setSpacing(14)

        self.scroll_area.setWidget(self.cards_container)
        root_layout.addWidget(self.scroll_area, stretch=1)

        # Build emergency cards
        self._populate_emergency_cards()

    def _populate_emergency_cards(self) -> None:
        """Render high-contrast emergency cards in a responsive grid."""
        for btn in self.action_buttons:
            self._button_map.pop(btn.target_id, None)
            btn.deleteLater()
        self.action_buttons.clear()

        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        actions = self.emergency_mgr.load_actions(enabled_only=True)
        cols = 2 if len(actions) <= 4 else 3

        for idx, act in enumerate(actions):
            row = idx // cols
            col = idx % cols

            btn_card = GazeButton(
                target_id=f"emg_act_{act.id}_{act.label.replace(' ', '_')}",
                text=f"{act.icon}  {act.label}",
                subtitle=act.speech_text,
                accent_color=act.accent_color,
                is_card=True,
                callback=lambda a=act: self._trigger_action(a),
            )
            btn_card.setMinimumHeight(110)
            self.action_buttons.append(btn_card)
            self._button_map[btn_card.target_id] = btn_card
            self.cards_grid.addWidget(btn_card, row, col)

    def _trigger_action(self, action: EmergencyAction) -> None:
        spoken = self.emergency_mgr.trigger_action(action)
        self.lbl_spoken.setText(f"🔊 SPOKEN: \"{spoken}\"")
        self.spoken_card.setStyleSheet(
            f"background-color: #1f2937; border: 2px solid {action.accent_color}; border-radius: 10px; padding: 8px 14px;"
        )

    def _on_action_triggered(self, action: EmergencyAction) -> None:
        self.lbl_spoken.setText(f"🔊 SPOKEN: \"{action.speech_text}\"")

    def _open_caregiver_settings(self) -> None:
        dlg = EmergencySettingsDialog(self.emergency_mgr, parent=self)
        dlg.settings_changed.connect(self._on_settings_updated)
        dlg.exec()

    def _on_settings_updated(self) -> None:
        self._populate_emergency_cards()
        self.register_all_targets()

    def set_dwell_engine(self, selector: DwellSelector, root_window: QWidget) -> None:
        """Bind dwell selector and root window to activate seamless dwell hover in Emergency Mode."""
        self._dwell_selector = selector
        self._root_window = root_window
        self.register_all_targets()

    def register_all_targets(self) -> None:
        """Register all emergency cards and controls into DwellSelector."""
        if self._dwell_selector is None or self._root_window is None:
            return

        self._dwell_selector.clear_targets()

        self._dwell_selector.register_target(self.btn_settings.create_dwell_target(self._root_window))
        self._dwell_selector.register_target(self.btn_exit.create_dwell_target(self._root_window))

        for btn in self.action_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

    def update_all_dwell_feedbacks(
        self,
        target_id: Optional[str],
        progress: float,
        is_cooldown: bool = False,
    ) -> None:
        """Update live hover/dwell visual feedback across all emergency cards."""
        all_buttons = [self.btn_settings, self.btn_exit] + self.action_buttons

        for btn in all_buttons:
            is_focused = (target_id is not None and btn.target_id == target_id)
            btn.is_in_cooldown = is_cooldown if is_focused else False
            btn.update_dwell_progress(progress if is_focused else 0.0)
