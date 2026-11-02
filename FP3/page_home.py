from datetime import date, datetime, timedelta

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget

import app_info
from history_store import HistoryStore
from page_history import clock, day_heading
from stats_store import StatsStore
from tone_manager import ToneManager
from ui_common import KeyCap, Page, Section, app_badge, card, clear_layout, divider, label


def duration_label(minutes: float) -> str:
    total = int(round(minutes))
    if total < 1:
        return "under a minute"
    hours, mins = divmod(total, 60)
    if hours == 0:
        return f"{mins} minute{'s' if mins != 1 else ''}"
    if mins == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{hours} hr {mins} min"


def plural(n: int, word: str) -> str:
    return f"{word}{'s' if n != 1 else ''}"


# ── Stat tile ──────────────────────────────────────────────────────────────────

class StatTile(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("Card")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)
        heading = label(title.upper(), "SectionTitle")
        v.addWidget(heading)
        row = QHBoxLayout()
        row.setSpacing(5)
        self.value = label("", "TileValue")
        self.unit = label("", "Secondary")
        row.addWidget(self.value)
        row.addWidget(self.unit, alignment=Qt.AlignmentFlag.AlignBottom)
        row.addStretch()
        v.addLayout(row)
        self.detail = label("", "Tertiary")
        v.addWidget(self.detail)

    def set(self, value: str, unit: str = "", detail: str = ""):
        self.value.setText(value)
        self.unit.setText(unit)
        self.detail.setText(detail)


# ── Activity grid ──────────────────────────────────────────────────────────────

class ActivityGrid(QWidget):
    """Last 20 weeks, one square per day. Columns are weeks (Sun–Sat), darker = more words."""

    WEEKS = 20
    CELL = 13
    GAP = 4
    TOP = 26      # room for the readout line
    LEFT = 30     # room for day labels
    OPACITY = (0.18, 0.38, 0.62, 0.88)    # ink strength for bands 1–4

    def __init__(self, stats: StatsStore):
        super().__init__()
        self._stats = stats
        self._hover: date | None = None
        self.setMouseTracking(True)
        step = self.CELL + self.GAP
        self.setFixedHeight(self.TOP + 7 * step + 28)
        self.setMinimumWidth(self.LEFT + self.WEEKS * step)

    def _first_day(self) -> date:
        today = date.today()
        this_sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        return this_sunday - timedelta(weeks=self.WEEKS - 1)

    def _cell_rect(self, week: int, weekday: int) -> QRectF:
        step = self.CELL + self.GAP
        return QRectF(self.LEFT + week * step, self.TOP + weekday * step, self.CELL, self.CELL)

    @staticmethod
    def _band(words: int) -> int:
        """0 words → 0, 1–249 → 1, 250–499 → 2, 500–749 → 3, 750+ → 4."""
        if words == 0:
            return 0
        if words < 250:
            return 1
        if words < 500:
            return 2
        if words < 750:
            return 3
        return 4

    def _fill(self, words: int, c: dict) -> QColor:
        band = self._band(words)
        if band == 0:
            return QColor(c["field"])
        color = QColor(c["text"])
        color.setAlphaF(self.OPACITY[band - 1])
        return color

    def paintEvent(self, event):
        import theme
        c = theme.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        small = QFont(theme.FONT_FAMILY)
        small.setPixelSize(11)
        p.setFont(small)

        # Readout: hovered day, or the range
        p.setPen(QColor(c["text2"]))
        if self._hover:
            words = self._stats.words_on(self._hover)
            text = f"{self._hover:%a, %b} {self._hover.day} · {words:,} {plural(words, 'word')}"
        else:
            text = f"Last {self.WEEKS} weeks"
        p.drawText(QRectF(self.LEFT, 0, 400, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

        # Day labels
        p.setPen(QColor(c["text3"]))
        for weekday, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
            r = self._cell_rect(0, weekday)
            p.drawText(QRectF(0, r.y() - 2, self.LEFT - 6, self.CELL + 4),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, name)

        # Squares
        today = date.today()
        first = self._first_day()
        p.setPen(Qt.PenStyle.NoPen)
        for week in range(self.WEEKS):
            for weekday in range(7):
                d = first + timedelta(days=week * 7 + weekday)
                if d > today:
                    continue
                p.setBrush(self._fill(self._stats.words_on(d), c))
                p.drawRoundedRect(self._cell_rect(week, weekday), 3, 3)
                if d == self._hover:
                    p.setPen(QColor(c["text2"]))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRoundedRect(self._cell_rect(week, weekday).adjusted(-1, -1, 1, 1), 3, 3)
                    p.setPen(Qt.PenStyle.NoPen)

        # Legend
        y = self._cell_rect(0, 6).bottom() + 12
        right = self._cell_rect(self.WEEKS - 1, 0).right()
        x = right - 5 * (self.CELL + 3)
        p.setPen(QColor(c["text3"]))
        p.drawText(QRectF(x - 40, y - 2, 34, self.CELL + 4),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "Less")
        p.setPen(Qt.PenStyle.NoPen)
        for i, words in enumerate((0, 1, 250, 500, 750)):
            p.setBrush(self._fill(words, c))
            p.drawRoundedRect(QRectF(x + i * (self.CELL + 3), y, self.CELL, self.CELL), 3, 3)
        p.setPen(QColor(c["text3"]))
        p.drawText(QRectF(right + 6, y - 2, 40, self.CELL + 4),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "More")

    def mouseMoveEvent(self, event):
        pos = event.position()
        first = self._first_day()
        hover = None
        for week in range(self.WEEKS):
            for weekday in range(7):
                if self._cell_rect(week, weekday).contains(pos):
                    d = first + timedelta(days=week * 7 + weekday)
                    hover = d if d <= date.today() else None
        if hover != self._hover:
            self._hover = hover
            self.update()

    def leaveEvent(self, event):
        self._hover = None
        self.update()


# ── Top-app bar ────────────────────────────────────────────────────────────────

class Bar(QWidget):
    def __init__(self, fraction: float):
        super().__init__()
        self._fraction = max(0.0, min(1.0, fraction))
        self.setFixedHeight(6)
        self.setMinimumWidth(80)

    def paintEvent(self, event):
        import theme
        c = theme.colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["field"]))
        p.drawRoundedRect(QRectF(self.rect()), 3, 3)
        p.setBrush(QColor(c["text2"]))
        p.drawRoundedRect(QRectF(0, 0, max(6.0, self.width() * self._fraction), self.height()), 3, 3)


# ── Page ───────────────────────────────────────────────────────────────────────

class HomePage(Page):
    def __init__(self, ctx):
        super().__init__()
        self._stats = StatsStore()
        self._history = HistoryStore()
        self._tm = ToneManager()

        # Hint
        hint = QHBoxLayout()
        hint.setSpacing(6)
        hint.addWidget(label("Hold", "Secondary"))
        hint.addWidget(KeyCap("F15"))
        hint.addWidget(label("in any app to dictate.", "Secondary"))
        hint.addStretch()
        self.column.addLayout(hint)

        # Hero
        hero = QVBoxLayout()
        hero.setSpacing(2)
        heading = label("WORDS DICTATED", "SectionTitle")
        font = heading.font()
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        heading.setFont(font)
        hero.addWidget(heading)
        self._total = label("", "Big")
        hero.addWidget(self._total)
        self._saved = label("", "Secondary")
        hero.addWidget(self._saved)
        self._saved_note = label("", "Tertiary", wrap=True)
        hero.addWidget(self._saved_note)
        self.column.addLayout(hero)

        # Tiles
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self._speed = StatTile("Speaking speed")
        self._streak = StatTile("Streak")
        self._week = StatTile("This week")
        for tile in (self._speed, self._streak, self._week):
            tiles.addWidget(tile, 1)
        self.column.addLayout(tiles)

        # Activity
        activity = Section("Activity")
        self._grid = ActivityGrid(self._stats)
        activity.body.addWidget(self._grid)
        self.column.addWidget(activity)

        # Top apps
        apps = Section("Where you dictate")
        self._apps = apps.body
        self._apps.setSpacing(10)
        self.column.addWidget(apps)

        # Recent
        recent = Section("Recent")
        self._recent = recent.body
        self._recent.setSpacing(0)
        self.column.addWidget(recent)

        self.column.addStretch()
        self.refresh()

    def refresh(self):
        s = self._stats.summary()

        self._total.setText(f"{s['total_words']:,}")
        if s["total_words"] == 0:
            self._saved.setText("Your first dictation starts the count.")
        else:
            self._saved.setText(
                f"About {duration_label(s['minutes_saved'])} saved compared with typing at 45 wpm")
        untimed = s["total_words"] - s["timed_words"]
        self._saved_note.setText(
            "Time saved and speaking speed count dictations made since this update — "
            "older history didn't record how long you spoke." if untimed > 0 else "")
        self._saved_note.setVisible(untimed > 0)

        if s["wpm"] is None:
            self._speed.set("—", "", "Includes pauses")
        else:
            self._speed.set(str(s["wpm"]), "wpm", "Includes pauses")
        cur, best = s["current_streak"], s["longest_streak"]
        self._streak.set(str(cur), plural(cur, "day"), f"Longest: {best} {plural(best, 'day')}")
        self._week.set(f"{s['week_words']:,}", "words")

        self._grid.update()
        self._fill_apps(s["top_apps"])
        self._fill_recent()

    def _fill_apps(self, top_apps: list[tuple[str, int]]):
        clear_layout(self._apps)
        if not top_apps:
            self._apps.addWidget(label("Your most-used apps will show up here.", "Tertiary"))
            return
        most = top_apps[0][1] or 1
        for exe, words in top_apps:
            path = self._tm.app_path(exe)
            name = app_info.friendly_name(exe, path)
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(10)
            h.addWidget(app_badge(app_info.app_icon(path), name))
            title = label(name)
            title.setFixedWidth(170)
            h.addWidget(title)
            h.addWidget(Bar(words / most), 1)
            count = label(f"{words:,}", "Secondary")
            count.setFixedWidth(64)
            count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            h.addWidget(count)
            self._apps.addWidget(row)

    def _fill_recent(self):
        clear_layout(self._recent)
        entries = self._history.get_all()[:3]
        if not entries:
            self._recent.addWidget(label("Nothing yet — your latest dictations will show up here.", "Tertiary"))
            return
        for i, entry in enumerate(entries):
            if i:
                self._recent.addWidget(divider())
            ts = datetime.fromisoformat(entry["timestamp"])
            row = QWidget()
            v = QVBoxLayout(row)
            v.setContentsMargins(0, 8, 0, 8)
            v.setSpacing(3)
            text = " ".join(entry["text"].split())
            v.addWidget(label(text if len(text) <= 140 else text[:140].rstrip() + "…", wrap=True))
            meta = f"{day_heading(ts.date())}, {clock(ts)}"
            exe = entry.get("app", "")
            if exe:
                meta += " · " + app_info.friendly_name(exe, self._tm.app_path(exe))
            v.addWidget(label(meta, "Tertiary"))
            self._recent.addWidget(row)
