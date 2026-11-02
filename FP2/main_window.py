import os

from PyQt6.QtCore import QByteArray, Qt, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import theme
from page_dictionary import DictionaryPage
from page_history import HistoryPage
from page_settings import SettingsPage
from page_style import StylePage
from tone_manager import ToneManager
from ui_common import KeyCap, label


ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

# (key, sidebar title, page class) — in sidebar order
PAGES = [
    ("history",    "History",    HistoryPage),
    ("style",      "Style",      StylePage),
    ("dictionary", "Dictionary", DictionaryPage),
    ("settings",   "Settings",   SettingsPage),
]


class MainWindow(QWidget):
    """One window for everything: sidebar on the left, the chosen page on the right."""

    def __init__(self, ctx):
        super().__init__()
        self._tm = ToneManager()
        self.setObjectName("MainWindow")
        self.setWindowTitle("OpenWhispr")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(820, 560)
        self.resize(980, 680)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}
        for key, _, cls in PAGES:
            page = cls(ctx)
            self._pages[key] = page
            self._stack.addWidget(page)
        layout.addWidget(self._stack, 1)

        self._restore_geometry()
        self.show_page(PAGES[0][0])

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        side.setFixedWidth(210)
        v = QVBoxLayout(side)
        v.setContentsMargins(12, 18, 12, 14)
        v.setSpacing(2)

        brand = QHBoxLayout()
        brand.setContentsMargins(8, 0, 0, 14)
        logo = QLabel()
        logo.setPixmap(QIcon(ICON_PATH).pixmap(22, 22))
        brand.addWidget(logo)
        name = label("OpenWhispr")
        name.setStyleSheet("font-size: 15px; font-weight: 600;")
        brand.addWidget(name)
        brand.addStretch()
        v.addLayout(brand)

        self._nav = QButtonGroup(self)
        self._nav.setExclusive(True)
        self._nav_buttons: dict[str, QPushButton] = {}
        for key, title, _ in PAGES:
            btn = QPushButton(title)
            btn.setObjectName("NavItem")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self.show_page(k))
            self._nav.addButton(btn)
            self._nav_buttons[key] = btn
            v.addWidget(btn)

        v.addStretch()

        # Black "island" chip — live model / pipeline status
        island = QFrame()
        island.setObjectName("Island")
        ih = QHBoxLayout(island)
        ih.setContentsMargins(12, 9, 12, 9)
        ih.setSpacing(8)
        self._status_dot = QLabel("●")
        self._status_text = QLabel("Ready")
        self._status_text.setStyleSheet("font-weight: 600;")
        ih.addWidget(self._status_dot)
        ih.addWidget(self._status_text, 1)
        v.addWidget(island)
        self.set_status("Ready", theme.COLOR_DONE)

        hint = QHBoxLayout()
        hint.setContentsMargins(4, 10, 0, 0)
        hint.setSpacing(5)
        hint.addWidget(label("Hold", "Tertiary"))
        hint.addWidget(KeyCap("F15"))
        hint.addWidget(label("to dictate", "Tertiary"))
        hint.addStretch()
        v.addLayout(hint)
        return side

    # ── Public API ────────────────────────────────────────────────────────────

    def show_page(self, key: str):
        if key not in self._pages:
            return
        self._nav_buttons[key].setChecked(True)
        self._stack.setCurrentWidget(self._pages[key])
        self._pages[key].refresh()

    @pyqtSlot(str, str)
    def set_status(self, text: str, color: str):
        self._status_dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        self._status_text.setText(text)

    def refresh_current(self):
        """Reload the visible page (e.g. after a new dictation)."""
        if self.isVisible():
            self._stack.currentWidget().refresh()

    # ── Window position memory ────────────────────────────────────────────────

    def _restore_geometry(self):
        saved = self._tm.settings.get("window_geometry")
        if saved:
            self.restoreGeometry(QByteArray.fromBase64(saved.encode()))

    def _save_geometry(self):
        self._tm.settings["window_geometry"] = bytes(self.saveGeometry().toBase64()).decode()
        self._tm.save_settings()

    def showEvent(self, event):
        self._stack.currentWidget().refresh()
        super().showEvent(event)

    def closeEvent(self, event):
        # Closing only hides the window; OpenWhispr keeps running in the tray
        self._save_geometry()
        super().closeEvent(event)
