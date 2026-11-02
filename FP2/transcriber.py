import gc
import re
from collections import Counter

import numpy as np
import torch
from faster_whisper import WhisperModel


# Tags Whisper sometimes writes instead of words when it hears silence or noise
NOISE_TOKENS = (
    "[BLANK_AUDIO]", "[NO_SPEECH]", "(blank_audio)", "(no speech)",
    "[MUSIC PLAYING]", "[MUSIC]", "(music playing)", "(music)",
    "[SOUND]", "[NOISE]", "[SILENCE]", "[APPLAUSE]", "[LAUGHTER]",
    "(sound)", "(noise)", "(silence)", "(applause)", "(laughter)",
    "[INAUDIBLE]", "(inaudible)",
)

_BRACKETED = re.compile(r"\[.*?\]|\(.*?\)")

# Phrases Whisper invents on silence or room noise. Only discarded when the
# recording was also quiet, so a real spoken "Thank you" still comes through.
SILENCE_PHRASES = {
    "thank you", "thank you very much", "thanks for watching",
    "thank you for watching", "bye", "you",
}
QUIET_PEAK = 0.02   # loudest 30 ms of real speech ≈ 0.2; a quiet room ≈ 0.003


def _loudest_frame(audio: np.ndarray) -> float:
    """RMS loudness of the loudest 30 ms slice of the recording."""
    n = 480   # 30 ms at 16 kHz
    if len(audio) < n:
        return float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
    frames = audio[: len(audio) // n * n].reshape(-1, n)
    return float(np.sqrt(np.mean(np.square(frames), axis=1)).max())


def _is_silence_hallucination(text: str, audio: np.ndarray) -> bool:
    phrase = re.sub(r"[^\w\s]", "", text).strip().lower()
    return phrase in SILENCE_PHRASES and _loudest_frame(audio) < QUIET_PEAK


def _is_repetition_hallucination(text: str) -> bool:
    """True if the text is one word or a short phrase looping (a known Whisper failure)."""
    words = text.lower().split()
    if len(words) < 4:
        return False

    # Any single word making up more than 60% of all words
    if max(Counter(words).values()) / len(words) > 0.6:
        return True

    # The opening 1–3 word phrase repeating back-to-back
    for length in (1, 2, 3):
        if len(words) < length * 3:
            continue
        pattern = words[:length]
        matches = sum(
            1 for i in range(0, len(words) - length + 1, length)
            if words[i:i + length] == pattern
        )
        if matches >= 3 and (matches * length) / len(words) > 0.5:
            return True

    return False


def clean_transcript(text: str) -> str:
    """
    Remove noise tags and discard looping output.
    Returns "" when nothing real was said.
    """
    cleaned = text.strip()
    for token in NOISE_TOKENS:
        cleaned = re.sub(re.escape(token), "", cleaned, flags=re.IGNORECASE)
    cleaned = _BRACKETED.sub("", cleaned)
    cleaned = " ".join(cleaned.split())

    if _is_repetition_hallucination(cleaned):
        print("[Transcriber] Detected repetition hallucination, discarding")
        return ""
    return cleaned


class WhisperTranscriber:
    def __init__(self, model_size: str = "large-v3", status_callback=None):
        """
        Loads the Whisper model onto the GPU.
        status_callback(msg): optional function called with progress messages.
        First load downloads the model (~3 GB) — subsequent launches are instant.
        """
        if status_callback:
            status_callback(f"Loading Whisper {model_size}…")

        self._model = WhisperModel(
            model_size,
            device="cuda",
            compute_type="int8_float16",
        )

        gc.collect()
        torch.cuda.empty_cache()

        if status_callback:
            status_callback("Whisper ready.")

    def transcribe(self, audio: np.ndarray, always_english: bool = True) -> str:
        """
        Transcribe a 1-D float32 numpy array recorded at 16 kHz.
        always_english=True: assumes English input (best accuracy for English speakers).
        always_english=False: auto-detects language and translates output to English.
        Returns the cleaned transcript, or "" if nothing real was said.
        """
        if audio is None or len(audio) == 0:
            return ""

        if always_english:
            segments, _ = self._model.transcribe(audio, language="en")
        else:
            segments, _ = self._model.transcribe(audio, task="translate")

        result = " ".join(segment.text.strip() for segment in segments).strip()
        torch.cuda.empty_cache()
        result = clean_transcript(result)
        if _is_silence_hallucination(result, audio):
            print("[Transcriber] Silence hallucination, discarding")
            return ""
        return result
