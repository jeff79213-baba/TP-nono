import threading
import time
import logging
import numpy as np
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("voice-typer.audio")


class RecorderState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    STOPPED = "stopped"


@dataclass
class AudioRecorder:
    sample_rate: int = 16000
    channels: int = 1
    silence_threshold: float = 0.02
    silence_timeout: float = 2.0

    _state: RecorderState = RecorderState.IDLE
    _chunks: list = field(default_factory=list)
    _stream: sd.InputStream = None
    _thread: threading.Thread = None
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _stop_event: threading.Event = field(default_factory=threading.Event)
    _last_voice_time: float = 0.0
    _volume_callback = None
    _auto_stop_callback = None
    _peak_volume: float = 0.0

    def set_volume_callback(self, callback):
        self._volume_callback = callback

    def set_auto_stop_callback(self, callback):
        self._auto_stop_callback = callback

    def start_recording(self) -> bool:
        with self._lock:
            if self._state == RecorderState.RECORDING:
                return False
            self._state = RecorderState.RECORDING
            self._chunks = []
            self._last_voice_time = time.time()
            self._stop_event.clear()

        logger.info(f"開始錄音 (threshold={self.silence_threshold}, timeout={self.silence_timeout}s)")
        devices = sd.query_devices()
        default_input = sd.default.device[0]
        logger.info(f"預設輸入裝置: {devices[default_input]['name'] if default_input else '系統預設'}")
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        return True

    def stop_recording(self) -> bool:
        with self._lock:
            if self._state != RecorderState.RECORDING:
                return False
            self._state = RecorderState.STOPPED
            self._stop_event.set()
        return True

    def _record_loop(self):
        def callback(indata, frames, time_info, status):
            if self._state != RecorderState.RECORDING:
                raise sd.CallbackStop

            volume = float(np.sqrt(np.mean(indata ** 2)))
            if volume > self._peak_volume:
                self._peak_volume = volume
            if self._volume_callback:
                self._volume_callback(volume)

            with self._lock:
                self._chunks.append(indata.copy())
                if volume > self.silence_threshold:
                    self._last_voice_time = time.time()
                elif len(self._chunks) % 50 == 0:
                    logger.debug(f"音量偏低: {volume:.4f} (threshold: {self.silence_threshold})")

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                callback=callback,
                blocksize=1024,
            ):
                while self._state == RecorderState.RECORDING:
                    if self._stop_event.wait(0.1):
                        break
                    elapsed = time.time() - self._last_voice_time
                    if elapsed > self.silence_timeout and len(self._chunks) > 0:
                        logger.info(f"靜音超時 ({self.silence_timeout}s)，自動停止錄音")
                        self.stop_recording()
                        if self._auto_stop_callback:
                            self._auto_stop_callback()
                        break
        except Exception as e:
            logger.error(f"錄音錯誤: {e}", exc_info=True)
            devices = sd.query_devices()
            logger.error(f"可用輸入裝置: {[d['name'] for d in devices if d['max_input_channels'] > 0]}")
            with self._lock:
                self._chunks = []
                self._state = RecorderState.IDLE

    def get_audio_data(self) -> bytes | None:
        self._thread.join(timeout=3.0)

        with self._lock:
            if not self._chunks:
                return None
            audio = np.concatenate(self._chunks, axis=0)
            self._chunks = []

        tmp = Path.home() / ".voice-typer" / "temp_recording.wav"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(tmp), audio, self.sample_rate, subtype="PCM_16")
        with open(str(tmp), "rb") as f:
            data = f.read()
        tmp.unlink(missing_ok=True)
        return data

    def reset(self):
        with self._lock:
            self._state = RecorderState.IDLE
            self._chunks = []
            self._peak_volume = 0.0
            self._last_voice_time = 0.0
            self._stop_event.set()

    @property
    def peak_volume(self) -> float:
        return self._peak_volume

    @property
    def is_recording(self) -> bool:
        return self._state == RecorderState.RECORDING

    @property
    def state(self) -> RecorderState:
        return self._state
