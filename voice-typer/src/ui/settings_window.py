from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QLabel, QMessageBox, QHBoxLayout,
)
from PyQt6.QtCore import Qt

from src.config.manager import ConfigManager
from src.api.groq_client import test_api_connection


SETTINGS_STYLESHEET = """
QDialog {
    background-color: #2b2b2b;
    color: #f0f0f0;
}
QLabel {
    color: #f0f0f0;
}
QLineEdit {
    background-color: #3c3c3c;
    color: #f0f0f0;
    border: 1px solid #555;
    padding: 4px;
    border-radius: 4px;
}
QComboBox {
    background-color: #3c3c3c;
    color: #f0f0f0;
    border: 1px solid #555;
    padding: 4px;
    border-radius: 4px;
}
QPushButton {
    background-color: #4a86c8;
    color: white;
    border: none;
    padding: 6px 16px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #5a96d8;
}
"""


class SettingsWindow(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("語音輸入 - 設定")
        self.setFixedSize(420, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setText(config.config.api.groq_api_key)
        self._api_key_input.setPlaceholderText("輸入你的 Groq API Key")
        form.addRow("Groq API Key:", self._api_key_input)

        self._stt_model = QComboBox()
        self._stt_model.addItems(["whisper-large-v3-turbo", "whisper-large-v3", "distil-whisper-large-v3-en"])
        idx = self._stt_model.findText(config.config.api.stt_model)
        if idx >= 0:
            self._stt_model.setCurrentIndex(idx)
        form.addRow("STT 模型:", self._stt_model)

        self._llm_model = QComboBox()
        self._llm_model.addItems([
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ])
        idx2 = self._llm_model.findText(config.config.api.llm_model)
        if idx2 >= 0:
            self._llm_model.setCurrentIndex(idx2)
        form.addRow("LLM 模型:", self._llm_model)

        layout.addLayout(form)
        layout.addStretch()

        self._test_btn = QPushButton("測試連線")
        self._test_btn.clicked.connect(self._on_test)
        layout.addWidget(self._test_btn)

        self._test_result = QLabel("")
        self._test_result.setWordWrap(True)
        layout.addWidget(self._test_result)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("儲存設定")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _on_test(self):
        key = self._api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "警告", "請先填入 Groq API Key")
            return
        self._test_btn.setEnabled(False)
        self._test_btn.setText("測試中...")
        self._test_result.setStyleSheet("color: #f0f0f0;")
        self._test_result.setText("正在連線...")
        ok, msg = test_api_connection(key)
        self._test_btn.setEnabled(True)
        self._test_btn.setText("測試連線")
        if ok:
            self._test_result.setStyleSheet("color: #80c080;")
        else:
            self._test_result.setStyleSheet("color: #e08080;")
        self._test_result.setText(msg)

    def _on_save(self):
        key = self._api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "警告", "請填入 Groq API Key")
            return
        self._config.update_api_key(key)
        self._config.update_stt_model(self._stt_model.currentText())
        self._config.update_llm_model(self._llm_model.currentText())
        QMessageBox.information(self, "完成", "設定已儲存")
        self.accept()
