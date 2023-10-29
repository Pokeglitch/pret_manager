from typing import Callable
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSlider, QLabel

from src.qt.base import *
from src.qt.layouts import Grid, HBox

class ToggleSlider(QSlider, Styleable):
    def __init__(self, parent):
        super().__init__(Qt.Horizontal)
        self.setMinimum(0)
        self.setMaximum(1)
        self.valueChanged.connect(parent.setActive)

        parent.add(self, 1, 1)

    def setActive(self, value):
        self.setProperty("active", value)
        self.updateStyle()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setValue(1 - self.sliderPosition())

class ToggleBG(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.addTo(parent, 1, 1)

    def setActive(self, value):
        self.setProperty("active", value)
        self.updateStyle()
        
class ToggleWidget(Grid):
    BG: ToggleBG
    Slider: ToggleSlider
    Handler: Callable | None

    def __init__(self, parent, initialValue, handler):
        super().__init__(parent.GUI)

        self.Handler = None
        self.BG = ToggleBG(self)
        self.Slider = ToggleSlider(self)
        self.Slider.setValue(int(initialValue))
        self.Handler = handler

        self.addTo(parent)

    def setActive(self, value):
        value = bool(value)

        self.BG.setActive(value)
        self.Slider.setActive(value)

        if self.Handler:
            self.Handler(value)

class Toggle(HBox):
    Name: str
    Label: QLabel
    Toggle: ToggleWidget
    
    def __init__(self, parent, name, initialValue, handler=None):
        super().__init__(parent.GUI)
        self.Name = name
        self.Label = self.label(name)
        self.Toggle = ToggleWidget(self, initialValue, handler)

        self.addTo(parent)

    def set(self, value):
        self.Toggle.Slider.setValue( int(value) )

    def value(self):
        return self.Toggle.Slider.value()
