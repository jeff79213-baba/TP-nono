import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QShortcut, QKeySequence

from src.config.manager import ConfigManager


_LOG_DIR = Path.home() / ".voice-typer"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(_LOG_DIR / "app.log"), mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("voice-typer")
from src.core.pipeline import PipelineOrchestrator
from src.core.hotkey_manager import HotkeyManager
from src.ui.tray import TrayManager
from src.ui.settings_window import SettingsWindow, PromptEditDialog
from src.ui.volume_widget import VolumeWidget


ABOUT_TEXT = """語音輸入 v0.1.0

Typeless 開源平替版 — 本地端語音輸入工具

功能：
• 按 F8 開始 / 停止錄音
• 自動語音辨識（Groq STT）
• AI 潤飾文字（Groq LLM）
• 自動填入游標位置
• 支援多組 API Key 自動輪詢，分散 Rate Limit

使用方式：
1. 在設定中填入 Groq API Key（可填入多組，每行一組）
2. 按 F8 開始說話
3. 再按 F8 結束，文字自動輸入

快捷鍵：
• F8：開始 / 停止錄音
• Ctrl + Alt + S：開啟設定
• Ctrl + Q：離開程式
"""


class AppController(QObject):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._config = ConfigManager()
        self._pipeline = PipelineOrchestrator(self._config, self)
        self._hotkey = HotkeyManager(self)
        self._tray = TrayManager(self)
        self._volume_widget = VolumeWidget(None)
        self._settings_window = None

        app.installNativeEventFilter(self._hotkey.native_event_filter())
        self._connect_signals()
        self._hotkey.register(int(self._tray.native_window_id()))
        self._tray.show()

        if not self._config.config.api.groq_api_keys:
            self._show_settings()

    def _connect_signals(self):
        self._hotkey.toggled.connect(self._pipeline.toggle_recording)
        self._hotkey.settings_requested.connect(self._show_settings)
        self._hotkey.edit_prompt_requested.connect(self._quick_save_prompt)
        self._pipeline.recording_started.connect(self._on_recording_started)
        self._pipeline.recording_stopped.connect(self._on_recording_stopped)
        self._pipeline.processing_started.connect(self._on_processing_started)
        self._pipeline.processing_done.connect(self._on_processing_done)
        self._pipeline.cancelled.connect(self._on_cancelled)
        self._pipeline.error_occurred.connect(self._on_error)
        self._pipeline.status_changed.connect(self._on_status)
        self._pipeline.set_volume_callback(self._volume_widget.set_volume)
        self._tray.toggle_requested.connect(self._pipeline.toggle_recording)
        self._tray.cancel_requested.connect(self._pipeline.cancel)
        self._tray.show_about_requested.connect(self._show_about)
        self._tray.show_settings_requested.connect(self._show_settings)
        self._tray.edit_prompt_requested.connect(self._show_edit_prompt)
        self._tray.quit_requested.connect(self._quit)

        shortcut = QShortcut(QKeySequence("Ctrl+Q"), self._tray)
        shortcut.activated.connect(self._quit)

    def _show_about(self):
        QMessageBox.about(None, "關於 語音輸入", ABOUT_TEXT)

    def _on_recording_started(self):
        self._tray.set_recording()
        screen = self._app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            w = self._volume_widget.width()
            x = geo.x() + (geo.width() - w) // 2
            y = geo.y() + geo.height() - self._volume_widget.height() - 60
            self._volume_widget.move(x, y)
        self._volume_widget.show()

    def _on_recording_stopped(self):
        self._volume_widget.set_processing_mode(True)
        self._volume_widget.show_status("文字處理中...")

    def _on_cancelled(self):
        self._volume_widget.set_processing_mode(False)
        self._volume_widget.hide_status()
        self._volume_widget.hide()
        self._tray.set_idle()
        self._tray.notify("已取消", "錄音已取消")

    def _on_processing_started(self):
        self._tray.set_processing()
        self._volume_widget.set_processing_mode(True)
        self._volume_widget.show_status("文字處理中...")

    def _on_processing_done(self):
        self._volume_widget.set_processing_mode(False)
        self._volume_widget.hide_status()
        self._volume_widget.hide()
        self._tray.flash_done()

    def _on_error(self, msg: str):
        self._volume_widget.set_processing_mode(False)
        self._volume_widget.hide_status()
        self._volume_widget.hide()
        self._tray.flash_done()
        self._tray.notify_error("錯誤", msg)

    def _on_status(self, msg: str):
        self._tray.notify("狀態", msg)

    def _show_settings(self):
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self._config)
            self._settings_window.accepted.connect(self._pipeline.sync_api_keys)
            self._settings_window.show()
        else:
            self._settings_window.raise_()

    def _show_edit_prompt(self):
        dialog = PromptEditDialog(self._config)
        dialog.exec()

    def _quick_save_prompt(self):
        prompt = self._config.config.llm.system_prompt.strip()
        if not prompt:
            self._tray.notify_error("錯誤", "潤飾指令不能為空白")
            return
        self._config.update_system_prompt(prompt)
        self._tray.notify("狀態", "潤飾指令已重新儲存")

    def _quit(self):
        self._hotkey.unregister(int(self._tray.native_window_id()))
        self._app.quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("語音輸入")
    app.setQuitOnLastWindowClosed(False)
    controller = AppController(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

