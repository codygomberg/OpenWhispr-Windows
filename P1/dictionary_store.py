import json
import os
import re


DATA_DIR = os.path.join(os.environ["APPDATA"], "OpenWhispr")
DICT_FILE = os.path.join(DATA_DIR, "dictionary.json")


class DictionaryStore:
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
        self._data = self._load()
        self._pattern_cache: dict[str, re.Pattern] = {}
        self._compile_all()
        self._loaded = True

    def _load(self):
        if not os.path.exists(DICT_FILE):
            return {"enabled": False, "corrections": {}}
        try:
            with open(DICT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Ensure enabled defaults to False per v1.1
            data.setdefault("enabled", False)
            data.setdefault("corrections", {})
            return data
        except (json.JSONDecodeError, OSError):
            return {"enabled": False, "corrections": {}}

    def _save(self):
        with open(DICT_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _compile_all(self):
        self._pattern_cache = {}
        for key in self._data["corrections"]:
            self._compile(key)

    def _compile(self, key: str):
        escaped = re.escape(key)
        self._pattern_cache[key] = re.compile(rf"\b{escaped}\b", re.IGNORECASE)

    @property
    def enabled(self) -> bool:
        return self._data["enabled"]

    @enabled.setter
    def enabled(self, value: bool):
        self._data["enabled"] = value
        self._save()

    def apply(self, text: str) -> str:
        if not self.enabled:
            return text
        for key, correction in self._data["corrections"].items():
            pattern = self._pattern_cache.get(key)
            if pattern:
                text = pattern.sub(correction, text)
        return text

    def add(self, original: str, corrected: str):
        self._data["corrections"][original.lower()] = corrected
        self._compile(original.lower())
        self._save()

    def remove(self, original: str):
        key = original.lower()
        self._data["corrections"].pop(key, None)
        self._pattern_cache.pop(key, None)
        self._save()

    def get_all(self) -> dict:
        return dict(self._data["corrections"])
