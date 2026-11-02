"""Shared look and building blocks for the main window's pages."""
import os
import tempfile

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import theme


# ── App-wide styling ───────────────────────────────────────────────────────────

def _chevron_file(color: str) -> str:
    """Write a small ▾ chevron SVG in the given color; return its path for the stylesheet."""
    path = os.path.join(tempfile.gettempdir(), f"openwhispr_chevron_{color.lstrip('#')}.svg")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6">'
                f'<path d="M1 1l4 4 4-4" fill="none" stroke="{color}" stroke-width="1.5" '
                'stroke-linecap="round" stroke-linejoin="round"/></svg>'
            )
    return path.replace("\\", "/")


def stylesheet(c: dict) -> str:
    chevron = _chevron_file(c["text2"])
    return f"""
    QWidget {{ color: {c['text']}; font-family: "{theme.FONT_FAMILY}"; font-size: 13px; }}
    QWidget#MainWindow, QWidget#PageBody, QScrollArea, QStackedWidget {{ background: {c['bg']}; }}
    QScrollArea {{ border: none; }}

    QWidget#Sidebar {{ background: {c['sidebar']}; border-right: 1px solid {c['divider']}; }}
    QPushButton#NavItem {{
        text-align: left; padding: 7px 10px; border: none; border-radius: 6px;
        background: transparent; color: {c['text']};
    }}
    QPushButton#NavItem:hover {{ background: {c['sidebar_sel']}; }}
    QPushButton#NavItem:checked {{ background: {c['sidebar_sel']}; font-weight: 600; }}

    QLabel#PageTitle {{ font-size: 24px; font-weight: 600; }}
    QLabel#Secondary {{ color: {c['text2']}; }}
    QLabel#Tertiary {{ color: {c['text3']}; font-size: 12px; }}
    QLabel#SectionTitle {{ color: {c['text3']}; font-size: 11px; font-weight: 600; }}
    QLabel#Big {{ font-size: 48px; font-weight: 600; }}
    QLabel#TileValue {{ font-size: 24px; font-weight: 600; }}

    QFrame#Card {{ background: {c['card']}; border: 1px solid {c['divider']}; border-radius: 10px; }}
    QFrame#Card QLabel, QFrame#Card QAbstractButton#Switch {{ background: transparent; }}
    QFrame#Divider {{ background: {c['divider']}; border: none; }}

    QFrame#ToneCard {{ background: {c['card']}; border: 1px solid {c['divider']}; border-radius: 10px; }}
    QFrame#ToneCard:hover {{ border: 1px solid {c['text3']}; }}
    QFrame#ToneCard[selected="true"] {{ border: 2px solid {c['text']}; }}
    QFrame#ToneCard QLabel {{ background: transparent; }}

    QFrame#Island {{ background: {theme.ISLAND}; border-radius: 10px; }}
    QFrame#Island QLabel {{ background: transparent; color: #FFFFFF; }}

    QFrame#KeyCap {{ background: {c['card']}; border: 1px solid {c['divider']}; border-radius: 5px; }}
    QFrame#KeyCap QLabel {{ font-size: 11px; font-weight: 600; background: transparent; }}

    QLineEdit, QPlainTextEdit, QComboBox {{
        background: {c['field']}; border: 1px solid {c['divider']}; border-radius: 6px;
        padding: 6px 8px; selection-background-color: {c['text3']};
    }}
    QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {c['text3']}; }}
    QComboBox {{ padding-right: 24px; }}
    QComboBox::drop-down {{ border: none; background: transparent; width: 22px; }}
    QComboBox::down-arrow {{ image: url("{chevron}"); width: 10px; height: 6px; }}
    QLabel#AppInitial, QFrame#Card QLabel#AppInitial {{
        background: {c['sidebar_sel']}; color: {c['text2']}; border-radius: 5px;
        font-size: 11px; font-weight: 600;
    }}
    QComboBox QAbstractItemView {{
        background: {c['card']}; border: 1px solid {c['divider']};
        selection-background-color: {c['sidebar_sel']}; selection-color: {c['text']};
    }}

    QPushButton {{
        background: {c['card']}; border: 1px solid {c['divider']}; border-radius: 6px; padding: 6px 12px;
    }}
    QPushButton:hover {{ background: {c['sidebar_sel']}; }}
    QPushButton:disabled {{ color: {c['text3']}; }}
    QPushButton#Primary {{ background: {c['text']}; color: {c['bg']}; border: none; font-weight: 600; }}
    QPushButton#Primary:hover {{ background: {c['text2']}; }}
    QPushButton#Primary:disabled {{ background: {c['divider']}; color: {c['text3']}; }}
    QPushButton#Ghost {{ background: transparent; border: none; color: {c['text2']}; padding: 4px 8px; }}
    QPushButton#Ghost:hover {{ color: {c['text']}; background: {c['sidebar_sel']}; }}
    QPushButton::menu-indicator {{ width: 0; }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['divider']}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['text3']}; }}
    QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
        height: 0; background: none;
    }}

    QMenu {{ background: {c['card']}; border: 1px solid {c['divider']}; padding: 4px; }}
    QMenu::item {{ padding: 6px 20px 6px 10px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {c['sidebar_sel']}; }}
    QMenu::item:disabled {{ color: {c['text3']}; }}
    QMenu::separator {{ height: 1px; background: {c['divider']}; margin: 4px 6px; }}
    QMenu::icon {{ padding-left: 6px; }}

    QToolTip {{ background: {c['card']}; color: {c['text']}; border: 1px solid {c['divider']}; padding: 4px; }}
    QDialog {{ background: {c['bg']}; }}
    """


def apply_theme(app: QApplication):
    """Push the current light/dark palette into every Qt widget, menu and dialog."""
    c = theme.colors()
    pal = QPalette()
    for role, key in (
        (QPalette.ColorRole.Window, "bg"),
        (QPalette.ColorRole.WindowText, "text"),
        (QPalette.ColorRole.Base, "field"),
        (QPalette.ColorRole.AlternateBase, "card"),
        (QPalette.ColorRole.Text, "text"),
        (QPalette.ColorRole.Button, "card"),
        (QPalette.ColorRole.ButtonText, "text"),
        (QPalette.ColorRole.ToolTipBase, "card"),
        (QPalette.ColorRole.ToolTipText, "text"),
        (QPalette.ColorRole.PlaceholderText, "text3"),
        (QPalette.ColorRole.Highlight, "sidebar_sel"),
        (QPalette.ColorRole.HighlightedText, "text"),
    ):
        pal.setColor(role, QColor(c[key]))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet(c))


# ── Small helpers ──────────────────────────────────────────────────────────────

def label(text: str = "", role: str = "", wrap: bool = False) -> QLabel:
    """A QLabel with a style role: '', 'Secondary', 'Tertiary', 'SectionTitle', 'PageTitle'…"""
    lbl = QLabel(text)
    if role:
        lbl.setObjectName(role)
    lbl.setWordWrap(wrap)
    return lbl


def clear_layout(layout):
    """Remove and delete every widget in a layout (used before rebuilding a list)."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()


def app_badge(icon, name: str, size: int = 20) -> QLabel:
    """An app's icon, or its first letter in a rounded square when there's no icon."""
    badge = QLabel()
    badge.setFixedSize(size + 2, size + 2)
    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if icon is not None and not icon.isNull():
        badge.setPixmap(icon.pixmap(QSize(size, size)))
    else:
        badge.setObjectName("AppInitial")
        badge.setText((name[:1] or "?").upper())
    return badge


def divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    line.setFixedHeight(1)
    return line


def card() -> tuple[QFrame, QVBoxLayout]:
    """A rounded card; returns (frame, its layout)."""
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    return frame, layout


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        layout.addWidget(label(title, "PageTitle"))
        if subtitle:
            layout.addWidget(label(subtitle, "Secondary", wrap=True))


class Section(QWidget):
    """Small caps title above a card. Add rows to `.body`."""

    def __init__(self, title: str, in_card: bool = True):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        heading = label(title.upper(), "SectionTitle")
        font = heading.font()
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        heading.setFont(font)
        layout.addWidget(heading)
        if in_card:
            frame, self.body = card()
            layout.addWidget(frame)
        else:
            self.body = QVBoxLayout()
            self.body.setSpacing(8)
            layout.addLayout(self.body)


class KeyCap(QFrame):
    """A keyboard key, e.g. KeyCap("F15")."""

    def __init__(self, text: str):
        super().__init__()
        self.setObjectName("KeyCap")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 6, 2)
        layout.addWidget(QLabel(text), alignment=Qt.AlignmentFlag.AlignCenter)
        self.setMinimumWidth(24)
        self.setFixedHeight(22)


def key_combo(*keys: str) -> QWidget:
    """KeyCaps joined by '+', e.g. key_combo("Ctrl", "F15")."""
    box = QWidget()
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(4)
    for i, key in enumerate(keys):
        if i:
            row.addWidget(label("+", "Tertiary"))
        row.addWidget(KeyCap(key))
    row.addStretch()
    return box


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "Search"):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMinimumHeight(32)


class Switch(QAbstractButton):
    """An on/off toggle switch."""

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setObjectName("Switch")
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(36, 20)

    def sizeHint(self):
        return QSize(36, 20)

    def paintEvent(self, event):
        c = theme.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        track = QColor(c["text"]) if self.isChecked() else QColor(c["divider"])
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, 36, 20), 10, 10)
        knob_x = 18 if self.isChecked() else 2
        p.setBrush(QColor(c["bg"]) if self.isChecked() else QColor(c["card"]))
        p.drawEllipse(QRectF(knob_x, 2, 16, 16))


def switch_row(title: str, note: str, checked: bool, on_toggle) -> tuple[QWidget, Switch]:
    """Title + grey note on the left, switch on the right."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    text = QVBoxLayout()
    text.setSpacing(2)
    text.addWidget(label(title))
    if note:
        text.addWidget(label(note, "Tertiary", wrap=True))
    h.addLayout(text, 1)
    sw = Switch(checked)
    sw.toggled.connect(on_toggle)
    h.addWidget(sw, alignment=Qt.AlignmentFlag.AlignTop)
    return row, sw


class Page(QScrollArea):
    """
    Base class for a sidebar page: a scrolling column, max 760px wide.
    Subclasses add widgets to `self.column` and may override `refresh()`.
    """

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body.setObjectName("PageBody")
        outer = QHBoxLayout(body)
        outer.setContentsMargins(36, 32, 36, 32)
        inner = QWidget()
        inner.setMaximumWidth(760)
        self.column = QVBoxLayout(inner)
        self.column.setContentsMargins(0, 0, 0, 0)
        self.column.setSpacing(24)
        outer.addWidget(inner, 1)
        self.setWidget(body)

    def refresh(self):
        """Called each time the page is shown. Reload data here."""
        pass
