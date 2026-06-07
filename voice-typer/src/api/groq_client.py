import httpx


GROQ_BASE = "https://api.groq.com/openai/v1"


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
    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo"):
        self.api_key = api_key
        self.model = model
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def transcribe(self, audio_data: bytes, filename: str = "audio.wav") -> str:
        url = f"{GROQ_BASE}/audio/transcriptions"
        files = {"file": (filename, audio_data, "audio/wav")}
        data = {"model": self.model, "language": "zh", "response_format": "json"}

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=self._headers, data=data, files=files)
            resp.raise_for_status()
            result = resp.json()
            return result.get("text", "").strip()


class GroqLLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ):
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def polish(self, text: str) -> str:
        url = f"{GROQ_BASE}/chat/completions"
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
            resp = client.post(url, headers=self._headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            choice = result["choices"][0]
            return choice["message"]["content"].strip()
