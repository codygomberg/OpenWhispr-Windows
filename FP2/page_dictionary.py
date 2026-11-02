from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dictionary_store import DictionaryStore
from ui_common import Page, PageHeader, Section, SearchField, card, clear_layout, divider, label, switch_row


class AddWordDialog(QDialog):
    """Two fields: what Whisper writes → what it should be."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Word")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(12)
        layout.addWidget(label("Add Word", "PageTitle"))
        layout.addWidget(label(
            "When Whisper writes the first one, OpenWhispr replaces it with the second. "
            "Matches whole words, ignoring capitals.", "Secondary", wrap=True))

        form = QFormLayout()
        form.setSpacing(10)
        self.heard = QLineEdit()
        self.heard.setPlaceholderText("e.g. open whisper")
        self.fixed = QLineEdit()
        self.fixed.setPlaceholderText("e.g. OpenWhispr")
        form.addRow("Whisper writes", self.heard)
        form.addRow("Replace with", self.fixed)
        layout.addLayout(form)

        self.hint = label("", "Tertiary")
        layout.addWidget(self.hint)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        self.add_btn = QPushButton("Add")
        self.add_btn.setObjectName("Primary")
        self.add_btn.setDefault(True)
        cancel.clicked.connect(self.reject)
        self.add_btn.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(self.add_btn)
        layout.addLayout(buttons)

        self.heard.textChanged.connect(self._validate)
        self.fixed.textChanged.connect(self._validate)
        self._validate()

    def _validate(self):
        heard, fixed = self.heard.text().strip(), self.fixed.text().strip()
        same = bool(heard) and heard == fixed
        self.hint.setText("These are identical — there's nothing to correct." if same else "")
        self.add_btn.setEnabled(bool(heard) and bool(fixed) and not same)

    def values(self) -> tuple[str, str]:
        return self.heard.text().strip(), self.fixed.text().strip()


class DictionaryPage(Page):
    def __init__(self, ctx):
        super().__init__()
        self._store = DictionaryStore()

        self.column.addWidget(PageHeader(
            "Dictionary",
            "Fix names, brands and jargon Whisper keeps getting wrong. Corrections apply just before pasting.",
        ))

        toggle = Section("Corrections")
        row, self._switch = switch_row(
            "Use dictionary corrections", "", self._store.enabled, self._on_toggle)
        toggle.body.addWidget(row)
        self._off_note = label("Off — the words below are not being applied.", "Tertiary")
        toggle.body.addWidget(self._off_note)
        self.column.addWidget(toggle)

        # Search + Add
        bar = QHBoxLayout()
        self._search = SearchField("Search words")
        self._search.textChanged.connect(self.refresh)
        add = QPushButton("Add Word")
        add.setObjectName("Primary")
        add.clicked.connect(self._on_add)
        bar.addWidget(self._search, 1)
        bar.addWidget(add)
        self.column.addLayout(bar)

        # Word list (rebuilt by refresh)
        self._list_frame, self._list = card()
        self._list.setSpacing(0)
        self._list.setContentsMargins(16, 6, 8, 6)
        self.column.addWidget(self._list_frame)

        self.column.addStretch()
        self.refresh()

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self):
        self._off_note.setVisible(not self._store.enabled)
        clear_layout(self._list)

        query = self._search.text().strip().lower()
        words = sorted(self._store.get_all().items())
        if query:
            words = [(k, v) for k, v in words if query in k.lower() or query in v.lower()]

        if not words:
            msg = "No matches." if query else "No words yet. Click Add Word to teach OpenWhispr a spelling."
            empty = label(msg, "Tertiary")
            empty.setContentsMargins(0, 12, 0, 12)
            self._list.addWidget(empty)
            return

        for i, (heard, fixed) in enumerate(words):
            if i:
                self._list.addWidget(divider())
            self._list.addWidget(self._word_row(heard, fixed))

    def _word_row(self, heard: str, fixed: str) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 6, 0, 6)
        h.addWidget(label(heard, "Secondary"))
        h.addWidget(label("→", "Tertiary"))
        h.addWidget(label(fixed))
        h.addStretch()
        remove = QPushButton("✕")
        remove.setObjectName("Ghost")
        remove.setToolTip("Remove")
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.clicked.connect(lambda: self._on_remove(heard))
        h.addWidget(remove)
        return row

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_toggle(self, checked: bool):
        self._store.enabled = checked
        self._off_note.setVisible(not checked)

    def _on_add(self):
        dialog = AddWordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            heard, fixed = dialog.values()
            self._store.add(heard, fixed)
            self._search.clear()
            self.refresh()

    def _on_remove(self, heard: str):
        self._store.remove(heard)
        self.refresh()
