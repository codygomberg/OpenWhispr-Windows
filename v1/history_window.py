import pyperclip
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import theme
from history_store import HistoryStore


_STYLE = f"""
    QWidget {{ background: {theme.WINDOW_BG}; color: {theme.TEXT_PRIMARY}; }}
    QLineEdit {{
        background: {theme.SURFACE_BG};
        border: 1px solid {theme.SEPARATOR};
        border-radius: 6px;
        padding: 6px 10px;
        color: {theme.TEXT_PRIMARY};
        font-size: {theme.FONT_SIZE_UI}px;
    }}
    QListWidget {{
        background: {theme.SURFACE_BG};
        border: 1px solid {theme.SEPARATOR};
        border-radius: 6px;
        color: {theme.TEXT_PRIMARY};
        font-size: {theme.FONT_SIZE_UI}px;
    }}
    QListWidget::item {{ padding: 8px; border-bottom: 1px solid {theme.SEPARATOR}; }}
    QListWidget::item:selected {{ background: {theme.ACCENT}; }}
    QPushButton {{
        background: {theme.SURFACE_BG};
        border: 1px solid {theme.SEPARATOR};
        border-radius: 6px;
        padding: 6px 14px;
        color: {theme.TEXT_PRIMARY};
        font-size: {theme.FONT_SIZE_UI}px;
    }}
    QPushButton:hover {{ background: {theme.ACCENT}; border-color: {theme.ACCENT}; }}
"""


class HistoryWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenWhispr — History")
        self.setMinimumSize(560, 480)
        self.setStyleSheet(_STYLE)

        self._store = HistoryStore()
        self._entries = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search transcriptions…")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # List
        self._list = QListWidget()
        self._list.setFont(QFont(theme.FONT_FAMILY, theme.FONT_SIZE_UI))
        layout.addWidget(self._list)

        # Buttons
        btn_row = QHBoxLayout()
        self._copy_btn = QPushButton("Copy")
        self._delete_btn = QPushButton("Delete")
        self._clear_btn = QPushButton("Clear All")
        for btn in (self._copy_btn, self._delete_btn, self._clear_btn):
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        self._copy_btn.clicked.connect(self._on_copy)
        self._delete_btn.clicked.connect(self._on_delete)
        self._clear_btn.clicked.connect(self._on_clear)

        self._refresh()

    def showEvent(self, event):
        self._refresh()
        super().showEvent(event)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh(self, entries=None):
        self._entries = entries if entries is not None else self._store.get_all()
        self._list.clear()
        for entry in self._entries:
            ts = entry["timestamp"][:16].replace("T", "  ")
            preview = entry["text"][:120].replace("\n", " ")
            item = QListWidgetItem(f"{ts}  —  {preview}")
            item.setData(Qt.ItemDataRole.UserRole, entry["id"])
            self._list.addItem(item)

    def _on_search(self, query: str):
        if query.strip():
            self._refresh(self._store.search(query))
        else:
            self._refresh()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _selected_entry(self):
        items = self._list.selectedItems()
        if not items:
            return None
        entry_id = items[0].data(Qt.ItemDataRole.UserRole)
        return next((e for e in self._entries if e["id"] == entry_id), None)

    def _on_copy(self):
        entry = self._selected_entry()
        if entry:
            pyperclip.copy(entry["text"])

    def _on_delete(self):
        entry = self._selected_entry()
        if entry:
            self._store.delete(entry["id"])
            self._refresh()

    def _on_clear(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Delete all transcription history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._store.clear()
            self._refresh()
