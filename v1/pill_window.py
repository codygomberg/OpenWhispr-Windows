from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

import theme


class PillWindow(QWidget):
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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFont(QFont(theme.FONT_FAMILY, 9))

        self._label = QLabel("")
        self._label.setFont(QFont(theme.FONT_FAMILY, theme.FONT_SIZE_PILL))
        self._label.setStyleSheet(f"color: {theme.PILL_TEXT};")

        layout.addWidget(self._dot)
        layout.addWidget(self._label)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self.hide()

    # ── Drawing ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(28, 28, 30, 220))
        painter.drawRoundedRect(self.rect(), 22, 22)

    # ── Public API ────────────────────────────────────────────────────────────

    @pyqtSlot(str, str)
    def show_status(self, message: str, dot_color: str = theme.COLOR_NEUTRAL):
        self._hide_timer.stop()
        self._dot.setStyleSheet(f"color: {dot_color};")
        self._label.setText(message)
        self._reposition()
        self.show()
        self.raise_()

    @pyqtSlot()
    def show_done(self):
        self.show_status("Done", theme.COLOR_DONE)
        self._hide_timer.start(theme.DONE_DISPLAY_MS)

    @pyqtSlot()
    def hide_pill(self):
        self._hide_timer.stop()
        self.hide()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _reposition(self):
        self.adjustSize()
        width = max(self.sizeHint().width(), theme.PILL_MIN_WIDTH)
        self.setFixedWidth(width)
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - width) // 2
        self.move(x, theme.PILL_TOP_OFFSET)
