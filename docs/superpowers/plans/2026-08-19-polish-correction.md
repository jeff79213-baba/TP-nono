# 提升潤飾錯字修正能力 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將語音輸入的潤飾 prompt 從保守改為「依上下文積極改正明顯聽錯的字詞」，同時保留句子結構與語氣。

**Architecture:** 更換 LLM 系統 prompt 字串，共三處（使用者實際設定、manager.py 預設值、config.toml 範本）。不改程式邏輯，只改字串常數，以測試腳本驗證 Groq API 實際輸出。

**Tech Stack:** Python 3.12、Groq API（openai/gpt-oss-120b）、toml

## Global Constraints

- 新版 prompt 必須為下列字串（一字不差）：
```
你是一個語音辨識文字校正器。請依上下文把語音辨識的錯字修正確：

1. 刪除口語贅詞（僅限：嗯、啊、喔、那個、這個、就是說）
2. 依上下文改正明顯聽錯的字詞（如同音字、近音字、語意不通的字）
3. 繁體中文輸出

禁止事項（絕對遵守）：
- 禁止改寫句子結構或調整語序
- 禁止改變語氣（疑問句不准改成陳述句）
- 禁止添加、刪除原意以外的內容（贅詞除外）

只有無法從上下文判斷的字才原樣保留。只輸出校正後的文字，其他什麼都不要做。
```
- LLM 模型維持 `openai/gpt-oss-120b`，`max_tokens` 維持 `1024`，`temperature` 維持 `0.0`
- 驗證範例輸入「現在有人自助來了只是任世的攻擊不太強」，預期輸出應接近「現在有文字出來了 只是潤飾的功能不太強」
- 輸出不得包含 ` thinking` 區塊、不得為空字串

---

### Task 1: 更新使用者實際設定檔

**Files:**
- Modify: `C:\Users\TW-10\.voice-typer\config.toml`（`[llm].system_prompt`）

**Interfaces:**
- Consumes: 無
- Produces: `~/.voice-typer/config.toml` 中 `[llm].system_prompt` 更新為新版 prompt

- [ ] **Step 1: 讀取目前設定檔確認舊 prompt 內容**

Run: `Get-Content "$env:USERPROFILE\.voice-typer\config.toml"`
Expected: `[llm]` 區段存在 `system_prompt`，內容為舊版 prompt

- [ ] **Step 2: 更新 system_prompt**

以 Edit 工具將 `C:\Users\TW-10\.voice-typer\config.toml` 的 `system_prompt` 值取代為新版 prompt（TML 字串含 `\n` 換行）。

- [ ] **Step 3: 驗證寫入正確**

Run: `Get-Content "$env:USERPROFILE\.voice-typer\config.toml"`
Expected: `system_prompt` 開頭為「你是一個語音辨識文字校正器。請依上下文把語音辨識的錯字修正確：」

- [ ] **Step 4: Commit**

```bash
git add 無（此檔在 home 目錄，不在 repo）
```
不需 commit（檔案位於 repo 之外）。

---

### Task 2: 更新 manager.py 預設值

**Files:**
- Modify: `C:\Users\TW-10\Documents\TP-nono\voice-typer\src\config\manager.py:25-28`

**Interfaces:**
- Consumes: 無
- Produces: `LlmConfig.system_prompt` 預設值為新版 prompt

- [ ] **Step 1: 更新預設 prompt**

以 Edit 工具將 `voice-typer/src/config/manager.py` 中 `LlmConfig.system_prompt` 的字串常數取代為新版 prompt（Python 字串，需用雙引號包住、`\n` 為換行）。

- [ ] **Step 2: 驗證編譯**

Run: `python -m compileall -q "C:\Users\TW-10\Documents\TP-nono\voice-typer\src"`
Expected: 無輸出，exit code 0

- [ ] **Step 3: Commit**

```bash
git add voice-typer/src/config/manager.py
git commit -m "feat: 提升潤飾 prompt 的錯字修正能力（manager 預設值）"
```

---

### Task 3: 更新 config.toml 範本

**Files:**
- Modify: `C:\Users\TW-10\Documents\TP-nono\voice-typer\config.toml:18`

**Interfaces:**
- Consumes: 無
- Produces: 範本 `[llm].system_prompt` 更新為新版 prompt

- [ ] **Step 1: 更新範本 prompt**

以 Edit 工具將 `voice-typer/config.toml` 的 `system_prompt` 值取代為新版 prompt（TOML 字串，需用雙引號包住、`\n` 為換行）。

- [ ] **Step 2: 驗證 TOML 可解析**

Run: `python -c "import toml; c=toml.load(r'C:\Users\TW-10\Documents\TP-nono\voice-typer\config.toml'); print(c['llm']['system_prompt'][:20])"`
Expected: 輸出「你是一個語音辨識文字校正器」

- [ ] **Step 3: Commit**

```bash
git add voice-typer/config.toml
git commit -m "feat: 提升潤飾 prompt 的錯字修正能力（範本）"
```

---

### Task 4: 實測 Groq API 驗證校正效果

**Files:**
- Create: `C:\Users\TW-10\AppData\Local\Temp\opencode\verify_polish.py`（暫存，不入 repo）

**Interfaces:**
- Consumes: `~/.voice-typer/config.toml` 的新版 prompt、`openai/gpt-oss-120b` 模型、API Key
- Produces: 驗證結果（console 輸出）

- [ ] **Step 1: 撰寫驗證腳本**

建立 `C:\Users\TW-10\AppData\Local\Temp\opencode\verify_polish.py`：

```python
import sys
sys.path.insert(0, r"C:\Users\TW-10\Documents\TP-nono\voice-typer")
from src.config.manager import ConfigManager
from src.api.groq_client import GroqLLMClient, set_api_keys

cfg = ConfigManager().config
set_api_keys(cfg.api.groq_api_keys)

llm = GroqLLMClient(
    model=cfg.api.llm_model,
    system_prompt=cfg.llm.system_prompt,
    temperature=cfg.llm.temperature,
    max_tokens=cfg.llm.max_tokens,
)
for text in [
    "現在有人自助來了只是任世的攻擊不太強",
    "嗯那個今天天氣真的很好啊我們要去爬山",
]:
    result = llm.polish(text)
    print(f"in : {text}")
    print(f"out: {result}")
    print()
```

- [ ] **Step 2: 執行驗證**

Run: `$env:PYTHONIOENCODING='utf-8'; python "C:\Users\TW-10\AppData\Local\Temp\opencode\verify_polish.py"`
Expected:
- 第一個輸入「現在有人自助來了只是任世的攻擊不太強」輸出應接近「現在有文字出來了 只是潤飾的功能不太強」
- 第二個輸入輸出應為「今天天氣真的很好我們要去爬山」附近
- 兩者皆不含 ` thinking`、非空字串

- [ ] **Step 3: 若輸出不如預期**

回到 Task 1-3 檢視 prompt 是否為 Global Constraints 中的精確字串，或調整 prompt 措辭後重新驗證。若調整措辭，需同步更新三處與規格文件。

- [ ] **Step 4: 重啟應用程式**

Run: 關閉所有 `src.main` 實例後重新啟動：
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object { $_.CommandLine -match 'src\.main' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process pythonw -ArgumentList '-m','src.main' -WorkingDirectory 'C:\Users\TW-10\Documents\TP-nono\voice-typer'
```
Expected: 新實例啟動，`app.log` 無錯誤，無熱鍵註冊警告

- [ ] **Step 5: Commit 收尾**

```bash
git add docs/superpowers/specs/2026-08-19-polish-correction-design.md docs/superpowers/plans/2026-08-19-polish-correction.md
git commit -m "docs: 記錄潤飾錯字修正設計與實作計畫"（若已在前一任務提交則略過）
```