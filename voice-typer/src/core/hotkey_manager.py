import time
import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    toggled = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkey = "f8"
        self._settings_hotkey = "ctrl+alt+s"
        self._registered = False
        self._last_toggle = 0.0
        self._last_settings = 0.0
        self._toggle_handler = None
        self._settings_handler = None

    def register(self):
        if self._registered:
            return
        self._toggle_handler = keyboard.add_hotkey(self._hotkey, self._on_toggle, suppress=False)
        self._settings_handler = keyboard.add_hotkey(self._settings_hotkey, self._on_settings, suppress=False)
        self._registered = True

    def unregister(self):
        if not self._registered:
            return
        try:
            keyboard.remove_hotkey(self._toggle_handler)
            keyboard.remove_hotkey(self._settings_handler)
        except Exception:
            pass
        self._registered = False
        self._toggle_handler = None
        self._settings_handler = None

    def _on_toggle(self):
        now = time.time()
        if now - self._last_toggle < 0.3:
            return
        self._last_toggle = now
        self.toggled.emit()

    def _on_settings(self):
        now = time.time()
        if now - self._last_settings < 0.3:
            return
        self._last_settings = now
        self.settings_requested.emit()
