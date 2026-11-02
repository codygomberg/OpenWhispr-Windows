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
        self._state_lock = threading.Lock()   # stop() can be called by Escape and F15 at once
        self._stream: sd.InputStream | None = None
        self.is_recording = False
        self.level = 0.0   # 0–1 loudness of the latest audio chunk, drives the pill waveform

    def _callback(self, indata: np.ndarray, frames: int, time, status):
        with self._lock:
            self._frames.append(indata.copy())
        rms = float(np.sqrt(np.mean(np.square(indata))))
        # Square root lifts quiet speech so the waveform moves at normal speaking volume
        self.level = min(1.0, (rms ** 0.5) * 2.5)

    def start(self):
        with self._state_lock:
            if self.is_recording:
                return
            with self._lock:
                self._frames = []
            self.level = 0.0
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
        with self._state_lock:
            if not self.is_recording:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None
            self.is_recording = False
            self.level = 0.0
        with self._lock:
            if not self._frames:
                return np.zeros(0, dtype=np.float32)
            audio = np.concatenate(self._frames, axis=0)
        return audio.flatten()
