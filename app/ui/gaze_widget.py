"""Custom PySide6 widget for 2D gaze visualization."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QRadialGradient
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from app.vision.gaze_estimator import GazeResult


class GazeCanvas(QWidget):
    """2D coordinate target canvas visualizing normalized gaze position."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(140, 90)
        self.gaze_x: float = 0.5
        self.gaze_y: float = 0.5
        self.tracking_valid: bool = False

    def update_gaze(self, result: GazeResult) -> None:
        """Update gaze target position and trigger redraw."""
        self.gaze_x = result.smoothed_gaze_x
        self.gaze_y = result.smoothed_gaze_y
        self.tracking_valid = result.tracking_valid
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw 2D grid, axes, and gaze reticle."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Background
        painter.setBrush(QColor("#0f172a"))
        painter.setPen(QPen(QColor("#334155"), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 6, 6)

        # Center axes
        painter.setPen(QPen(QColor("#334155"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(w // 2, 4, w // 2, h - 4)
        painter.drawLine(4, h // 2, w - 4, h // 2)

        # Center crosshair tick
        painter.setPen(QPen(QColor("#475569"), 1))
        painter.drawEllipse(QPointF(w / 2, h / 2), 3, 3)

        if self.tracking_valid:
            # Map normalized [0, 1] to canvas coordinates (padding 10px from edges)
            px = 10 + self.gaze_x * (w - 20)
            py = 10 + self.gaze_y * (h - 20)

            # Outer glow
            gradient = QRadialGradient(QPointF(px, py), 12)
            gradient.setColorAt(0.0, QColor(56, 189, 248, 160))
            gradient.setColorAt(1.0, QColor(56, 189, 248, 0))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px, py), 12, 12)

            # Center gaze dot
            painter.setBrush(QColor("#38bdf8"))
            painter.setPen(QPen(QColor("#ffffff"), 1.5))
            painter.drawEllipse(QPointF(px, py), 4, 4)
        else:
            # Draw lost tracking indicator
            painter.setPen(QPen(QColor("#64748b"), 1))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "LOST")


class GazeWidget(QFrame):
    """Panel containing the 2D gaze canvas, coordinate readouts, and direction status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("gazePanel")
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(
            """
            QFrame#gazePanel {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 12px;
            }
            QLabel { color: #cbd5e1; font-size: 12px; }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(14)

        # 2D Canvas
        self.canvas = GazeCanvas(self)

        # Info column
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_direction = QLabel("Gaze: IDLE")
        self.lbl_direction.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_direction.setStyleSheet("color: #38bdf8; font-weight: bold;")

        self.lbl_coords = QLabel("X: --  Y: --")
        self.lbl_coords.setStyleSheet("color: #94a3b8; font-size: 11px;")

        info_layout.addWidget(self.lbl_direction)
        info_layout.addWidget(self.lbl_coords)

        layout.addWidget(self.canvas)
        layout.addLayout(info_layout)
        layout.addStretch()

    def update_gaze(self, result: GazeResult) -> None:
        """Update canvas and text labels from GazeResult."""
        self.canvas.update_gaze(result)

        if result.tracking_valid:
            dir_text = result.overall_direction.replace("LOOKING_", "")
            self.lbl_direction.setText(f"Gaze: {dir_text}")
            self.lbl_direction.setStyleSheet("color: #38bdf8; font-weight: bold;")
            self.lbl_coords.setText(f"X: {result.smoothed_gaze_x:.2f}  Y: {result.smoothed_gaze_y:.2f}")
        else:
            self.lbl_direction.setText("GAZE TRACKING LOST")
            self.lbl_direction.setStyleSheet("color: #f59e0b; font-weight: bold;")
            self.lbl_coords.setText("X: --  Y: --")
