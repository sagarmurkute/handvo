"""Full-screen 5-step guided Hand Calibration Dialog for HANDVO."""

import math
import time
from typing import List, Optional, Tuple
import cv2
import numpy as np

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QCloseEvent,
    QColor,
    QFont,
    QImage,
    QPaintEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.calibration.hand_calibration_model import (
    HandCalibrationData,
    HandCalibrationEngine,
)
from app.database.database import Database
from app.database.models import UserProfile
from app.database.profile_repository import ProfileRepository
from app.gestures.cursor import CursorPosition, HandCursorManager
from app.gestures.dwell import DwellResult, DwellSelector, DwellTarget
from app.gestures.pinch import PinchDetector, PinchState
from app.vision.camera import Camera
from app.vision.hand_detector import HandDetector
from app.vision.landmarks import HandLandmarks


class CalibrationCanvas(QLabel):
    """Custom canvas rendering the camera feed along with step-specific overlays and visual targets."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(540, 360)
        self.setStyleSheet(
            """
            background-color: #0b0f19;
            border: 2px solid #1e293b;
            border-radius: 12px;
            """
        )
        self.step_index: int = 1
        self.neutral_samples: List[Tuple[float, float]] = []
        self.range_samples: List[Tuple[float, float]] = []
        self.current_cursor: Optional[Tuple[float, float]] = None
        self.countdown_progress: float = 0.0
        self.current_bounds: Optional[Tuple[float, float, float, float]] = None
        self.validation_targets: List[Tuple[str, QRectF, bool]] = []
        self.test_cursor_px: Optional[Tuple[int, int]] = None
        self.pinch_active: bool = False

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()

        # Step 2: Draw Neutral Target Ring & Countdown Arc
        if self.step_index == 2:
            cx, cy = w / 2.0, h / 2.0
            # Target base
            painter.setPen(QPen(QColor(56, 189, 248, 60), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(56, 189, 248, 15)))
            painter.drawEllipse(QPointF(cx, cy), 45, 45)

            # Circular Countdown Arc
            if self.countdown_progress > 0.0:
                arc_rect = QRectF(cx - 55, cy - 55, 110, 110)
                pen = QPen(QColor("#22c55e"), 4)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                start_angle = 90 * 16
                span_angle = int(-self.countdown_progress * 360 * 16)
                painter.drawArc(arc_rect, start_angle, span_angle)

        # Step 3: Draw Range Bounding Box and 4 Extent Targets
        elif self.step_index == 3:
            # 4 Corner Guide Targets
            corners = [
                (w * 0.20, h * 0.20, "Top-Left"),
                (w * 0.80, h * 0.20, "Top-Right"),
                (w * 0.20, h * 0.80, "Bottom-Left"),
                (w * 0.80, h * 0.80, "Bottom-Right"),
            ]
            for cx, cy, label in corners:
                painter.setPen(QPen(QColor(99, 102, 241, 100), 1.5, Qt.PenStyle.DashLine))
                painter.setBrush(QBrush(QColor(99, 102, 241, 20)))
                painter.drawEllipse(QPointF(cx, cy), 30, 30)

            # Draw expanding live range bounding box
            if self.current_bounds is not None:
                min_x, max_x, min_y, max_y = self.current_bounds
                bx = min_x * w
                by = min_y * h
                bw = (max_x - min_x) * w
                bh = (max_y - min_y) * h

                box_rect = QRectF(bx, by, bw, bh)
                painter.setPen(QPen(QColor("#38bdf8"), 2))
                painter.setBrush(QBrush(QColor(56, 189, 248, 20)))
                painter.drawRoundedRect(box_rect, 8, 8)

        # Step 5: Draw Interactive Validation Playground Targets
        elif self.step_index == 5:
            for tid, rect, hit in self.validation_targets:
                color = QColor("#22c55e") if hit else QColor("#6366f1")
                bg_color = QColor(34, 197, 94, 60) if hit else QColor(99, 102, 241, 30)
                painter.setPen(QPen(color, 2))
                painter.setBrush(QBrush(bg_color))
                painter.drawRoundedRect(rect, 8, 8)

                painter.setPen(QColor("#ffffff"))
                painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, tid.upper())

            # Draw test cursor
            if self.test_cursor_px:
                tx, ty = self.test_cursor_px
                c_color = QColor("#10b981") if self.pinch_active else QColor("#38bdf8")
                painter.setPen(QPen(c_color, 2))
                painter.setBrush(QBrush(c_color))
                painter.drawEllipse(QPointF(tx, ty), 8, 8)


class HandCalibrationDialog(QDialog):
    """Full-screen 5-step guided calibration experience for HANDVO."""

    calibration_saved = Signal(HandCalibrationData)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("HANDVO — Hand Calibration System")
        self.setModal(True)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setStyleSheet(
            """
            QDialog { background-color: #090d16; color: #f8fafc; }
            QLabel { color: #f8fafc; }
            QPushButton {
                font-size: 13px;
                font-weight: 600;
                padding: 10px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#btnPrimary { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnPrimary:hover { background-color: #0369a1; }
            QPushButton#btnPrimary:disabled { background-color: #1e293b; color: #64748b; }
            QPushButton#btnSuccess { background-color: #10b981; color: #ffffff; }
            QPushButton#btnSuccess:hover { background-color: #059669; }
            QPushButton#btnSecondary { background-color: #1e293b; color: #cbd5e1; border: 1px solid #334155; }
            QPushButton#btnSecondary:hover { background-color: #334155; }
            QFrame#card {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 12px;
                padding: 16px;
            }
            """
        )

        # Core Engines
        self.camera = Camera(device_index=0)
        self.hand_detector = HandDetector()
        self.pinch_detector = PinchDetector()
        self.cursor_manager = HandCursorManager()
        self.db_repo = ProfileRepository(Database())

        # Calibration State
        self.step = 1  # 1 to 5
        self.dominant_hand = "Right"
        self.neutral_samples: List[Tuple[float, float]] = []
        self.range_samples: List[Tuple[float, float]] = []
        self.open_span_samples: List[float] = []
        self.pinch_dist_samples: List[float] = []
        self.calib_data = HandCalibrationData()

        # Step capturing flags & timers
        self._is_capturing = False
        self._capture_start_time = 0.0
        self._capture_duration = 2.5  # seconds
        self._pinch_substep = "open"  # "open" -> "pinch"

        # Validation playground hit targets
        self._validation_hits = {"target_1": False, "target_2": False, "target_3": False, "target_4": False}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_loop)

        self._init_ui()
        self._start_session()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 20, 28, 20)
        root_layout.setSpacing(16)

        # 1. Header Bar with Step Progress
        header_layout = QHBoxLayout()

        title_box = QVBoxLayout()
        lbl_app_title = QLabel("HANDVO CALIBRATION")
        lbl_app_title.setStyleSheet("color: #38bdf8; font-size: 20px; font-weight: bold; letter-spacing: 1px;")
        self.lbl_step_header = QLabel("Step 1 of 5: Hand Detection & Dominant Hand")
        self.lbl_step_header.setStyleSheet("color: #94a3b8; font-size: 14px;")
        title_box.addWidget(lbl_app_title)
        title_box.addWidget(self.lbl_step_header)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.step_progress_bar = QProgressBar()
        self.step_progress_bar.setRange(1, 5)
        self.step_progress_bar.setValue(1)
        self.step_progress_bar.setTextVisible(False)
        self.step_progress_bar.setFixedSize(220, 8)
        self.step_progress_bar.setStyleSheet(
            """
            QProgressBar { background-color: #1e293b; border-radius: 4px; }
            QProgressBar::chunk { background-color: #38bdf8; border-radius: 4px; }
            """
        )
        header_layout.addWidget(self.step_progress_bar)

        # Close button
        btn_close = QPushButton("✕ Exit")
        btn_close.setObjectName("btnSecondary")
        btn_close.clicked.connect(self.reject)
        header_layout.addWidget(btn_close)

        # 2. Main Content Splitter (Left: Live Canvas, Right: Guidance & Telemetry Card)
        main_content = QHBoxLayout()
        main_content.setSpacing(20)

        # Left: Live Preview Canvas
        self.canvas = CalibrationCanvas(self)
        main_content.addWidget(self.canvas, stretch=3)

        # Right: Step Instruction & Telemetry Panel
        self.side_panel = QFrame()
        self.side_panel.setObjectName("card")
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(20, 20, 20, 20)
        side_layout.setSpacing(14)

        self.lbl_step_title = QLabel("Step 1: Hand Detection")
        self.lbl_step_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")

        self.lbl_instructions = QLabel(
            "Raise your hand in front of the webcam.\n"
            "HANDVO will detect your hand and determine your dominant hand automatically."
        )
        self.lbl_instructions.setWordWrap(True)
        self.lbl_instructions.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.4;")

        # Live Telemetry Frame
        self.telemetry_frame = QFrame()
        self.telemetry_frame.setStyleSheet("background-color: #0b0f19; border-radius: 8px; padding: 12px;")
        telem_layout = QVBoxLayout(self.telemetry_frame)
        telem_layout.setSpacing(6)

        self.lbl_telem_hand = QLabel("Hand: Waiting for detection...")
        self.lbl_telem_hand.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 12px;")
        self.lbl_telem_pos = QLabel("Position (X, Y): --")
        self.lbl_telem_pos.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.lbl_telem_pinch = QLabel("Pinch Distance: --")
        self.lbl_telem_pinch.setStyleSheet("color: #94a3b8; font-size: 12px;")

        telem_layout.addWidget(self.lbl_telem_hand)
        telem_layout.addWidget(self.lbl_telem_pos)
        telem_layout.addWidget(self.lbl_telem_pinch)

        # Dynamic Controls Stack
        self.control_stack = QStackedWidget()

        # Page 1 Controls: Hand Selection
        page1 = QWidget()
        p1_layout = QVBoxLayout(page1)
        p1_layout.setContentsMargins(0, 0, 0, 0)
        p1_layout.setSpacing(10)
        hand_btn_box = QHBoxLayout()
        self.btn_hand_right = QPushButton("👉 Right Hand")
        self.btn_hand_right.setObjectName("btnPrimary")
        self.btn_hand_right.clicked.connect(lambda: self._set_hand_override("Right"))
        self.btn_hand_left = QPushButton("👈 Left Hand")
        self.btn_hand_left.setObjectName("btnSecondary")
        self.btn_hand_left.clicked.connect(lambda: self._set_hand_override("Left"))
        hand_btn_box.addWidget(self.btn_hand_right)
        hand_btn_box.addWidget(self.btn_hand_left)
        p1_layout.addLayout(hand_btn_box)
        p1_layout.addStretch()
        self.control_stack.addWidget(page1)

        # Page 2 Controls: Neutral Capture
        page2 = QWidget()
        p2_layout = QVBoxLayout(page2)
        p2_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_capture_neutral = QPushButton("🎯 Start Neutral Capture (2.5s)")
        self.btn_capture_neutral.setObjectName("btnPrimary")
        self.btn_capture_neutral.clicked.connect(self._start_neutral_capture)
        p2_layout.addWidget(self.btn_capture_neutral)
        p2_layout.addStretch()
        self.control_stack.addWidget(page2)

        # Page 3 Controls: Range Extents
        page3 = QWidget()
        p3_layout = QVBoxLayout(page3)
        p3_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_capture_range = QPushButton("📐 Start Movement Range Capture")
        self.btn_capture_range.setObjectName("btnPrimary")
        self.btn_capture_range.clicked.connect(self._start_range_capture)
        p3_layout.addWidget(self.btn_capture_range)
        p3_layout.addStretch()
        self.control_stack.addWidget(page3)

        # Page 4 Controls: Pinch Baseline
        page4 = QWidget()
        p4_layout = QVBoxLayout(page4)
        p4_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_pinch_action = QPushButton("✋ Capture Open Hand Span")
        self.btn_pinch_action.setObjectName("btnPrimary")
        self.btn_pinch_action.clicked.connect(self._start_pinch_capture)
        p4_layout.addWidget(self.btn_pinch_action)
        p4_layout.addStretch()
        self.control_stack.addWidget(page4)

        # Page 5 Controls: Validation Summary
        page5 = QWidget()
        p5_layout = QVBoxLayout(page5)
        p5_layout.setContentsMargins(0, 0, 0, 0)
        p5_layout.setSpacing(8)

        self.lbl_quality_badge = QLabel("QUALITY: EXCELLENT (92%)")
        self.lbl_quality_badge.setStyleSheet(
            "color: #22c55e; background-color: rgba(34,197,94,0.1); "
            "border: 1px solid #22c55e; border-radius: 8px; padding: 6px; font-weight: bold; font-size: 13px;"
        )
        self.lbl_quality_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_save_profile = QPushButton("💾 Save & Apply Profile")
        self.btn_save_profile.setObjectName("btnSuccess")
        self.btn_save_profile.clicked.connect(self._save_and_finish)

        self.btn_recalibrate = QPushButton("🔄 Recalibrate")
        self.btn_recalibrate.setObjectName("btnSecondary")
        self.btn_recalibrate.clicked.connect(self._restart_calibration)

        p5_layout.addWidget(self.lbl_quality_badge)
        p5_layout.addWidget(self.btn_save_profile)
        p5_layout.addWidget(self.btn_recalibrate)
        p5_layout.addStretch()
        self.control_stack.addWidget(page5)

        # Bottom Action Bar
        bottom_nav = QHBoxLayout()
        self.btn_prev = QPushButton("← Back")
        self.btn_prev.setObjectName("btnSecondary")
        self.btn_prev.setEnabled(False)
        self.btn_prev.clicked.connect(self._prev_step)

        self.btn_next = QPushButton("Next Step →")
        self.btn_next.setObjectName("btnPrimary")
        self.btn_next.clicked.connect(self._next_step)

        bottom_nav.addWidget(self.btn_prev)
        bottom_nav.addWidget(self.btn_next)

        side_layout.addWidget(self.lbl_step_title)
        side_layout.addWidget(self.lbl_instructions)
        side_layout.addWidget(self.telemetry_frame)
        side_layout.addWidget(self.control_stack, stretch=1)
        side_layout.addLayout(bottom_nav)

        main_content.addWidget(self.side_panel, stretch=2)

        root_layout.addLayout(header_layout)
        root_layout.addLayout(main_content, stretch=1)

    def _start_session(self) -> None:
        if self.camera.open():
            self.timer.start(33)
        self._update_step_view()

    def _set_hand_override(self, hand: str) -> None:
        self.dominant_hand = hand
        self.calib_data.dominant_hand = hand
        if hand == "Right":
            self.btn_hand_right.setObjectName("btnPrimary")
            self.btn_hand_left.setObjectName("btnSecondary")
        else:
            self.btn_hand_right.setObjectName("btnSecondary")
            self.btn_hand_left.setObjectName("btnPrimary")
        self.btn_hand_right.setStyle(self.btn_hand_right.style())
        self.btn_hand_left.setStyle(self.btn_hand_left.style())

    def _update_step_view(self) -> None:
        self.step_progress_bar.setValue(self.step)
        self.control_stack.setCurrentIndex(self.step - 1)
        self.canvas.step_index = self.step
        self.btn_prev.setEnabled(self.step > 1)

        if self.step == 1:
            self.lbl_step_header.setText("Step 1 of 5: Hand Detection & Dominant Hand")
            self.lbl_step_title.setText("Step 1: Hand Detection")
            self.lbl_instructions.setText(
                "Raise your hand in front of the webcam.\n"
                "Verify that the hand skeleton is tracked steadily and select your dominant hand."
            )
            self.btn_next.setText("Proceed to Neutral Position →")
            self.btn_next.setEnabled(True)

        elif self.step == 2:
            self.lbl_step_header.setText("Step 2 of 5: Neutral Resting Position")
            self.lbl_step_title.setText("Step 2: Neutral Resting Position")
            self.lbl_instructions.setText(
                "Place your hand in your most comfortable, natural resting position.\n"
                "Click 'Start Neutral Capture' and hold steady for 2.5 seconds."
            )
            self.btn_next.setText("Proceed to Movement Range →")
            self.btn_next.setEnabled(len(self.neutral_samples) >= 10)

        elif self.step == 3:
            self.lbl_step_header.setText("Step 3 of 5: Movement Range Extents")
            self.lbl_step_title.setText("Step 3: Movement Range Extents")
            self.lbl_instructions.setText(
                "Move your hand across your comfortable reach:\n"
                "Top-Left, Top-Right, Bottom-Left, and Bottom-Right.\n"
                "The bounding box on the screen will adapt to your natural range."
            )
            self.btn_next.setText("Proceed to Pinch Baseline →")
            self.btn_next.setEnabled(len(self.range_samples) >= 20)

        elif self.step == 4:
            self.lbl_step_header.setText("Step 4 of 5: Pinch Gesture Baseline")
            self.lbl_step_title.setText("Step 4: Pinch Gesture Baseline")
            self._pinch_substep = "open"
            self.btn_pinch_action.setText("✋ Capture Open Hand Span")
            self.lbl_instructions.setText(
                "1. Open your hand fully and click 'Capture Open Hand Span'.\n"
                "2. Then pinch thumb and index finger together to measure contact."
            )
            self.btn_next.setText("Proceed to Validation →")
            self.btn_next.setEnabled(self.calib_data.open_hand_span > 0 and self.calib_data.pinch_contact_dist > 0)

        elif self.step == 5:
            self.lbl_step_header.setText("Step 5 of 5: Validation & Quality Summary")
            self.lbl_step_title.setText("Step 5: Validation Playground")
            self.lbl_instructions.setText(
                "Move your calibrated cursor into each target box and pinch to select.\n"
                "Review your calibration quality score below and save to your profile."
            )
            self.btn_next.setText("Save & Complete")
            self.btn_next.setEnabled(False)
            self._setup_validation_targets()
            self._calculate_final_metrics()

    def _setup_validation_targets(self) -> None:
        w = self.canvas.width()
        h = self.canvas.height()
        tw, th = 90, 60
        self.canvas.validation_targets = [
            ("target_1", QRectF(w * 0.15, h * 0.20, tw, th), False),
            ("target_2", QRectF(w * 0.70, h * 0.20, tw, th), False),
            ("target_3", QRectF(w * 0.15, h * 0.70, tw, th), False),
            ("target_4", QRectF(w * 0.70, h * 0.70, tw, th), False),
        ]
        self._validation_hits = {t[0]: False for t in self.canvas.validation_targets}

    def _calculate_final_metrics(self) -> None:
        # Calculate neutral centroid
        nx, ny = HandCalibrationEngine.compute_neutral(self.neutral_samples)
        self.calib_data.neutral_x = nx
        self.calib_data.neutral_y = ny

        # Calculate bounding range
        min_x, max_x, min_y, max_y = HandCalibrationEngine.compute_range(self.range_samples)
        self.calib_data.range_min_x = min_x
        self.calib_data.range_max_x = max_x
        self.calib_data.range_min_y = min_y
        self.calib_data.range_max_y = max_y

        # Calculate pinch thresholds
        p_trig, p_rel = HandCalibrationEngine.compute_pinch_thresholds(
            self.calib_data.open_hand_span,
            self.calib_data.pinch_contact_dist,
        )
        self.calib_data.pinch_threshold = p_trig
        self.calib_data.pinch_release_threshold = p_rel

        # Evaluate quality
        q_label, q_pct = HandCalibrationEngine.evaluate_quality(
            (nx, ny),
            (min_x, max_x, min_y, max_y),
            self.calib_data.open_hand_span,
            self.calib_data.pinch_contact_dist,
        )
        self.calib_data.quality_score = q_label
        self.calib_data.quality_pct = q_pct
        self.calib_data.is_calibrated = True

        color = "#22c55e" if q_label == "EXCELLENT" else ("#38bdf8" if q_label == "GOOD" else "#f59e0b")
        self.lbl_quality_badge.setText(f"QUALITY: {q_label} ({q_pct:.0f}%)")
        self.lbl_quality_badge.setStyleSheet(
            f"color: {color}; background-color: rgba(255,255,255,0.05); "
            f"border: 1px solid {color}; border-radius: 8px; padding: 8px; font-weight: bold; font-size: 13px;"
        )

    def _start_neutral_capture(self) -> None:
        self.neutral_samples.clear()
        self._is_capturing = True
        self._capture_start_time = time.perf_counter()
        self.btn_capture_neutral.setEnabled(False)
        self.btn_capture_neutral.setText("Capturing Neutral Position...")

    def _start_range_capture(self) -> None:
        self.range_samples.clear()
        self._is_capturing = True
        self._capture_start_time = time.perf_counter()
        self._capture_duration = 6.0  # 6 seconds to move across reach
        self.btn_capture_range.setEnabled(False)
        self.btn_capture_range.setText("Recording Reach Extents (Move freely)...")

    def _start_pinch_capture(self) -> None:
        if self._pinch_substep == "open":
            self.open_span_samples.clear()
            self._is_capturing = True
            self._capture_start_time = time.perf_counter()
            self._capture_duration = 2.0
            self.btn_pinch_action.setEnabled(False)
            self.btn_pinch_action.setText("Recording Open Hand...")
        else:
            self.pinch_dist_samples.clear()
            self._is_capturing = True
            self._capture_start_time = time.perf_counter()
            self._capture_duration = 2.0
            self.btn_pinch_action.setEnabled(False)
            self.btn_pinch_action.setText("Recording Pinch Contact...")

    def _next_step(self) -> None:
        if self.step < 5:
            self.step += 1
            self._update_step_view()

    def _prev_step(self) -> None:
        if self.step > 1:
            self.step -= 1
            self._update_step_view()

    def _restart_calibration(self) -> None:
        self.step = 1
        self.neutral_samples.clear()
        self.range_samples.clear()
        self.open_span_samples.clear()
        self.pinch_dist_samples.clear()
        self.calib_data = HandCalibrationData()
        self._update_step_view()

    def _save_and_finish(self) -> None:
        profile = self.db_repo.get_or_create_default()
        profile.dominant_hand = self.calib_data.dominant_hand
        profile.neutral_x = self.calib_data.neutral_x
        profile.neutral_y = self.calib_data.neutral_y
        profile.range_min_x = self.calib_data.range_min_x
        profile.range_max_x = self.calib_data.range_max_x
        profile.range_min_y = self.calib_data.range_min_y
        profile.range_max_y = self.calib_data.range_max_y
        profile.open_hand_span = self.calib_data.open_hand_span
        profile.pinch_threshold = self.calib_data.pinch_threshold
        profile.pinch_release_threshold = self.calib_data.pinch_release_threshold
        profile.calibration_quality = self.calib_data.quality_score

        self.db_repo.save_calibration(profile)
        self.calibration_saved.emit(self.calib_data)
        self.accept()

    def _update_loop(self) -> None:
        now = time.perf_counter()
        success, frame = self.camera.read_frame()
        if not success or frame is None:
            return

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hands = self.hand_detector.detect(rgb)
        annotated = self.hand_detector.draw_skeleton(frame, hands)

        primary_hand = hands[0] if len(hands) > 0 else None

        if primary_hand and primary_hand.is_valid:
            # Step 1: Auto-detect handedness
            if self.step == 1 and not hasattr(self, "_hand_locked"):
                self.dominant_hand = primary_hand.handedness
                self.calib_data.dominant_hand = self.dominant_hand
                self._set_hand_override(self.dominant_hand)

            idx_tip = primary_hand.index_tip
            thumb_tip = primary_hand.thumb_tip

            # Pinch metric
            pinch_res = self.pinch_detector.detect(primary_hand)
            self.lbl_telem_hand.setText(f"Hand: {primary_hand.handedness} (Confidence: {primary_hand.confidence:.2f})")
            if idx_tip:
                self.lbl_telem_pos.setText(f"Position (X, Y): ({idx_tip.x:.2f}, {idx_tip.y:.2f})")
            self.lbl_telem_pinch.setText(f"Pinch Norm Dist: {pinch_res.normalized_distance:.3f}")

            # Capture Logic
            if self._is_capturing and idx_tip:
                elapsed = now - self._capture_start_time
                progress = min(1.0, elapsed / self._capture_duration)
                self.canvas.countdown_progress = progress

                # Step 2 Capture
                if self.step == 2:
                    self.neutral_samples.append((idx_tip.x, idx_tip.y))
                    if progress >= 1.0:
                        self._is_capturing = False
                        self.canvas.countdown_progress = 0.0
                        self.btn_capture_neutral.setEnabled(True)
                        self.btn_capture_neutral.setText("✓ Captured Neutral Position")
                        self.btn_next.setEnabled(True)

                # Step 3 Capture
                elif self.step == 3:
                    self.range_samples.append((idx_tip.x, idx_tip.y))
                    bounds = HandCalibrationEngine.compute_range(self.range_samples)
                    self.canvas.current_bounds = bounds
                    if progress >= 1.0:
                        self._is_capturing = False
                        self.btn_capture_range.setEnabled(True)
                        self.btn_capture_range.setText("✓ Range Captured")
                        self.btn_next.setEnabled(True)

                # Step 4 Capture
                elif self.step == 4:
                    if self._pinch_substep == "open":
                        self.open_span_samples.append(pinch_res.normalized_distance)
                        if progress >= 1.0:
                            self._is_capturing = False
                            avg_span = sum(self.open_span_samples) / max(1, len(self.open_span_samples))
                            self.calib_data.open_hand_span = avg_span
                            self._pinch_substep = "pinch"
                            self.btn_pinch_action.setEnabled(True)
                            self.btn_pinch_action.setText("🤏 Capture Pinch Contact Distance")
                            self.lbl_instructions.setText("Now pinch your index and thumb together firmly and click Capture.")
                    else:
                        self.pinch_dist_samples.append(pinch_res.normalized_distance)
                        if progress >= 1.0:
                            self._is_capturing = False
                            avg_dist = sum(self.pinch_dist_samples) / max(1, len(self.pinch_dist_samples))
                            self.calib_data.pinch_contact_dist = avg_dist
                            self.btn_pinch_action.setText("✓ Pinch Baseline Captured")
                            self.btn_next.setEnabled(True)

            # Step 5: Validation Test Cursor
            if self.step == 5 and idx_tip:
                cx, cy = HandCalibrationEngine.remap_coordinate(idx_tip.x, idx_tip.y, self.calib_data)
                canvas_w = self.canvas.width()
                canvas_h = self.canvas.height()
                px = int(cx * canvas_w)
                py = int(cy * canvas_h)
                self.canvas.test_cursor_px = (px, py)
                self.canvas.pinch_active = pinch_res.is_pinched

                # Test target collisions & pinch activation
                updated_targets = []
                for tid, rect, hit in self.canvas.validation_targets:
                    is_inside = rect.contains(float(px), float(py))
                    new_hit = hit or (is_inside and pinch_res.is_pinched)
                    updated_targets.append((tid, rect, new_hit))
                    if new_hit:
                        self._validation_hits[tid] = True
                self.canvas.validation_targets = updated_targets

        else:
            self.lbl_telem_hand.setText("Hand: Searching for hand...")
            self.lbl_telem_pos.setText("Position (X, Y): --")
            self.lbl_telem_pinch.setText("Pinch Distance: --")
            self.canvas.test_cursor_px = None

        # Render annotated frame onto canvas
        rgb_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        q_img = QImage(rgb_frame.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img).scaled(
            self.canvas.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.canvas.setPixmap(pixmap)
        self.canvas.update()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.timer.stop()
        self.camera.release()
        self.hand_detector.close()
        super().closeEvent(event)
