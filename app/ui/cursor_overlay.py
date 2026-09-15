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
        self.cursor_size: int = 14
        self.cursor_size_name: str = "medium"
        self.base_radius: float = 14.0
        self.cursor_color: str = "#38bdf8"
        self.reduced_motion: bool = False
        self.show_debug: bool = False

    def set_appearance(
        self,
        size: int | str = 14,
        color: str = "#38bdf8",
        reduced_motion: bool = False,
    ) -> None:
        """Update cursor visual properties live."""
        if isinstance(size, str):
            size_map = {"small": 10, "medium": 14, "large": 16, "extra_large": 22}
            size_val = size_map.get(size.lower(), 14)
            self.cursor_size_name = size
        else:
            size_val = int(size)
            self.cursor_size_name = "medium"

        self.cursor_size = max(8, min(36, size_val))
        self.base_radius = float(self.cursor_size)
        self.cursor_color = color
        self.reduced_motion = reduced_motion
        self.update()

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
        r = float(self.cursor_size)

        base_color = QColor(self.cursor_color)

        # 1. Outer subtle glow (omitted if reduced_motion is enabled)
        if not self.reduced_motion:
            glow_color = QColor(base_color)
            glow_color.setAlpha(65)
            glow_pen = QPen(glow_color, r * 0.4)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r * 1.3, r * 1.3)

        # 2. Main cursor ring
        ring_color = base_color
        if self._dwell_res and self._dwell_res.state == DwellState.COOLDOWN:
            ring_color = QColor("#10b981")
        elif self._dwell_res and self._dwell_res.state == DwellState.DWELLING:
            ring_color = QColor("#f59e0b")

        painter.setPen(QPen(ring_color, max(2.0, r * 0.18)))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 3. Center dot
        dot_r = max(2.5, r * 0.25)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(ring_color))
        painter.drawEllipse(QPointF(cx, cy), dot_r, dot_r)

        # 4. Draw dwell progress arc
        if self._dwell_res and self._dwell_res.progress > 0.0:
            arc_r = r * 1.45
            arc_rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2.0, arc_r * 2.0)
            arc_pen = QPen(QColor("#22c55e"), max(3.0, r * 0.28))
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            start_angle = 90 * 16
            span_angle = int(-self._dwell_res.progress * 360 * 16)
            painter.drawArc(arc_rect, start_angle, span_angle)

