"""Premium Accessible Communication Board UI for HANDVO with Smart Prediction Chips."""

from typing import Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.communication.communication_board import (
    CommunicationBoardModel,
    CommunicationCategory,
    CommunicationItem,
)
from app.communication.prediction import PredictionCandidate, SmartPredictionEngine
from app.communication.speech import SpeechEngine
from app.interaction.dwell_selector import DwellSelector
from app.ui.gaze_button import GazeButton


class CommunicationWidget(QWidget):
    """
    State-of-the-art AAC desktop interface with live sentence builder,
    Smart Prediction chips, 6 category navigation tabs, large high-contrast
    phrase cards, and full integration with the hand dwell selection engine.
    """

    def __init__(
        self,
        model: Optional[CommunicationBoardModel] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.model = model or CommunicationBoardModel()
        self.speech_engine = SpeechEngine()
        self.prediction_engine = SmartPredictionEngine()

        self._dwell_selector: Optional[DwellSelector] = None
        self._root_window: Optional[QWidget] = None

        self.category_buttons: List[GazeButton] = []
        self.action_buttons: List[GazeButton] = []
        self.phrase_buttons: List[GazeButton] = []
        self.prediction_buttons: List[GazeButton] = []
        self._button_map: Dict[str, GazeButton] = {}

        self._init_ui()
        self._bind_model_events()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 10, 14, 10)
        root_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. Top Sentence Bar & Action Toolbar Card
        # -------------------------------------------------------------
        composer_card = QFrame()
        composer_card.setObjectName("composerCard")
        composer_card.setStyleSheet(
            """
            QFrame#composerCard {
                background-color: #0b0f19;
                border: 2px solid #1e293b;
                border-radius: 12px;
                padding: 10px 12px;
            }
            """
        )
        composer_layout = QVBoxLayout(composer_card)
        composer_layout.setContentsMargins(10, 8, 10, 8)
        composer_layout.setSpacing(8)

        # Sentence header row
        header_row = QHBoxLayout()
        lbl_composer_title = QLabel("💬 SENTENCE BUILDER")
        lbl_composer_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        header_row.addWidget(lbl_composer_title)
        header_row.addStretch()

        self.lbl_token_count = QLabel("0 Words")
        self.lbl_token_count.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 600;")
        header_row.addWidget(self.lbl_token_count)
        composer_layout.addLayout(header_row)

        # Composed Text Display Container
        self.msg_display_box = QFrame()
        self.msg_display_box.setStyleSheet(
            """
            background-color: #111827;
            border: 1.5px solid #1f2937;
            border-radius: 8px;
            padding: 8px 12px;
            """
        )
        msg_inner_layout = QHBoxLayout(self.msg_display_box)
        msg_inner_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_message = QLabel("Point or click on cards below to compose a sentence...")
        self.lbl_message.setFont(QFont("Segoe UI", 15, QFont.Weight.DemiBold))
        self.lbl_message.setStyleSheet("color: #64748b;")
        self.lbl_message.setWordWrap(True)
        msg_inner_layout.addWidget(self.lbl_message)

        composer_layout.addWidget(self.msg_display_box)

        # Action Toolbar (Speak, Delete, Space, Clear)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_speak = GazeButton(
            target_id="act_speak",
            text="🔊 Speak Message",
            accent_color="#0284c7",
            callback=self._on_speak_clicked,
        )
        self.btn_speak.setMinimumHeight(42)

        self.btn_backspace = GazeButton(
            target_id="act_backspace",
            text="⌫ Delete Last",
            accent_color="#f59e0b",
            callback=self.model.delete_last,
        )
        self.btn_backspace.setMinimumHeight(42)

        self.btn_space = GazeButton(
            target_id="act_space",
            text="␣ Space",
            accent_color="#6366f1",
            callback=self.model.add_space,
        )
        self.btn_space.setMinimumHeight(42)

        self.btn_clear = GazeButton(
            target_id="act_clear",
            text="🗑 Clear All",
            accent_color="#ef4444",
            callback=self.model.clear_message,
        )
        self.btn_clear.setMinimumHeight(42)

        self.action_buttons = [self.btn_speak, self.btn_backspace, self.btn_space, self.btn_clear]
        for btn in self.action_buttons:
            action_bar.addWidget(btn)
            self._button_map[btn.target_id] = btn

        composer_layout.addLayout(action_bar)
        root_layout.addWidget(composer_card)

        # -------------------------------------------------------------
        # 2. Smart Prediction Chips Bar
        # -------------------------------------------------------------
        pred_card = QFrame()
        pred_card.setStyleSheet(
            """
            background-color: #0b0f19;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 6px 10px;
            """
        )
        pred_layout = QVBoxLayout(pred_card)
        pred_layout.setContentsMargins(6, 4, 6, 4)
        pred_layout.setSpacing(6)

        pred_title_row = QHBoxLayout()
        lbl_pred_title = QLabel("⚡ SMART PREDICTIONS")
        lbl_pred_title.setStyleSheet("color: #a855f7; font-size: 10px; font-weight: bold; letter-spacing: 0.8px;")
        pred_title_row.addWidget(lbl_pred_title)
        pred_title_row.addStretch()
        pred_layout.addLayout(pred_title_row)

        self.pred_chips_layout = QHBoxLayout()
        self.pred_chips_layout.setSpacing(8)
        pred_layout.addLayout(self.pred_chips_layout)

        root_layout.addWidget(pred_card)

        # -------------------------------------------------------------
        # 3. Category Navigation Tabs
        # -------------------------------------------------------------
        self.cat_bar_layout = QHBoxLayout()
        self.cat_bar_layout.setSpacing(8)
        root_layout.addLayout(self.cat_bar_layout)

        # -------------------------------------------------------------
        # 4. Responsive Accessible Phrase Card Grid
        # -------------------------------------------------------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none; background: #0f172a; width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #334155; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #475569; }
            """
        )

        self.phrase_container = QWidget()
        self.phrase_grid = QGridLayout(self.phrase_container)
        self.phrase_grid.setContentsMargins(2, 2, 2, 2)
        self.phrase_grid.setSpacing(10)

        self.scroll_area.setWidget(self.phrase_container)
        root_layout.addWidget(self.scroll_area, stretch=1)

        # Initial renders
        self._populate_categories()
        self._update_prediction_chips()

    def _populate_categories(self) -> None:
        """Rebuild category navigation tab buttons for active language."""
        for btn in self.category_buttons:
            self._button_map.pop(btn.target_id, None)
            btn.deleteLater()
        self.category_buttons.clear()

        while self.cat_bar_layout.count():
            item = self.cat_bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        categories = self.model.get_categories()
        for cat in categories:
            btn_cat = GazeButton(
                target_id=f"cat_{cat.category_id}",
                text=f"{cat.icon} {cat.name}",
                accent_color=cat.accent_color,
                callback=lambda cid=cat.category_id: self.model.set_category(cid),
            )
            btn_cat.setMinimumHeight(42)
            self.category_buttons.append(btn_cat)
            self._button_map[btn_cat.target_id] = btn_cat
            self.cat_bar_layout.addWidget(btn_cat)

        self._update_category_tab_styles(self.model.active_category_id)
        self._populate_phrase_grid()

    def _bind_model_events(self) -> None:
        """Connect state changes to UI re-rendering."""
        self.model.on_message_changed(self._on_message_changed)
        self.model.on_category_changed(self._on_category_changed)

    def _on_speak_clicked(self) -> None:
        text = self.model.current_message
        if text:
            self.speech_engine.speak(text)
            self.model.request_speak()

    def _on_message_changed(self, new_text: str) -> None:
        tokens = self.model.message_tokens
        count = len([t for t in tokens if t])
        self.lbl_token_count.setText(f"{count} {'Words' if count != 1 else 'Word'}")

        if new_text.strip():
            self.lbl_message.setText(new_text)
            self.lbl_message.setStyleSheet("color: #38bdf8; font-weight: bold;")
        else:
            self.lbl_message.setText("Point or click on cards below to compose a sentence...")
            self.lbl_message.setStyleSheet("color: #64748b; font-weight: normal;")

        self._update_prediction_chips()
        if self._dwell_selector is not None and self._root_window is not None:
            self.register_all_targets()

    def _on_category_changed(self, active_category_id: str) -> None:
        self._update_category_tab_styles(active_category_id)
        self._populate_phrase_grid()
        self._update_prediction_chips()
        if self._dwell_selector is not None and self._root_window is not None:
            self.register_all_targets()

    def _on_prediction_selected(self, candidate: PredictionCandidate) -> None:
        prev = self.model.current_message
        self.prediction_engine.learn_selection(prev, candidate.text, self.model.active_category_id)
        self.model.add_text(candidate.text)

    def _update_prediction_chips(self) -> None:
        """Fetch next-word predictions and dynamically update the prediction chip buttons."""
        # Clear old prediction buttons
        for btn in self.prediction_buttons:
            self._button_map.pop(btn.target_id, None)
            btn.deleteLater()
        self.prediction_buttons.clear()

        while self.pred_chips_layout.count():
            item = self.pred_chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        candidates = self.prediction_engine.get_predictions(
            current_sentence=self.model.current_message,
            active_category_id=self.model.active_category_id,
            limit=5,
        )

        for idx, cand in enumerate(candidates):
            btn_chip = GazeButton(
                target_id=f"pred_{idx}_{cand.text.replace(' ', '_')}",
                text=cand.label,
                accent_color=cand.accent_color,
                callback=lambda c=cand: self._on_prediction_selected(c),
            )
            btn_chip.setMinimumHeight(38)
            btn_chip.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
            self.prediction_buttons.append(btn_chip)
            self._button_map[btn_chip.target_id] = btn_chip
            self.pred_chips_layout.addWidget(btn_chip)

        self.pred_chips_layout.addStretch()

    def _update_category_tab_styles(self, active_id: str) -> None:
        for btn in self.category_buttons:
            cat_id = btn.target_id.replace("cat_", "")
            if cat_id == active_id:
                btn.setStyleSheet("font-weight: bold; border-width: 2px;")
                btn.is_in_cooldown = True
            else:
                btn.setStyleSheet("")
                btn.is_in_cooldown = False
            btn.update()

    def _populate_phrase_grid(self) -> None:
        """Rebuild large accessible phrase cards for active category."""
        for btn in self.phrase_buttons:
            self._button_map.pop(btn.target_id, None)
            btn.deleteLater()
        self.phrase_buttons.clear()

        while self.phrase_grid.count():
            item = self.phrase_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self.model.get_active_items()
        columns = 4

        for idx, item in enumerate(items):
            row = idx // columns
            col = idx % columns

            btn_phrase = GazeButton(
                target_id=f"phrase_{item.item_id}",
                text=item.label,
                icon_str=item.icon,
                subtitle=item.text,
                accent_color=item.accent_color,
                is_card=True,
                callback=lambda it=item: self._on_phrase_card_selected(it),
            )
            btn_phrase.setMinimumHeight(84)
            self.phrase_buttons.append(btn_phrase)
            self._button_map[btn_phrase.target_id] = btn_phrase
            self.phrase_grid.addWidget(btn_phrase, row, col)

    def _on_phrase_card_selected(self, item: CommunicationItem) -> None:
        prev = self.model.current_message
        self.prediction_engine.learn_selection(prev, item.text, self.model.active_category_id)
        self.model.add_item(item)

    def set_dwell_engine(self, selector: DwellSelector, root_window: QWidget) -> None:
        """Bind dwell selector and parent window to activate seamless dwell hover."""
        self._dwell_selector = selector
        self._root_window = root_window
        self.register_all_targets()

    def register_all_targets(self) -> None:
        """Register all action buttons, prediction chips, category tabs, and phrase cards into DwellSelector."""
        if self._dwell_selector is None or self._root_window is None:
            return

        self._dwell_selector.clear_targets()

        for btn in self.action_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

        for btn in self.prediction_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

        for btn in self.category_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

        for btn in self.phrase_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

    def update_all_dwell_feedbacks(
        self,
        target_id: Optional[str],
        progress: float,
        is_cooldown: bool = False,
    ) -> None:
        """Update live hover/dwell visual feedback across all registered buttons and chips."""
        all_buttons = self.action_buttons + self.prediction_buttons + self.category_buttons + self.phrase_buttons

        for btn in all_buttons:
            is_focused = (target_id is not None and btn.target_id == target_id)
            btn_progress = progress if is_focused else 0.0
            btn_cooldown = is_cooldown if is_focused else False
            btn.update_dwell_feedback(is_focused, btn_progress, btn_cooldown)
