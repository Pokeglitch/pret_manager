from typing import Callable
from PyQt5.QtCore import Qt, QPoint, QMargins, QPoint, QRect, QSize
from PyQt5.QtWidgets import QStyleOption, QStyle, QLabel, QLayout, QSizePolicy, QVBoxLayout, QGridLayout, QHBoxLayout, QScrollArea, QWidget
from PyQt5.QtGui import QPainter

from src.qt.base import *

# https://doc.qt.io/qtforpython/examples/example_widgets_layouts_flowlayout.html
class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

class Scroll():
    Scroll: QScrollArea

    def __init__(self, *args):
        super().__init__(*args) # forwards arguments up to the Widget class

        self.Scroll = QScrollArea()
        self.Scroll.setWidgetResizable(True)
        self.Scroll.setWidget(self)

        self.Wrapper = self.Scroll

class Widget(QWidget, Styleable):
    LayoutClass: Callable
    Wrapper: QWidget

    def __init__(self, GUI):
        super().__init__()
        self.Wrapper = self

        self.Parent = None
        self.GUI = GUI
        self.Layout = self.LayoutClass()
        self.setLayout(self.Layout)
        
        self.Layout.setContentsMargins(0,0,0,0)
        self.Layout.setSpacing(0)

    def paintEvent(self, event):
        opt= QStyleOption()
        painter = QPainter(self)
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        painter.end()

    def add(self, widget, *args):
        self.Layout.addWidget(widget, *args)

    def addTo(self, parent, *args):
        self.Parent = parent
        if parent:
            parent.add(self.Wrapper, *args)
        else:
            self.setParent(None)

    def label(self, text='', *args):
        label = QLabel(text)
        self.add(label, *args)
        return label

    def addStretch(self):
        self.Layout.addStretch()

class Grid(Widget):
    LayoutClass = QGridLayout

class HBox(Widget):
    LayoutClass = QHBoxLayout

class VBox(Widget):
    LayoutClass = QVBoxLayout

class Flow(Scroll, Widget):
    LayoutClass = FlowLayout

class VScroll(Scroll, VBox):
    pass

class Center():
    def __init__(self, child):
        super().__init__(child.GUI if hasattr(child, "GUI") else None)

        self.addStretch()
        self.add(child)
        self.addStretch()

class HCenter(Center, HBox):
    pass

class VCenter(Center, VBox):
    pass

class VHCenter(VCenter):
    def __init__(self, child):
        super().__init__( HCenter(child) )

class HVCenter(HCenter):
    def __init__(self, child):
        super().__init__( VCenter(child) )
