import sys, webbrowser

'''
TODO:
- each list item and tile can have icons for quick add/remove to queue
    - highlight whichever is active

- Status message should be the self.print('', True) messages
'''

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

    def label(self, text='', *args):
        label = QLabel(text)
        self.add(label, *args)
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
        self.addTo(GUI, 25)

class GameQueue(HBox):
    def __init__(self, game):
        super().__init__(game.GUI)
        self.Game = game
        self.label(game.Game.name)
        self.addTo(self.GUI.Queue.List)

    def mousePressEvent(self, event):
        self.GUI.Panel.setActive(self.Game)

    def update(self):
        self.setVisible(self.Game.Game in self.GUI.Queue.List.List)

class GameTile(VBox):
    def __init__(self, game):
        super().__init__(game.GUI)
        self.Game = game
        self.Name = self.label(game.Game.name)
        self.Artwork = self.label('<Artwork>')
        self.Title = self.label(game.Game.title)
        self.Author = self.label(game.Game.author)
        self.addTo(self.GUI.Tiles.Content)

    def mousePressEvent(self, event):
        self.GUI.Panel.setActive(self.Game)

    def update(self):
        self.setVisible( self.GUI.Tiles.contains(self.Game.Game) )

class Field(HBox):
    def __init__(self, parent, left, right):
        super().__init__(parent.GUI)
        self.Left = self.label(left+':')
        self.Right = self.label(right)
        self.addTo(parent)

class GamePanel(VBox):
    def __init__(self, game):
        super().__init__(game.GUI)
        self.Game = game
        self.Artwork = self.label("<Artwork>")
        self.Title = Field(self, 'Title', game.Game.title)
        self.Author = Field(self, 'Author', game.Game.author)
        if game.Game.url:
            self.Website = Field(self, 'Website', 'Github')
            self.Website.Right.mousePressEvent = self.openURL
        self.Tags = Field(self, 'Tags', ','.join(game.Game.tags))
        self.Builds = Field(self, 'Builds', '\n'.join(game.Game.builds.keys()))
        # TODO - each specific ROM within each build (expand.collapse)
        # - Can clean on ROM to launch in emulator

        # if git repo
        self.Branch = Field(self, 'Branch', '<Change Branch>')
        self.Commit = Field(self, 'Commit', '<Change Commit>')
        self.Make = Field(self, 'Make', '<Specific Make Commands>')
        self.SetRGBDSVersion = Field(self, 'RGBDS', '<Change RGBDS Version>')

        # if IPS
        self.BaseROM = Field(self, 'Base', '<Selection Base ROM>')

        self.addTo(self.GUI.Panel.Display, 0, 0)

    def openURL(self, event):
        webbrowser.open(self.Game.Game.url)

    def update(self):
        self.setVisible(self.GUI.Panel.Active == self)

class Game:
    def __init__(self, GUI, game):
        self.GUI = GUI
        self.Game = game
        game.GUI = self

        # TODO
        self.isIPS = False
        self.isGit = True
        
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

class QueueList(VScroll):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.List = []
        self.addTo(parent, 80)

    def addGame(self, game):
        if game not in self.List:
            self.List.append(game)
            game.Queue.setVisible(True)
            self.GUI.Manager.add_to_selection([game.Game])

    def addGames(self, games):
        [self.addGame(game.GUI) for game in games]

    def removeGame(self, game):
        if game in self.List:
            self.List.pop( self.List.index(game) )
            game.Queue.setVisible(False)
            self.GUI.Manager.remove_from_selection([game.Game])

    def removeGames(self, games):
        [self.removeGame(game.GUI) for game in games]

    def clear(self, event):
        self.removeGames([game.Game for game in self.List])

    def process(self, event):
        pass
    
    def save(self, event):
        pass
    
    def invert(self, event):
        pass

class QueueHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.addTo(parent, 10)
        self.label('Queue')

class QueueFooter(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Clear = Button(self, 'Clear', parent.List.clear)
        self.Process = Button(self, 'Process', parent.List.process)
        self.Invert = Button(self, 'Invert', parent.List.invert)
        self.Save = Button(self, 'Save', parent.List.save)
        self.addTo(parent, 10)

class Queue(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = QueueHeader(self)
        self.List = QueueList(self)
        self.Footer = QueueFooter(self)
        self.addTo(GUI, 15)

class TileContent(Flow):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.addTo(parent, 80)

class TilesHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Label = self.label()
        self.addTo(parent, 10)

    def setText(self, text):
        self.Label.setText(text)

class TilesFooter(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)

        self.AddToQueue = Button(self, 'Add All', parent.addToQueue)
        self.RemoveFromQueue = Button(self, 'Remove All', parent.removeFromQueue)
        self.Process = Button(self, 'Process All', parent.process)
        self.addTo(parent, 10)

class Tiles(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Active = None
        self.List = []
        self.Header = TilesHeader(self)
        self.Content = TileContent(self)
        self.Footer = TilesFooter(self)
        self.addTo(GUI, 40)

    def setActive(self, instance):
        [game.GUI.Tile.setVisible(False) for game in self.List]

        self.Active = None if instance == self.Active else instance

        if self.Active:
            self.Header.setText(self.Active.Name)
            self.List = self.Active.getData()
        else:
            self.Header.setText('All Games')
            self.List = [game.Game for game in self.GUI.Games.All]

        [game.GUI.Tile.setVisible(True) for game in self.List]

    def addToQueue(self, event):
        self.GUI.Queue.List.addGames(self.List)

    def removeFromQueue(self, event):
        self.GUI.Queue.List.removeGames(self.List)

    def process(self, event):
        pass

    def contains(self, game):
        if self.Active:
            return game in self.Active.getData()
        else:
            return False

class Button(QLabel):
    def __init__(self, parent, text, click):
        super().__init__(text)

        self.mousePressEvent = click
        parent.add(self)

class PanelHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Left = HBox(parent.GUI)
        self.Label = self.Left.label()
        self.Left.addTo(self)

        self.Right = HBox(parent.GUI)
        self.Favorite = Button(self.Right, 'Favorite', parent.favorite)
        self.Exclude = Button(self.Right, 'Exclude', parent.exclude)
        self.Right.addTo(self)

        self.addTo(parent, 10)

    def setText(self, text):
        self.Label.setText(text)

class PanelFooter(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.AddToQueue = Button(self, 'Add', parent.addToQueue)
        self.RemoveFromQueue = Button(self, 'Remove', parent.removeFromQueue)
        self.Process = Button(self, 'Process', parent.process)
        self.addTo(parent, 10)

class Panel(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = PanelHeader(self)

        self.Display = Grid(GUI)
        self.Display.addTo(self, 80)
        
        self.Footer = PanelFooter(self)

        self.Active = None
        self.setActive(None)
        self.addTo(GUI, 20)

    def setActive(self, game):
        if self.Active:
            self.Active.Panel.setVisible(False)
        self.Active = None if game == self.Active else game
        if self.Active:
            self.Active.Panel.setVisible(True)
            self.Header.setText(self.Active.Game.name)
        else:
            self.Header.setText("Select a Game")

        self.Footer.setVisible(bool(self.Active))
        self.Header.Right.setVisible(bool(self.Active))

    def addToQueue(self, event):
        if self.Active:
            self.GUI.Queue.List.addGame(self.Active)

    def removeFromQueue(self, event):
        if self.Active:
            self.GUI.Queue.List.removeGame(self.Active)

    def process(self, event):
        pass

    def favorite(self, event):
        pass

    def exclude(self, event):
        pass

    def applyPatch(self, event):
        pass


class MainHeader(HBox):
    def __init__(self, window):
        super().__init__(self)
        self.Window = window
        self.Manager = window.Manager

        self.Left = HBox(self)
        self.CheckForUpdates = Button(self.Left, 'Check for Updates', self.checkForUpdates)
        self.Settings = Button(self.Left, 'Settings', self.accessSettings)
        self.Left.addTo(self)

        self.Right = HBox(self)
        self.Right.label("Process Actions:")
        self.ToggleUpdate = Button(self.Right, 'Update', self.toggleUpdate)
        self.ToggleBuild = Button(self.Right, 'Build', self.toggleBuild)
        self.ToggleClean = Button(self.Right, 'Clean', self.toggleClean)
        self.Right.addTo(self)

        self.addTo(window.Widget, 5)

    def accessSettings(self, event):
        pass
    
    def checkForUpdates(self, event):
        pass

    def toggleUpdate(self, event):
        pass

    def toggleBuild(self, event):
        pass

    def toggleClean(self, event):
        pass


class MainContents(HBox):
    def __init__(self, window):
        super().__init__(self)
        self.Window = window
        self.Manager = window.Manager
        self.Groups = Groups(self)
        self.Tiles = Tiles(self)
        self.Panel = Panel(self)
        self.Queue = Queue(self)
        self.Games = Games(self)
        self.Tiles.setActive(None)
        self.addTo(window.Widget, 90)

class MainFooter(HBox):
    def __init__(self, window):
        super().__init__(self)
        self.Window = window
        self.Manager = window.Manager
        self.label("Status:",5)
        self.Status = self.label('',95)
        self.addTo(window.Widget, 5)

class PRET_Manager_GUI(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.Manager = manager
        self.setWindowTitle("pret manager")
        self.Widget = VBox(self)
        self.Header = MainHeader(self)
        self.Content = MainContents(self)
        self.Footer = MainFooter(self)
        self.setCentralWidget(self.Widget)
        self.show()

def init(manager):
    return QApplication(sys.argv), PRET_Manager_GUI(manager)
