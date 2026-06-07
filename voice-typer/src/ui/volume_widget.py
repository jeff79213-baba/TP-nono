import math
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QTimer, QRect


class VolumeWidget(QWidget):
    BAR_COUNT = 48
    BAR_WIDTH = 6
    BAR_GAP = 3
    MAX_HEIGHT = 140
    MIN_HEIGHT = 2
    SMOOTHING = 0.3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        width = self.BAR_COUNT * (self.BAR_WIDTH + self.BAR_GAP) + self.BAR_GAP
        self.setFixedSize(width, self.MAX_HEIGHT + 40)

        screen = parent.screen() if parent else None
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - width) // 2
            y = geo.y() + geo.height() - self.height() - 60
            self.move(x, y)
        else:
            self.move(0, 0)

        self._levels = np.zeros(self.BAR_COUNT, dtype=np.float32)
        self._target_levels = np.zeros(self.BAR_COUNT, dtype=np.float32)
        self._current_volume = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.setInterval(30)

    def showEvent(self, event):
        super().showEvent(event)
        self._levels.fill(0)
        self._target_levels.fill(0)
        self._current_volume = 0.0
        self._timer.start()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def set_volume(self, volume: float):
        self._current_volume = min(volume * 10.0, 1.0)

    def _tick(self):
        target = self._current_volume
        spread = max(int(target * self.BAR_COUNT * 1.5), 1)

        for i in range(self.BAR_COUNT):
            pos = abs(i - self.BAR_COUNT // 2) / (self.BAR_COUNT // 2)
            falloff = max(0.0, 1.0 - pos * 1.8)
            t = target * falloff * (1.0 + 0.3 * math.sin(i * 0.5))
            t = max(0.0, min(t, 1.0))
            self._target_levels[i] = t
            self._levels[i] += (self._target_levels[i] - self._levels[i]) * self.SMOOTHING

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h - 20

        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(self.BAR_COUNT):
            level = self._levels[i]
            bar_h = self.MIN_HEIGHT + level * self.MAX_HEIGHT
            x = i * (self.BAR_WIDTH + self.BAR_GAP) + self.BAR_GAP
            y = cy - bar_h

            alpha = int(160 + 95 * level)
            if level > 0.6:
                color = QColor(50, 210, 80, alpha)
            elif level > 0.3:
                color = QColor(50, 150, 210, alpha)
            else:
                color = QColor(90, 110, 200, alpha)

            painter.setBrush(QBrush(color))
            rect = QRect(int(x), int(y), self.BAR_WIDTH, int(bar_h))
            painter.drawRoundedRect(rect, 2, 2)
