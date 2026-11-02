"""
Lifetime usage totals per day, for the Home page.
Counts only — never transcript text — so stats survive deleting or clearing history.
"""
import json
import os
from datetime import date, datetime, timedelta


DATA_DIR = os.path.join(os.environ["APPDATA"], "OpenWhispr")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

TYPING_WPM = 45   # typing speed used for "time saved"


def _new_day() -> dict:
    return {
        "words": 0,          # all words dictated
        "seconds": 0.0,      # recording time (only known for dictations made since FP3)
        "timed_words": 0,    # words from dictations whose recording time is known
        "dictations": 0,
        "apps": {},          # exe name → words
    }


class StatsStore:
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
        self._days: dict[str, dict] = {}
        self._exists = self._load()
        self._loaded = True

    # ── Storage ───────────────────────────────────────────────────────────────

    def _load(self) -> bool:
        if not os.path.exists(STATS_FILE):
            return False
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                self._days = json.load(f).get("days", {})
            return True
        except (json.JSONDecodeError, OSError):
            return False

    def _save(self):
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "days": self._days}, f, indent=1)

    def backfill_if_new(self, history_entries: list[dict]):
        """First run with stats: count the history we already have."""
        if self._exists:
            return
        for entry in reversed(history_entries):
            self._add(entry)
        self._save()
        self._exists = True

    # ── Recording ─────────────────────────────────────────────────────────────

    def _add(self, entry: dict):
        key = entry["timestamp"][:10]   # "YYYY-MM-DD", local time
        day = self._days.setdefault(key, _new_day())
        words = len(entry.get("text", "").split())
        day["words"] += words
        day["dictations"] += 1
        duration = entry.get("duration") or 0
        if duration:
            day["seconds"] = round(day["seconds"] + duration, 1)
            day["timed_words"] += words
        app = entry.get("app", "")
        if app:
            day["apps"][app] = day["apps"].get(app, 0) + words

    def record(self, entry: dict):
        self._add(entry)
        self._save()

    # ── Reading ───────────────────────────────────────────────────────────────

    def words_on(self, d: date) -> int:
        return self._days.get(d.isoformat(), {}).get("words", 0)

    def summary(self, today: date | None = None) -> dict:
        today = today or date.today()
        days = self._days

        total_words = sum(d["words"] for d in days.values())
        timed_words = sum(d["timed_words"] for d in days.values())
        seconds = sum(d["seconds"] for d in days.values())

        active = {datetime.strptime(k, "%Y-%m-%d").date() for k, d in days.items() if d["words"] > 0}

        # Current streak counts from yesterday if nothing yet today, so it doesn't read 0 every morning
        cursor = today if today in active else today - timedelta(days=1)
        current = 0
        while cursor in active:
            current += 1
            cursor -= timedelta(days=1)

        longest = run = 0
        previous = None
        for d in sorted(active):
            run = run + 1 if previous and (d - previous).days == 1 else 1
            longest = max(longest, run)
            previous = d

        # Weeks start on Sunday, matching the activity grid
        week_start = today - timedelta(days=(today.weekday() + 1) % 7)
        week_words = sum(
            d["words"] for k, d in days.items()
            if datetime.strptime(k, "%Y-%m-%d").date() >= week_start
        )

        apps: dict[str, int] = {}
        for d in days.values():
            for app, words in d["apps"].items():
                apps[app] = apps.get(app, 0) + words
        top_apps = sorted(apps.items(), key=lambda item: item[1], reverse=True)[:5]

        # Speaking speed = words ÷ recording minutes (includes pauses, so it runs a bit low)
        wpm = round(timed_words / (seconds / 60)) if seconds >= 10 else None
        # Typing the same words at 45 wpm, minus the time spent speaking them
        minutes_saved = max(0.0, timed_words / TYPING_WPM - seconds / 60)

        return {
            "total_words": total_words,
            "timed_words": timed_words,
            "seconds": seconds,
            "current_streak": current,
            "longest_streak": longest,
            "week_words": week_words,
            "top_apps": top_apps,
            "wpm": wpm,
            "minutes_saved": minutes_saved,
        }
