import sys
import threading
import time

import pyperclip
from PIL import Image, ImageDraw
from pynput import keyboard as kb
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import theme
from dictionary_store import DictionaryStore
from history_store import HistoryStore
from history_window import HistoryWindow
from pill_window import PillWindow
from recorder import AudioRecorder
from settings_window import SettingsWindow
from text_processor import TextProcessor
from tone_manager import ToneManager
from transcriber import WhisperTranscriber


# ── Tray icon ──────────────────────────────────────────────────────────────────

def _make_tray_icon() -> QIcon:
    """Draw a simple microphone icon for the system tray."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Mic body
    d.rounded_rectangle([20, 4, 44, 38], radius=12, fill="#FFFFFF")
    # Mic stand arm
    d.arc([10, 24, 54, 52], start=0, end=180, fill="#FFFFFF", width=4)
    # Mic stand base
    d.line([32, 50, 32, 60], fill="#FFFFFF", width=4)
    d.line([24, 60, 40, 60], fill="#FFFFFF", width=4)

    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import QByteArray, QBuffer
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buf.getvalue())
    return QIcon(pixmap)


# ── Pipeline signals ───────────────────────────────────────────────────────────

class PipelineSignals(QObject):
    status   = pyqtSignal(str, str)   # message, dot_color
    done     = pyqtSignal()
    hide     = pyqtSignal()


# ── Main application ───────────────────────────────────────────────────────────

class OpenWhispr(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._signals = PipelineSignals()

        # UI
        self._pill = PillWindow()
        self._settings_win: SettingsWindow | None = None
        self._history_win: HistoryWindow | None = None

        # Connect signals (all UI updates happen on the main thread)
        self._signals.status.connect(self._pill.show_status)
        self._signals.done.connect(self._pill.show_done)
        self._signals.hide.connect(self._pill.hide_pill)

        # Data/logic
        self._tone_mgr   = ToneManager()
        self._history    = HistoryStore()
        self._dictionary = DictionaryStore()
        self._recorder   = AudioRecorder()

        # State
        self._recording      = False
        self._hands_free     = False
        self._processing     = False
        self._f15_held       = False
        self._last_f15_time  = 0.0
        self._current_mode   = "normal"
        self._ctrl_held      = False
        self._alt_held       = False
        self._last_text      = ""
        self._saved_clipboard = ""

        # Load models (blocking — shows status in pill while loading)
        self._load_models()

        # System tray
        self._tray = self._build_tray()
        self._tray.show()

        # Keyboard listener (background thread)
        self._start_keyboard_listener()

    # ── Model loading ──────────────────────────────────────────────────────────

    def _load_models(self):
        def _status(msg):
            self._signals.status.emit(msg, theme.COLOR_WORKING)
            QApplication.processEvents()

        self._signals.status.emit("Starting up…", theme.COLOR_WORKING)
        QApplication.processEvents()

        self._transcriber = WhisperTranscriber(
            model_size=self._tone_mgr.settings.get("whisper_model", "large-v3"),
            status_callback=_status,
        )
        self._processor = TextProcessor(status_callback=_status)

        self._signals.done.emit()

    # ── System tray ────────────────────────────────────────────────────────────

    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(_make_tray_icon(), self._app)
        tray.setToolTip("OpenWhispr")

        menu = QMenu()
        menu.setStyleSheet(
            f"QMenu {{ background: {theme.WINDOW_BG}; color: {theme.TEXT_PRIMARY}; "
            f"border: 1px solid {theme.SEPARATOR}; font-size: {theme.FONT_SIZE_UI}px; }}"
            f"QMenu::item:selected {{ background: {theme.ACCENT}; }}"
        )

        settings_action = menu.addAction("Settings")
        history_action  = menu.addAction("History")
        menu.addSeparator()
        quit_action = menu.addAction("Quit")

        settings_action.triggered.connect(self._open_settings)
        history_action.triggered.connect(self._open_history)
        quit_action.triggered.connect(self._quit)

        tray.setContextMenu(menu)
        tray.activated.connect(
            lambda reason: self._open_settings()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick
            else None
        )
        return tray

    # ── Keyboard listener ──────────────────────────────────────────────────────

    def _start_keyboard_listener(self):
        listener = kb.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        listener.daemon = True
        listener.start()

    def _on_key_press(self, key):
        if key in (kb.Key.ctrl_l, kb.Key.ctrl_r):
            self._ctrl_held = True
            return
        if key in (kb.Key.alt_l, kb.Key.alt_r):
            self._alt_held = True
            return

        # Ctrl+Alt+V — re-paste last transcription
        if self._ctrl_held and self._alt_held and hasattr(key, "char") and key.char == "v":
            if self._last_text:
                threading.Thread(target=self._paste, args=(self._last_text,), daemon=True).start()
            return

        if key == kb.Key.f15:
            if not self._f15_held:   # ignore Windows key-repeat events
                self._f15_held = True
                self._on_f15_press()

    def _on_key_release(self, key):
        if key in (kb.Key.ctrl_l, kb.Key.ctrl_r):
            self._ctrl_held = False
        elif key in (kb.Key.alt_l, kb.Key.alt_r):
            self._alt_held = False
        elif key == kb.Key.f15:
            self._f15_held = False
            self._on_f15_release()

    # ── F13 logic ──────────────────────────────────────────────────────────────

    def _on_f15_press(self):
        if self._processing:
            return
        now = time.time()
        elapsed = now - self._last_f15_time
        self._last_f15_time = now

        if elapsed < theme.DOUBLE_TAP_MS / 1000:
            # Double-tap — toggle hands-free
            self._toggle_hands_free()
            return

        if self._hands_free:
            return  # hands-free mode is controlled by toggle, not hold

        # Determine mode from held modifiers
        if self._ctrl_held:
            self._current_mode = "summarize"
        elif self._alt_held:
            self._current_mode = "qa"
        else:
            self._current_mode = "normal"

        self._start_recording()

    def _on_f15_release(self):
        if self._hands_free or self._processing:
            return
        if self._recording:
            threading.Thread(target=self._stop_and_process, daemon=True).start()

    def _toggle_hands_free(self):
        if self._hands_free:
            # Stop hands-free recording
            self._hands_free = False
            if self._recording:
                threading.Thread(target=self._stop_and_process, daemon=True).start()
        else:
            # Start hands-free recording
            self._hands_free = True
            if self._ctrl_held:
                self._current_mode = "summarize"
            elif self._alt_held:
                self._current_mode = "qa"
            else:
                self._current_mode = "normal"
            self._start_recording()

    # ── Recording pipeline ─────────────────────────────────────────────────────

    def _start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._signals.status.emit("Recording…", theme.COLOR_RECORDING)
        self._recorder.start()

    def _stop_and_process(self):
        """Runs on a background thread: stop mic, transcribe, polish, paste."""
        self._processing = True
        try:
            audio = self._recorder.stop()
            self._recording = False

            if audio is None or len(audio) < 8000:  # less than 0.5 s — ignore
                self._signals.hide.emit()
                return

            # Capture tone/app before focus changes
            tone = self._tone_mgr.get_active_tone()
            app  = self._tone_mgr.get_active_process()

            # Transcribe
            self._signals.status.emit("Transcribing…", theme.COLOR_WORKING)
            always_english = self._tone_mgr.settings.get("always_english", True)
            raw = self._transcriber.transcribe(audio, always_english=always_english)

            if not raw.strip():
                self._signals.hide.emit()
                return

            # Polish — skip if globally disabled or tone is set to Raw
            polish_enabled = self._tone_mgr.settings.get("polish_enabled", True)
            if not polish_enabled or tone == "raw":
                polished = raw
            else:
                self._signals.status.emit("Polishing…", theme.COLOR_WORKING)
                style = self._tone_mgr.settings.get("style_description", "")
                polished = self._processor.process(raw, mode=self._current_mode, tone=tone, style_description=style)

            # Dictionary corrections (off by default)
            polished = self._dictionary.apply(polished)

            # Save to history
            self._history.add(raw, polished, self._current_mode, tone, app)
            self._last_text = polished

            # Paste
            self._paste(polished)

            self._signals.done.emit()

        except Exception as e:
            print(f"[OpenWhispr] Pipeline error: {e}")
            self._signals.hide.emit()

        finally:
            self._processing = False
            self._recording = False

    def _paste(self, text: str):
        """Copy text to clipboard and simulate Ctrl+V in the focused window."""
        try:
            self._saved_clipboard = pyperclip.paste()
        except Exception:
            self._saved_clipboard = ""

        pyperclip.copy(text)
        time.sleep(0.05)

        controller = kb.Controller()
        with controller.pressed(kb.Key.ctrl):
            controller.press("v")
            controller.release("v")

        # Restore clipboard after a short delay
        def _restore():
            time.sleep(0.5)
            try:
                pyperclip.copy(self._saved_clipboard)
            except Exception:
                pass
        threading.Thread(target=_restore, daemon=True).start()

    # ── Windows ────────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _open_settings(self):
        if self._settings_win is None:
            self._settings_win = SettingsWindow()
        self._settings_win.show()
        self._settings_win.raise_()
        self._settings_win.activateWindow()

    @pyqtSlot()
    def _open_history(self):
        if self._history_win is None:
            self._history_win = HistoryWindow()
        self._history_win.show()
        self._history_win.raise_()
        self._history_win.activateWindow()

    @pyqtSlot()
    def _quit(self):
        self._tray.hide()
        self._app.quit()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # keep running when windows are closed
    ow = OpenWhispr(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
