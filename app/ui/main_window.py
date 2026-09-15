"""Main application window for EYEVO camera feed, gaze tracking, calibration, cursor, and Communication Board."""

import time
from pathlib import Path
from typing import List, Optional
import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QImage, QPixmap, QResizeEvent
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
from app.config import CONFIG
from app.gaze.calibration_model import CalibrationModel
from app.gaze.gaze_cursor import GazeCursorManager
from app.interaction.dwell_selector import (
    DwellResult,
    DwellSelector,
    DwellSelectorConfig,
    DwellState,
)
from app.ui.calibration_dialog import CALIBRATION_SAVE_PATH, CalibrationDialog
from app.ui.communication_widget import CommunicationWidget
from app.ui.cursor_overlay import CursorOverlay
from app.ui.gaze_button import GazeButton
from app.ui.gaze_widget import GazeWidget
from app.vision.blink_detector import BlinkDetector, BlinkResult
from app.vision.camera import Camera
from app.vision.eye_tracker import EyeTracker
from app.vision.face_detector import FaceDetector
from app.vision.gaze_estimator import GazeEstimator, GazeResult


class MainWindow(QMainWindow):
    """EYEVO desktop interface with live camera feed, gaze tracking, calibration, and Communication Board."""

    def __init__(self) -> None:
        super().__init__()
        self.camera = Camera(device_index=0)
        self.face_detector = FaceDetector()
        self.eye_tracker = EyeTracker()
        self.blink_detector = BlinkDetector()
        self.gaze_estimator = GazeEstimator()
        self.calibration_model = CalibrationModel()
        self.cursor_manager = GazeCursorManager()
        self.dwell_selector = DwellSelector(DwellSelectorConfig(dwell_time_sec=0.80, cooldown_sec=0.60))
        self.comm_model = CommunicationBoardModel()

        # Load saved calibration if present
        if CALIBRATION_SAVE_PATH.exists():
            self.calibration_model.load_from_json(CALIBRATION_SAVE_PATH)

        self.calibration_dialog: CalibrationDialog | None = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

        # Blink flash timer tracking
        self._last_blink_display_time: float = 0.0

        self._init_window()
        self._init_ui()

        # Bind Dwell Selector to the Communication Board
        self.comm_widget.set_dwell_engine(self.dwell_selector, self)

        # Transparent overlay for virtual gaze cursor and dwell feedback
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
            QPushButton#btnAction { background-color: #0d9488; color: #ffffff; font-size: 12px; }
            QPushButton#btnAction:hover { background-color: #0f766e; }
            QPushButton#btnTabActive { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnTabInactive { background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; }
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

        # Primary status indicators
        status_box = QHBoxLayout()
        status_box.setSpacing(8)

        self.camera_status_label = QLabel("Camera Ready")
        self._set_badge(self.camera_status_label, "Camera Ready", "#38bdf8")

        self.tracking_status_label = QLabel("NO FACE DETECTED")
        self._set_badge(self.tracking_status_label, "NO FACE DETECTED", "#64748b")

        self.cursor_status_label = QLabel("● Tracking Lost")
        self._set_badge(self.cursor_status_label, "● Tracking Lost", "#64748b")

        self.calib_status_label = QLabel("Calibration: Off")
        self._update_calib_badge()

        status_box.addWidget(self.camera_status_label)
        status_box.addWidget(self.tracking_status_label)
        status_box.addWidget(self.cursor_status_label)
        status_box.addWidget(self.calib_status_label)

        header.addLayout(header_text)
        header.addStretch()
        header.addLayout(status_box)

        # 2. Main View Switcher Tabs ([💬 Communication Board] & [📹 Camera / Diagnostic])
        view_tabs = QHBoxLayout()
        view_tabs.setSpacing(8)

        self.btn_view_comm = QPushButton("💬 Communication Board")
        self.btn_view_comm.setObjectName("btnTabActive")
        self.btn_view_comm.clicked.connect(lambda: self._switch_view(0))

        self.btn_view_camera = QPushButton("📹 Camera & Diagnostics")
        self.btn_view_camera.setObjectName("btnTabInactive")
        self.btn_view_camera.clicked.connect(lambda: self._switch_view(1))

        view_tabs.addWidget(self.btn_view_comm)
        view_tabs.addWidget(self.btn_view_camera)
        view_tabs.addStretch()

        # Stacked Views Container
        self.view_stack = QStackedWidget()

        # Page 0: Communication Board View
        self.comm_widget = CommunicationWidget(model=self.comm_model)
        self.view_stack.addWidget(self.comm_widget)

        # Page 1: Camera Feed & Diagnostics View
        camera_page = QWidget()
        cam_layout = QVBoxLayout(camera_page)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.setSpacing(8)

        self.preview_label = QLabel("Camera Offline — Click 'Start Camera' to begin")
        self.preview_label.setObjectName("preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(480, 240)

        diag_layout = QHBoxLayout()
        self.gaze_widget = GazeWidget()

        eye_status_frame = QFrame()
        eye_status_frame.setObjectName("statusBar")
        eye_layout = QVBoxLayout(eye_status_frame)
        eye_layout.setContentsMargins(12, 10, 12, 10)
        eye_layout.setSpacing(6)

        lbl_eye_title = QLabel("EYE & BLINK TELEMETRY")
        lbl_eye_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")

        self.lbl_left_eye = QLabel("LEFT EYE: --")
        self.lbl_left_eye.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        self.lbl_right_eye = QLabel("RIGHT EYE: --")
        self.lbl_right_eye.setStyleSheet("color: #cbd5e1; font-size: 12px;")

        self.lbl_blink_counter = QLabel("Blinks: 0")
        self.lbl_blink_counter.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")

        self.blink_status_badge = QLabel("EYES IDLE")
        self._set_badge(self.blink_status_badge, "EYES IDLE", "#64748b")

        eye_layout.addWidget(lbl_eye_title)
        eye_layout.addWidget(self.lbl_left_eye)
        eye_layout.addWidget(self.lbl_right_eye)
        eye_layout.addWidget(self.lbl_blink_counter)
        eye_layout.addWidget(self.blink_status_badge)
        eye_layout.addStretch()

        diag_layout.addWidget(self.gaze_widget, stretch=1)
        diag_layout.addWidget(eye_status_frame, stretch=1)

        cam_layout.addWidget(self.preview_label, stretch=2)
        cam_layout.addLayout(diag_layout, stretch=1)

        self.view_stack.addWidget(camera_page)

        # 3. Bottom Control Bar
        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.btn_start = QPushButton("Start Camera")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_camera)

        self.btn_stop = QPushButton("Stop Camera")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_camera)

        self.btn_calibrate = QPushButton("Calibrate Gaze")
        self.btn_calibrate.setObjectName("btnCalibrate")
        self.btn_calibrate.setEnabled(False)
        self.btn_calibrate.clicked.connect(self.open_calibration)

        self.btn_recenter = QPushButton("Center Gaze")
        self.btn_recenter.setObjectName("btnAction")
        self.btn_recenter.setToolTip("Click while looking at center to zero baseline")
        self.btn_recenter.clicked.connect(self._recenter_gaze)

        self.btn_sensitivity = QPushButton("Sensitivity: Normal")
        self.btn_sensitivity.setObjectName("btnToggle")
        self.btn_sensitivity.clicked.connect(self._cycle_sensitivity)

        self.btn_toggle_cursor = QPushButton("Gaze Cursor: ON")
        self.btn_toggle_cursor.setObjectName("btnToggle")
        self.btn_toggle_cursor.clicked.connect(self._toggle_cursor)

        self.btn_toggle_debug = QPushButton("Debug HUD: OFF")
        self.btn_toggle_debug.setObjectName("btnToggle")
        self.btn_toggle_debug.clicked.connect(self._toggle_debug)

        controls.addWidget(self.btn_start)
        controls.addWidget(self.btn_stop)
        controls.addWidget(self.btn_calibrate)
        controls.addWidget(self.btn_recenter)
        controls.addStretch()
        controls.addWidget(self.btn_sensitivity)
        controls.addWidget(self.btn_toggle_cursor)
        controls.addWidget(self.btn_toggle_debug)

        root_layout.addLayout(header)
        root_layout.addLayout(view_tabs)
        root_layout.addWidget(self.view_stack, stretch=1)
        root_layout.addLayout(controls)

        self.setCentralWidget(central)

    def _switch_view(self, index: int) -> None:
        """Switch between Communication Board and Camera Diagnostic view."""
        self.view_stack.setCurrentIndex(index)
        if index == 0:
            self.btn_view_comm.setObjectName("btnTabActive")
            self.btn_view_camera.setObjectName("btnTabInactive")
            self.comm_widget.register_all_targets()
        else:
            self.btn_view_comm.setObjectName("btnTabInactive")
            self.btn_view_camera.setObjectName("btnTabActive")
            self.dwell_selector.clear_targets()

        self.btn_view_comm.setStyle(self.btn_view_comm.style())
        self.btn_view_camera.setStyle(self.btn_view_camera.style())

    def _set_badge(self, label: QLabel, text: str, color: str) -> None:
        label.setText(text)
        label.setStyleSheet(
            f"color: {color}; background-color: rgba(255,255,255,0.05); "
            f"border: 1px solid {color}; border-radius: 12px; padding: 3px 10px; font-weight: 600; font-size: 11px;"
        )

    def _update_calib_badge(self) -> None:
        if self.calibration_model.is_trained:
            q = self.calibration_model.metrics.quality
            color = "#22c55e" if q in ("EXCELLENT", "GOOD") else "#f59e0b"
            self._set_badge(self.calib_status_label, f"Calibrated ({q})", color)
        else:
            self._set_badge(self.calib_status_label, "Not Calibrated", "#64748b")

    def _cycle_sensitivity(self) -> None:
        cycle_order = ["NORMAL", "HIGH", "ULTRA", "LOW"]
        cur_idx = cycle_order.index(self.gaze_estimator.sensitivity_mode) if self.gaze_estimator.sensitivity_mode in cycle_order else 0
        next_mode = cycle_order[(cur_idx + 1) % len(cycle_order)]
        self.gaze_estimator.set_sensitivity_preset(next_mode)
        self.btn_sensitivity.setText(f"Sensitivity: {next_mode.capitalize()}")

    def _recenter_gaze(self) -> None:
        self.gaze_estimator.recenter_baseline()

    def _toggle_cursor(self) -> None:
        new_state = not self.cursor_manager.is_enabled
        self.cursor_manager.set_enabled(new_state)
        self.btn_toggle_cursor.setText(f"Gaze Cursor: {'ON' if new_state else 'OFF'}")

    def _toggle_debug(self) -> None:
        new_state = not self.cursor_overlay.show_debug
        self.cursor_overlay.set_debug_mode(new_state)
        self.btn_toggle_debug.setText(f"Debug HUD: {'ON' if new_state else 'OFF'}")

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep cursor overlay and targets matched to window dimensions."""
        super().resizeEvent(event)
        if hasattr(self, "cursor_overlay"):
            self.cursor_overlay.setGeometry(self.rect())
        if hasattr(self, "comm_widget"):
            self.comm_widget.register_all_targets()

    def start_camera(self) -> None:
        """Start camera feed and timer."""
        if self.camera.open():
            self.timer.start(33)  # ~30 FPS
            self._set_badge(self.camera_status_label, "Camera Active", "#22c55e")
            self._set_badge(self.tracking_status_label, "NO FACE DETECTED", "#f59e0b")
            self._set_badge(self.blink_status_badge, "EYES OPEN", "#38bdf8")
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_calibrate.setEnabled(True)
        else:
            self._set_badge(self.camera_status_label, "Camera Error", "#ef4444")
            self.preview_label.setText("Failed to open camera. Check device availability.")

    def stop_camera(self) -> None:
        """Stop camera feed and release hardware."""
        self.timer.stop()
        self.camera.release()
        self.blink_detector.reset()
        self.gaze_estimator.reset()
        self.cursor_manager.reset()
        self.dwell_selector.reset()
        self.gaze_widget.update_gaze(GazeResult(tracking_valid=False))
        self.cursor_overlay.update_cursor(self.cursor_manager._last_position, None, None)
        self.comm_widget.update_all_dwell_feedbacks(None, 0.0, False)

        self.preview_label.clear()
        self.preview_label.setText("Camera Offline — Click 'Start Camera' to begin")
        self._set_badge(self.camera_status_label, "Camera Ready", "#38bdf8")
        self._set_badge(self.tracking_status_label, "NO FACE DETECTED", "#64748b")
        self._set_badge(self.blink_status_badge, "EYES IDLE", "#64748b")
        self._set_badge(self.cursor_status_label, "● Tracking Lost", "#64748b")
        self.lbl_left_eye.setText("LEFT EYE: --")
        self.lbl_right_eye.setText("RIGHT EYE: --")
        self.lbl_blink_counter.setText("Blinks: 0")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_calibrate.setEnabled(False)

    def open_calibration(self) -> None:
        """Launch the 9-point calibration modal."""
        self.calibration_dialog = CalibrationDialog(self)
        self.calibration_dialog.calibration_finished.connect(self._on_calibration_finished)
        self.calibration_dialog.exec()
        self.calibration_dialog = None

    def _on_calibration_finished(self, model: CalibrationModel) -> None:
        """Receive calibrated regression model."""
        self.calibration_model = model
        self._update_calib_badge()

    def _update_frame(self) -> None:
        """Read, process landmarks, track gaze, update cursor, dwell selector, and Communication Board."""
        now = time.perf_counter()
        success, frame = self.camera.read_frame()
        if not success or frame is None:
            self._set_badge(self.camera_status_label, "Camera Error", "#ef4444")
            self.preview_label.setText("Error reading camera frame.")
            self.stop_camera()
            return

        h, w = frame.shape[:2]

        # 1. Face landmark detection
        face_detected, display_frame, _, norm_landmarks = self.face_detector.process_frame(frame)

        # 2. Eye/Iris tracking, Blink detection, & Gaze estimation
        if face_detected:
            eye_data = self.eye_tracker.extract(norm_landmarks, w, h)
            blink_res = self.blink_detector.process(norm_landmarks, current_time=now)
            eyes_open = blink_res.left_open and blink_res.right_open
            gaze_res = self.gaze_estimator.estimate(norm_landmarks, eyes_open=eyes_open)

            # Stream sample to calibration dialog if active
            if self.calibration_dialog is not None and self.calibration_dialog.isVisible():
                self.calibration_dialog.process_gaze_sample(gaze_res)

            if eye_data.detected:
                display_frame = self.eye_tracker.draw_overlay(display_frame, eye_data)
                self._set_badge(self.tracking_status_label, "EYES DETECTED", "#22c55e")
            else:
                self._set_badge(self.tracking_status_label, "FACE DETECTED", "#38bdf8")

            # Update Virtual Gaze Cursor
            cursor_pos = self.cursor_manager.update(
                gaze_x=gaze_res.smoothed_gaze_x,
                gaze_y=gaze_res.smoothed_gaze_y,
                tracking_valid=gaze_res.tracking_valid,
                calibration_model=self.calibration_model,
                window_w=self.width(),
                window_h=self.height(),
            )

            # Update Gaze Dwell Interaction Engine
            dwell_res = self.dwell_selector.update(
                cursor_px=(cursor_pos.pixel_x, cursor_pos.pixel_y),
                tracking_valid=cursor_pos.is_valid,
                confidence=gaze_res.confidence,
                current_time=now,
            )

            # Update Communication Board visual dwell states
            self.comm_widget.update_all_dwell_feedbacks(
                target_id=dwell_res.target_id,
                progress=dwell_res.progress,
                is_cooldown=(dwell_res.state == DwellState.COOLDOWN),
            )

            self.cursor_overlay.update_cursor(cursor_pos, gaze_res, dwell_res)

            if cursor_pos.is_valid:
                self._set_badge(self.cursor_status_label, "● Gaze Tracking", "#22c55e")
            else:
                self._set_badge(self.cursor_status_label, "● Tracking Lost", "#f59e0b")

            # Update Gaze visualizer
            self.gaze_widget.update_gaze(gaze_res)

            # Update eye openness labels
            left_status = "OPEN" if blink_res.left_open else "CLOSED"
            right_status = "OPEN" if blink_res.right_open else "CLOSED"
            self.lbl_left_eye.setText(f"LEFT EYE: {left_status} ({blink_res.left_ear:.2f})")
            self.lbl_right_eye.setText(f"RIGHT EYE: {right_status} ({blink_res.right_ear:.2f})")
            self.lbl_blink_counter.setText(f"Blinks: {blink_res.blink_count}")

            # Blink event handling
            if blink_res.blink_detected:
                self._last_blink_display_time = now

            if now - self._last_blink_display_time < 0.40:
                self._set_badge(self.blink_status_badge, "BLINK DETECTED", "#10b981")
            elif not blink_res.left_open and not blink_res.right_open:
                self._set_badge(self.blink_status_badge, "EYES CLOSED", "#f59e0b")
            else:
                self._set_badge(self.blink_status_badge, "EYES OPEN", "#38bdf8")
        else:
            self._set_badge(self.tracking_status_label, "NO FACE DETECTED", "#f59e0b")
            self._set_badge(self.blink_status_badge, "NO EYES", "#64748b")
            self._set_badge(self.cursor_status_label, "● Tracking Lost", "#64748b")
            self.lbl_left_eye.setText("LEFT EYE: --")
            self.lbl_right_eye.setText("RIGHT EYE: --")
            self.gaze_widget.update_gaze(GazeResult(tracking_valid=False))

            cursor_pos = self.cursor_manager.update(0.5, 0.5, False, None, self.width(), self.height())
            dwell_res = self.dwell_selector.update((0.0, 0.0), tracking_valid=False, confidence=0.0, current_time=now)
            self.comm_widget.update_all_dwell_feedbacks(None, 0.0, False)
            self.cursor_overlay.update_cursor(cursor_pos, None, dwell_res)

        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(pixmap)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure clean resource cleanup upon window closure."""
        self.stop_camera()
        self.face_detector.close()
        super().closeEvent(event)
