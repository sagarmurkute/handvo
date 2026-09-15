"""Full-window calibration modal dialog with dwell progress ring and manual capture."""

import math
from pathlib import Path
from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.gaze.calibration import CalibrationSession, CalibrationState
from app.vision.gaze_estimator import GazeResult

CALIBRATION_SAVE_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "calibration.json"


class CalibrationCanvas(QWidget):
    """Renders the active calibration target dot with circular dwell progress ring."""

    def __init__(self, session: CalibrationSession, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self._pulse_phase: float = 0.0

    def set_pulse_phase(self, phase: float) -> None:
        self._pulse_phase = phase
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor("#090d16"))

        pt = self.session.current_point
        if pt is None or self.session.state not in (CalibrationState.SETTLING, CalibrationState.DWELLING):
            return

        target_x = pt.norm_x * w
        target_y = pt.norm_y * h

        base_radius = 26
        dwell = self.session.dwell_progress

        # Outer glowing halo
        grad = QRadialGradient(QPointF(target_x, target_y), base_radius + 18)
        if self.session.state == CalibrationState.DWELLING and dwell > 0.05:
            grad.setColorAt(0.0, QColor(34, 197, 94, 180))
            grad.setColorAt(1.0, QColor(34, 197, 94, 0))
            ring_color = QColor("#22c55e")
        else:
            grad.setColorAt(0.0, QColor(56, 189, 248, 160))
            grad.setColorAt(1.0, QColor(56, 189, 248, 0))
            ring_color = QColor("#38bdf8")

        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(target_x, target_y), base_radius + 18, base_radius + 18)

        # Background track ring
        painter.setBrush(QColor(15, 23, 42, 140))
        painter.setPen(QPen(QColor("#334155"), 2.0))
        painter.drawEllipse(QPointF(target_x, target_y), base_radius, base_radius)

        # Dwell progress arc (0° to 360°)
        if dwell > 0.0:
            pen = QPen(ring_color, 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            arc_rect = QRectF(target_x - base_radius, target_y - base_radius, base_radius * 2, base_radius * 2)
            # 16ths of a degree
            span_angle = int(-dwell * 360 * 16)
            painter.drawArc(arc_rect, 90 * 16, span_angle)

        # Center target dot
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#0f172a"), 1.0))
        painter.drawEllipse(QPointF(target_x, target_y), 5, 5)


class CalibrationDialog(QDialog):
    """Modal dialog guiding user through interactive 9-point gaze calibration."""

    calibration_finished = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = CalibrationSession()
        self.save_path = CALIBRATION_SAVE_PATH

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_step)
        self._pulse_time: float = 0.0

        self._init_window()
        self._init_ui()

    def _init_window(self) -> None:
        self.setWindowTitle("EYEVO — Gaze Calibration")
        self.resize(800, 560)
        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(
            """
            QDialog { background-color: #0f172a; color: #ffffff; }
            QLabel#heading { color: #38bdf8; font-size: 22px; font-weight: bold; }
            QLabel#instruction { color: #cbd5e1; font-size: 14px; line-height: 1.4; }
            QLabel#subtext { color: #94a3b8; font-size: 13px; }
            QFrame#card {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 20px;
            }
            QPushButton {
                font-size: 13px;
                font-weight: 600;
                padding: 10px 22px;
                border-radius: 6px;
                border: none;
            }
            QPushButton#btnPrimary { background-color: #0284c7; color: #ffffff; }
            QPushButton#btnPrimary:hover { background-color: #0369a1; }
            QPushButton#btnSecondary { background-color: #334155; color: #cbd5e1; }
            QPushButton#btnSecondary:hover { background-color: #475569; }
            """
        )

    def _init_ui(self) -> None:
        self.stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)

        self.stack.addWidget(self._build_intro_page())
        self.stack.addWidget(self._build_active_page())
        self.stack.addWidget(self._build_complete_page())

    def _build_intro_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(40, 32, 40, 32)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)

        title = QLabel("Gaze Calibration Setup")
        title.setObjectName("heading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        instructions = QLabel(
            "EYEVO will guide you through 9 target points across the screen.\n\n"
            "• Position your face comfortably and keep your head stationary.\n"
            "• Look steadily at each dot to fill the green progress ring.\n"
            "• Tip: You can also press SPACEBAR to capture the point immediately."
        )
        instructions.setObjectName("instruction")
        instructions.setWordWrap(True)

        btn_row = QHBoxLayout()
        btn_start = QPushButton("Start Calibration")
        btn_start.setObjectName("btnPrimary")
        btn_start.clicked.connect(self.start_calibration)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnSecondary")
        btn_cancel.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_start)

        card_layout.addWidget(title)
        card_layout.addWidget(instructions)
        card_layout.addSpacing(8)
        card_layout.addLayout(btn_row)

        page_layout.addWidget(card)
        return page

    def _build_active_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Header status overlay
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: rgba(15, 23, 42, 0.90); border-bottom: 1px solid #334155; padding: 6px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 6, 20, 6)

        self.lbl_progress = QLabel("Point 1 of 9")
        self.lbl_progress.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 14px;")

        self.lbl_status = QLabel("LOOK AT THE DOT (Hold steady or press SPACEBAR)")
        self.lbl_status.setStyleSheet("color: #e2e8f0; font-weight: 600; font-size: 13px;")

        top_layout.addWidget(self.lbl_progress)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_status)

        self.canvas = CalibrationCanvas(self.session, self)

        page_layout.addWidget(top_bar)
        page_layout.addWidget(self.canvas, stretch=1)
        return page

    def _build_complete_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(40, 32, 40, 32)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Calibration Complete")
        title.setObjectName("heading")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_quality = QLabel("Calibration quality: GOOD")
        self.lbl_quality.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_quality.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")

        self.lbl_metrics = QLabel("Samples: 45  |  Mean Error: Low")
        self.lbl_metrics.setObjectName("subtext")
        self.lbl_metrics.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_row = QHBoxLayout()
        btn_apply = QPushButton("Apply Calibration")
        btn_apply.setObjectName("btnPrimary")
        btn_apply.clicked.connect(self._apply_and_close)

        btn_recal = QPushButton("Calibrate Again")
        btn_recal.setObjectName("btnSecondary")
        btn_recal.clicked.connect(self.start_calibration)

        btn_row.addWidget(btn_recal)
        btn_row.addWidget(btn_apply)

        card_layout.addWidget(title)
        card_layout.addWidget(self.lbl_quality)
        card_layout.addWidget(self.lbl_metrics)
        card_layout.addSpacing(12)
        card_layout.addLayout(btn_row)

        page_layout.addWidget(card)
        return page

    def start_calibration(self) -> None:
        """Start or restart the calibration sequence."""
        self.session.start()
        self.stack.setCurrentIndex(1)
        self._anim_timer.start(30)
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle spacebar / enter manual trigger."""
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.session.state in (CalibrationState.SETTLING, CalibrationState.DWELLING):
                self.session.capture_point_manually()
                self._update_ui_state()
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Allow clicking on active canvas to trigger point capture."""
        if self.session.state in (CalibrationState.SETTLING, CalibrationState.DWELLING):
            self.session.capture_point_manually()
            self._update_ui_state()
        super().mousePressEvent(event)

    def process_gaze_sample(self, gaze_res: GazeResult) -> None:
        """Feed current gaze sample into the calibration session."""
        if self.session.state not in (CalibrationState.SETTLING, CalibrationState.DWELLING):
            return

        self.session.add_sample(
            gaze_res.gaze_x,
            gaze_res.gaze_y,
            tracking_valid=gaze_res.tracking_valid,
        )
        self._update_ui_state()

    def _update_ui_state(self) -> None:
        pt = self.session.current_point
        pt_idx = self.session.current_point_idx + 1
        total_pts = len(self.session.points)

        if pt is not None:
            self.lbl_progress.setText(f"Point {pt_idx} of {total_pts} ({pt.label})")

        state = self.session.state
        if state == CalibrationState.SETTLING:
            self.lbl_status.setText("LOOK AT THE DOT")
            self.lbl_status.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        elif state == CalibrationState.DWELLING:
            pct = int(self.session.dwell_progress * 100)
            self.lbl_status.setText(f"HOLD STEADY ({pct}%) — or press SPACEBAR")
            self.lbl_status.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 13px;")
        elif state == CalibrationState.COMPLETED:
            self._anim_timer.stop()
            self._show_results()
        elif state == CalibrationState.FAILED:
            self._anim_timer.stop()
            self._show_results(failed=True)

    def _animate_step(self) -> None:
        self._pulse_time += 0.08
        self.canvas.set_pulse_phase(self._pulse_time)

    def _show_results(self, failed: bool = False) -> None:
        self.stack.setCurrentIndex(2)
        if failed:
            self.lbl_quality.setText("Calibration Quality: NEEDS IMPROVEMENT")
            self.lbl_quality.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
            self.lbl_metrics.setText("Insufficient valid samples collected. Please try again.")
        else:
            q = self.session.model.metrics.quality
            color = "#22c55e" if q in ("EXCELLENT", "GOOD") else "#f59e0b"
            self.lbl_quality.setText(f"Calibration Quality: {q}")
            self.lbl_quality.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
            self.lbl_metrics.setText(
                f"Points: 9  |  Samples: {self.session.model.metrics.sample_count}  |  "
                f"RMSE: {self.session.model.metrics.rmse:.3f}"
            )
            self.session.model.save_to_json(self.save_path)

    def _apply_and_close(self) -> None:
        self.calibration_finished.emit(self.session.model)
        self.accept()

    def reject(self) -> None:
        self._anim_timer.stop()
        self.session.cancel()
        super().reject()
