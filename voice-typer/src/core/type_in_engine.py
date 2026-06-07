import pyperclip
import time
from pynput.keyboard import Controller, Key


class TypeInEngine:
    def __init__(self):
        self._keyboard = Controller()

    def type_text(self, text: str):
        pyperclip.copy(text)
        time.sleep(0.1)
        with self._keyboard.pressed(Key.ctrl):
            self._keyboard.press("v")
            self._keyboard.release("v")
