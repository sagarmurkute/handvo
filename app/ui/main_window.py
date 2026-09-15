"""Main application window for HANDVO hand tracking, interaction, and Communication Board."""

import time
from typing import Optional
import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QImage, QKeyEvent, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.communication.communication_board import CommunicationBoardModel
from app.communication.emergency_model import EmergencyManager
from app.config import CONFIG
from app.database.database import Database
from app.database.models import UserProfile
from app.database.profile_repository import ProfileRepository
from app.gestures.cursor import HandCursorManager
from app.gestures.dwell import DwellSelector
from app.gestures.pinch import PinchDetector
from app.ui.communication_widget import CommunicationWidget
from app.ui.cursor_overlay import CursorOverlay
from app.ui.emergency_widget import EmergencyWidget
from app.ui.profile_manager_dialog import ProfileManagerDialog
from app.vision.camera import Camera
from app.vision.hand_detector import HandDetector


class MainWindow(QMainWindow):
    """HANDVO desktop interface with live camera feed, hand tracking, cursor, and Communication Board."""

    def __init__(self) -> None:
        super().__init__()
        self.repo = ProfileRepository(Database())
        self.active_profile = self.repo.get_active_profile()

        self.camera = Camera(device_index=0)
        self.hand_detector = HandDetector()
        self.cursor_manager = HandCursorManager()
        self.pinch_detector = PinchDetector()
        self.dwell_selector = DwellSelector(
            dwell_time_sec=self.active_profile.dwell_time,
            cooldown_sec=0.60,
        )
        self.comm_model = CommunicationBoardModel()
        self.emergency_mgr = EmergencyManager(repository=self.repo)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

        self._init_window()
        self._init_ui()

        # Bind Dwell Selector to the Communication Board
        self.comm_widget.set_dwell_engine(self.dwell_selector, self)
        self.emergency_widget.set_dwell_engine(self.dwell_selector, self)
        self.comm_widget.register_all_targets()

        # Transparent overlay for virtual cursor and dwell feedback
        self.cursor_overlay = CursorOverlay(self)
        self.cursor_overlay.setGeometry(self.rect())
        self.cursor_overlay.show()

    def _init_window(self) -> None:
        self.setWindowTitle(CONFIG.window_title)
        self.resize(1024, 720)
        self.setMinimumSize(880, 620)
        self.setStyleSheet(
            """
            QMainWindow { background-color: #0f172a; }
            QLabel#title { color: #38bdf8; font-size: 22px; font-weight: bold; }
            QLabel#subtitle { color: #94a3b8; font-size: 13px; }
            QLabel#preview {
                background-color: #1e293b;
                border: 2px solid #334155;
                border-radius: 8px;
                color: #64748b;
                font-size: 14px;
            }
            QFrame#statusBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QPushButton {
                font-size: 13px;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton#btnStart { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnStart:hover { background-color: #0369a1; }
            QPushButton#btnStart:disabled { background-color: #334155; color: #64748b; }
            QPushButton#btnStop { background-color: #ef4444; color: #ffffff; }
            QPushButton#btnStop:hover { background-color: #dc2626; }
            QPushButton#btnStop:disabled { background-color: #334155; color: #64748b; }
            QPushButton#btnCalibrate { background-color: #6366f1; color: #ffffff; }
            QPushButton#btnCalibrate:hover { background-color: #4f46e5; }
            QPushButton#btnCalibrate:disabled { background-color: #334155; color: #64748b; }
            QPushButton#btnToggle { background-color: #334155; color: #e2e8f0; font-size: 12px; }
            QPushButton#btnToggle:hover { background-color: #475569; }
            QPushButton#btnTabActive { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnTabInactive { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; }
            QPushButton#btnEmergencyTab { background-color: #dc2626; color: #ffffff; font-weight: bold; }
            QPushButton#btnEmergencyTab:hover { background-color: #ef4444; }
            """
        )

    def _init_ui(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 12, 18, 12)
        root_layout.setSpacing(10)

        # 1. Header bar
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel(CONFIG.app_name)
        title.setObjectName("title")
        subtitle = QLabel(CONFIG.app_subtitle)
        subtitle.setObjectName("subtitle")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)

        # Status indicators
        status_box = QHBoxLayout()
        status_box.setSpacing(8)

        self.camera_status_label = QLabel("Camera Ready")
        self._set_badge(self.camera_status_label, "Camera Ready", "#38bdf8")

        self.tracking_status_label = QLabel("NO HAND DETECTED")
        self._set_badge(self.tracking_status_label, "NO HAND DETECTED", "#64748b")

        self.pinch_status_label = QLabel("PINCH IDLE")
        self._set_badge(self.pinch_status_label, "PINCH IDLE", "#64748b")

        self.cursor_status_label = QLabel("● Tracking Lost")
        self._set_badge(self.cursor_status_label, "● Tracking Lost", "#64748b")

        status_box.addWidget(self.camera_status_label)
        status_box.addWidget(self.tracking_status_label)
        status_box.addWidget(self.pinch_status_label)
        status_box.addWidget(self.cursor_status_label)

        self.btn_profile = QPushButton(f"👤 {self.active_profile.name}")
        self.btn_profile.setObjectName("btnToggle")
        self.btn_profile.setToolTip("Open Caregiver Profile Manager")
        self.btn_profile.clicked.connect(self.open_profile_manager)

        header.addLayout(header_text)
        header.addStretch()
        header.addWidget(self.btn_profile)
        header.addLayout(status_box)

        # 2. View Switcher Tabs
        view_tabs = QHBoxLayout()
        view_tabs.setSpacing(8)

        self.btn_view_comm = QPushButton("💬 Communication Board")
        self.btn_view_comm.setObjectName("btnTabActive")
        self.btn_view_comm.clicked.connect(lambda: self._switch_view(0))

        self.btn_view_camera = QPushButton("📹 Camera & Vision")
        self.btn_view_camera.setObjectName("btnTabInactive")
        self.btn_view_camera.clicked.connect(lambda: self._switch_view(1))

        self.btn_view_emergency = QPushButton("🚨 EMERGENCY (F1)")
        self.btn_view_emergency.setObjectName("btnEmergencyTab")
        self.btn_view_emergency.clicked.connect(lambda: self._switch_view(2))

        view_tabs.addWidget(self.btn_view_comm)
        view_tabs.addWidget(self.btn_view_camera)
        view_tabs.addStretch()
        view_tabs.addWidget(self.btn_view_emergency)

        # Stacked Container
        self.view_stack = QStackedWidget()

        # Page 0: Communication Board View
        self.comm_widget = CommunicationWidget(model=self.comm_model)
        self.view_stack.addWidget(self.comm_widget)

        # Page 1: Camera Feed View
        camera_page = QWidget()
        cam_layout = QVBoxLayout(camera_page)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(8)

        self.preview_label = QLabel("Camera Offline — Click 'Start Camera' to begin")
        self.preview_label.setObjectName("preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(480, 240)

        cam_layout.addWidget(self.preview_label, stretch=1)
        self.view_stack.addWidget(camera_page)

        # Page 2: Emergency Mode View
        self.emergency_widget = EmergencyWidget(emergency_mgr=self.emergency_mgr)
        self.emergency_widget.exit_requested.connect(lambda: self._switch_view(0))
        self.view_stack.addWidget(self.emergency_widget)

        # 3. Bottom Controls
        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.btn_start = QPushButton("Start Camera")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_camera)

        self.btn_stop = QPushButton("Stop Camera")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_camera)

        self.btn_calibrate = QPushButton("Calibrate Hand")
        self.btn_calibrate.setObjectName("btnCalibrate")
        self.btn_calibrate.clicked.connect(self.open_calibration)

        self.btn_toggle_cursor = QPushButton("Cursor: ON")
        self.btn_toggle_cursor.setObjectName("btnToggle")
        self.btn_toggle_cursor.clicked.connect(self._toggle_cursor)

        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_stop)
        controls.addWidget(self.btn_calibrate)
        controls.addStretch()
        controls.addWidget(self.btn_toggle_cursor)

        root_layout.addLayout(header)
        root_layout.addLayout(view_tabs)
        root_layout.addWidget(self.view_stack, stretch=1)
        root_layout.addLayout(controls)

        self.setCentralWidget(central)

    def _switch_view(self, index: int) -> None:
        self.view_stack.setCurrentIndex(index)
        if index == 0:
            self.btn_view_comm.setObjectName("btnTabActive")
            self.btn_view_camera.setObjectName("btnTabInactive")
            self.comm_widget.register_all_targets()
        elif index == 1:
            self.btn_view_comm.setObjectName("btnTabInactive")
            self.btn_view_camera.setObjectName("btnTabActive")
            self.dwell_selector.clear_targets()
        elif index == 2:
            self.btn_view_comm.setObjectName("btnTabInactive")
            self.btn_view_camera.setObjectName("btnTabInactive")
            self.emergency_widget.register_all_targets()

        self.btn_view_comm.setStyle(self.btn_view_comm.style())
        self.btn_view_camera.setStyle(self.btn_view_camera.style())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_F1:
            if self.view_stack.currentIndex() == 2:
                self._switch_view(0)
            else:
                self._switch_view(2)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _set_badge(self, label: QLabel, text: str, color: str) -> None:
        label.setText(text)
        label.setStyleSheet(
            f"color: {color}; background-color: rgba(255,255,255,0.05); "
            f"border: 1px solid {color}; border-radius: 12px; padding: 3px 10px; font-weight: 600; font-size: 11px;"
        )

    def _toggle_cursor(self) -> None:
        new_state = not self.cursor_manager.is_enabled
        self.cursor_manager.is_enabled = new_state
        self.btn_toggle_cursor.setText(f"Cursor: {'ON' if new_state else 'OFF'}")

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "cursor_overlay"):
            self.cursor_overlay.setGeometry(self.rect())
        if self.view_stack.currentIndex() == 0 and hasattr(self, "comm_widget"):
            self.comm_widget.register_all_targets()
        elif self.view_stack.currentIndex() == 2 and hasattr(self, "emergency_widget"):
            self.emergency_widget.register_all_targets()

    def start_camera(self) -> None:
        if self.camera.open():
            self.timer.start(33)  # ~30 FPS
            self._set_badge(self.camera_status_label, "Camera Active", "#22c55e")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
        else:
            self._set_badge(self.camera_status_label, "Camera Error", "#ef4444")
            self.preview_label.setText("Failed to open camera. Check device availability.")

    def stop_camera(self) -> None:
        self.timer.stop()
        self.camera.release()
        self.cursor_manager.reset()
        self.dwell_selector.reset()
        self.pinch_detector.reset()

        self.preview_label.clear()
        self.preview_label.setText("Camera Offline — Click 'Start Camera' to begin")
        self._set_badge(self.camera_status_label, "Camera Ready", "#38bdf8")
        self._set_badge(self.tracking_status_label, "NO HAND DETECTED", "#64748b")
        self._set_badge(self.pinch_status_label, "PINCH IDLE", "#64748b")
        self._set_badge(self.cursor_status_label, "● Tracking Lost", "#64748b")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def open_calibration(self) -> None:
        from app.ui.hand_calibration_dialog import HandCalibrationDialog
        was_running = self.timer.isActive()
        if was_running:
            self.timer.stop()
            self.camera.release()

        dlg = HandCalibrationDialog(self)
        dlg.exec()

        if was_running:
            self.start_camera()

    def open_profile_manager(self) -> None:
        dlg = ProfileManagerDialog(repository=self.repo, parent=self)
        dlg.profile_switched.connect(self._on_profile_switched)
        dlg.exec()

    def _on_profile_switched(self, new_profile: UserProfile) -> None:
        self.active_profile = new_profile
        self.btn_profile.setText(f"👤 {new_profile.name}")
        self.dwell_selector.dwell_time = new_profile.dwell_time
        if hasattr(self, "comm_widget"):
            self.comm_widget.register_all_targets()
        if hasattr(self, "emergency_widget"):
            self.emergency_widget.register_all_targets()


    def _update_frame(self) -> None:
        now = time.perf_counter()
        success, frame = self.camera.read_frame()
        if not success or frame is None:
            self.stop_camera()
            return

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands = self.hand_detector.detect(rgb)
        annotated = self.hand_detector.draw_skeleton(frame, hands)

        primary_hand = hands[0] if len(hands) > 0 else None

        if primary_hand and primary_hand.is_valid:
            self._set_badge(self.tracking_status_label, f"{primary_hand.handedness.upper()} HAND", "#22c55e")

            # Cursor update
            cursor_pos = self.cursor_manager.update(primary_hand, self.width(), self.height())
            if cursor_pos.is_valid:
                self._set_badge(self.cursor_status_label, "● Hand Tracking", "#22c55e")
            else:
                self._set_badge(self.cursor_status_label, "● Tracking Lost", "#64748b")

            # Pinch detection
            pinch_res = self.pinch_detector.detect(primary_hand)
            if pinch_res.is_pinched:
                self._set_badge(self.pinch_status_label, "PINCH ACTIVE", "#10b981")
            else:
                self._set_badge(self.pinch_status_label, "PINCH IDLE", "#64748b")

            # Dwell selection update
            dwell_res = self.dwell_selector.update(
                cursor_px=(cursor_pos.pixel_x, cursor_pos.pixel_y),
                tracking_valid=cursor_pos.is_valid,
                current_time=now,
            )

            # Update visual dwell states on active view
            is_cooldown = (dwell_res.state.name == "COOLDOWN")
            if self.view_stack.currentIndex() == 0:
                self.comm_widget.update_all_dwell_feedbacks(
                    target_id=dwell_res.target_id,
                    progress=dwell_res.progress,
                    is_cooldown=is_cooldown,
                )
            elif self.view_stack.currentIndex() == 2:
                self.emergency_widget.update_all_dwell_feedbacks(
                    target_id=dwell_res.target_id,
                    progress=dwell_res.progress,
                    is_cooldown=is_cooldown,
                )

            self.cursor_overlay.update_cursor(cursor_pos, dwell_res)
        else:
            self._set_badge(self.tracking_status_label, "NO HAND DETECTED", "#64748b")
            self._set_badge(self.pinch_status_label, "PINCH IDLE", "#64748b")
            self._set_badge(self.cursor_status_label, "● Tracking Lost", "#64748b")
            cursor_pos = self.cursor_manager.update(None, self.width(), self.height())
            dwell_res = self.dwell_selector.update((0, 0), tracking_valid=False, current_time=now)
            if self.view_stack.currentIndex() == 0:
                self.comm_widget.update_all_dwell_feedbacks(None, 0.0, False)
            elif self.view_stack.currentIndex() == 2:
                self.emergency_widget.update_all_dwell_feedbacks(None, 0.0, False)
            self.cursor_overlay.update_cursor(cursor_pos, dwell_res)

        rgb_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(pixmap)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.stop_camera()
        self.hand_detector.close()
        super().closeEvent(event)
