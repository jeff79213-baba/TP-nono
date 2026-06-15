from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QPushButton, QLabel, QMessageBox, QHBoxLayout,
    QTextEdit, QPlainTextEdit,
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
QLineEdit, QPlainTextEdit {
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
        self.setFixedSize(460, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._api_key_input = QPlainTextEdit()
        self._api_key_input.setPlaceholderText("每行輸入一組 Groq API Key\n多組 Key 會自動輪流使用，分散 Rate Limit")
        self._api_key_input.setPlainText("\n".join(config.config.api.groq_api_keys))
        self._api_key_input.setMaximumHeight(80)
        form.addRow("Groq API Keys:", self._api_key_input)

        self._stt_model = QComboBox()
        self._stt_model.addItems(["whisper-large-v3-turbo", "whisper-large-v3", "distil-whisper-large-v3-en"])
        idx = self._stt_model.findText(config.config.api.stt_model)
        if idx >= 0:
            self._stt_model.setCurrentIndex(idx)
        form.addRow("STT 模型:", self._stt_model)

        self._llm_model = QComboBox()
        self._llm_model.addItems([
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
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

    def _get_keys(self) -> list[str]:
        return [
            line.strip()
            for line in self._api_key_input.toPlainText().splitlines()
            if line.strip()
        ]

    def _on_test(self):
        keys = self._get_keys()
        if not keys:
            QMessageBox.warning(self, "警告", "請先填入至少一組 Groq API Key")
            return
        self._test_btn.setEnabled(False)
        self._test_btn.setText("測試中...")
        self._test_result.setStyleSheet("color: #f0f0f0;")
        results = []
        all_ok = True
        for i, key in enumerate(keys, 1):
            self._test_result.setText(f"正在測試第 {i}/{len(keys)} 組 Key...")
            ok, msg = test_api_connection(key)
            status = "✅" if ok else "❌"
            results.append(f"Key {i}: {status} {msg}")
            if not ok:
                all_ok = False
        self._test_btn.setEnabled(True)
        self._test_btn.setText("測試連線")
        color = "#80c080" if all_ok else "#e08080"
        self._test_result.setStyleSheet(f"color: {color};")
        self._test_result.setText("\n".join(results))

    def _on_save(self):
        keys = self._get_keys()
        if not keys:
            QMessageBox.warning(self, "警告", "請填入至少一組 Groq API Key")
            return
        self._config.update_api_keys(keys)
        self._config.update_stt_model(self._stt_model.currentText())
        self._config.update_llm_model(self._llm_model.currentText())
        QMessageBox.information(self, "完成", "設定已儲存")
        self.accept()


class PromptEditDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("編輯潤飾指令")
        self.setFixedSize(600, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        layout = QVBoxLayout(self)

        label = QLabel("當語音辨識完成後，AI 會依照以下指令潤飾文字：")
        label.setWordWrap(True)
        layout.addWidget(label)

        self._editor = QTextEdit()
        self._editor.setPlainText(config.config.llm.system_prompt)
        self._editor.setStyleSheet("""
            QTextEdit {
                background-color: #3c3c3c;
                color: #f0f0f0;
                border: 1px solid #555;
                padding: 6px;
                border-radius: 4px;
                font-family: 'Microsoft JhengHei', 'Noto Sans TC', sans-serif;
                font-size: 13px;
            }
        """)
        layout.addWidget(self._editor)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("儲存")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _on_save(self):
        text = self._editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "指令不能為空白")
            return
        self._config.update_system_prompt(text)
        QMessageBox.information(self, "完成", "潤飾指令已更新")
        self.accept()
