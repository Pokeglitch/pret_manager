import sys

from PyQt5.QtCore import Qt, QMargins, QPoint, QRect, QSize
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
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
)

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

class Widget(QWidget):
    def __init__(self, GUI, layout):
        super().__init__()
        self.Parent = None
        self.GUI = GUI
        self.Layout = layout()
        self.setLayout(self.Layout)

    def add(self, widget, *args):
        self.Layout.addWidget(widget, *args)

    def addTo(self, parent, *args):
        self.Parent = parent
        parent.add(self, *args)

    def label(self, text):
        label = QLabel(text)
        self.add(label)
        return label

class Grid(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, QGridLayout)

class Flow(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, FlowLayout)
        
        self.Scroll = QScrollArea()
        self.Scroll.setWidgetResizable(True)
        self.Scroll.setWidget(self)

    def addTo(self, parent, *args):
        self.Parent = parent
        parent.add(self.Scroll, *args)

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

    def addTo(self, parent, *args):
        self.Parent = parent
        parent.add(self.Scroll, *args)

class ListElement(HBox):
    def __init__(self, parent, Name, Source):
        super().__init__(parent.GUI)
        self.Name = Name
        self.Source = Source
        self.Label = self.label(Name)
        self.Data = Source[Name]
        self.addTo(parent)

    def mousePressEvent(self, event):
        self.GUI.Tiles.setActive(self)

class Author(ListElement):
    def __init__(self, *args):
        super().__init__(*args)

    def getData(self):
        return [self.Source[self.Name][title] for title in self.Source[self.Name]]

class Tag(ListElement):
    def __init__(self, *args):
        super().__init__(*args)

    def getData(self):
        return self.Source[self.Name]

class List(VScroll):
    def __init__(self, parent, Class, Source, width):
        super().__init__(parent.GUI)
        self.List = {}
        self.Class = Class
        self.Source = Source
        [Class(self, name, Source) for name in Source]
        self.Layout.addStretch()
        self.addTo(parent, width)

    def add(self, widget, *args):
        self.List[widget.Name] = widget
        super().add(widget, *args)

class Authors(List):
    def __init__(self, parent):
        super().__init__(parent, Author, parent.GUI.Manager.Authors, 2)

class Tags(List):
    def __init__(self, parent):
        super().__init__(parent, Tag, parent.GUI.Manager.Tags, 1)

class Groups(HBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Authors = Authors(self)
        self.Tags = Tags(self)
        self.addTo(GUI.Widget, 25)

class GameQueue(HBox):
    def __init__(self, game):
        super().__init__(game.GUI)
        self.Game = game
        self.label(game.Game.name)
        self.addTo(self.GUI.Queue)

    def mousePressEvent(self, event):
        self.GUI.Panel.setActive(self.Game)

    def update(self):
        self.setVisible(self.Game.Game in self.GUI.Manager.Selection)

class GameTile(VBox):
    def __init__(self, game):
        super().__init__(game.GUI)
        self.Game = game
        self.label(game.Game.title)
        self.addTo(self.GUI.Tiles)

    def mousePressEvent(self, event):
        self.GUI.Panel.setActive(self.Game)

    def update(self):
        self.setVisible( self.GUI.Tiles.contains(self.Game.Game) )

class GamePanel(VBox):
    def __init__(self, game):
        super().__init__(game.GUI)
        self.Game = game
        self.label(game.Game.title)
        self.addTo(self.GUI.Panel, 0, 0)

    def update(self):
        self.setVisible(self.GUI.Panel.Active == self)

class Game:
    def __init__(self, GUI, game):
        self.GUI = GUI
        self.Game = game
        game.GUI = self
        
        self.Queue = GameQueue(self)
        self.Tile = GameTile(self)
        self.Panel = GamePanel(self)

    def update(self):
        self.Queue.update()
        self.Tile.update()
        self.Panel.update()

class Games:
    def __init__(self, GUI):
        self.GUI = GUI
        self.All = [Game(GUI, repo) for repo in GUI.Manager.All]
        self.update()

    def update(self):
        [game.update() for game in self.All]

class Queue(VScroll):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.addTo(GUI.Widget, 15)

class Tiles(Flow):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Active = None
        self.addTo(GUI.Widget, 40)

    def setActive(self, instance):
        if self.Active:
            [game.GUI.Tile.setVisible(False) for game in self.Active.getData()]

        self.Active = instance
        [game.GUI.Tile.setVisible(True) for game in self.Active.getData()]

    def contains(self, game):
        if self.Active:
            return game in self.Active.getData()
        else:
            return False

class Panel(Grid):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Active = None
        self.addTo(GUI.Widget, 20)

    def setActive(self, game):
        if self.Active:
            self.Active.Panel.setVisible(False)
        self.Active = game
        self.Active.Panel.setVisible(True)

class PRET_Manager_GUI(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.Manager = manager
        self.setWindowTitle("pret manager")
        self.Widget = HBox(self)
        self.Groups = Groups(self)
        self.Tiles = Tiles(self)
        self.Panel = Panel(self)
        self.Queue = Queue(self)
        self.Games = Games(self)

        self.setCentralWidget(self.Widget)
        self.show()

def init(manager):
    return QApplication(sys.argv), PRET_Manager_GUI(manager)
