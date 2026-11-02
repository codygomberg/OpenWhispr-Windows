import os

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import app_info
from tone_manager import ToneManager
from ui_common import Page, PageHeader, Section, app_badge, card, clear_layout, divider, label


SPOKEN_EXAMPLE = "hey can you send me that thing"

# (stored value, title, example output) — same examples as the macOS app
TONE_OPTIONS = [
    ("casual",       "Casual",       "hey, can you send me that thing?"),
    ("neutral",      "Neutral",      "Hey, can you send me that thing we talked about?"),
    ("professional", "Professional", "Could you please send me the item we discussed?"),
    ("raw",          "Raw",          "hey can you send me that thing"),
]
TONE_TITLES = {value: title for value, title, _ in TONE_OPTIONS}


class ToneCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, value: str, title: str, example: str):
        super().__init__()
        self.value = value
        self.setObjectName("ToneCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(110)
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)
        v.addWidget(label(title))
        v.addWidget(label(example, "Secondary", wrap=True))
        if value == "raw":
            v.addWidget(label("No polishing", "Tertiary"))
        v.addStretch()

    def set_selected(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        self.clicked.emit(self.value)


class StylePage(Page):
    def __init__(self, ctx):
        super().__init__()
        self._tm = ToneManager()
        s = self._tm.settings

        self.column.addWidget(PageHeader("Style", "How OpenWhispr writes what you say."))

        # Default tone
        tone = Section("Default tone", in_card=False)
        tone.body.addWidget(label(f"You say “{SPOKEN_EXAMPLE}”", "Secondary"))
        cards = QHBoxLayout()
        cards.setSpacing(10)
        self._cards: list[ToneCard] = []
        for value, title, example in TONE_OPTIONS:
            tc = ToneCard(value, title, example)
            tc.clicked.connect(self._on_base_tone)
            cards.addWidget(tc, 1)
            self._cards.append(tc)
        tone.body.addLayout(cards)
        self.column.addWidget(tone)
        self._select_card(s.get("base_tone", "neutral"))

        # Personal style
        style = Section("Your style")
        self._style_input = QLineEdit()
        self._style_input.setPlaceholderText("e.g. Clean and direct. No fluff.")
        self._style_input.setText(s.get("style_description", ""))
        self._style_input.editingFinished.connect(self._on_style_changed)
        style.body.addWidget(self._style_input)
        style.body.addWidget(label("Added to every polish. Leave empty for the default.", "Tertiary"))
        self.column.addWidget(style)

        # Per-app tones
        per_app = Section("Per-app tones", in_card=False)
        per_app.body.addWidget(label(
            "Use a different tone in specific apps — professional in email, raw in code editors.",
            "Secondary", wrap=True))
        self._apps_frame, self._apps = card()
        self._apps.setSpacing(0)
        self._apps.setContentsMargins(14, 6, 8, 6)
        per_app.body.addWidget(self._apps_frame)

        add_row = QHBoxLayout()
        self._add_btn = QPushButton("Add App  ▾")
        self._add_menu = QMenu(self)
        self._add_menu.aboutToShow.connect(self._fill_add_menu)
        self._add_btn.setMenu(self._add_menu)
        add_row.addWidget(self._add_btn)
        add_row.addStretch()
        per_app.body.addLayout(add_row)
        self.column.addWidget(per_app)

        self.column.addStretch()
        self.refresh()

    # ── Default tone + style ──────────────────────────────────────────────────

    def _select_card(self, value: str):
        for tc in self._cards:
            tc.set_selected(tc.value == value)

    def _on_base_tone(self, value: str):
        self._tm.settings["base_tone"] = value
        self._tm.save_settings()
        self._select_card(value)

    def _on_style_changed(self):
        self._tm.settings["style_description"] = self._style_input.text().strip()
        self._tm.save_settings()

    # ── Per-app tones ─────────────────────────────────────────────────────────

    def refresh(self):
        clear_layout(self._apps)

        overrides = self._tm.get_all_overrides()
        if not overrides:
            empty = label("No app-specific tones yet. Every app uses the default tone.", "Tertiary")
            empty.setContentsMargins(0, 12, 0, 12)
            self._apps.addWidget(empty)
            return

        names = {exe: app_info.friendly_name(exe, self._tm.app_path(exe)) for exe in overrides}
        for i, exe in enumerate(sorted(overrides, key=lambda e: names[e].lower())):
            if i:
                self._apps.addWidget(divider())
            self._apps.addWidget(self._app_row(exe, names[exe], overrides[exe]))

    def _app_row(self, exe: str, name: str, tone: str) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 6, 0, 6)
        h.setSpacing(10)

        h.addWidget(app_badge(app_info.app_icon(self._tm.app_path(exe)), name))

        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(label(name))
        text.addWidget(label(exe, "Tertiary"))
        h.addLayout(text, 1)

        combo = QComboBox()
        for value, title, _ in TONE_OPTIONS:
            combo.addItem(title, value)
        combo.setCurrentIndex(max(0, combo.findData(tone)))
        combo.setMinimumWidth(130)
        combo.currentIndexChanged.connect(lambda _, c=combo: self._tm.set_override(exe, c.currentData()))
        h.addWidget(combo)

        remove = QPushButton("✕")
        remove.setObjectName("Ghost")
        remove.setToolTip("Remove — this app goes back to the default tone")
        remove.clicked.connect(lambda: self._remove_app(exe))
        h.addWidget(remove)
        return row

    def _fill_add_menu(self):
        self._add_menu.clear()
        existing = self._tm.get_all_overrides()
        apps = [(exe, path) for exe, path in app_info.running_apps() if exe not in existing]
        if apps:
            self._add_menu.addSection("Open apps")
            for exe, path in apps:
                action = self._add_menu.addAction(app_info.app_icon(path), app_info.friendly_name(exe, path))
                action.triggered.connect(lambda _, e=exe, p=path: self._add_app(e, p))
            self._add_menu.addSeparator()
        choose = self._add_menu.addAction("Choose App…")
        choose.triggered.connect(self._choose_app)

    def _choose_app(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose an app", os.environ.get("ProgramFiles", "C:\\"), "Programs (*.exe)")
        if path:
            path = os.path.normpath(path)
            self._add_app(os.path.basename(path).lower(), path)

    def _add_app(self, exe: str, path: str):
        self._tm.remember_app(exe, path)
        self._tm.set_override(exe, "neutral")
        self.refresh()

    def _remove_app(self, exe: str):
        self._tm.remove_override(exe)
        self.refresh()
