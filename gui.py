import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFontComboBox,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
)

class Widget(QWidget):
    def __init__(self, GUI, layout):
        super().__init__()
        self.Parent = None
        self.GUI = GUI
        self.Layout = layout()
        self.setLayout(self.Layout)

    def add(self, widget):
        self.Layout.addWidget(widget)

    def addTo(self, parent):
        self.Parent = parent
        parent.add(self)

    def label(self, text):
        label = QLabel(text)
        self.add(label)
        return label

class HBox(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, QHBoxLayout)

class VBox(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, QVBoxLayout)

class VScroll(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        
        self.Scroll = QScrollArea()
        self.Scroll.setWidgetResizable(True)
        self.Scroll.setWidget(self)

    def addTo(self, parent):
        self.Parent = parent
        parent.add(self.Scroll)

class ListElement(HBox):
    def __init__(self, parent, name):
        super().__init__(parent.GUI)
        self.Name = name
        self.Label = self.label(name)
        self.addTo(parent)

class Author(ListElement):
    def __init__(self, *args):
        super().__init__(*args)

class Tag(ListElement):
    def __init__(self, *args):
        super().__init__(*args)

class List(VScroll):
    def __init__(self, parent, Class, Source):
        super().__init__(parent.GUI)
        self.List = {}
        self.Class = Class
        self.Source = Source
        [Class(self, name) for name in Source]

        self.addTo(parent)

    def add(self, widget):
        self.List[widget.Name] = widget
        super().add(widget)

class Authors(List):
    def __init__(self, parent):
        super().__init__(parent, Author, parent.GUI.Manager.Authors)

class Tags(List):
    def __init__(self, parent):
        super().__init__(parent, Tag, parent.GUI.Manager.Tags)

class Groups(HBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Authors = Authors(self)
        self.Tags = Tags(self)

        self.addTo(GUI.Widget)

class PRET_Manager_GUI(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.Manager = manager
        self.setWindowTitle("pret manager")
        self.Widget = HBox(self)
        self.Groups = Groups(self)

        self.setCentralWidget(self.Widget)
        self.show()

def init(manager):
    return QApplication(sys.argv), PRET_Manager_GUI(manager)
