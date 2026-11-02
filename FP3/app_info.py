"""Friendly names, icons, and the list of open apps — for per-app tones and stats."""
import os

import psutil
import win32api
import win32gui
import win32process
from PyQt6.QtCore import QFileInfo
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileIconProvider


# Background Windows processes that own windows but aren't apps you type in
_SKIP = {
    "applicationframehost.exe", "textinputhost.exe", "shellexperiencehost.exe",
    "searchhost.exe", "startmenuexperiencehost.exe", "systemsettings.exe",
    "python.exe", "pythonw.exe", "lockapp.exe", "widgets.exe",
}

_name_cache: dict[str, str] = {}
_icon_provider = None


def running_apps() -> list[tuple[str, str]]:
    """[(exe_name, exe_path)] for every app with a visible window, sorted by friendly name."""
    found: dict[str, str] = {}

    def visit(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
            return True
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            name = proc.name().lower()
            if name not in _SKIP and name not in found:
                found[name] = proc.exe()
        except (psutil.Error, OSError):
            pass
        return True

    win32gui.EnumWindows(visit, None)
    return sorted(found.items(), key=lambda item: friendly_name(item[0], item[1]).lower())


def friendly_name(exe_name: str, path: str = "") -> str:
    """'chrome.exe' → 'Google Chrome' (from the program's own description when available)."""
    if exe_name in _name_cache:
        return _name_cache[exe_name]
    name = ""
    if path and os.path.exists(path):
        try:
            lang, codepage = win32api.GetFileVersionInfo(path, "\\VarFileInfo\\Translation")[0]
            key = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\FileDescription"
            name = (win32api.GetFileVersionInfo(path, key) or "").strip()
        except Exception:
            name = ""
    if not name:
        stem = exe_name[:-4] if exe_name.endswith(".exe") else exe_name
        name = stem.replace("_", " ").replace("-", " ").title()
    if path:   # only cache real lookups, so a later call with a path can improve it
        _name_cache[exe_name] = name
    return name


def app_icon(path: str) -> QIcon:
    """The program's own icon, or an empty icon if the path is unknown."""
    global _icon_provider
    if not path or not os.path.exists(path):
        return QIcon()
    if _icon_provider is None:
        _icon_provider = QFileIconProvider()
    return _icon_provider.icon(QFileInfo(path))
