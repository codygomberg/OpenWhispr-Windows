# Visual constants shared across all UI components.

# ── Status pill (always dark, in both light and dark mode) ─────────────────────

PILL_BG          = "rgba(28, 28, 30, 220)"   # dark translucent background
PILL_TEXT        = "#FFFFFF"
PILL_HEIGHT      = 44
PILL_MIN_WIDTH   = 180
PILL_TOP_OFFSET  = 32                         # pixels from top of screen

COLOR_RECORDING  = "#FF3B30"                  # red dot while recording
COLOR_WORKING    = "#FFD60A"                  # yellow dot while processing
COLOR_DONE       = "#30D158"                  # green dot when finished
COLOR_NEUTRAL    = "#8E8E93"                  # grey dot when idle
COLOR_SUMMARIZE  = "#BF5AF2"                  # purple — Ctrl+F15 summarize mode
COLOR_QUESTION   = "#0A84FF"                  # blue — Alt+F15 question mode
COLOR_LOCKED     = "#FF9F0A"                  # orange — hands-free (double-tap) recording

FONT_FAMILY      = "Segoe UI"
FONT_SIZE_PILL   = 13

DONE_DISPLAY_MS  = 1800                       # how long "Done" stays visible
DOUBLE_TAP_MS    = 300                        # max gap between taps to count as double-tap

# ── Main window palette — warm paper in light mode, warm graphite in dark ──────
# Same values as the macOS app's Theme.swift.

LIGHT = {
    "bg":          "#FAFAF8",
    "sidebar":     "#F5F4F0",
    "sidebar_sel": "#EDE9DE",
    "card":        "#FFFFFF",
    "field":       "#F2F1EC",   # inset: slightly darker than its surroundings
    "text":        "#1A1A1A",
    "text2":       "#75736E",
    "text3":       "#A3A19B",
    "divider":     "#E8E6E0",
}

DARK = {
    "bg":          "#1C1B19",
    "sidebar":     "#191816",
    "sidebar_sel": "#2E2C28",
    "card":        "#242320",
    "field":       "#151412",
    "text":        "#EDEBE6",
    "text2":       "#9C9991",
    "text3":       "#6E6B65",
    "divider":     "#302E2A",
}

ISLAND = "#000000"   # the model-status chip in the sidebar is always black

# Set to "light" or "dark" to override the system setting (used by tests)
FORCE_SCHEME = None


def _registry_dark() -> bool:
    """Fallback: read Windows' 'Choose your app mode' setting directly."""
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def is_dark() -> bool:
    if FORCE_SCHEME:
        return FORCE_SCHEME == "dark"
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication
    scheme = QGuiApplication.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return True
    if scheme == Qt.ColorScheme.Light:
        return False
    return _registry_dark()


def colors() -> dict:
    """The palette for the current light/dark mode."""
    return DARK if is_dark() else LIGHT
