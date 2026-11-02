from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import theme
from tone_manager import ToneManager, TONES


_STYLE = f"""
    QWidget {{ background: {theme.WINDOW_BG}; color: {theme.TEXT_PRIMARY}; font-family: {theme.FONT_FAMILY}; }}
    QGroupBox {{
        border: 1px solid {theme.SEPARATOR};
        border-radius: 8px;
        margin-top: 12px;
        padding: 10px;
        font-size: {theme.FONT_SIZE_UI}px;
        color: {theme.TEXT_SECONDARY};
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
    QComboBox, QLineEdit {{
        background: {theme.SURFACE_BG};
        border: 1px solid {theme.SEPARATOR};
        border-radius: 6px;
        padding: 5px 8px;
        color: {theme.TEXT_PRIMARY};
        font-size: {theme.FONT_SIZE_UI}px;
    }}
    QComboBox::drop-down {{ border: none; }}
    QPushButton {{
        background: {theme.SURFACE_BG};
        border: 1px solid {theme.SEPARATOR};
        border-radius: 6px;
        padding: 5px 12px;
        color: {theme.TEXT_PRIMARY};
        font-size: {theme.FONT_SIZE_UI}px;
    }}
    QPushButton:hover {{ background: {theme.ACCENT}; border-color: {theme.ACCENT}; }}
    QCheckBox {{ font-size: {theme.FONT_SIZE_UI}px; spacing: 8px; }}
    QTableWidget {{
        background: {theme.SURFACE_BG};
        border: 1px solid {theme.SEPARATOR};
        border-radius: 6px;
        gridline-color: {theme.SEPARATOR};
        font-size: {theme.FONT_SIZE_UI}px;
    }}
    QHeaderView::section {{
        background: {theme.WINDOW_BG};
        color: {theme.TEXT_SECONDARY};
        padding: 4px;
        border: none;
        font-size: {theme.FONT_SIZE_SMALL}px;
    }}
    QLabel {{ font-size: {theme.FONT_SIZE_UI}px; }}
"""


class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OpenWhispr — Settings")
        self.setMinimumWidth(480)
        self.setStyleSheet(_STYLE)

        self._tm = ToneManager()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_polish_group())
        layout.addWidget(self._build_tone_group())
        layout.addWidget(self._build_overrides_group())
        layout.addWidget(self._build_dict_group())
        layout.addWidget(self._build_hotkeys_group())
        layout.addStretch()

    # ── Polishing ─────────────────────────────────────────────────────────────

    def _build_polish_group(self) -> QGroupBox:
        box = QGroupBox("Text Polishing")
        vbox = QVBoxLayout(box)

        self._polish_toggle = QCheckBox("Enable LLM polishing")
        self._polish_toggle.setChecked(self._tm.settings.get("polish_enabled", True))
        self._polish_toggle.toggled.connect(self._on_polish_toggled)
        note = QLabel("When off, Whisper output is pasted as-is with no grammar cleanup.")
        note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: {theme.FONT_SIZE_SMALL}px;")
        note.setWordWrap(True)
        vbox.addWidget(self._polish_toggle)
        vbox.addWidget(note)

        self._english_toggle = QCheckBox("Always output in English")
        self._english_toggle.setChecked(self._tm.settings.get("always_english", True))
        self._english_toggle.toggled.connect(self._on_english_toggled)
        eng_note = QLabel("When off, Whisper auto-detects the spoken language and outputs in that language.")
        eng_note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: {theme.FONT_SIZE_SMALL}px;")
        eng_note.setWordWrap(True)
        vbox.addWidget(self._english_toggle)
        vbox.addWidget(eng_note)

        form = QFormLayout()
        self._style_input = QLineEdit()
        self._style_input.setPlaceholderText("e.g. Keep sentences short and punchy.")
        self._style_input.setText(self._tm.settings.get("style_description", ""))
        self._style_input.editingFinished.connect(self._on_style_changed)
        style_note = QLabel("Style hint passed to the LLM on every polish.")
        style_note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: {theme.FONT_SIZE_SMALL}px;")
        form.addRow("Custom style:", self._style_input)
        vbox.addLayout(form)
        vbox.addWidget(style_note)

        return box

    def _on_polish_toggled(self, checked: bool):
        self._tm.settings["polish_enabled"] = checked
        self._tm.save_settings()

    def _on_english_toggled(self, checked: bool):
        self._tm.settings["always_english"] = checked
        self._tm.save_settings()

    def _on_style_changed(self):
        self._tm.settings["style_description"] = self._style_input.text().strip()
        self._tm.save_settings()

    # ── Tone ──────────────────────────────────────────────────────────────────

    def _build_tone_group(self) -> QGroupBox:
        box = QGroupBox("Base Tone")
        form = QFormLayout(box)
        self._tone_combo = QComboBox()
        for t in TONES:
            self._tone_combo.addItem(t.capitalize(), t)
        current = self._tm.settings.get("base_tone", "neutral")
        self._tone_combo.setCurrentIndex(list(TONES).index(current))
        self._tone_combo.currentIndexChanged.connect(self._on_tone_changed)
        form.addRow("Default tone for all apps:", self._tone_combo)
        return box

    def _on_tone_changed(self):
        self._tm.settings["base_tone"] = self._tone_combo.currentData()
        self._tm.save_settings()

    # ── Per-app overrides ─────────────────────────────────────────────────────

    def _build_overrides_group(self) -> QGroupBox:
        box = QGroupBox("Per-App Tone Overrides")
        vbox = QVBoxLayout(box)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Process (e.g. chrome.exe)", "Tone"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        vbox.addWidget(self._table)

        row = QHBoxLayout()
        self._proc_input = QLineEdit()
        self._proc_input.setPlaceholderText("chrome.exe")
        self._override_combo = QComboBox()
        for t in TONES:
            self._override_combo.addItem(t.capitalize(), t)
        add_btn = QPushButton("Add")
        remove_btn = QPushButton("Remove Selected")
        add_btn.clicked.connect(self._on_add_override)
        remove_btn.clicked.connect(self._on_remove_override)
        row.addWidget(self._proc_input)
        row.addWidget(self._override_combo)
        row.addWidget(add_btn)
        row.addWidget(remove_btn)
        vbox.addLayout(row)

        self._refresh_table()
        return box

    def _refresh_table(self):
        overrides = self._tm.get_all_overrides()
        self._table.setRowCount(0)
        for proc, tone in overrides.items():
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(proc))
            self._table.setItem(r, 1, QTableWidgetItem(tone.capitalize()))

    def _on_add_override(self):
        proc = self._proc_input.text().strip().lower()
        if not proc:
            return
        tone = self._override_combo.currentData()
        self._tm.set_override(proc, tone)
        self._proc_input.clear()
        self._refresh_table()

    def _on_remove_override(self):
        selected = self._table.selectedItems()
        if not selected:
            return
        proc = self._table.item(selected[0].row(), 0).text()
        self._tm.remove_override(proc)
        self._refresh_table()

    # ── Dictionary ────────────────────────────────────────────────────────────

    def _build_dict_group(self) -> QGroupBox:
        box = QGroupBox("Custom Dictionary")
        vbox = QVBoxLayout(box)

        from dictionary_store import DictionaryStore
        self._dict = DictionaryStore()

        self._dict_toggle = QCheckBox("Enable dictionary corrections")
        self._dict_toggle.setChecked(self._dict.enabled)
        self._dict_toggle.toggled.connect(self._on_dict_toggled)
        note = QLabel("When enabled, the app learns corrections from your edits after pasting.")
        note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: {theme.FONT_SIZE_SMALL}px;")
        note.setWordWrap(True)
        vbox.addWidget(self._dict_toggle)
        vbox.addWidget(note)
        return box

    def _on_dict_toggled(self, checked: bool):
        self._dict.enabled = checked

    # ── Hotkey reference ──────────────────────────────────────────────────────

    def _build_hotkeys_group(self) -> QGroupBox:
        box = QGroupBox("Hotkeys")
        form = QFormLayout(box)
        hotkeys = [
            ("Hold F15",         "Record and transcribe"),
            ("Double-tap F15",   "Toggle hands-free recording"),
            ("Ctrl + F15",       "Record and summarize"),
            ("Alt + F15",        "Record and ask (Q&A mode)"),
            ("Ctrl + Alt + V",   "Re-paste last transcription"),
        ]
        for key, desc in hotkeys:
            key_label = QLabel(key)
            key_label.setStyleSheet(
                f"background: {theme.SURFACE_BG}; border-radius: 4px; "
                f"padding: 2px 6px; font-family: Consolas; font-size: {theme.FONT_SIZE_SMALL}px;"
            )
            form.addRow(key_label, QLabel(desc))
        return box
