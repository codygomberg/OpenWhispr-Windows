from collections import deque

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QApplication, QWidget

import theme


# Layout (pixels)
PAD_X     = 16    # space inside the left/right edges
ICON_W    = 14    # dot / lock / spinner / check
GAP       = 9     # between icon, label and waveform
WAVE_BARS = 14
BAR_W     = 3
BAR_GAP   = 2
BUTTON    = 24    # stop / cancel buttons on a hands-free recording
WAVE_W    = WAVE_BARS * (BAR_W + BAR_GAP) - BAR_GAP

# Label and color for each recording mode
MODE_STYLE = {
    "normal":    ("Listening",      theme.COLOR_RECORDING),
    "summarize": ("Summarize",      theme.COLOR_SUMMARIZE),
    "qa":        ("Ask a question", theme.COLOR_QUESTION),
}


class PillWindow(QWidget):
    """
    Floating status HUD at the top of the screen. Hidden while idle.
    States: recording (waveform), working (spinner), status (dot), done (check).
    """

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedHeight(theme.PILL_HEIGHT)
        self.setMouseTracking(True)

        self._font = QFont(theme.FONT_FAMILY, theme.FONT_SIZE_PILL)
        self._state = "hidden"
        self._message = ""
        self._color = theme.COLOR_NEUTRAL
        self._mode = "normal"
        self._hands_free = False
        self._hovered = False
        self._spin = 0
        self._levels = deque([0.0] * WAVE_BARS, maxlen=WAVE_BARS)
        self._level_source = lambda: 0.0
        self._stop_rect = QRectF()
        self._cancel_rect = QRectF()

        # Set by main.py — called when the hands-free buttons are clicked
        self.on_stop = None
        self.on_cancel = None

        self._anim = QTimer(self)
        self._anim.setInterval(33)   # ~30 fps
        self._anim.timeout.connect(self._tick)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_pill)

        self.hide()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_level_source(self, source):
        """source() returns the current mic loudness, 0–1."""
        self._level_source = source

    @pyqtSlot(str, bool)
    def show_recording(self, mode: str, hands_free: bool):
        self._mode = mode if mode in MODE_STYLE else "normal"
        self._hands_free = hands_free
        self._levels = deque([0.0] * WAVE_BARS, maxlen=WAVE_BARS)
        label, color = MODE_STYLE[self._mode]
        if hands_free and self._mode == "normal":
            label = "Hands-free"
        self._enter("recording", label, color)

    @pyqtSlot(str, str)
    def show_working(self, message: str, color: str = theme.COLOR_WORKING):
        self._enter("working", message, color)

    @pyqtSlot(str, str)
    def show_status(self, message: str, dot_color: str = theme.COLOR_NEUTRAL):
        self._enter("status", message, dot_color)

    @pyqtSlot()
    def show_done(self):
        self._enter("done", "Done", theme.COLOR_DONE)
        self._hide_timer.start(theme.DONE_DISPLAY_MS)

    @pyqtSlot(str)
    def flash(self, message: str):
        """Show a short grey message, then hide (e.g. "Cancelled")."""
        self._enter("status", message, theme.COLOR_NEUTRAL)
        self._hide_timer.start(theme.DONE_DISPLAY_MS)

    @pyqtSlot()
    def hide_pill(self):
        self._hide_timer.stop()
        self._anim.stop()
        self._state = "hidden"
        self.hide()

    # ── State changes ─────────────────────────────────────────────────────────

    def _enter(self, state: str, message: str, color: str):
        self._hide_timer.stop()
        self._state = state
        self._message = message
        self._color = color
        if state in ("recording", "working"):
            self._anim.start()
        else:
            self._anim.stop()
        self._reposition()
        self.show()
        self.raise_()
        self.update()

    def _tick(self):
        if self._state == "recording":
            self._levels.append(self._level_source())
        elif self._state == "working":
            self._spin = (self._spin + 12) % 360
        self.update()

    # ── Geometry ──────────────────────────────────────────────────────────────

    def _reposition(self):
        text_w = QFontMetrics(self._font).horizontalAdvance(self._message)
        width = PAD_X + ICON_W + GAP + text_w + PAD_X
        if self._state == "recording":
            width += GAP + max(WAVE_W, BUTTON * 2 + 4)
        width = max(width, theme.PILL_MIN_WIDTH)
        self.setFixedWidth(width)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.x() + (screen.width() - width) // 2, screen.y() + theme.PILL_TOP_OFFSET)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        cy = r.height() / 2

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(28, 28, 30, 235))
        p.drawRoundedRect(r, cy, cy)

        self._draw_icon(p, PAD_X + ICON_W / 2, cy)

        p.setFont(self._font)
        p.setPen(QColor(theme.PILL_TEXT))
        text_x = PAD_X + ICON_W + GAP
        p.drawText(QRectF(text_x, 0, r.width() - text_x, r.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._message)

        if self._state == "recording":
            right = r.width() - PAD_X
            if self._hands_free and self._hovered:
                self._draw_buttons(p, right, cy)
            else:
                self._draw_wave(p, right, cy)

    def _draw_icon(self, p: QPainter, cx: float, cy: float):
        color = QColor(self._color)
        if self._state == "recording" and self._hands_free:
            self._draw_lock(p, cx, cy, QColor(theme.COLOR_LOCKED))
        elif self._state == "working":
            pen = QPen(color, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Qt angles are in 1/16 degree, counter-clockwise
            p.drawArc(QRectF(cx - 6, cy - 6, 12, 12), -self._spin * 16, 270 * 16)
        elif self._state == "done":
            pen = QPen(color, 2.2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath(QPointF(cx - 5, cy))
            path.lineTo(cx - 1.5, cy + 3.5)
            path.lineTo(cx + 5, cy - 4)
            p.drawPath(path)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(cx, cy), 4.5, 4.5)

    def _draw_lock(self, p: QPainter, cx: float, cy: float, color: QColor):
        p.setPen(QPen(color, 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - 3.5, cy - 7, 7, 8), 0, 180 * 16)        # shackle
        p.drawLine(QPointF(cx - 3.5, cy - 3), QPointF(cx - 3.5, cy - 1))
        p.drawLine(QPointF(cx + 3.5, cy - 3), QPointF(cx + 3.5, cy - 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(cx - 5.5, cy - 1, 11, 8), 2, 2)       # body

    def _draw_wave(self, p: QPainter, right: float, cy: float):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(MODE_STYLE[self._mode][1]))
        max_h = self.height() - 18
        x = right - WAVE_W
        for level in self._levels:
            h = max(3.0, level * max_h)
            p.drawRoundedRect(QRectF(x, cy - h / 2, BAR_W, h), 1.5, 1.5)
            x += BAR_W + BAR_GAP

    def _draw_buttons(self, p: QPainter, right: float, cy: float):
        self._cancel_rect = QRectF(right - BUTTON, cy - BUTTON / 2, BUTTON, BUTTON)
        self._stop_rect = QRectF(right - BUTTON * 2 - 4, cy - BUTTON / 2, BUTTON, BUTTON)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 38))
        p.drawEllipse(self._stop_rect)
        p.drawEllipse(self._cancel_rect)

        # ■ stop
        p.setBrush(QColor(theme.PILL_TEXT))
        c = self._stop_rect.center()
        p.drawRoundedRect(QRectF(c.x() - 4, c.y() - 4, 8, 8), 1.5, 1.5)

        # ✕ cancel
        pen = QPen(QColor(theme.PILL_TEXT), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        c = self._cancel_rect.center()
        p.drawLine(QPointF(c.x() - 4, c.y() - 4), QPointF(c.x() + 4, c.y() + 4))
        p.drawLine(QPointF(c.x() + 4, c.y() - 4), QPointF(c.x() - 4, c.y() + 4))

    # ── Mouse (hands-free buttons) ────────────────────────────────────────────

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self._state == "recording" and self._hands_free:
            pos = event.position()
            if self._stop_rect.contains(pos) and self.on_stop:
                self.on_stop()
            elif self._cancel_rect.contains(pos) and self.on_cancel:
                self.on_cancel()
        super().mousePressEvent(event)
