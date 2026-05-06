# OpenWhispr Windows

A Windows voice-to-text dictation app that runs silently in the system tray. Hold a key, speak, release — your words are transcribed and pasted into whatever you're typing in, instantly.

Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for transcription and [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) for optional grammar polishing.

---

## Features

- **Hold-to-record** — hold F15 to record, release to transcribe and paste
- **Hands-free mode** — double-tap F15 to toggle continuous recording
- **Grammar polishing** — an on-device LLM cleans up filler words, fixes punctuation, and formats numbers
- **Tone control** — choose Neutral, Professional, Casual, or Raw (no polishing) globally or per app
- **Summarize mode** — Ctrl+F15 to record and get a bullet-point summary
- **Q&A mode** — Alt+F15 to ask a question and get a short answer
- **Per-app tone overrides** — automatically switch tone based on which app is focused
- **Custom style hints** — add a free-text instruction to every LLM polish (e.g. "Keep sentences short")
- **History browser** — view your last 500 transcriptions
- **No internet required** — all models run locally on your GPU

---

## Requirements

- Windows 10 or 11
- Python 3.10 or newer ([python.org](https://www.python.org/downloads/))
- An NVIDIA GPU with at least 4 GB of VRAM
- CUDA-capable drivers (no CUDA toolkit install needed — just up-to-date GPU drivers)

> **RTX 5000 series (Blackwell) users:** PyTorch cu128 or newer is required. The `install.bat` script handles this automatically.

---

## Installation

1. Download or clone this repo
2. Open the `P1` folder
3. Double-click `install.bat`

The script will:
- Create a Python virtual environment
- Install PyTorch with CUDA 12.8 support
- Install all remaining dependencies

On first launch, faster-whisper and Qwen3 will download their models (~2 GB total, one time only).

---

## Running the App

Double-click `run.bat` inside the `P1` folder. The app will appear in your system tray — no window opens.

For a cleaner launch with no console window, create a shortcut pointing to:

```
<path-to-P1>\.venv\Scripts\pythonw.exe "<path-to-P1>\main.py"
```

Set the working directory to the `P1` folder.

---

## Hotkeys

| Key | Action |
|---|---|
| Hold F15 | Record and transcribe |
| Double-tap F15 | Toggle hands-free recording |
| Ctrl + F15 | Record and summarize (bullet points) |
| Alt + F15 | Record and ask (Q&A mode) |
| Ctrl + Alt + V | Re-paste last transcription |

> F15 is a key found on extended keyboards. It can also be mapped from another key using software like AutoHotkey or supported gaming keyboards.

---

## Settings

Right-click the tray icon and choose **Settings**.

| Setting | Default | Description |
|---|---|---|
| LLM polishing | On | Clean up filler words, punctuation, and formatting |
| Always output in English | On | Off = auto-detect language and output in that language |
| Custom style | _(empty)_ | Free-text hint added to every LLM polish |
| Base tone | Neutral | Neutral / Professional / Casual / Raw |
| Per-app tone overrides | _(none)_ | Different tone for specific apps (e.g. chrome.exe) |
| Custom dictionary | Off | Apply word corrections after transcription |

Settings are saved to `%APPDATA%\OpenWhispr\settings.json`.

---

## Versions

| Version | Description |
|---|---|
| `v1` | Initial build |
| `P1` | Switched Whisper model to `large-v3-turbo`, added memory cleanup after model load — reduces idle RAM from ~7.7 GB to ~2.5 GB |

`P1` is the current recommended version.

---

## Technical Notes

- Models load once at startup and stay in VRAM for instant response
- Idle VRAM usage: ~1 GB (large-v3-turbo ~800 MB + Qwen3-0.6B ~1.2 GB)
- Idle RAM usage: ~2.5 GB, stabilizes around 4–5 GB after first use
- VAD (voice activity detection) is disabled — Whisper handles silence natively and the VAD filter caused hangs on repeated use
- Transcription history is stored locally at `%APPDATA%\OpenWhispr\history.json`
