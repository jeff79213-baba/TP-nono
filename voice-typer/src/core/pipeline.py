import threading
import logging
from PyQt6.QtCore import QObject, pyqtSignal

from src.config.manager import ConfigManager
from src.core.audio_recorder import AudioRecorder
from src.api.groq_client import GroqSTTClient, GroqLLMClient
from src.core.type_in_engine import TypeInEngine

logger = logging.getLogger("voice-typer.pipeline")


class PipelineOrchestrator(QObject):
    status_changed = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    processing_started = pyqtSignal()
    processing_done = pyqtSignal()
    cancelled = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._recorder = AudioRecorder(
            sample_rate=config.config.audio.sample_rate,
            channels=config.config.audio.channels,
            silence_threshold=config.config.audio.silence_threshold,
            silence_timeout=config.config.audio.silence_timeout_seconds,
        )
        self._type_in = TypeInEngine()
        self._lock = threading.Lock()
        self._processing = False

        self._recorder.set_auto_stop_callback(self._on_auto_stop)

    def set_volume_callback(self, callback):
        self._recorder.set_volume_callback(callback)

    def cancel(self):
        with self._lock:
            if self._recorder.is_recording:
                logger.info("取消錄音")
                self._recorder.stop_recording()
                self._recorder.reset()
                self.cancelled.emit()

    def _on_auto_stop(self):
        with self._lock:
            if self._processing:
                return
            logger.info("自動停止錄音（靜音超時），開始處理")
            self.recording_stopped.emit()
            self._process_audio_async()

    def toggle_recording(self):
        with self._lock:
            if self._processing:
                logger.debug("正在處理中，忽略切換請求")
                return
            if self._recorder.is_recording:
                logger.info("停止錄音，開始處理")
                self._recorder.stop_recording()
                self.recording_stopped.emit()
                self._process_audio_async()
            else:
                logger.info("開始錄音")
                self._recorder.reset()
                self._recorder.start_recording()
                self.recording_started.emit()

    def _process_audio_async(self):
        self._processing = True
        self.processing_started.emit()
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _process_audio(self):
        try:
            cfg = self._config.config
            if not cfg.api.groq_api_key:
                logger.warning("API Key 未設定")
                self.error_occurred.emit("請先在設定中填入 Groq API Key")
                self._processing = False
                self.processing_done.emit()
                return

            audio_data = self._recorder.get_audio_data()
            if audio_data is None:
                logger.error("無法取得錄音資料 (chunks 為空)")
                self.error_occurred.emit("無法取得錄音資料，請確認麥克風已連接且未被其他程式佔用")
                self._processing = False
                self.processing_done.emit()
                return

            logger.info(f"取得錄音資料，大小: {len(audio_data)} bytes")

            stt = GroqSTTClient(api_key=cfg.api.groq_api_key, model=cfg.api.stt_model)
            logger.info("呼叫語音辨識 API...")
            text = stt.transcribe(audio_data)
            logger.info(f"語音辨識結果: '{text}'")

            if not text:
                logger.warning("語音辨識回傳空文字")
                self.status_changed.emit("未偵測到語音，已取消")
                self._processing = False
                self.processing_done.emit()
                return

            llm = GroqLLMClient(
                api_key=cfg.api.groq_api_key,
                model=cfg.api.llm_model,
                system_prompt=cfg.llm.system_prompt,
                temperature=cfg.llm.temperature,
                max_tokens=cfg.llm.max_tokens,
            )
            logger.info("呼叫文字潤飾 API...")
            polished = llm.polish(text)
            logger.info(f"潤飾結果: '{polished}'")

            logger.info("模擬 Ctrl+V 貼上文字")
            self._type_in.type_text(polished)
            self.status_changed.emit(f"✅ 已輸入 ({len(polished)} 字)")
        except Exception as e:
            logger.error(f"處理失敗: {e}", exc_info=True)
            self.error_occurred.emit(f"處理失敗: {str(e)}")
        finally:
            self._processing = False
            self._recorder.reset()
            self.processing_done.emit()
