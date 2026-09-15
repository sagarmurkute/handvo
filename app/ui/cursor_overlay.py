"""Transparent PySide6 overlay rendering the EYEVO virtual gaze cursor, dwell indicator, and debug telemetry."""

from typing import Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from app.gaze.gaze_cursor import CursorPosition
from app.interaction.dwell_selector import DwellResult, DwellState
from app.vision.gaze_estimator import GazeResult


class CursorOverlay(QWidget):
    """Non-interactive transparent overlay rendering the internal gaze cursor, dwell ring, and debug HUD."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.cursor_pos = CursorPosition()
        self.gaze_result: Optional[GazeResult] = None
        self.dwell_result: Optional[DwellResult] = None
        self.show_debug: bool = False

    def update_cursor(
        self,
        position: CursorPosition,
        gaze_res: Optional[GazeResult] = None,
        dwell_res: Optional[DwellResult] = None,
    ) -> None:
        """Update cursor and dwell state and trigger redraw."""
        self.cursor_pos = position
        self.gaze_result = gaze_res
        self.dwell_result = dwell_res
        self.update()

    def set_debug_mode(self, enabled: bool) -> None:
        """Toggle development debug HUD."""
        self.show_debug = enabled
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw gaze cursor, dwell animation ring, and optional debug telemetry."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Render Virtual Gaze Cursor
        if self.cursor_pos.is_visible:
            cx = self.cursor_pos.pixel_x
            cy = self.cursor_pos.pixel_y

            if self.cursor_pos.is_valid:
                # Active tracking: glowing cyan circular cursor
                grad = QRadialGradient(QPointF(cx, cy), 24)
                grad.setColorAt(0.0, QColor(56, 189, 248, 140))
                grad.setColorAt(1.0, QColor(56, 189, 248, 0))
                painter.setBrush(grad)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx, cy), 24, 24)

                # Outer ring (32px diameter)
                painter.setBrush(QColor(15, 23, 42, 60))
                painter.setPen(QPen(QColor("#38bdf8"), 2.5))
                painter.drawEllipse(QPointF(cx, cy), 16, 16)

                # Inner center pip
                painter.setBrush(QColor("#ffffff"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx, cy), 4, 4)

                # Dwell progress arc around cursor when dwelling
                if self.dwell_result and self.dwell_result.progress > 0.0:
                    dwell_pen = QPen(QColor("#38bdf8"), 3.5)
                    dwell_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                    painter.setPen(dwell_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    span_angle = int(-self.dwell_result.progress * 360 * 16)
                    painter.drawArc(
                        int(cx - 22),
                        int(cy - 22),
                        44,
                        44,
                        90 * 16,
                        span_angle,
                    )
            else:
                # Tracking lost: muted amber dashed ring
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor(245, 158, 11, 140), 2, Qt.PenStyle.DashLine))
                painter.drawEllipse(QPointF(cx, cy), 16, 16)
                painter.setBrush(QColor(245, 158, 11, 180))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx, cy), 3, 3)

        # 2. Render Debug HUD (when enabled)
        if self.show_debug:
            self._render_debug_hud(painter)

    def _render_debug_hud(self, painter: QPainter) -> None:
        """Render development debug metrics box."""
        hud_w, hud_h = 280, 110
        hud_x, hud_y = 20, 20

        # Background card
        painter.setBrush(QColor(15, 23, 42, 230))
        painter.setPen(QPen(QColor("#334155"), 1.5))
        painter.drawRoundedRect(QRectF(hud_x, hud_y, hud_w, hud_h), 8, 8)

        # Debug text
        painter.setFont(QFont("Consolas", 9, QFont.Weight.DemiBold))

        res = self.gaze_result
        if res:
            painter.setPen(QColor("#38bdf8"))
            painter.drawText(hud_x + 12, hud_y + 20, f"Gaze Pos : X: {res.gaze_x:.2f}  Y: {res.gaze_y:.2f}")
            painter.setPen(QColor("#e2e8f0"))
            painter.drawText(hud_x + 12, hud_y + 40, f"Cursor   : X: {int(self.cursor_pos.pixel_x)}  Y: {int(self.cursor_pos.pixel_y)}")
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(hud_x + 12, hud_y + 60, f"Tracking : Conf: {res.confidence:.2f} Valid: {res.tracking_valid}")
        else:
            painter.setPen(QColor("#94a3b8"))
            painter.drawText(hud_x + 12, hud_y + 20, "Tracking : Inactive")

        # Dwell Info
        if self.dwell_result and self.dwell_result.target_id:
            dw = self.dwell_result
            painter.setPen(QColor("#22c55e"))
            painter.drawText(hud_x + 12, hud_y + 82, f"Target   : {dw.target_id} ({dw.state.value})")
            painter.drawText(hud_x + 12, hud_y + 100, f"Dwell    : {int(dw.progress * 100)}% ({dw.remaining_time_sec:.2f}s)")
        else:
            painter.setPen(QColor("#64748b"))
            painter.drawText(hud_x + 12, hud_y + 82, "Target   : None (IDLE)")
            painter.drawText(hud_x + 12, hud_y + 100, "Dwell    : 0%")
