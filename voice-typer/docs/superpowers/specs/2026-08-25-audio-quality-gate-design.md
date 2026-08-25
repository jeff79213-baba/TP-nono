# 錄音品質前檢 + Whisper 幻覺過濾

**日期**: 2026-08-25
**狀態**: 已核准

## 問題

使用 `whisper-large-v3-turbo` 進行語音辨識時，有兩類系統性失敗：

1. **低音量錄音**：錄音峰值音量 < 0.005 RMS 時，Whisper 輸出亂碼或垃圾文字
2. **Whisper 幻覺**：近靜音或噪音錄音時，Whisper 輸出固定模式的垃圾中文（如「请不吝点赞 订阅 转发 打赏支持明镜与点点栏目」）

這兩類問題消耗 API 配額，且 LLM 潤飾無法修復已毀損的輸入。

## 解決方案

兩層防護：錄音後立即檢查音量，再對 STT 結果做幻覺過濾。

### 流程圖

```
錄音結束
  ↓
peak_volume < min_volume_threshold?
  ├── 是 → 狀態列:「錄音音量過低，已略過」→ 結束
  └── 否 → 呼叫 STT API
              ↓
         匹配幻覺 pattern?
           ├── 是 → 狀態列:「未偵測到語音」→ 結束
           └── 否 → 呼叫 LLM 潤飾 → 貼上文字
```

## 改動檔案

| 檔案 | 改動 |
|------|------|
| `src/core/audio_recorder.py` | 追蹤 `_peak_volume`，新增 `peak_volume` 屬性，`reset()` 歸零 |
| `src/config/manager.py` | `AudioConfig` 新增 `min_volume_threshold: float = 0.003` |
| `src/core/pipeline.py` | STT 前檢查 `peak_volume`；STT 後檢查幻覺 pattern |

## 詳細設計

### 1. audio_recorder.py — 音量追蹤

新增實例變數 `_peak_volume: float = 0.0`。

在 callback 中：
```python
volume = float(np.sqrt(np.mean(indata ** 2)))
if volume > self._peak_volume:
    self._peak_volume = volume
```

新增屬性：
```python
@property
def peak_volume(self) -> float:
    return self._peak_volume
```

`reset()` 中加 `self._peak_volume = 0.0`。

### 2. manager.py — 設定

```python
class AudioConfig(BaseModel):
    silence_threshold: float = 0.01
    silence_timeout_seconds: float = 3.0
    sample_rate: int = 16000
    channels: int = 1
    min_volume_threshold: float = 0.003  # 新增
```

### 3. pipeline.py — 品質閘門

在 `_process_audio()` 中，STT 呼叫前：
```python
peak = self._recorder.peak_volume
min_vol = cfg.audio.min_volume_threshold
if peak < min_vol:
    logger.info(f"錄音音量過低 (peak={peak:.4f} < threshold={min_vol})，跳過處理")
    self.status_changed.emit("錄音音量過低，已略過")
    self._processing = False
    self.processing_done.emit()
    return
```

在 STT 結果出來後、LLM 呼叫前：
```python
import re

HALLUCINATION_PATTERNS = [
    r"请不吝点赞",
    r"感谢观看",
    r"订阅",
    r"转发",
    r"打赏",
    r"明镜与点点栏目",
]

def _is_hallucination(text: str) -> bool:
    return any(re.search(p, text) for p in HALLUCINATION_PATTERNS)
```

```python
if _is_hallucination(text):
    logger.warning(f"偵測到 Whisper 幻覺: '{text[:50]}...'")
    self.status_changed.emit("未偵測到語音")
    self._processing = False
    self.processing_done.emit()
    return
```

## 預期效果

- 低音量垃圾文字：100% 攔截（前檢）
- Whisper 幻覺（近靜音）：~90% 攔截（pattern 過濾）
- 正常語音辨識：不受影響
- API 呼叫次數：減少 ~15-20%（依使用場景）

## 風險

- `min_volume_threshold = 0.003` 可能太嚴格或太寬鬆，需要實際測試調整
- 幻覺 pattern 不完整，新出現的幻覺模式可能漏過（後續可擴充）
- 繁體中文語音的幻覺 pattern 可能與簡體不同（目前收集到的都是簡體）
