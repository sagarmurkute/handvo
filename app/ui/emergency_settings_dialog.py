"""Caregiver customization settings dialog for emergency phrases and layout."""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.communication.emergency_model import EmergencyManager
from app.database.models import EmergencyAction


class EmergencySettingsDialog(QDialog):
    """Allows caregivers to add, edit, delete, and reorder emergency actions."""

    settings_changed = Signal()

    def __init__(self, emergency_mgr: EmergencyManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.emergency_mgr = emergency_mgr
        self._actions: List[EmergencyAction] = []
        self._selected_color = "#ef4444"

        self.setWindowTitle("Caregiver Settings — Emergency Mode Configuration")
        self.resize(780, 560)
        self.setModal(True)
        self._init_ui()
        self._load_actions()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #0b0f19;
                color: #f8fafc;
            }
            QLabel {
                color: #e2e8f0;
                font-size: 13px;
            }
            QLabel#headerTitle {
                color: #ef4444;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#headerSub {
                color: #94a3b8;
                font-size: 12px;
            }
            QTableWidget {
                background-color: #111827;
                border: 1px solid #374151;
                border-radius: 8px;
                gridline-color: #1f2937;
                color: #f8fafc;
                font-size: 13px;
                selection-background-color: #374151;
            }
            QHeaderView::section {
                background-color: #1f2937;
                color: #9ca3af;
                font-weight: 600;
                border: 1px solid #374151;
                padding: 6px;
            }
            QLineEdit, QComboBox {
                background-color: #1f2937;
                border: 1px solid #4b5563;
                border-radius: 6px;
                color: #f8fafc;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #ef4444;
            }
            QPushButton {
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
                border: none;
            }
            QPushButton#btnSave {
                background-color: #ef4444;
                color: #ffffff;
            }
            QPushButton#btnSave:hover {
                background-color: #dc2626;
            }
            QPushButton#btnSecondary {
                background-color: #1f2937;
                color: #e2e8f0;
                border: 1px solid #374151;
            }
            QPushButton#btnSecondary:hover {
                background-color: #374151;
            }
            QPushButton#btnDelete {
                background-color: #7f1d1d;
                color: #fca5a5;
            }
            QPushButton#btnDelete:hover {
                background-color: #991b1b;
            }
            QPushButton#btnReset {
                background-color: #334155;
                color: #cbd5e1;
            }
            QPushButton#btnReset:hover {
                background-color: #475569;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # Header
        header = QVBoxLayout()
        lbl_title = QLabel("⚙️ Caregiver Emergency Customization")
        lbl_title.setObjectName("headerTitle")
        lbl_sub = QLabel("Customize emergency actions, spoken phrases, and display order for optimal patient safety.")
        lbl_sub.setObjectName("headerSub")
        header.addWidget(lbl_title)
        header.addWidget(lbl_sub)
        root.addLayout(header)

        # Action Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Icon", "Card Label", "Spoken Emergency Phrase", "Accent Color"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_table_selection)
        root.addWidget(self.table, stretch=1)

        # Reorder & Delete Bar
        reorder_bar = QHBoxLayout()
        reorder_bar.setSpacing(8)

        self.btn_up = QPushButton("▲ Move Up")
        self.btn_up.setObjectName("btnSecondary")
        self.btn_up.clicked.connect(self._move_up)

        self.btn_down = QPushButton("▼ Move Down")
        self.btn_down.setObjectName("btnSecondary")
        self.btn_down.clicked.connect(self._move_down)

        self.btn_delete = QPushButton("🗑️ Delete Selected")
        self.btn_delete.setObjectName("btnDelete")
        self.btn_delete.clicked.connect(self._delete_selected)

        self.btn_reset = QPushButton("↺ Reset to Defaults")
        self.btn_reset.setObjectName("btnReset")
        self.btn_reset.clicked.connect(self._reset_defaults)

        reorder_bar.addWidget(self.btn_up)
        reorder_bar.addWidget(self.btn_down)
        reorder_bar.addWidget(self.btn_delete)
        reorder_bar.addStretch()
        reorder_bar.addWidget(self.btn_reset)
        root.addLayout(reorder_bar)

        # Add/Edit Card Editor Form
        form_frame = QFrame()
        form_frame.setStyleSheet("background-color: #111827; border: 1px solid #374151; border-radius: 8px; padding: 10px;")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(8)

        form_title = QLabel("Add / Edit Emergency Action")
        form_title.setStyleSheet("color: #f87171; font-weight: bold; font-size: 14px;")
        form_layout.addWidget(form_title)

        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(8)

        self.combo_icon = QComboBox()
        self.combo_icon.addItems(["🚨", "👨‍⚕️", "⚡", "🫁", "🆘", "💊", "🛑", "✅", "❌", "💧", "📞", "🙏"])
        self.combo_icon.setFixedWidth(70)

        self.txt_label = QLineEdit()
        self.txt_label.setPlaceholderText("Card Label (e.g., Call Help)")

        self.txt_speech = QLineEdit()
        self.txt_speech.setPlaceholderText("Spoken Phrase (e.g., Emergency! Please help me immediately!)")

        self.btn_color = QPushButton("Color")
        self.btn_color.setObjectName("btnSecondary")
        self.btn_color.setFixedWidth(70)
        self._update_color_button()
        self.btn_color.clicked.connect(self._choose_color)

        self.btn_add_or_update = QPushButton("Save Action")
        self.btn_add_or_update.setObjectName("btnSave")
        self.btn_add_or_update.clicked.connect(self._save_form_action)

        inputs_row.addWidget(QLabel("Icon:"))
        inputs_row.addWidget(self.combo_icon)
        inputs_row.addWidget(QLabel("Label:"))
        inputs_row.addWidget(self.txt_label, stretch=1)
        inputs_row.addWidget(QLabel("Speech:"))
        inputs_row.addWidget(self.txt_speech, stretch=2)
        inputs_row.addWidget(self.btn_color)
        inputs_row.addWidget(self.btn_add_or_update)
        form_layout.addLayout(inputs_row)

        root.addWidget(form_frame)

        # Bottom Close Button
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_close = QPushButton("Done")
        btn_close.setObjectName("btnSecondary")
        btn_close.clicked.connect(self.accept)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._selected_color), self, "Select Accent Color")
        if color.isValid():
            self._selected_color = color.name()
            self._update_color_button()

    def _update_color_button(self) -> None:
        self.btn_color.setStyleSheet(f"background-color: {self._selected_color}; color: #ffffff; font-weight: bold;")

    def _load_actions(self) -> None:
        self._actions = self.emergency_mgr.load_actions(enabled_only=False)
        self.table.setRowCount(len(self._actions))

        for row, action in enumerate(self._actions):
            item_icon = QTableWidgetItem(action.icon)
            item_icon.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_label = QTableWidgetItem(action.label)
            item_speech = QTableWidgetItem(action.speech_text)
            item_color = QTableWidgetItem(action.accent_color)
            item_color.setForeground(QColor(action.accent_color))
            item_color.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, item_icon)
            self.table.setItem(row, 1, item_label)
            self.table.setItem(row, 2, item_speech)
            self.table.setItem(row, 3, item_color)

    def _on_table_selection(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self._actions):
            act = self._actions[row]
            idx = self.combo_icon.findText(act.icon)
            if idx >= 0:
                self.combo_icon.setCurrentIndex(idx)
            self.txt_label.setText(act.label)
            self.txt_speech.setText(act.speech_text)
            self._selected_color = act.accent_color
            self._update_color_button()

    def _save_form_action(self) -> None:
        label = self.txt_label.text().strip()
        speech = self.txt_speech.text().strip()
        icon = self.combo_icon.currentText()
        if not label:
            QMessageBox.warning(self, "Validation", "Card label cannot be empty.")
            return
        if not speech:
            speech = label

        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            action = self._actions[row]
            action.label = label
            action.speech_text = speech
            action.icon = icon
            action.accent_color = self._selected_color
        else:
            action = EmergencyAction(
                label=label,
                speech_text=speech,
                icon=icon,
                accent_color=self._selected_color,
                sort_order=len(self._actions),
                is_enabled=True,
            )

        self.emergency_mgr.save_action(action)
        self._load_actions()
        self.settings_changed.emit()
        self.txt_label.clear()
        self.txt_speech.clear()

    def _delete_selected(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        act = self._actions[row]
        if act.id is not None:
            self.emergency_mgr.delete_action(act.id)
            self._load_actions()
            self.settings_changed.emit()

    def _move_up(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row <= 0:
            return

        self._actions[row], self._actions[row - 1] = self._actions[row - 1], self._actions[row]
        for idx, act in enumerate(self._actions):
            act.sort_order = idx
            self.emergency_mgr.save_action(act)

        self._load_actions()
        self.table.selectRow(row - 1)
        self.settings_changed.emit()

    def _move_down(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row >= len(self._actions) - 1:
            return

        self._actions[row], self._actions[row + 1] = self._actions[row + 1], self._actions[row]
        for idx, act in enumerate(self._actions):
            act.sort_order = idx
            self.emergency_mgr.save_action(act)

        self._load_actions()
        self.table.selectRow(row + 1)
        self.settings_changed.emit()

    def _reset_defaults(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset Emergency Actions",
            "Are you sure you want to reset all emergency actions to factory defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.emergency_mgr.reset_defaults()
            self._load_actions()
            self.settings_changed.emit()
