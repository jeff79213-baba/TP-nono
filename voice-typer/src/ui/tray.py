from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget
from PyQt6.QtGui import QIcon, QAction, QCursor
from PyQt6.QtCore import QObject, pyqtSignal


_ICON_PATH = str(Path(__file__).parent / "icon.ico")


class TrayManager(QObject):
    toggle_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    show_settings_requested = pyqtSignal()
    show_about_requested = pyqtSignal()
    edit_prompt_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hidden = QWidget()
        self._hidden.setWindowTitle("語音輸入")
        self._hidden.setFixedSize(0, 0)
        self._hidden.showMinimized()

        self._tray = QSystemTrayIcon(self._hidden)
        self._tray.setIcon(QIcon(_ICON_PATH))
        self._tray.setToolTip("語音輸入 - 待命")

        self._menu = QMenu(self._hidden)
        self._toggle_action = QAction("開始錄音 (F8)")
        self._toggle_action.triggered.connect(self.toggle_requested.emit)
        self._menu.addAction(self._toggle_action)

        self._cancel_action = QAction("取消")
        self._cancel_action.setVisible(False)
        self._cancel_action.triggered.connect(self.cancel_requested.emit)
        self._menu.addAction(self._cancel_action)

        self._menu.addSeparator()

        self._about_action = QAction("說明")
        self._about_action.triggered.connect(self.show_about_requested.emit)
        self._menu.addAction(self._about_action)

        self._edit_prompt_action = QAction("編輯潤飾指令")
        self._edit_prompt_action.triggered.connect(self.edit_prompt_requested.emit)
        self._menu.addAction(self._edit_prompt_action)

        self._settings_action = QAction("設定")
        self._settings_action.triggered.connect(self.show_settings_requested.emit)
        self._menu.addAction(self._settings_action)

        self._menu.addSeparator()

        self._quit_action = QAction("離開")
        self._quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(self._quit_action)

        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            self._menu.exec(QCursor.pos())
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_settings_requested.emit()

    def native_window_id(self):
        return int(self._hidden.winId())

    def show(self):
        self._tray.show()

    def set_idle(self):
        self._tray.setToolTip("語音輸入 - 待命\nF8：開始錄音")
        self._toggle_action.setText("開始錄音 (F8)")
        self._toggle_action.setEnabled(True)
        self._cancel_action.setVisible(False)

    def set_recording(self):
        self._tray.setToolTip("🔴 錄音中...\nF8：停止錄音")
        self._toggle_action.setText("停止錄音 (F8)")
        self._toggle_action.setEnabled(True)
        self._cancel_action.setText("取消錄音")
        self._cancel_action.setVisible(True)

    def set_processing(self):
        self._tray.setToolTip("⚙️ 處理中...")
        self._toggle_action.setText("處理中...")
        self._toggle_action.setEnabled(False)
        self._cancel_action.setVisible(False)

    def flash_done(self):
        import threading
        self._tray.setToolTip("✅ 已輸入")
        self._toggle_action.setEnabled(True)
        threading.Timer(2.0, self.set_idle).start()

    def notify(self, title: str, message: str, duration_ms: int = 2000):
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, duration_ms)

    def notify_error(self, title: str, message: str):
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Critical, 5000)
