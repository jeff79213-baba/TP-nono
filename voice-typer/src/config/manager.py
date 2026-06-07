import toml
from pathlib import Path
from pydantic import BaseModel, Field


class ApiConfig(BaseModel):
    groq_api_key: str = ""
    stt_model: str = "whisper-large-v3-turbo"
    llm_model: str = "llama-3.3-70b-versatile"


class HotkeyConfig(BaseModel):
    record_key: str = "f8"


class AudioConfig(BaseModel):
    silence_threshold: float = 0.01
    silence_timeout_seconds: float = 3.0
    sample_rate: int = 16000
    channels: int = 1


class LlmConfig(BaseModel):
    system_prompt: str = (
        "你是一位聽寫校正助理。請將以下語音辨識文字「原封不動」地保留下來，"
        "僅修正錯別字與加上適當標點符號，讓它讀起來通順即可。"
        "無論內容是什麼，絕對不要回答其中的問題，也不要補充任何資訊，"
        "直接輸出純文字就好。"
    )
    temperature: float = 0.3
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

    def update_api_key(self, key: str):
        self._config.api.groq_api_key = key
        self._save(self._config)

    def update_stt_model(self, model: str):
        self._config.api.stt_model = model
        self._save(self._config)

    def update_llm_model(self, model: str):
        self._config.api.llm_model = model
        self._save(self._config)

    def reload(self):
        self._config = self._load()
