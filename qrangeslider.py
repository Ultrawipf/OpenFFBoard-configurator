# Based on https://github.com/introkun/qt-range-slider
from dataclasses import dataclass
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QSizePolicy)
from PyQt6.QtGui import QPainter, QBrush, QColor, QPalette


def _left_thumb_adjuster(value, min_value):
    value = max(value, min_value)

def _right_thumb_adjuster(value, max_value):
    value = min(value, max_value)

@dataclass
class Thumb:
    """Thumb class which holds information about a thumb.
    """
    value: int
    rect: QRect
    pressed: bool

class QtRangeSlider(QWidget):
    """
        QtRangeSlider is a class which implements a slider with 2 thumbs.
        Methods
            * __init__ (self, QWidget parent, left_value, right_value, left_thumb_value=0, right_thumb_value=None)
            * set_left_thumb_value (self, int value):
            * set_right_thumb_value (self, int value):
            * (int) get_left_thumb_value (self):
            * (int) get_right_thumb_value (self):
        Signals
            * left_thumb_value_changed (int)
            * right_thumb_value_changed (int)
    """
    HEIGHT = 21
    WIDTH = 120
    THUMB_WIDTH = 5
    THUMB_HEIGHT = 15
    TRACK_HEIGHT = 2
    FILL_HEIGHT = 10
    TRACK_COLOR = QColor(0xc7, 0xc7, 0xc7,127)
    TRACK_FILL_COLOR = QColor(0x01, 0x81, 0xff,127)
    TRACK_VAL_COLOR = QColor(0x10, 0xff, 0x1f)
    TRACK_PADDING = THUMB_WIDTH // 2 + 2
    TICK_PADDING = 5

    left_thumb_value_changed = pyqtSignal('unsigned long long')
    right_thumb_value_changed = pyqtSignal('unsigned long long')

    def __init__(self, parent, right_value, left_thumb_value=0, right_thumb_value=None):
        super().__init__(parent)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding
        )
        self.setMinimumWidth(self.WIDTH)
        self.setMinimumHeight(self.HEIGHT)

        #self._left_value = left_value
        self._right_value = right_value
        #self._value = 0

        self._left_thumb = Thumb(left_thumb_value, None, False)
        _right_thumb_value = right_thumb_value if right_thumb_value is not None \
            else self._right_value
        if _right_thumb_value < left_thumb_value + 1:
            raise ValueError("Right thumb value is less or equal left thumb value.")
        self._right_thumb = Thumb(_right_thumb_value, None, False)

        self._canvas_width = None
        self._canvas_height = None

        self._ticks_count = 0

        parent_palette = parent.palette()
        self._background_color = parent_palette.color(QPalette.ColorRole.Window)
        self._base_color = parent_palette.color(QPalette.ColorRole.Base)
        self._button_color = parent_palette.color(QPalette.ColorRole.Button)
        self._border_color = parent_palette.color(QPalette.ColorRole.Mid)


    # def setValue(self,val : int):
    #     self._value = val

    def paintEvent(self, unused_e):
        del unused_e
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        #self.__draw_value(self._canvas_width, self._canvas_height, painter)
        self.__draw_track(self._canvas_width, self._canvas_height, painter)
        self.__draw_track_fill(self._canvas_width, self._canvas_height, painter)
        self.__draw_ticks(self._canvas_width, self._canvas_height, painter, self._ticks_count)
        self.__draw_left_thumb(self._canvas_width, self._canvas_height, painter)
        self.__draw_right_thumb(self._canvas_width, self._canvas_height, painter)

        painter.end()

    def __get_track_y_position(self):
        return self._canvas_height // 2 - self.TRACK_HEIGHT // 2

    def __draw_value(self, canvas_width, canvas_height, painter):
        del canvas_height
        brush = QBrush()
        brush.setColor(self.TRACK_VAL_COLOR)
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        available_width = canvas_width - 2 * self.TRACK_PADDING
        x1 = self.TRACK_PADDING#self._left_thumb.value / self._right_value * available_width + self.TRACK_PADDING
        x2 = self._value / self._right_value * available_width + self.TRACK_PADDING
        rect = QRect(round(x1), canvas_height // 2 - self.FILL_HEIGHT // 2, \
            round(x2) - round(x1), self.FILL_HEIGHT)
        painter.fillRect(rect, brush)

    def __draw_track(self, canvas_width, canvas_height, painter):
        del canvas_height
        brush = QBrush()
        brush.setColor(self.TRACK_COLOR)
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        rect = QRect(self.TRACK_PADDING, self.__get_track_y_position(), \
            canvas_width - 2 * self.TRACK_PADDING, self.TRACK_HEIGHT)
        painter.fillRect(rect, brush)

    def __draw_track_fill(self, canvas_width, canvas_height, painter):
        del canvas_height
        brush = QBrush()
        brush.setColor(self.TRACK_FILL_COLOR)
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        available_width = canvas_width - 2 * self.TRACK_PADDING
        x1 = self._left_thumb.value / self._right_value * available_width + self.TRACK_PADDING
        x2 = self._right_thumb.value / self._right_value * available_width + self.TRACK_PADDING
        rect = QRect(round(x1), self.__get_track_y_position(), \
            round(x2) - round(x1), self.TRACK_HEIGHT)
        painter.fillRect(rect, brush)

    # pylint: disable=no-self-use
    def __set_painter_pen_color(self, painter, pen_color):
        pen = painter.pen()
        pen.setColor(pen_color)
        painter.setPen(pen)

    def __draw_thumb(self, x, y, painter):
        brush = QBrush()
        brush.setColor(self._base_color)
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        self.__set_painter_pen_color(painter, self._border_color)

        painter.setBrush(brush)

        thumb_rect = QRect(round(x) - self.THUMB_WIDTH // 2 + self.TRACK_PADDING, \
            y + self.TRACK_HEIGHT // 2 - self.THUMB_HEIGHT // 2, self.THUMB_WIDTH, self.THUMB_HEIGHT)
        painter.drawRect(thumb_rect)
        return thumb_rect

    def __draw_right_thumb(self, canvas_width, canvas_height, painter):
        del canvas_height
        available_width = canvas_width - 2 * self.TRACK_PADDING
        x = self._right_thumb.value / self._right_value * available_width
        y = self.__get_track_y_position()
        self._right_thumb.rect = self.__draw_thumb(x, y, painter)

    def __draw_left_thumb(self, canvas_width, canvas_height, painter):
        del canvas_height
        available_width = canvas_width - 2 * self.TRACK_PADDING
        x = round(self._left_thumb.value / self._right_value * available_width)
        y = self.__get_track_y_position()
        self._left_thumb.rect = self.__draw_thumb(x, y, painter)

    def set_left_thumb_value(self, value):
        if value < 0 or value > self._right_thumb.value - 1:
            return
        if value == self._left_thumb.value:
            # nothing to update
            return
        self._left_thumb.value = value

        self.left_thumb_value_changed.emit(value)
        self.repaint()

    def set_right_thumb_value(self, value):
        if value > self._right_value or value < self._left_thumb.value + 1:
            return
        if value == self._right_thumb.value:
            # nothing to update
            return
        self._right_thumb.value = value

        self.right_thumb_value_changed.emit(value)
        self.repaint()

    # override Qt event
    def mousePressEvent(self, event):

        if self._left_thumb.rect.contains(event.pos().x(), event.pos().y()):
            self._left_thumb.pressed = True
        if self._right_thumb.rect.contains(event.pos().x(), event.pos().y()):
            self._right_thumb.pressed = True
        super().mousePressEvent(event)

    # override Qt event
    def mouseReleaseEvent(self, event):

        self._left_thumb.pressed = False
        self._right_thumb.pressed = False
        super().mouseReleaseEvent(event)

    # pylint: disable=no-self-use
    def __get_thumb_value(self, x, canvas_width, right_value):

        return round(x / canvas_width * right_value)

    # override Qt event
    def mouseMoveEvent(self, event):

        thumb = self._left_thumb if self._left_thumb.pressed else self._right_thumb

        if thumb.pressed:
            if thumb == self._left_thumb:
                value_setter = self.set_left_thumb_value
                value_adjuster = lambda val: _left_thumb_adjuster(val, 0)
            else:
                value_setter = self.set_right_thumb_value
                value_adjuster = lambda val: _right_thumb_adjuster(val, self._right_value)

            new_val = self.__get_thumb_value(event.pos().x(), self._canvas_width, self._right_value)
            value_adjuster(new_val)
            value_changed = new_val != thumb.value
            if value_changed:
                value_setter(new_val)

        super().mouseMoveEvent(event)

    def get_left_thumb_value(self):
        return self._left_thumb.value

    def get_right_thumb_value(self):
        return self._right_thumb.value

    def set_ticks_count(self, count):
        if count < 0:
            raise ValueError("Invalid ticks count.")
        self._ticks_count = count

    def __draw_ticks(self, canvas_width, canvas_height, painter, ticks_count):
        del canvas_height
        if not self._ticks_count:
            return

        self.__set_painter_pen_color(painter, self._border_color)

        tick_step = (canvas_width - 2 * self.TRACK_PADDING) // ticks_count
        y1 = self.__get_track_y_position() - self.TICK_PADDING
        y2 = y1 - self.THUMB_HEIGHT // 2
        for x in range(0, ticks_count + 1):
            x = x * tick_step + self.TRACK_PADDING
            painter.drawLine(x, y1, x, y2)

    def resizeEvent(self, event):
        del event
        self._canvas_width = self.width()
        self._canvas_height = self.height()