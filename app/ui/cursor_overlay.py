"""Transparent PySide6 overlay rendering the HANDVO virtual cursor, dwell indicator, and debug telemetry."""

from typing import Optional, Tuple
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPaintEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from app.gestures.cursor import CursorPosition
from app.gestures.dwell import DwellResult, DwellState


class CursorOverlay(QWidget):
    """Transparent overlay drawing virtual cursor ring and dwell progress arc."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._cursor_pos: Optional[CursorPosition] = None
        self._dwell_res: Optional[DwellResult] = None
        self.show_debug: bool = False

    def update_cursor(
        self,
        cursor_pos: Optional[CursorPosition],
        dwell_res: Optional[DwellResult] = None,
    ) -> None:
        self._cursor_pos = cursor_pos
        self._dwell_res = dwell_res
        self.update()

    def set_debug_mode(self, enabled: bool) -> None:
        self.show_debug = enabled
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._cursor_pos is None or not self._cursor_pos.is_valid:
            return

        cx = float(self._cursor_pos.pixel_x)
        cy = float(self._cursor_pos.pixel_y)

        # Draw outer subtle glow
        glow_pen = QPen(QColor(56, 189, 248, 80), 6)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), 18, 18)

        # Draw main cursor ring
        ring_color = QColor("#38bdf8")
        if self._dwell_res and self._dwell_res.state == DwellState.COOLDOWN:
            ring_color = QColor("#10b981")
        elif self._dwell_res and self._dwell_res.state == DwellState.DWELLING:
            ring_color = QColor("#f59e0b")

        painter.setPen(QPen(ring_color, 2.5))
        painter.drawEllipse(QPointF(cx, cy), 14, 14)

        # Draw center point
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(ring_color))
        painter.drawEllipse(QPointF(cx, cy), 3.5, 3.5)

        # Draw dwell progress arc
        if self._dwell_res and self._dwell_res.progress > 0.0:
            arc_rect = QRectF(cx - 20, cy - 20, 40, 40)
            arc_pen = QPen(QColor("#22c55e"), 4)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            start_angle = 90 * 16
            span_angle = int(-self._dwell_res.progress * 360 * 16)
            painter.drawArc(arc_rect, start_angle, span_angle)
