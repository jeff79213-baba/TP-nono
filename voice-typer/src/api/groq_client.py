import logging
import threading
import httpx

logger = logging.getLogger("voice-typer.groq")


GROQ_BASE = "https://api.groq.com/openai/v1"

# 多 Key 輪詢的全域狀態
_key_pool: list[str] = []
_key_index = 0
_key_lock = threading.Lock()


def set_api_keys(keys: list[str]):
    global _key_pool, _key_index
    with _key_lock:
        _key_pool = list(keys)
        _key_index = 0


def _next_key() -> str:
    global _key_index
    with _key_lock:
        if not _key_pool:
            return ""
        key = _key_pool[_key_index]
        suffix = key[-4:] if len(key) > 4 else key
        logger.info(f"使用 Key[{_key_index + 1}/{len(_key_pool)}] ...{suffix}")
        _key_index = (_key_index + 1) % len(_key_pool)
        return key


def test_api_connection(api_key: str) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{GROQ_BASE}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            return True, "連線成功！API Key 有效"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return False, "API Key 無效，請檢查是否輸入正確"
        return False, f"HTTP 錯誤: {e.response.status_code}"
    except httpx.ConnectError:
        return False, "無法連線到 Groq 伺服器，請檢查網路"
    except httpx.TimeoutException:
        return False, "連線超時，請檢查網路"
    except Exception as e:
        return False, f"錯誤: {str(e)}"


class GroqSTTClient:
    def __init__(self, model: str = "whisper-large-v3-turbo"):
        self.model = model

    def transcribe(self, audio_data: bytes, filename: str = "audio.wav") -> str:
        url = f"{GROQ_BASE}/audio/transcriptions"
        api_key = _next_key()
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {"file": (filename, audio_data, "audio/wav")}
        data = {"model": self.model, "language": "zh", "response_format": "json"}

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, data=data, files=files)
            resp.raise_for_status()
            result = resp.json()
            return result.get("text", "").strip()


class GroqLLMClient:
    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens

    def polish(self, text: str) -> str:
        url = f"{GROQ_BASE}/chat/completions"
        api_key = _next_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            choice = result["choices"][0]
            return choice["message"]["content"].strip()
