import json
import os
import uuid
from datetime import datetime


DATA_DIR = os.path.join(os.environ["APPDATA"], "OpenWhispr")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


class HistoryStore:
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
        self._entries = self._load()
        self._loaded = True

    def _load(self):
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, indent=2, ensure_ascii=False)

    def add(self, raw_text: str, polished_text: str, mode: str, tone: str, app: str):
        entry = {
            "id": str(uuid.uuid4()),
            "raw": raw_text,
            "text": polished_text,
            "mode": mode,
            "tone": tone,
            "app": app,
            "timestamp": datetime.now().isoformat(),
        }
        self._entries.insert(0, entry)
        # Keep last 500 entries
        self._entries = self._entries[:500]
        self._save()
        return entry

    def get_all(self):
        return list(self._entries)

    def get_last(self) -> str:
        if self._entries:
            return self._entries[0]["text"]
        return ""

    def search(self, query: str):
        query = query.lower()
        return [e for e in self._entries if query in e["text"].lower() or query in e["raw"].lower()]

    def delete(self, entry_id: str):
        self._entries = [e for e in self._entries if e["id"] != entry_id]
        self._save()

    def clear(self):
        self._entries = []
        self._save()
