import threading

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16_000   # Hz — required by Whisper
CHANNELS    = 1        # mono
DTYPE       = "float32"


class AudioRecorder:
    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self.is_recording = False

    def _callback(self, indata: np.ndarray, frames: int, time, status):
        with self._lock:
            self._frames.append(indata.copy())

    def start(self):
        if self.is_recording:
            return
        with self._lock:
            self._frames = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()
        self.is_recording = True

    def stop(self) -> np.ndarray:
        """Stop recording and return all captured audio as a 1-D float32 array."""
        if not self.is_recording:
            return np.zeros(0, dtype=np.float32)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self.is_recording = False
        with self._lock:
            if not self._frames:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._frames, axis=0)
        return audio.flatten()
