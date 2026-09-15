"""Gaze-interactive button widget with animated dwell progress visualization."""

from typing import Callable, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton, QWidget

from app.interaction.dwell_selector import DwellSelector, DwellTarget


class GazeButton(QPushButton):
    """
    A push button with built-in gaze dwell progress visualization and fallback click handling.
    """

    def __init__(
        self,
        target_id: str,
        text: str,
        parent: Optional[QWidget] = None,
        callback: Optional[Callable[[], None]] = None,
        accent_color: str = "#0ea5e9",  # Sky blue accent
    ) -> None:
        super().__init__(text, parent)
        self.target_id = target_id
        self._custom_callback = callback
        self.accent_color = QColor(accent_color)

        self.dwell_progress: float = 0.0  # 0.0 to 1.0
        self.is_gaze_focused: bool = False
        self.is_in_cooldown: bool = False

        self.setMinimumSize(120, 50)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Connect click to fallback callback
        self.clicked.connect(self._on_manual_click)

    def _on_manual_click(self) -> None:
        """Handle manual mouse/keyboard click fallback."""
        if self._custom_callback:
            self._custom_callback()

    def create_dwell_target(self, parent_window: QWidget) -> DwellTarget:
        """Create and return a DwellTarget bound to this widget's window-relative coordinates."""

        def get_window_bounds():
            if not self.isVisible() or not self.isEnabled():
                return (-1000.0, -1000.0, 0.0, 0.0)
            top_left = self.mapTo(parent_window, self.rect().topLeft())
            return (
                float(top_left.x()),
                float(top_left.y()),
                float(self.width()),
                float(self.height()),
            )

        return DwellTarget(
            target_id=self.target_id,
            bounds=get_window_bounds,
            enabled=self.isEnabled(),
            callback=self._custom_callback,
            label=self.text(),
        )

    def update_dwell_feedback(self, focused: bool, progress: float, in_cooldown: bool = False) -> None:
        """Update the visual dwell state and trigger a repaint."""
        changed = (
            self.is_gaze_focused != focused
            or abs(self.dwell_progress - progress) > 0.01
            or self.is_in_cooldown != in_cooldown
        )
        self.is_gaze_focused = focused
        self.dwell_progress = progress
        self.is_in_cooldown = in_cooldown

        if changed:
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        """Custom rendering with smooth dwell progress ring and glowing active state."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        r = 10.0  # Corner radius

        # 1. Background Fill
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(1, 1, w - 2, h - 2), r, r)

        if not self.isEnabled():
            bg_color = QColor("#1e293b")
            border_color = QColor("#334155")
            text_color = QColor("#64748b")
        elif self.is_in_cooldown:
            bg_color = QColor("#0f2b38")
            border_color = QColor("#14b8a6")
            text_color = QColor("#5eead4")
        elif self.is_gaze_focused:
            bg_color = QColor("#172554")  # Deep highlight blue
            border_color = self.accent_color
            text_color = QColor("#ffffff")
        else:
            bg_color = QColor("#1e293b")
            border_color = QColor("#334155")
            text_color = QColor("#e2e8f0")

        painter.fillPath(bg_path, bg_color)

        # 2. Dwell Progress Fill (Expanding glowing border / progress bar)
        if self.is_gaze_focused and self.dwell_progress > 0.0:
            # Bottom progress bar fill
            progress_w = (w - 4) * self.dwell_progress
            prog_path = QPainterPath()
            prog_path.addRoundedRect(QRectF(2, h - 6, progress_w, 4), 2, 2)
            painter.fillPath(prog_path, self.accent_color)

            # Circular dwell indicator in the top-right corner
            indicator_cx = w - 18
            indicator_cy = 18
            indicator_rad = 9

            # Background circle
            painter.setPen(QPen(QColor(255, 255, 255, 40), 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(indicator_cx, indicator_cy), indicator_rad, indicator_rad)

            # Active Progress Arc
            arc_pen = QPen(self.accent_color, 2.5)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)

            span_angle = int(-self.dwell_progress * 360 * 16)
            painter.drawArc(
                int(indicator_cx - indicator_rad),
                int(indicator_cy - indicator_rad),
                int(indicator_rad * 2),
                int(indicator_rad * 2),
                90 * 16,
                span_angle,
            )

        # 3. Outer Border
        border_width = 2.5 if self.is_gaze_focused else 1.5
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(bg_path)

        # 4. Text Label
        painter.setPen(text_color)
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
