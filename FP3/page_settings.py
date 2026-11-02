from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from tone_manager import ToneManager
from ui_common import Page, PageHeader, Section, divider, key_combo, label, switch_row


SHORTCUTS = [
    (("Hold F15",),          "Dictate — release to paste"),
    (("F15 ×2",),            "Double-tap for hands-free recording"),
    (("Ctrl", "F15"),        "Summarize what you say"),
    (("Alt", "F15"),         "Ask a question"),
    (("Esc",),               "Cancel recording or dictation"),
    (("Ctrl", "Alt", "V"),   "Paste the last transcription again"),
]


class SettingsPage(Page):
    def __init__(self, ctx):
        super().__init__()
        self._ctx = ctx
        self._tm = ToneManager()
        s = self._tm.settings

        self.column.addWidget(PageHeader("Settings"))

        # General
        general = Section("General")
        row, _ = switch_row(
            "Always English",
            "On: assumes you're speaking English (most accurate). "
            "Off: detects the language you speak and translates it into English.",
            s.get("always_english", True), self._setter("always_english"),
        )
        general.body.addWidget(row)
        self.column.addWidget(general)

        # Polishing
        polishing = Section("Polishing")
        row, _ = switch_row(
            "Polish with Qwen3",
            "Fixes grammar, punctuation and filler words. When off, Whisper's text is pasted as-is.",
            s.get("polish_enabled", True), self._setter("polish_enabled"),
        )
        polishing.body.addWidget(row)
        polishing.body.addWidget(label("Tone and your personal style are on the Style page.", "Tertiary"))
        self.column.addWidget(polishing)

        # Models
        models = Section("Models")
        models.body.addWidget(self._model_row("Speech", f"Whisper {ctx.model_name}"))
        models.body.addWidget(divider())
        models.body.addWidget(self._model_row("Polishing", "Qwen3 0.6B"))
        models.body.addWidget(divider())
        self._timing = label("", "Tertiary")
        models.body.addWidget(self._timing)
        self.column.addWidget(models)

        # Shortcuts
        shortcuts = Section("Shortcuts")
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        for i, (keys, desc) in enumerate(SHORTCUTS):
            grid.addWidget(key_combo(*keys), i, 0)
            grid.addWidget(label(desc), i, 1)
        grid.setColumnStretch(1, 1)
        shortcuts.body.addLayout(grid)
        self.column.addWidget(shortcuts)

        self.column.addStretch()
        self.refresh()

    def _setter(self, key: str):
        def save(value: bool):
            self._tm.settings[key] = value
            self._tm.save_settings()
        return save

    def _model_row(self, role: str, name: str) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(name))
        text.addWidget(label(f"{role} · runs on your GPU, loaded at startup", "Tertiary"))
        h.addLayout(text, 1)
        h.addWidget(label("● Ready", "Secondary"))
        return row

    def refresh(self):
        t = getattr(self._ctx, "last_timing", None)
        if not t:
            self._timing.setText("No dictations yet since OpenWhispr started.")
        elif t.get("polish") is None:
            self._timing.setText(f"Last dictation: transcribed in {t['transcribe']:.2f}s (not polished)")
        else:
            self._timing.setText(
                f"Last dictation: transcribed in {t['transcribe']:.2f}s, polished in {t['polish']:.2f}s"
            )
