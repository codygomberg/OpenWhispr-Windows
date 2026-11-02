from datetime import date, datetime, timedelta

import pyperclip
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout, QWidget

import app_info
from history_store import HistoryStore
from tone_manager import ToneManager
from ui_common import Page, PageHeader, SearchField, Section, clear_layout, divider, label


PAGE_SIZE = 100
PREVIEW_CHARS = 160
MODE_NAMES = {"summarize": "Summary", "qa": "Question"}


def day_heading(d: date) -> str:
    today = date.today()
    if d == today:
        return "Today"
    if d == today - timedelta(days=1):
        return "Yesterday"
    text = f"{d:%A, %B} {d.day}"
    return text if d.year == today.year else f"{text}, {d.year}"


def clock(dt: datetime) -> str:
    return f"{dt:%I:%M %p}".lstrip("0")


def word_count(text: str) -> int:
    return len(text.split())


class HistoryRow(QFrame):
    """One dictation. Click to expand to the full text (and what Whisper heard)."""

    def __init__(self, entry: dict, app_name: str, on_delete):
        super().__init__()
        self._entry = entry
        self._expanded = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 10, 0, 10)
        h.setSpacing(12)

        when = label(clock(datetime.fromisoformat(entry["timestamp"])), "Tertiary")
        when.setFixedWidth(62)
        when.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        h.addWidget(when, alignment=Qt.AlignmentFlag.AlignTop)

        body = QVBoxLayout()
        body.setSpacing(4)
        self._text = label("", wrap=True)
        self._text.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        body.addWidget(self._text)
        self._raw = label("", "Tertiary", wrap=True)
        body.addWidget(self._raw)

        meta = []
        if app_name:
            meta.append(app_name)
        words = word_count(entry["text"])
        meta.append(f"{words} word{'s' if words != 1 else ''}")
        if entry.get("duration"):
            meta.append(f"{entry['duration']:.0f}s")
        if entry.get("mode") in MODE_NAMES:
            meta.append(MODE_NAMES[entry["mode"]])
        body.addWidget(label(" · ".join(meta), "Tertiary"))
        h.addLayout(body, 1)

        self._copy = QPushButton("Copy")
        self._copy.setObjectName("Ghost")
        self._copy.clicked.connect(self._on_copy)
        delete = QPushButton("✕")
        delete.setObjectName("Ghost")
        delete.setToolTip("Delete")
        delete.clicked.connect(lambda: on_delete(entry["id"]))
        h.addWidget(self._copy, alignment=Qt.AlignmentFlag.AlignTop)
        h.addWidget(delete, alignment=Qt.AlignmentFlag.AlignTop)

        self._render()

    def _render(self):
        text = self._entry["text"]
        raw = self._entry.get("raw", "")
        if self._expanded:
            self._text.setText(text)
            show_raw = bool(raw) and raw.strip() != text.strip()
            self._raw.setText(f"Whisper heard: {raw}" if show_raw else "")
            self._raw.setVisible(show_raw)
        else:
            flat = " ".join(text.split())
            self._text.setText(flat if len(flat) <= PREVIEW_CHARS else flat[:PREVIEW_CHARS].rstrip() + "…")
            self._raw.setVisible(False)

    def mousePressEvent(self, event):
        self._expanded = not self._expanded
        self._render()

    def _on_copy(self):
        pyperclip.copy(self._entry["text"])
        self._copy.setText("Copied")
        QTimer.singleShot(1500, lambda: self._copy.setText("Copy"))


class HistoryPage(Page):
    def __init__(self, ctx):
        super().__init__()
        self._store = HistoryStore()
        self._tm = ToneManager()
        self._limit = PAGE_SIZE

        self.column.addWidget(PageHeader(
            "History", "Everything you've dictated, newest first. The last 500 are kept on this PC."))

        bar = QHBoxLayout()
        self._search = SearchField("Search transcriptions")
        self._search.textChanged.connect(self._on_search)
        self._count = label("", "Tertiary")
        clear = QPushButton("Clear All")
        clear.setObjectName("Ghost")
        clear.clicked.connect(self._on_clear)
        bar.addWidget(self._search, 1)
        bar.addWidget(self._count)
        bar.addWidget(clear)
        self.column.addLayout(bar)

        # Day groups go here (rebuilt by refresh)
        self._groups = QVBoxLayout()
        self._groups.setSpacing(24)
        self.column.addLayout(self._groups)

        self._more = QPushButton("Show more")
        self._more.clicked.connect(self._on_more)
        self.column.addWidget(self._more, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.column.addStretch()

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        clear_layout(self._groups)

        query = self._search.text().strip()
        entries = self._store.search(query) if query else self._store.get_all()
        total = len(self._store.get_all())
        self._count.setText(f"{len(entries)} of {total}" if query else f"{total} dictation{'s' if total != 1 else ''}")

        if not entries:
            msg = "No matches." if query else "Nothing yet — hold F15 in any app to dictate."
            self._groups.addWidget(label(msg, "Secondary"))
            self._more.hide()
            return

        shown = entries[: self._limit]
        self._more.setVisible(len(entries) > self._limit)

        current_day, section, count_in_day = None, None, 0
        for entry in shown:
            day = datetime.fromisoformat(entry["timestamp"]).date()
            if day != current_day:
                current_day = day
                section = Section(day_heading(day))
                section.body.setSpacing(0)
                section.body.setContentsMargins(16, 2, 8, 2)
                self._groups.addWidget(section)
                count_in_day = 0
            if count_in_day:
                section.body.addWidget(divider())
            exe = entry.get("app", "")
            name = app_info.friendly_name(exe, self._tm.app_path(exe)) if exe else ""
            section.body.addWidget(HistoryRow(entry, name, self._on_delete))
            count_in_day += 1

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_search(self):
        self._limit = PAGE_SIZE
        self.refresh()

    def _on_more(self):
        self._limit += PAGE_SIZE
        self.refresh()

    def _on_delete(self, entry_id: str):
        self._store.delete(entry_id)
        self.refresh()

    def _on_clear(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Delete all transcription history? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._store.clear()
            self.refresh()
