import json
import os

import psutil
import win32gui
import win32process


DATA_DIR = os.path.join(os.environ["APPDATA"], "OpenWhispr")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

TONES = ("neutral", "professional", "casual", "raw")


class ToneManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return
        os.makedirs(DATA_DIR, exist_ok=True)
        self._settings = self._load_settings()
        self._loaded = True

    # ── Settings ──────────────────────────────────────────────────────────────

    def _load_settings(self) -> dict:
        if not os.path.exists(SETTINGS_FILE):
            return self._default_settings()
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                s = json.load(f)
            s.setdefault("base_tone", "neutral")
            s.setdefault("app_tones", {})
            s.setdefault("dictionary_enabled", False)
            s.setdefault("whisper_model", "large-v3-turbo")
            s.setdefault("polish_enabled", True)
            s.setdefault("style_description", "")
            s.setdefault("always_english", True)
            s.setdefault("app_paths", {})
            return s
        except (json.JSONDecodeError, OSError):
            return self._default_settings()

    def _default_settings(self) -> dict:
        return {
            "base_tone": "neutral",
            "app_tones": {},
            "dictionary_enabled": False,
            "whisper_model": "large-v3-turbo",
            "polish_enabled": True,
            "style_description": "",
            "always_english": True,
            "app_paths": {},   # exe name → full path, for icons and friendly names
        }

    def save_settings(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2)

    @property
    def settings(self) -> dict:
        return self._settings

    # ── Active window ─────────────────────────────────────────────────────────

    def get_active_process(self) -> str:
        """Return the exe name of the currently focused window, e.g. 'chrome.exe'."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower()
        except Exception:
            return ""

    def get_active_process_path(self) -> str:
        """Full path of the focused window's program, e.g. 'C:\\...\\chrome.exe'."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).exe()
        except Exception:
            return ""

    # ── Known app paths (icons / names) ───────────────────────────────────────

    def remember_app(self, process: str, path: str):
        """Save where an app lives so its icon shows even when it isn't running."""
        if not process or not path:
            return
        paths = self._settings.setdefault("app_paths", {})
        if paths.get(process.lower()) != path:
            paths[process.lower()] = path
            self.save_settings()

    def app_path(self, process: str) -> str:
        return self._settings.get("app_paths", {}).get(process.lower(), "")

    # ── Tone resolution ───────────────────────────────────────────────────────

    def get_active_tone(self) -> str:
        """Return the effective tone for whatever window is currently focused."""
        process = self.get_active_process()
        overrides = self._settings.get("app_tones", {})
        if process in overrides:
            return overrides[process]
        return self._settings.get("base_tone", "neutral")

    # ── Override management ───────────────────────────────────────────────────

    def set_override(self, process: str, tone: str):
        self._settings["app_tones"][process.lower()] = tone
        self.save_settings()

    def remove_override(self, process: str):
        self._settings["app_tones"].pop(process.lower(), None)
        self.save_settings()

    def get_all_overrides(self) -> dict:
        return dict(self._settings.get("app_tones", {}))
