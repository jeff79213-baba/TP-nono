import logging
import threading
import numpy as np

logger = logging.getLogger("voice-typer.local-stt")

_MODEL = None
_MODEL_LOCK = threading.Lock()
_MODEL_NAME = None


def _load_model(model_name: str):
    global _MODEL, _MODEL_NAME
    if _MODEL is not None and _MODEL_NAME == model_name:
        return
    logger.info(f"正在載入本機模型: {model_name}...")
    from faster_whisper import WhisperModel
    _MODEL = WhisperModel(model_name, device="cpu", compute_type="int8", num_workers=2)
    _MODEL_NAME = model_name
    logger.info(f"模型 {model_name} 載入完成")


def unload_model():
    global _MODEL, _MODEL_NAME
    with _MODEL_LOCK:
        _MODEL = None
        _MODEL_NAME = None


class LocalSTTClient:
    def __init__(self, model_name: str = "tiny"):
        self.model_name = model_name

    def transcribe(self, audio_data: bytes) -> str:
        with _MODEL_LOCK:
            _load_model(self.model_name)

        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

        segments, _ = _MODEL.transcribe(
            audio_np, language="zh", beam_size=1, best_of=1,
            vad_filter=True, condition_on_previous_text=False,
        )
        text = "".join(seg.text for seg in segments).strip()
        return text
