import numpy as np
from faster_whisper import WhisperModel


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
            compute_type="float16",
        )

        if status_callback:
            status_callback("Whisper ready.")

    def transcribe(self, audio: np.ndarray, always_english: bool = True) -> str:
        """
        Transcribe a 1-D float32 numpy array recorded at 16 kHz.
        always_english=True: assumes English input (best accuracy for English speakers).
        always_english=False: auto-detects language and translates output to English.
        Returns the transcribed text as a single string.
        """
        if audio is None or len(audio) == 0:
            return ""

        if always_english:
            segments, _ = self._model.transcribe(audio, language="en")
        else:
            segments, _ = self._model.transcribe(audio, task="translate")

        return " ".join(segment.text.strip() for segment in segments).strip()
