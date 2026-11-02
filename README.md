# OpenWhispr Windows

A Windows port of [OpenWhispr](https://github.com/MrPrinceRawat/OpenWhispr) by [@MrPrinceRawat](https://github.com/MrPrinceRawat) — originally built for macOS using Swift and WhisperKit. This version rebuilds the app in Python so it runs natively on Windows. Later versions also bring over the redesign and features from [codygomberg/OpenWhispr](https://github.com/codygomberg/OpenWhispr), the macOS fork.

A Windows voice-to-text dictation app that runs quietly in the system tray. Hold a key, speak, release — your words are transcribed and pasted into whatever you're typing in, instantly.

Powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for transcription and [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) for optional grammar polishing.

---

## Features

**Dictation**
- **Hold-to-record** — hold F15 to record, release to transcribe and paste
- **Hands-free mode** — double-tap F15 to record without holding; hover the status pill for ■ stop and ✕ cancel
- **Cancel anytime** — press Escape to drop a recording or a dictation that's still processing
- **Grammar polishing** — an on-device LLM cleans up filler words, fixes punctuation, and formats numbers
- **Summarize mode** — Ctrl+F15 to record and get a bullet-point summary
- **Q&A mode** — Alt+F15 to ask a question and get a short answer
- **Junk filter** — drops Whisper's noise tags (`[BLANK_AUDIO]`), repetition loops, and the "Thank you." it invents on silence
- **Status pill** — a small HUD at the top of the screen, colored by mode, with a live waveform while you speak
- **No internet required** — all models run locally on your GPU

**Main window** (click the tray icon)
- **Home** — words dictated, time saved compared with typing, speaking speed, streaks, a 20-week activity grid, your top apps, and recent dictations
- **History** — your last 500 dictations grouped by day; click to expand, copy, delete, or search
- **Style** — pick a default tone (Casual, Neutral, Professional, Raw) from example cards, add a personal style hint, and set a different tone per app (with app icons)
- **Dictionary** — teach it names, brands, and jargon it keeps getting wrong
- **Settings** — language, polishing, model status with the last dictation's timing, and a shortcut reference
- **Light and dark mode** — follows your Windows setting and switches live

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
2. Open the `FP3` folder
3. Double-click `install.bat`

The script will:
- Create a Python virtual environment
- Install PyTorch with CUDA 12.8 support
- Install all remaining dependencies

On first launch, faster-whisper and Qwen3 will download their models (~2 GB total, one time only).

---

## Running the App

Double-click `run.bat` inside the `FP3` folder. The status pill at the top of the screen shows the models loading; after that the app sits in your system tray. (The console window that opens alongside shows any errors.) Click the tray icon to open the main window; right-click it for the menu.

For a cleaner launch with no console window, create a shortcut pointing to:

```
<path-to-FP3>\.venv\Scripts\pythonw.exe main.py
```

Set the shortcut's **Start in** folder to the `FP3` folder.

---

## Hotkeys

| Key | Action |
|---|---|
| Hold F15 | Record and transcribe |
| Double-tap F15 | Toggle hands-free recording |
| Ctrl + F15 | Record and summarize (bullet points) |
| Alt + F15 | Record and ask (Q&A mode) |
| Escape | Cancel the current recording or dictation |
| Ctrl + Alt + V | Re-paste last transcription |

> F15 is a key found on extended keyboards. It can also be mapped from another key using software like AutoHotkey or supported gaming keyboards.

---

## Settings

Click the tray icon to open the main window. Tone and style live on the **Style** page, word corrections on the **Dictionary** page, and everything else on **Settings**.

| Setting | Default | Description |
|---|---|---|
| Polish with Qwen3 | On | Clean up filler words, punctuation, and formatting |
| Always English | On | On = assume English speech (most accurate). Off = detect the spoken language and translate it into English |
| Default tone | Neutral | Casual / Neutral / Professional / Raw (Raw skips polishing) |
| Your style | _(empty)_ | Free-text hint added to every polish |
| Per-app tones | _(none)_ | Different tone for specific apps — pick from open apps or choose any `.exe` |
| Dictionary corrections | Off | Replace words Whisper gets wrong with your spelling |

Data is stored in `%APPDATA%\OpenWhispr\`:

| File | Contents |
|---|---|
| `settings.json` | All settings |
| `history.json` | Last 500 dictations |
| `dictionary.json` | Word corrections |
| `stats.json` | Daily totals for the Home page — counts only, no text, so stats survive clearing history |

---

## Versions

Each version lives in its own folder; older versions are kept unchanged.

| Version | Description |
|---|---|
| `v1` | Initial build |
| `P1` | Switched Whisper model to `large-v3-turbo`, added memory cleanup after model load — reduces idle RAM from ~7.7 GB to ~2.5 GB |
| `P2` | Lower GPU memory: Whisper in `int8_float16`, GPU memory freed after each dictation, shorter polish limit |
| `FP1` | Escape to cancel, junk/silence filter, mode-colored status pill with waveform and hands-free stop/cancel |
| `FP2` | One main window with sidebar (History, Style, Dictionary, Settings), light/dark mode, new tray menu |
| `FP3` | Home page with dictation stats |

`FP3` is the current recommended version.

---

## Technical Notes

- Models load once at startup and stay in VRAM for instant response
- Idle RAM usage: ~2.5 GB, stabilizes around 4–5 GB after first use
- VAD (voice activity detection) is disabled — the silero VAD filter caused hangs on repeated use. Silence is handled by the junk filter instead: Whisper's well-known silence phrases are discarded only when the recording was quiet, so a spoken "Thank you" still comes through
- "Time saved" and "speaking speed" on the Home page count dictations made with FP3 or later — older history didn't record how long you spoke
- Everything — audio, transcripts, history, and stats — stays on your PC
