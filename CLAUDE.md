# CLAUDE.md — OpenWhispr Windows

---

## MANDATORY PRE-TASK CHECKLIST — COMPLETE BEFORE ANY ACTION

Before writing code, running a command, or creating any file, answer every item:

- [ ] Have I confirmed all four components: deliverable, constraints, workflow, output format?
- [ ] Have I proposed a versioning convention and gotten approval?
- [ ] Have I explained what each planned command does in plain English?
- [ ] Have I flagged any missing or ambiguous requirements?
- [ ] Have I checked the current project state with `ls` before assuming anything?

**Do not proceed until all five items are resolved.**

---

## Project Context

- **Project:** OpenWhispr Windows — voice-to-text dictation app
- **Stack:** Python 3.13, PyQt6, faster-whisper, transformers (Qwen3-0.6B), pynput, sounddevice, pywin32, psutil, Pillow
- **Current state:** P1 is current. v1 preserved. P1 switches Whisper to large-v3-turbo and adds gc.collect() after model loads to reduce idle RAM.
- **Locked surfaces:** None currently locked.
- **Active work:** None — P1 shipped.

---

## What This App Does

Hold F15 → speak → release → transcribed and grammar-polished text auto-pastes into whatever you're typing in. Runs silently in the system tray.

---

## Project Structure

```
OpenWhispr-Windows/
├── CLAUDE.md               ← you are here
├── v1/                     ← original base (preserved, do not modify)
└── P1/                     ← current version (RAM fix + large-v3-turbo)
    ├── main.py             ← entry point, hotkeys, pipeline orchestration
    ├── recorder.py         ← audio capture (sounddevice, 16kHz mono)
    ├── transcriber.py      ← Whisper transcription (faster-whisper, large-v3-turbo, CUDA)
    ├── text_processor.py   ← LLM polishing (Qwen3-0.6B, transformers, CUDA)
    ├── tone_manager.py     ← per-app tone + all settings (singleton)
    ├── history_store.py    ← transcription history (JSON)
    ├── dictionary_store.py ← custom corrections, OFF by default (JSON)
    ├── pill_window.py      ← floating status HUD (PyQt6)
    ├── settings_window.py  ← settings UI (PyQt6)
    ├── history_window.py   ← history browser (PyQt6)
    ├── theme.py            ← colors, fonts, constants
    ├── create_icon.py      ← run once to regenerate icon.ico
    ├── icon.ico            ← app icon (orbital design, 4 sizes embedded)
    ├── requirements.txt    ← pip dependencies
    ├── install.bat         ← one-time setup (creates venv, installs packages)
    └── run.bat             ← launches app with console (for debugging)
```

---

## Versioning Convention

- **v1** — current base
- **P1, P2…** — bug patches
- **FP1, FP2…** — feature additions
- Never overwrite a version folder. Copy it forward.

---

## Hotkeys

| Key | Action |
|---|---|
| Hold F15 | Record and transcribe |
| Double-tap F15 | Toggle hands-free recording |
| Ctrl + F15 | Record and summarize |
| Alt + F15 | Record and ask (Q&A mode) |
| Ctrl + Alt + V | Re-paste last transcription |

---

## Settings (stored in %APPDATA%\OpenWhispr\settings.json)

| Setting | Default | Notes |
|---|---|---|
| base_tone | neutral | neutral / professional / casual / raw |
| polish_enabled | true | false = paste raw Whisper output |
| always_english | true | false = auto-detect language |
| style_description | "" | free text hint added to LLM prompt |
| dictionary_enabled | false | custom word corrections |
| app_tones | {} | per-app tone overrides |
| whisper_model | large-v3-turbo | switched from large-v3 in P1 |

---

## Critical Technical Notes

- **PyTorch must be cu128 or newer.** RTX 5070 Ti is Blackwell (sm_120) — cu124 crashes with "no kernel image available."
- **No CUDA toolkit installed** (no nvcc). Use prebuilt wheels only.
- **VAD filter removed** from faster-whisper. silero-vad hangs on second use. Whisper handles silence natively.
- **`device_map="cuda"` hangs** with this GPU/PyTorch combo. Use `low_cpu_mem_usage=True` + `.to("cuda")` instead.
- **Windows key-repeat**: pynput fires repeated key-down events while a key is held. The `_f15_held` flag in `main.py` prevents this from triggering the double-tap logic.
- **Models are always loaded in VRAM** for instant response. They load once at startup.
- **Memory profile (P1):** Idle ~2.5 GB RAM, stabilizes ~4–5 GB after first use. 64 GB system RAM — no workflow impact.
- **gc.collect() after model loads** in both `transcriber.py` and `text_processor.py` — forces Python to release CPU-side model weight copies after transferring to CUDA. Do not remove.
- **large-v3-turbo chosen over large-v3** — ~¼ the VRAM footprint, near-identical accuracy for English. large-v3 cache deleted from `~/.cache/huggingface/hub`.

---

## Launcher

- **Normal use:** Taskbar pin → `pythonw.exe main.py` (no console window)
- **Debugging:** Double-click `run.bat` (shows console output)
- **Regenerate icon:** Run `create_icon.py` with the venv Python, then delete and recreate the shortcut

---

## Data Files (in %APPDATA%\OpenWhispr\)

| File | Contents |
|---|---|
| settings.json | All app settings |
| history.json | Transcription history (last 500) |
| dictionary.json | Custom word corrections |
