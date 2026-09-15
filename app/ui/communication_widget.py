"""Communication Board UI widget with accessible message composition and category navigation."""

from typing import Callable, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.communication.communication_board import (
    CommunicationBoardModel,
    CommunicationCategory,
    CommunicationItem,
)
from app.interaction.dwell_selector import DwellSelector
from app.ui.gaze_button import GazeButton


class CommunicationWidget(QWidget):
    """
    Accessible Gaze Communication Board UI.
    Contains composed message banner, category navigation tabs, action buttons, and phrase grid.
    """

    def __init__(
        self,
        model: Optional[CommunicationBoardModel] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.model = model or CommunicationBoardModel()

        self.category_buttons: List[GazeButton] = []
        self.action_buttons: List[GazeButton] = []
        self.phrase_buttons: List[GazeButton] = []

        self._dwell_selector: Optional[DwellSelector] = None
        self._root_window: Optional[QWidget] = None

        self._init_ui()

        # Connect model event subscriptions
        self.model.on_message_changed(self._on_message_updated)
        self.model.on_category_changed(self._on_category_switched)
        self.model.on_speak_requested(self._on_speak_triggered)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Top Message Composition Card
        msg_card = QFrame()
        msg_card.setStyleSheet(
            """
            QFrame {
                background-color: #0f172a;
                border: 2px solid #38bdf8;
                border-radius: 10px;
                padding: 10px 16px;
            }
            """
        )
        msg_layout = QVBoxLayout(msg_card)
        msg_layout.setContentsMargins(8, 6, 8, 6)
        msg_layout.setSpacing(4)

        msg_header = QHBoxLayout()
        lbl_composer_title = QLabel("COMPOSED MESSAGE")
        lbl_composer_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: bold; letter-spacing: 1px;")

        self.lbl_speak_status = QLabel("Ready")
        self.lbl_speak_status.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
        msg_header.addWidget(lbl_composer_title)
        msg_header.addStretch()
        msg_header.addWidget(self.lbl_speak_status)

        self.lbl_message = QLabel("Type or gaze-select phrases below to build a message...")
        self.lbl_message.setStyleSheet(
            "color: #f8fafc; font-size: 20px; font-weight: bold; min-height: 38px; line-height: 1.3;"
        )
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        msg_layout.addLayout(msg_header)
        msg_layout.addWidget(self.lbl_message)

        # 2. Composition Action Bar ([Speak], [Backspace], [Space], [Clear])
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.btn_speak = GazeButton(
            target_id="act_speak",
            text="🔊 Speak",
            accent_color="#10b981",
            callback=self.model.request_speak,
        )
        self.btn_speak.setMinimumHeight(44)

        self.btn_backspace = GazeButton(
            target_id="act_backspace",
            text="⌫ Delete Last",
            accent_color="#f59e0b",
            callback=self.model.delete_last,
        )
        self.btn_backspace.setMinimumHeight(44)

        self.btn_space = GazeButton(
            target_id="act_space",
            text="␣ Space",
            accent_color="#64748b",
            callback=self.model.add_space,
        )
        self.btn_space.setMinimumHeight(44)

        self.btn_clear = GazeButton(
            target_id="act_clear",
            text="🗑 Clear All",
            accent_color="#ef4444",
            callback=self.model.clear_message,
        )
        self.btn_clear.setMinimumHeight(44)

        self.action_buttons = [self.btn_speak, self.btn_backspace, self.btn_space, self.btn_clear]
        for btn in self.action_buttons:
            action_bar.addWidget(btn)

        # 3. Category Navigation Tabs
        cat_bar = QHBoxLayout()
        cat_bar.setSpacing(8)

        categories = self.model.get_categories()
        self.category_buttons.clear()

        for cat in categories:
            btn_cat = GazeButton(
                target_id=f"cat_{cat.category_id}",
                text=f"{cat.icon} {cat.name}",
                accent_color=cat.accent_color,
                callback=lambda cid=cat.category_id: self.model.set_category(cid),
            )
            btn_cat.setMinimumHeight(44)
            self.category_buttons.append(btn_cat)
            cat_bar.addWidget(btn_cat)

        # 4. Phrase Items Grid Container
        self.phrase_container = QWidget()
        self.phrase_grid = QGridLayout(self.phrase_container)
        self.phrase_grid.setContentsMargins(4, 4, 4, 4)
        self.phrase_grid.setSpacing(10)

        # Populate active category phrases
        self._populate_phrase_grid()

        layout.addWidget(msg_card)
        layout.addLayout(action_bar)
        layout.addLayout(cat_bar)
        layout.addWidget(self.phrase_container, stretch=1)

    def set_dwell_engine(self, selector: DwellSelector, root_window: QWidget) -> None:
        """Bind the dwell selector and parent window to enable interactive target registration."""
        self._dwell_selector = selector
        self._root_window = root_window
        self.register_all_targets()

    def register_all_targets(self) -> None:
        """Register all active action buttons, category tabs, and phrase cards with the DwellSelector."""
        if self._dwell_selector is None or self._root_window is None:
            return

        # Register Action Buttons
        for btn in self.action_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

        # Register Category Buttons
        for btn in self.category_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

        # Register Phrase Buttons
        for btn in self.phrase_buttons:
            self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

    def _populate_phrase_grid(self) -> None:
        """Build large accessible gaze buttons for the currently active category."""
        # Clear existing phrase buttons
        for btn in self.phrase_buttons:
            if self._dwell_selector:
                self._dwell_selector.unregister_target(btn.target_id)
            btn.setParent(None)
            btn.deleteLater()
        self.phrase_buttons.clear()

        # Clear layout items
        while self.phrase_grid.count():
            item = self.phrase_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = self.model.get_active_items()
        cols = 3  # 3 columns for large, spacious hit areas

        for i, item in enumerate(items):
            row = i // cols
            col = i % cols

            btn_phrase = GazeButton(
                target_id=f"phrase_{item.item_id}",
                text=item.label,
                accent_color=item.accent_color,
                callback=lambda it=item: self.model.add_item(it),
            )
            btn_phrase.setMinimumHeight(64)
            btn_phrase.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            btn_phrase.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            self.phrase_buttons.append(btn_phrase)
            self.phrase_grid.addWidget(btn_phrase, row, col)

        # Re-register with dwell selector if connected
        if self._dwell_selector is not None and self._root_window is not None:
            for btn in self.phrase_buttons:
                self._dwell_selector.register_target(btn.create_dwell_target(self._root_window))

    def update_all_dwell_feedbacks(self, target_id: Optional[str], progress: float, is_cooldown: bool) -> None:
        """Update dwell progress rings and highlights across all buttons on the board."""
        all_buttons = self.action_buttons + self.category_buttons + self.phrase_buttons
        for btn in all_buttons:
            focused = (target_id == btn.target_id)
            prog = progress if focused else 0.0
            in_cool = (is_cooldown and focused)
            btn.update_dwell_feedback(focused, prog, in_cool)

    def _on_message_updated(self, msg: str) -> None:
        """Update display label when message changes."""
        if msg.strip():
            self.lbl_message.setText(msg)
            self.lbl_message.setStyleSheet("color: #38bdf8; font-size: 22px; font-weight: bold; min-height: 38px;")
        else:
            self.lbl_message.setText("Type or gaze-select phrases below to build a message...")
            self.lbl_message.setStyleSheet("color: #64748b; font-size: 16px; font-style: italic; min-height: 38px;")

    def _on_category_switched(self, cat_id: str) -> None:
        """Re-render phrase cards when active category changes."""
        self._populate_phrase_grid()

    def _on_speak_triggered(self, msg: str) -> None:
        """Visual feedback when speak action is triggered."""
        if msg.strip():
            self.lbl_speak_status.setText("🔊 Spoken: " + (msg if len(msg) < 30 else msg[:27] + "..."))
            self.lbl_speak_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_speak_status.setText("⚠️ Message empty")
            self.lbl_speak_status.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11px;")
