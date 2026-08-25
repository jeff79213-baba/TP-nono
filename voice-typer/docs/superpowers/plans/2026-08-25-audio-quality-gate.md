# 錄音品質前檢 + Whisper 幻覺過濾 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在語音辨識 API 呼叫前攔截低音量錄音和 Whisper 幻覺，減少無效 API 呼叫。

**Architecture:** 兩層防護——`audio_recorder.py` 追蹤峰值音量，`pipeline.py` 在 STT 前檢查音量、在 STT 後檢查幻覺 pattern。`AudioConfig` 新增 `min_volume_threshold` 設定。

**Tech Stack:** Python 3, numpy, sounddevice, PyQt6, pydantic, toml, re

## Global Constraints

- 預設值：`min_volume_threshold = 0.003`
- 幻覺 pattern 為硬編碼列表，後續可擴充
- 不改動錄音行為（silence threshold/timeout 維持原樣）
- 不改動 LLM prompt

---

### Task 1: audio_recorder.py — 追蹤峰值音量

**Files:**
- Modify: `voice-typer/src/core/audio_recorder.py:21-36, 68-83, 110-125, 127-131`

**Interfaces:**
- Consumes: 無
- Produces: `AudioRecorder.peak_volume` (float property)

- [ ] **Step 1: 新增 `_peak_volume` 實例變數**

在 `AudioRecorder` dataclass 中，`_auto_stop_callback` 後面加：

```python
_peak_volume: float = 0.0
```

- [ ] **Step 2: callback 中更新 peak volume**

在 `_record_loop` 的 callback 函式中，`volume = float(...)` 之後、`if self._volume_callback` 之前加：

```python
if volume > self._peak_volume:
    self._peak_volume = volume
```

- [ ] **Step 3: 新增 `peak_volume` 屬性**

在 `is_recording` 屬性之前加：

```python
@property
def peak_volume(self) -> float:
    return self._peak_volume
```

- [ ] **Step 4: `reset()` 歸零**

在 `reset()` 方法的 `self._chunks = []` 之後加：

```python
self._peak_volume = 0.0
```

- [ ] **Step 5: Commit**

```bash
git add voice-typer/src/core/audio_recorder.py
git commit -m "feat: AudioRecorder 追蹤 peak_volume"
```

---

### Task 2: manager.py — AudioConfig 新增 min_volume_threshold

**Files:**
- Modify: `voice-typer/src/config/manager.py:18-23`

**Interfaces:**
- Consumes: 無
- Produces: `AudioConfig.min_volume_threshold` (float, default 0.003)

- [ ] **Step 1: 新增欄位**

在 `AudioConfig` 的 `channels` 之後加：

```python
min_volume_threshold: float = 0.003
```

- [ ] **Step 2: Commit**

```bash
git add voice-typer/src/config/manager.py
git commit -m "feat: AudioConfig 新增 min_volume_threshold"
```

---

### Task 3: pipeline.py — 錄音音量前檢

**Files:**
- Modify: `voice-typer/src/core/pipeline.py:82-144`

**Interfaces:**
- Consumes: `AudioRecorder.peak_volume` (from Task 1), `AudioConfig.min_volume_threshold` (from Task 2)
- Produces: 無

- [ ] **Step 1: 在 `_process_audio()` 中加入音量檢查**

在 `logger.info(f"取得錄音資料，大小: {len(audio_data)} bytes")` 之後、`if cfg.api.stt_mode == "local":` 之前加：

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

- [ ] **Step 2: Commit**

```bash
git add voice-typer/src/core/pipeline.py
git commit -m "feat: STT 前攔截低音量錄音"
```

---

### Task 4: pipeline.py — Whisper 幻覺過濾

**Files:**
- Modify: `voice-typer/src/core/pipeline.py:1-11, 115-123`

**Interfaces:**
- Consumes: STT 輸出文字 (str)
- Produces: 無

- [ ] **Step 1: 在檔案頂端 import re**

在 `import logging` 後面加：

```python
import re
```

- [ ] **Step 2: 定義幻覺 pattern**

在 `logger = ...` 之後、`class PipelineOrchestrator` 之前加：

```python
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

- [ ] **Step 3: 在 `_process_audio()` 中加入幻覺檢查**

在 `logger.info(f"語音辨識結果: '{text}'")` 之後、`if not text:` 之前加：

```python
if _is_hallucination(text):
    logger.warning(f"偵測到 Whisper 幻覺: '{text[:50]}...'")
    self.status_changed.emit("未偵測到語音")
    self._processing = False
    self.processing_done.emit()
    return
```

- [ ] **Step 4: Commit**

```bash
git add voice-typer/src/core/pipeline.py
git commit -m "feat: STT 後攔截 Whisper 幻覺文字"
```

---

### Task 5: 更新 config.toml 範本

**Files:**
- Modify: `voice-typer/config.toml`

**Interfaces:**
- Consumes: 無
- Produces: 無

- [ ] **Step 1: 在 `[audio]` 區塊加入 min_volume_threshold**

在 `channels = 1` 之後加：

```toml
min_volume_threshold = 0.003
```

- [ ] **Step 2: Commit**

```bash
git add voice-typer/config.toml
git commit -m "feat: config.toml 範本新增 min_volume_threshold"
```

---

### Task 6: 更新使用者 config.toml

**Files:**
- Modify: `C:\Users\TW-10\.voice-typer\config.toml`

**Interfaces:**
- Consumes: 無
- Produces: 無

- [ ] **Step 1: 在 `[audio]` 區塊加入 min_volume_threshold**

在 `channels = 1` 之後加：

```toml
min_volume_threshold = 0.003
```

（此變更不需 commit，因為是使用者設定檔）
