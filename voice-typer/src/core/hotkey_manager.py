import ctypes
import ctypes.wintypes
import logging
import time
from PyQt6.QtCore import QObject, QAbstractNativeEventFilter, pyqtSignal

logger = logging.getLogger("voice-typer.hotkey")

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002

VK_F8 = 0x77
VK_S = 0x53

user32 = ctypes.windll.user32
user32.RegisterHotKey.argtypes = [
    ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
]
user32.RegisterHotKey.restype = ctypes.c_int
user32.UnregisterHotKey.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = ctypes.c_int


class HotkeyManager(QObject):
    toggled = pyqtSignal()
    settings_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hotkey_id = 1
        self._settings_hotkey_id = 2
        self._registered = False
        self._hwnd = None
        self._last_toggle = 0.0
        self._last_settings = 0.0
        self._filter = _HotkeyEventFilter(self)

    def register(self, hwnd: int):
        if self._registered:
            return
        self._hwnd = hwnd
        ok1 = user32.RegisterHotKey(hwnd, self._hotkey_id, 0, VK_F8)
        ok2 = user32.RegisterHotKey(
            hwnd, self._settings_hotkey_id, MOD_ALT | MOD_CONTROL, VK_S
        )
        if not ok1:
            logger.warning("RegisterHotKey F8 失敗，可能被其他程式佔用")
        if not ok2:
            logger.warning("RegisterHotKey Ctrl+Alt+S 失敗")
        self._registered = True

    def unregister(self, hwnd: int):
        if not self._registered:
            return
        user32.UnregisterHotKey(hwnd, self._hotkey_id)
        user32.UnregisterHotKey(hwnd, self._settings_hotkey_id)
        self._registered = False

    def reregister(self):
        if self._hwnd is None:
            return
        self._registered = False
        self.register(self._hwnd)

    def handle_wm_hotkey(self, wparam) -> bool:
        now = time.time()
        if wparam == self._hotkey_id:
            if now - self._last_toggle < 0.3:
                return True
            self._last_toggle = now
            self.toggled.emit()
            return True
        elif wparam == self._settings_hotkey_id:
            if now - self._last_settings < 0.3:
                return True
            self._last_settings = now
            self.settings_requested.emit()
            return True
        return False

    def native_event_filter(self):
        return self._filter


class _HotkeyEventFilter(QAbstractNativeEventFilter):
    def __init__(self, manager: HotkeyManager):
        super().__init__()
        self._mgr = manager

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(message.__int__())
            if msg.message == WM_HOTKEY:
                handled = self._mgr.handle_wm_hotkey(msg.wParam)
                return (handled, 0)
        return (False, 0)
