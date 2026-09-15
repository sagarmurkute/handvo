"""Caregiver Profile Management Dialog for HANDVO.

Supports multi-user profile switching, creation, editing, duplication, archiving,
custom phrase authoring, and offline JSON export/import backup.
"""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.database import Database
from app.database.models import CustomPhrase, UserProfile
from app.database.profile_repository import ProfileRepository


class ProfileEditorDialog(QDialog):
    """Sub-dialog to create or edit profile properties."""

    def __init__(
        self,
        profile: Optional[UserProfile] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile or UserProfile(name="")
        self.is_new = profile is None or profile.id is None

        self.setWindowTitle("New User Profile" if self.is_new else f"Edit Profile: {self.profile.name}")
        self.resize(480, 420)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            """
            QDialog { background-color: #0f172a; color: #f8fafc; }
            QLabel { color: #cbd5e1; font-size: 13px; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus { border-color: #38bdf8; }
            QPushButton {
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                border: none;
            }
            QPushButton#btnSave { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnSave:hover { background-color: #0369a1; }
            QPushButton#btnCancel { background-color: #334155; color: #cbd5e1; }
            QPushButton#btnCancel:hover { background-color: #475569; }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Name
        grid.addWidget(QLabel("Profile / User Name:"), 0, 0)
        self.txt_name = QLineEdit(self.profile.name)
        self.txt_name.setPlaceholderText("e.g. Alex, Patient Room 4")
        grid.addWidget(self.txt_name, 0, 1)

        # Dominant Hand
        grid.addWidget(QLabel("Dominant Hand:"), 1, 0)
        self.combo_hand = QComboBox()
        self.combo_hand.addItems(["Right", "Left"])
        self.combo_hand.setCurrentText(self.profile.dominant_hand)
        grid.addWidget(self.combo_hand, 1, 1)

        # Dwell Time
        grid.addWidget(QLabel("Dwell Time (seconds):"), 2, 0)
        self.spin_dwell = QDoubleSpinBox()
        self.spin_dwell.setRange(0.30, 3.00)
        self.spin_dwell.setSingleStep(0.05)
        self.spin_dwell.setValue(self.profile.dwell_time)
        grid.addWidget(self.spin_dwell, 2, 1)

        # TTS Speech Rate
        grid.addWidget(QLabel("Voice Speed (WPM):"), 3, 0)
        self.spin_tts_rate = QSpinBox()
        self.spin_tts_rate.setRange(80, 260)
        self.spin_tts_rate.setValue(self.profile.tts_rate)
        grid.addWidget(self.spin_tts_rate, 3, 1)

        # TTS Volume
        grid.addWidget(QLabel("Voice Volume:"), 4, 0)
        self.spin_volume = QDoubleSpinBox()
        self.spin_volume.setRange(0.1, 1.0)
        self.spin_volume.setSingleStep(0.1)
        self.spin_volume.setValue(self.profile.tts_volume)
        grid.addWidget(self.spin_volume, 4, 1)

        # UI Scale
        grid.addWidget(QLabel("Card UI Scale:"), 5, 0)
        self.combo_scale = QComboBox()
        self.combo_scale.addItems(["medium", "large", "compact"])
        self.combo_scale.setCurrentText(self.profile.ui_scale)
        grid.addWidget(self.combo_scale, 5, 1)

        # High Contrast
        self.chk_contrast = QCheckBox("High Contrast Mode")
        self.chk_contrast.setChecked(self.profile.high_contrast)
        self.chk_contrast.setStyleSheet("color: #e2e8f0; font-size: 13px;")
        grid.addWidget(self.chk_contrast, 6, 1)

        root.addLayout(grid)
        root.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Profile")
        btn_save.setObjectName("btnSave")
        btn_save.clicked.connect(self._save)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

    def _save(self) -> None:
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Profile name cannot be blank.")
            return

        self.profile.name = name
        self.profile.dominant_hand = self.combo_hand.currentText()
        self.profile.dwell_time = self.spin_dwell.value()
        self.profile.tts_rate = self.spin_tts_rate.value()
        self.profile.tts_volume = self.spin_volume.value()
        self.profile.ui_scale = self.combo_scale.currentText()
        self.profile.high_contrast = self.chk_contrast.isChecked()
        self.accept()


class ProfileManagerDialog(QDialog):
    """
    Caregiver dashboard for managing user profiles, custom phrases,
    and backup JSON import/export.
    """

    profile_switched = Signal(UserProfile)

    def __init__(
        self,
        repository: Optional[ProfileRepository] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.repo = repository or ProfileRepository(Database())
        self._profiles: List[UserProfile] = []
        self._selected_profile: Optional[UserProfile] = None

        self.setWindowTitle("Caregiver Profile & AAC Manager — HANDVO")
        self.resize(920, 640)
        self.setModal(True)
        self._init_ui()
        self._load_profiles()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            """
            QDialog { background-color: #0b0f19; color: #f8fafc; }
            QTabWidget::pane { border: 1px solid #1e293b; background-color: #0f172a; border-radius: 8px; }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected { background-color: #0284c7; color: #ffffff; }
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
                gridline-color: #1e293b;
                color: #f8fafc;
                font-size: 13px;
                selection-background-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                font-weight: 600;
                border: 1px solid #1e293b;
                padding: 6px;
            }
            QPushButton {
                font-weight: 600;
                border-radius: 6px;
                padding: 8px 14px;
                font-size: 12px;
                border: none;
            }
            QPushButton#btnPrimary { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnPrimary:hover { background-color: #0369a1; }
            QPushButton#btnSecondary { background-color: #1e293b; color: #e2e8f0; border: 1px solid #334155; }
            QPushButton#btnSecondary:hover { background-color: #334155; }
            QPushButton#btnSuccess { background-color: #16a34a; color: #ffffff; }
            QPushButton#btnSuccess:hover { background-color: #15803d; }
            QPushButton#btnDanger { background-color: #991b1b; color: #fca5a5; }
            QPushButton#btnDanger:hover { background-color: #b91c1c; }
            QLabel#headerTitle { color: #38bdf8; font-size: 20px; font-weight: bold; }
            QLabel#headerSub { color: #94a3b8; font-size: 13px; }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        h_text = QVBoxLayout()
        lbl_title = QLabel("👥 Caregiver Profile Manager")
        lbl_title.setObjectName("headerTitle")
        lbl_sub = QLabel("Manage multi-user profiles, calibration profiles, custom AAC phrases, and backups.")
        lbl_sub.setObjectName("headerSub")
        h_text.addWidget(lbl_title)
        h_text.addWidget(lbl_sub)
        header.addLayout(h_text)
        header.addStretch()

        self.btn_export = QPushButton("📤 Export Profile (JSON)")
        self.btn_export.setObjectName("btnSecondary")
        self.btn_export.clicked.connect(self._export_profile_json)

        self.btn_import = QPushButton("📥 Import Profile (JSON)")
        self.btn_import.setObjectName("btnSecondary")
        self.btn_import.clicked.connect(self._import_profile_json)

        header.addWidget(self.btn_export)
        header.addWidget(self.btn_import)
        root.addLayout(header)

        # Tabs Container
        self.tabs = QTabWidget()

        # Tab 1: User Profiles
        tab_profiles = QWidget()
        p_layout = QVBoxLayout(tab_profiles)
        p_layout.setContentsMargins(14, 14, 14, 14)
        p_layout.setSpacing(10)

        # Filter row
        f_row = QHBoxLayout()
        self.chk_show_archived = QCheckBox("Show Archived Profiles")
        self.chk_show_archived.setStyleSheet("color: #94a3b8;")
        self.chk_show_archived.stateChanged.connect(self._load_profiles)
        f_row.addWidget(self.chk_show_archived)
        f_row.addStretch()
        p_layout.addLayout(f_row)

        # Profiles Table
        self.table_profiles = QTableWidget()
        self.table_profiles.setColumnCount(6)
        self.table_profiles.setHorizontalHeaderLabels([
            "Status", "Profile Name", "Hand", "Dwell Time", "Quality", "Archived"
        ])
        self.table_profiles.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_profiles.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_profiles.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_profiles.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_profiles.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_profiles.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table_profiles.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_profiles.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_profiles.itemSelectionChanged.connect(self._on_profile_selected)
        p_layout.addWidget(self.table_profiles, stretch=1)

        # Action Buttons Row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.btn_switch = QPushButton("⚡ Switch Active Profile")
        self.btn_switch.setObjectName("btnSuccess")
        self.btn_switch.clicked.connect(self._switch_active)

        self.btn_new = QPushButton("➕ New Profile")
        self.btn_new.setObjectName("btnPrimary")
        self.btn_new.clicked.connect(self._create_profile)

        self.btn_duplicate = QPushButton("📋 Duplicate")
        self.btn_duplicate.setObjectName("btnSecondary")
        self.btn_duplicate.clicked.connect(self._duplicate_profile)

        self.btn_edit = QPushButton("✏️ Edit")
        self.btn_edit.setObjectName("btnSecondary")
        self.btn_edit.clicked.connect(self._edit_profile)

        self.btn_archive = QPushButton("📦 Archive / Unarchive")
        self.btn_archive.setObjectName("btnSecondary")
        self.btn_archive.clicked.connect(self._toggle_archive)

        self.btn_delete = QPushButton("🗑️ Delete")
        self.btn_delete.setObjectName("btnDanger")
        self.btn_delete.clicked.connect(self._delete_profile)

        actions_row.addWidget(self.btn_switch)
        actions_row.addWidget(self.btn_new)
        actions_row.addWidget(self.btn_duplicate)
        actions_row.addWidget(self.btn_edit)
        actions_row.addWidget(self.btn_archive)
        actions_row.addWidget(self.btn_delete)
        p_layout.addLayout(actions_row)

        self.tabs.addTab(tab_profiles, "👤 User Profiles")

        # Tab 2: Custom Phrases Manager
        tab_phrases = QWidget()
        ph_layout = QVBoxLayout(tab_phrases)
        ph_layout.setContentsMargins(14, 14, 14, 14)
        ph_layout.setSpacing(10)

        # Phrase Category selector row
        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Category:"))
        self.combo_cat = QComboBox()
        self.combo_cat.addItems(["common", "needs", "feelings", "people", "places", "actions"])
        self.combo_cat.currentTextChanged.connect(self._load_custom_phrases)
        cat_row.addWidget(self.combo_cat)
        cat_row.addStretch()
        ph_layout.addLayout(cat_row)

        self.table_phrases = QTableWidget()
        self.table_phrases.setColumnCount(4)
        self.table_phrases.setHorizontalHeaderLabels(["Icon", "Label", "Full Spoken Text", "Color"])
        self.table_phrases.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_phrases.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_phrases.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_phrases.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_phrases.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        ph_layout.addWidget(self.table_phrases, stretch=1)

        # Add Custom Phrase Inputs
        ph_form = QFrame()
        ph_form.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        ph_form_layout = QHBoxLayout(ph_form)
        ph_form_layout.setSpacing(8)

        self.txt_ph_icon = QComboBox()
        self.txt_ph_icon.addItems(["💬", "💡", "🥤", "🍎", "🛌", "❤️", "👨‍👩‍👧", "🏡", "🚗", "👋", "🙏", "⚠️"])
        self.txt_ph_icon.setFixedWidth(65)

        self.txt_ph_label = QLineEdit()
        self.txt_ph_label.setPlaceholderText("Card Label")

        self.txt_ph_text = QLineEdit()
        self.txt_ph_text.setPlaceholderText("Spoken Sentence")

        btn_add_phrase = QPushButton("➕ Add Phrase")
        btn_add_phrase.setObjectName("btnPrimary")
        btn_add_phrase.clicked.connect(self._add_custom_phrase)

        btn_del_phrase = QPushButton("🗑️ Delete Selected")
        btn_del_phrase.setObjectName("btnDanger")
        btn_del_phrase.clicked.connect(self._delete_custom_phrase)

        ph_form_layout.addWidget(QLabel("Icon:"))
        ph_form_layout.addWidget(self.txt_ph_icon)
        ph_form_layout.addWidget(QLabel("Label:"))
        ph_form_layout.addWidget(self.txt_ph_label, stretch=1)
        ph_form_layout.addWidget(QLabel("Text:"))
        ph_form_layout.addWidget(self.txt_ph_text, stretch=2)
        ph_form_layout.addWidget(btn_add_phrase)
        ph_form_layout.addWidget(btn_del_phrase)
        ph_layout.addWidget(ph_form)

        self.tabs.addTab(tab_phrases, "💬 Custom Phrases")
        root.addWidget(self.tabs, stretch=1)

        # Bottom Done Button
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_done = QPushButton("Close")
        btn_done.setObjectName("btnSecondary")
        btn_done.clicked.connect(self.accept)
        bottom.addWidget(btn_done)
        root.addLayout(bottom)

    def _load_profiles(self) -> None:
        include_archived = self.chk_show_archived.isChecked()
        self._profiles = self.repo.get_all_profiles(include_archived=include_archived)
        self.table_profiles.setRowCount(len(self._profiles))

        for row, p in enumerate(self._profiles):
            status_str = "🟢 ACTIVE" if p.is_active else "⚪"
            item_status = QTableWidgetItem(status_str)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_name = QTableWidgetItem(f"{p.name}")
            if p.is_active:
                item_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

            item_hand = QTableWidgetItem(p.dominant_hand)
            item_hand.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_dwell = QTableWidgetItem(f"{p.dwell_time:.2f}s")
            item_dwell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_qual = QTableWidgetItem(p.calibration_quality)
            item_qual.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            item_arch = QTableWidgetItem("Yes" if p.is_archived else "No")
            item_arch.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table_profiles.setItem(row, 0, item_status)
            self.table_profiles.setItem(row, 1, item_name)
            self.table_profiles.setItem(row, 2, item_hand)
            self.table_profiles.setItem(row, 3, item_dwell)
            self.table_profiles.setItem(row, 4, item_qual)
            self.table_profiles.setItem(row, 5, item_arch)

        if self._profiles:
            self.table_profiles.selectRow(0)

    def _on_profile_selected(self) -> None:
        selected_rows = self.table_profiles.selectionModel().selectedRows()
        if selected_rows and 0 <= selected_rows[0].row() < len(self._profiles):
            self._selected_profile = self._profiles[selected_rows[0].row()]
            self._load_custom_phrases()
        else:
            self._selected_profile = None

    def _switch_active(self) -> None:
        if not self._selected_profile or self._selected_profile.id is None:
            return
        active_prof = self.repo.set_active_profile(self._selected_profile.id)
        if active_prof:
            self._load_profiles()
            self.profile_switched.emit(active_prof)
            QMessageBox.information(self, "Profile Switched", f"Active user profile is now: {active_prof.name}")

    def _create_profile(self) -> None:
        dlg = ProfileEditorDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_prof = self.repo.create_profile(dlg.profile)
            self._load_profiles()
            QMessageBox.information(self, "Profile Created", f"Successfully created profile: {new_prof.name}")

    def _edit_profile(self) -> None:
        if not self._selected_profile:
            return
        dlg = ProfileEditorDialog(profile=self._selected_profile, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.repo.save_profile(self._selected_profile)
            self._load_profiles()
            if self._selected_profile.is_active:
                self.profile_switched.emit(self._selected_profile)

    def _duplicate_profile(self) -> None:
        if not self._selected_profile or self._selected_profile.id is None:
            return
        new_name = f"{self._selected_profile.name} (Copy)"
        cloned = self.repo.duplicate_profile(self._selected_profile.id, new_name=new_name)
        if cloned:
            self._load_profiles()
            QMessageBox.information(self, "Profile Duplicated", f"Created duplicate profile: {cloned.name}")

    def _toggle_archive(self) -> None:
        if not self._selected_profile or self._selected_profile.id is None:
            return
        new_state = not self._selected_profile.is_archived
        self.repo.archive_profile(self._selected_profile.id, archived=new_state)
        self._load_profiles()
        active = self.repo.get_active_profile()
        self.profile_switched.emit(active)

    def _delete_profile(self) -> None:
        if not self._selected_profile or self._selected_profile.id is None:
            return
        if self._selected_profile.is_active:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the currently active profile. Switch to another profile first.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Are you sure you want to permanently delete profile '{self._selected_profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.repo.delete_profile(self._selected_profile.id)
            self._load_profiles()

    def _export_profile_json(self) -> None:
        if not self._selected_profile or self._selected_profile.id is None:
            QMessageBox.warning(self, "Export", "Select a profile to export first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile Backup (JSON)",
            f"{self._selected_profile.name.replace(' ', '_').lower()}_profile.json",
            "JSON Files (*.json)",
        )
        if path:
            try:
                json_data = self.repo.export_profile_json(self._selected_profile.id)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                QMessageBox.information(self, "Export Success", f"Profile exported successfully to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export profile:\n{e}")

    def _import_profile_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile Backup (JSON)",
            "",
            "JSON Files (*.json)",
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()
                imported = self.repo.import_profile_json(data)
                self._load_profiles()
                QMessageBox.information(self, "Import Success", f"Successfully imported profile:\n{imported.name}")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import profile:\n{e}")

    # -------------------------------------------------------------
    # Custom Phrases Logic
    # -------------------------------------------------------------
    def _load_custom_phrases(self) -> None:
        if not self._selected_profile or self._selected_profile.id is None:
            self.table_phrases.setRowCount(0)
            return

        category = self.combo_cat.currentText()
        phrases = self.repo.get_custom_phrases(self._selected_profile.id, category=category)
        self.table_phrases.setRowCount(len(phrases))

        for row, ph in enumerate(phrases):
            item_icon = QTableWidgetItem(ph.icon)
            item_icon.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_label = QTableWidgetItem(ph.label)
            item_text = QTableWidgetItem(ph.text)
            item_color = QTableWidgetItem(ph.accent_color)
            item_color.setForeground(QColor(ph.accent_color))
            item_color.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table_phrases.setItem(row, 0, item_icon)
            self.table_phrases.setItem(row, 1, item_label)
            self.table_phrases.setItem(row, 2, item_text)
            self.table_phrases.setItem(row, 3, item_color)

    def _add_custom_phrase(self) -> None:
        if not self._selected_profile or self._selected_profile.id is None:
            return
        label = self.txt_ph_label.text().strip()
        text = self.txt_ph_text.text().strip() or label
        icon = self.txt_ph_icon.currentText()
        if not label:
            QMessageBox.warning(self, "Validation", "Phrase label cannot be empty.")
            return

        cp = CustomPhrase(
            profile_id=self._selected_profile.id,
            category=self.combo_cat.currentText(),
            label=label,
            text=text,
            icon=icon,
            accent_color="#38bdf8",
        )
        self.repo.save_custom_phrase(cp)
        self._load_custom_phrases()
        self.txt_ph_label.clear()
        self.txt_ph_text.clear()

    def _delete_custom_phrase(self) -> None:
        selected_rows = self.table_phrases.selectionModel().selectedRows()
        if not selected_rows or not self._selected_profile or self._selected_profile.id is None:
            return
        row = selected_rows[0].row()
        category = self.combo_cat.currentText()
        phrases = self.repo.get_custom_phrases(self._selected_profile.id, category=category)
        if 0 <= row < len(phrases) and phrases[row].id is not None:
            self.repo.delete_custom_phrase(phrases[row].id)
            self._load_custom_phrases()
