from typing import Callable
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QLineEdit, QComboBox

from src.qt.base import *
from src.qt.layouts import HBox
from src.qt.toggle import Toggle

class Label(QLabel, Styleable):
    def __init__(self, text=''):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)

class LineEdit(QLineEdit):
    pass

class ComboBox(QComboBox, Styleable):
    pass

class Button(Label):
    Handler: Callable

    def __init__(self, parent, text, handler):
        super().__init__(text)
        self.Handler = handler
        parent.add(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.Handler()

    def setDisabled(self, isDisabled):
        self.setProperty('disabled', isDisabled)
        self.updateStyle()

    def setProcessing(self, isProcessing):
        self.setProperty('processing', isProcessing)
        self.updateStyle()

class Field(HBox):
    Left: QLabel
    Right: QLabel
    
    def __init__(self, parent, left, right, right_name='', right_handler=None):
        super().__init__(parent.GUI)
        self.Left = self.label(left+':')
        self.Right = self.label(right)
        
        if right_name:
            self.Right.setObjectName(right_name)
            
        if right_handler:
            self.Right.mouseDoubleClickEvent = right_handler

        self.addTo(parent)
