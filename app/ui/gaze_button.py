"""Accessible, high-contrast interactive button and card widget with live radial dwell visualization."""

from typing import Callable, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QPushButton, QWidget

from app.interaction.dwell_selector import DwellTarget


class GazeButton(QPushButton):
    """
    An accessible push button and communication card with built-in live radial dwell progress,
    glowing focus states, subtitle rendering, and manual click fallback.
    """

    def __init__(
        self,
        target_id: str,
        text: str,
        parent: Optional[QWidget] = None,
        callback: Optional[Callable[[], None]] = None,
        accent_color: str = "#0ea5e9",
        icon_str: str = "",
        subtitle: str = "",
        is_card: bool = False,
    ) -> None:
        super().__init__(text, parent)
        self.target_id = target_id
        self._custom_callback = callback
        self.accent_color = QColor(accent_color)
        self.icon_str = icon_str
        self.subtitle = subtitle
        self.is_card = is_card

        self.dwell_progress: float = 0.0  # 0.0 to 1.0
        self.is_gaze_focused: bool = False
        self.is_in_cooldown: bool = False

        if self.is_card:
            self.setMinimumSize(130, 85)
        else:
            self.setMinimumSize(110, 46)

        self.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.clicked.connect(self._on_manual_click)

    def _on_manual_click(self) -> None:
        """Execute action on mouse/touch fallback."""
        if self._custom_callback:
            self._custom_callback()

    def create_dwell_target(self, parent_window: QWidget) -> DwellTarget:
        """Generate a DwellTarget bound to this widget's live window coordinates."""
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
        """Update live dwell feedback state and trigger repaint."""
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        r = 12.0 if self.is_card else 8.0

        # 1. Background Fill & Colors
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(1.5, 1.5, w - 3, h - 3), r, r)

        if not self.isEnabled():
            bg_color = QColor("#1e293b")
            border_color = QColor("#334155")
            text_color = QColor("#64748b")
        elif self.is_in_cooldown:
            bg_color = QColor("#064e3b")  # Success green tint
            border_color = QColor("#10b981")
            text_color = QColor("#6ee7b7")
        elif self.is_gaze_focused:
            bg_color = QColor("#1e293b")  # Deep focused card
            border_color = self.accent_color
            text_color = QColor("#ffffff")
        else:
            bg_color = QColor("#111827") if self.is_card else QColor("#1e293b")
            border_color = QColor("#1f2937") if self.is_card else QColor("#334155")
            text_color = QColor("#f8fafc")

        painter.fillPath(bg_path, bg_color)

        # 2. Glowing Focused Fill Highlight
        if self.is_gaze_focused and self.isEnabled():
            glow_color = QColor(self.accent_color.red(), self.accent_color.green(), self.accent_color.blue(), 25)
            painter.fillPath(bg_path, glow_color)

        # 3. Dwell Progress Fill
        if self.is_gaze_focused and self.dwell_progress > 0.0:
            # Bottom progress bar line
            progress_w = (w - 6) * self.dwell_progress
            prog_path = QPainterPath()
            prog_path.addRoundedRect(QRectF(3, h - 5, progress_w, 3.5), 1.5, 1.5)
            painter.fillPath(prog_path, self.accent_color)

            # Circular dwell ring in the top-right corner
            indicator_cx = w - 16
            indicator_cy = 16
            indicator_rad = 8

            painter.setPen(QPen(QColor(255, 255, 255, 30), 2.5))
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

        # 4. Border Stroke
        border_width = 2.5 if self.is_gaze_focused else (1.5 if self.is_card else 1.0)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(bg_path)

        # 5. Content Rendering
        if self.is_card:
            # Render Icon + Main Label + Subtitle
            icon_y = 12
            if self.icon_str:
                painter.setFont(QFont("Segoe UI Emoji", 16))
                painter.setPen(QColor("#ffffff"))
                painter.drawText(QRectF(12, icon_y, w - 36, 24), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.icon_str)
                icon_y += 24

            # Main Title
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.setPen(text_color)
            painter.drawText(QRectF(12, icon_y, w - 24, 22), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())

            # Subtitle
            if self.subtitle:
                painter.setFont(QFont("Segoe UI", 9))
                painter.setPen(QColor("#94a3b8"))
                painter.drawText(QRectF(12, icon_y + 20, w - 24, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f'"{self.subtitle}"')
        else:
            # Standard Pill Button
            painter.setFont(self.font())
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
