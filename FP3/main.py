import sys
import threading
import time

import pyperclip
from PIL import Image, ImageDraw
from pynput import keyboard as kb
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QGuiApplication, QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import theme
import ui_common
from dictionary_store import DictionaryStore
from history_store import HistoryStore
from main_window import MainWindow
from pill_window import PillWindow
from recorder import AudioRecorder
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
    status    = pyqtSignal(str, str)   # message, dot_color
    recording = pyqtSignal(str, bool)  # mode, hands_free
    working   = pyqtSignal(str, str)   # message, spinner color
    flash     = pyqtSignal(str)        # short message, then hide
    done      = pyqtSignal()
    hide      = pyqtSignal()
    saved     = pyqtSignal()           # a dictation was added to history


# ── Main application ───────────────────────────────────────────────────────────

class OpenWhispr(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._signals = PipelineSignals()

        # UI
        self._pill = PillWindow()
        self._window: MainWindow | None = None
        self._tray = None
        self._tray_status = None

        # Connect signals (all UI updates happen on the main thread)
        self._signals.status.connect(self._pill.show_status)
        self._signals.recording.connect(self._pill.show_recording)
        self._signals.working.connect(self._pill.show_working)
        self._signals.flash.connect(self._pill.flash)
        self._signals.done.connect(self._pill.show_done)
        self._signals.hide.connect(self._pill.hide_pill)

        # Same events also update the tray status line and the window's status chip
        self._signals.recording.connect(self._on_recording_state)
        self._signals.working.connect(self._on_working_state)
        self._signals.flash.connect(self._on_flash_state)
        self._signals.done.connect(self._on_idle_state)
        self._signals.hide.connect(self._on_idle_state)
        self._signals.saved.connect(self._on_saved)

        # Data/logic
        self._tone_mgr   = ToneManager()
        self._history    = HistoryStore()
        self._dictionary = DictionaryStore()
        self._recorder   = AudioRecorder()

        # Pill waveform + hands-free ■ / ✕ buttons
        self._pill.set_level_source(lambda: self._recorder.level)
        self._pill.on_stop = self._stop_hands_free
        self._pill.on_cancel = self._cancel

        # State
        self._recording      = False
        self._hands_free     = False
        self._processing     = False
        self._cancelled      = False
        self._f15_held       = False
        self._last_f15_time  = 0.0
        self._current_mode   = "normal"
        self._ctrl_held      = False
        self._alt_held       = False
        self._last_text      = self._history.get_last()   # Ctrl+Alt+V works right after a restart
        self._saved_clipboard = ""

        # Read by the Settings page
        self.model_name  = self._tone_mgr.settings.get("whisper_model", "large-v3-turbo")
        self.last_timing = None   # {"transcribe": seconds, "polish": seconds or None}

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
        tray.setToolTip("OpenWhispr — Ready")

        menu = QMenu()
        self._tray_status = menu.addAction("OpenWhispr — Ready")
        self._tray_status.setEnabled(False)
        menu.addSeparator()
        open_action  = menu.addAction("Open OpenWhispr")
        self._paste_action = menu.addAction("Paste Last Transcription\tCtrl+Alt+V")
        settings_action = menu.addAction("Settings…")
        menu.addSeparator()
        quit_action = menu.addAction("Quit OpenWhispr")

        open_action.triggered.connect(lambda: self._open_window())
        self._paste_action.triggered.connect(self.paste_last)
        settings_action.triggered.connect(lambda: self._open_window("settings"))
        quit_action.triggered.connect(self._quit)
        menu.aboutToShow.connect(lambda: self._paste_action.setEnabled(bool(self._last_text)))

        self._tray_menu = menu   # keep a reference so it isn't garbage-collected
        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        return tray

    @pyqtSlot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason):
        # Single left-click opens the window; right-click shows the menu
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._open_window()

    # ── Status (tray line + window chip) ───────────────────────────────────────

    def _set_state(self, text: str, color: str):
        if self._tray_status is not None:
            self._tray_status.setText(f"OpenWhispr — {text}")
            self._tray.setToolTip(f"OpenWhispr — {text}")
        if self._window is not None:
            self._window.set_status(text, color)

    @pyqtSlot(str, bool)
    def _on_recording_state(self, mode: str, hands_free: bool):
        if hands_free:
            self._set_state("Recording (hands-free)", theme.COLOR_LOCKED)
        elif mode == "summarize":
            self._set_state("Recording summary", theme.COLOR_SUMMARIZE)
        elif mode == "qa":
            self._set_state("Recording question", theme.COLOR_QUESTION)
        else:
            self._set_state("Recording", theme.COLOR_RECORDING)

    @pyqtSlot(str, str)
    def _on_working_state(self, message: str, color: str):
        self._set_state(message.rstrip("…"), color)

    @pyqtSlot(str)
    def _on_flash_state(self, message: str):
        self._set_state("Ready", theme.COLOR_DONE)

    @pyqtSlot()
    def _on_idle_state(self):
        self._set_state("Ready", theme.COLOR_DONE)

    @pyqtSlot()
    def _on_saved(self):
        if self._window is not None:
            self._window.refresh_current()

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

        # Escape — cancel the current recording or dictation (ignored when idle)
        if key == kb.Key.esc:
            self._cancel()
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

    def _stop_hands_free(self):
        """Pill ■ button — same as double-tapping F15 to finish."""
        if self._hands_free:
            self._toggle_hands_free()

    def _cancel(self):
        """Escape or pill ✕ — drop the recording/dictation without pasting."""
        if not (self._recording or self._processing):
            return
        self._cancelled = True
        self._hands_free = False
        if self._recording and not self._processing:
            self._recorder.stop()
            self._recording = False
        self._signals.flash.emit("Cancelled")

    # ── Recording pipeline ─────────────────────────────────────────────────────

    def _start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._cancelled = False
        self._signals.recording.emit(self._current_mode, self._hands_free)
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
            self._tone_mgr.remember_app(app, self._tone_mgr.get_active_process_path())

            # Transcribe
            self._signals.working.emit("Transcribing…", theme.COLOR_WORKING)
            always_english = self._tone_mgr.settings.get("always_english", True)
            t0 = time.perf_counter()
            raw = self._transcriber.transcribe(audio, always_english=always_english)
            t1 = time.perf_counter()

            if self._cancelled:
                return
            if not raw.strip():
                self._signals.hide.emit()
                return

            # Polish — skip if globally disabled or tone is set to Raw
            polish_enabled = self._tone_mgr.settings.get("polish_enabled", True)
            did_polish = polish_enabled and tone != "raw"
            if not did_polish:
                polished = raw
            else:
                self._signals.working.emit("Polishing…", theme.COLOR_WORKING)
                style = self._tone_mgr.settings.get("style_description", "")
                polished = self._processor.process(raw, mode=self._current_mode, tone=tone, style_description=style)
            t2 = time.perf_counter()
            self.last_timing = {"transcribe": t1 - t0, "polish": (t2 - t1) if did_polish else None}

            if self._cancelled:
                return

            # Dictionary corrections (off by default)
            polished = self._dictionary.apply(polished)

            # Save to history
            duration = len(audio) / 16_000   # seconds of speech, for Home page stats
            self._history.add(raw, polished, self._current_mode, tone, app, duration=duration)
            self._last_text = polished
            self._signals.saved.emit()

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

    def paste_last(self):
        """Tray menu: paste the last transcription into whatever window had focus."""
        if not self._last_text:
            return
        def _go():
            time.sleep(0.3)   # let the tray menu close and focus return to the previous window
            self._paste(self._last_text)
        threading.Thread(target=_go, daemon=True).start()

    # ── Window ─────────────────────────────────────────────────────────────────

    def _open_window(self, page: str | None = None):
        if self._window is None:
            self._window = MainWindow(self)
        if page:
            self._window.show_page(page)
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    @pyqtSlot()
    def _quit(self):
        self._tray.hide()
        self._app.quit()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # keep running when windows are closed

    # Light/dark mode follows Windows, and switches live when Windows does
    app.setStyle("Fusion")
    ui_common.apply_theme(app)
    QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _: ui_common.apply_theme(app))

    ow = OpenWhispr(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
