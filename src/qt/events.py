from PyQt5.QtCore import Qt, QObject, QPoint
from PyQt5.QtWidgets import QWidget, QWidgetAction, QAction, QMenu, QLabel, QDialog
from PyQt5.QtGui import QIcon

from src.qt.ui import Label

class Dialog(QDialog):
    Title: str
    
    def __init__(self, *args):
        super().__init__(None, Qt.WindowCloseButtonHint)

        self.setWindowTitle( self.Title )
        self.setWindowIcon(QIcon("assets/images/icon.png"))

        self.init(*args)

    def init(self, *args):
        pass

class Menu(QMenu):
    Label: str
    Parent: QWidget

    def __init__(self, parent, *args):
        super().__init__(self.Label, parent)
        self.Parent = parent
        self.init(*args)

    def init(self, *args):
        pass

class EmptyAction(QWidgetAction):
    def __init__(self, parent, widget):
        super().__init__(parent)
        self.setDisabled(True)
        self.setDefaultWidget(widget)

class MenuLabel(Label):
    Action: EmptyAction

    def __init__(self, menu, label):
        super().__init__(label)
        self.Action = EmptyAction(menu, self)

class ContextMenu(QMenu):
    Coords: QPoint

    def __init__(self, parent, event):
        super().__init__(parent)
        self.Coords = parent.mapToGlobal(event.pos())

    def addLabel(self, text):
        label = MenuLabel(self, text)
        self.addAction(label.Action)

    def start(self):
        self.exec_(self.Coords)

class Action(QAction):
    Label: str
    Key: str

    def __init__(self, parent, handler=None, label=None):
        if label is None:
            label = self.Label

        if handler is None:
            handler = self.Key

        if type(handler) == str:
            handler = getattr(parent, handler)

        super().__init__(label, parent)
        self.triggered.connect(handler)

class Emitter(QObject):
    def on(self, key, handler, execNow=True):
        if hasattr(self, key + 'Signal'):
            getattr(self, key + 'Signal').connect(handler)
            if execNow:
                if hasattr(self, key):
                    handler( getattr(self, key) )
                else:
                    handler()

    def off(self, key, handler):
        if hasattr(self, key + 'Signal'):
            getattr(self, key + 'Signal').disconnect(handler)
