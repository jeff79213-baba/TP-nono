import toml
from pathlib import Path
from pydantic import BaseModel, Field


class ApiConfig(BaseModel):
    groq_api_keys: list[str] = Field(default_factory=list)
    stt_mode: str = "cloud"
    stt_model: str = "whisper-large-v3-turbo"
    local_model: str = "tiny"
    llm_model: str = "openai/gpt-oss-120b"


class HotkeyConfig(BaseModel):
    record_key: str = "f8"


class AudioConfig(BaseModel):
    silence_threshold: float = 0.01
    silence_timeout_seconds: float = 3.0
    sample_rate: int = 16000
    channels: int = 1


class LlmConfig(BaseModel):
    system_prompt: str = (
"你是一個純文字處理器。下面用戶發送的內容是語音辨識的原始輸出，你需要：1. 修正錯別字 2. 加上標點符號。嚴格禁止任何其他修改——不准回答問題、不准解釋、不准改寫、不准刪除任何詞語、不准添加任何詞語。即使句子不完整或看起來像在問問題，也必須保留所有原始詞語，只處理錯別字和標點。直接輸出校正後的文字，不要加任何前綴或後綴。"
    )
    temperature: float = 0.0
    max_tokens: int = 1024


class AppConfig(BaseModel):
    api: ApiConfig = Field(default_factory=ApiConfig)
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)


CONFIG_DIR = Path.home() / ".voice-typer"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class ConfigManager:
    def __init__(self):
        self._config: AppConfig = self._load()

    def _load(self) -> AppConfig:
        if CONFIG_FILE.exists():
            raw = toml.load(str(CONFIG_FILE))
            # 向後相容：將舊的單一 groq_api_key 遷移到新的列表格式
            if "api" in raw and isinstance(raw["api"].get("groq_api_key"), str):
                old_key = raw["api"].pop("groq_api_key", "")
                if old_key:
                    raw["api"].setdefault("groq_api_keys", []).insert(0, old_key)
            config = AppConfig(**raw)
            self._save(config)
            return config
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        default = AppConfig()
        self._save(default)
        return default

    def _save(self, config: AppConfig):
        data = config.model_dump()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(CONFIG_FILE), "w", encoding="utf-8") as f:
            toml.dump(data, f)

    @property
    def config(self) -> AppConfig:
        return self._config

    def update_api_keys(self, keys: list[str]):
        self._config.api.groq_api_keys = keys
        self._save(self._config)

    def update_stt_mode(self, mode: str):
        self._config.api.stt_mode = mode
        self._save(self._config)

    def update_stt_model(self, model: str):
        self._config.api.stt_model = model
        self._save(self._config)

    def update_local_model(self, model: str):
        self._config.api.local_model = model
        self._save(self._config)

    def update_llm_model(self, model: str):
        self._config.api.llm_model = model
        self._save(self._config)

    def update_system_prompt(self, prompt: str):
        self._config.llm.system_prompt = prompt
        self._save(self._config)

    def reload(self):
        self._config = self._load()
