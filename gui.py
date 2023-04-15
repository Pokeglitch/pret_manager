import sys, webbrowser

'''
TODO:
- each list item and tile can have icons for quick add/remove to queue
    - highlight whichever is active

- Each game widget should indicate if it is downloaded or not

- Show when game is being processed

- Show which games have updates

- Favorite/Exclude All

For settings:
- default emulator (or, per game or file type)
- custom tags
- default process actions
- different path for rgbds builds
- default list

Add search filter (use glob on authors tree?)

Groups of Tags
'''

from PyQt5.QtCore import Qt, QThreadPool, QRunnable, QMargins, QPoint, QRect, QSize
from PyQt5.QtWidgets import QApplication, QStyleOption, QStyle, QLabel, QMainWindow, QLayout, QSizePolicy, QVBoxLayout, QGridLayout, QHBoxLayout, QScrollArea, QWidget
from PyQt5.QtGui import QIcon, QPainter

threadpool = QThreadPool()

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
        
        self.Layout.setContentsMargins(0,0,0,0)
        self.Layout.setSpacing(0)

    def paintEvent(self, event):
        opt= QStyleOption()
        painter = QPainter(self)
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        painter.end()

    def updateStyle(self):
        self.style().polish(self)

    def add(self, widget, *args):
        self.Layout.addWidget(widget, *args)

    def addTo(self, parent, *args):
        self.Parent = parent
        parent.add(self, *args)

    def label(self, text='', *args):
        label = QLabel(text)
        self.add(label, *args)
        return label

    def addStretch(self):
        self.Layout.addStretch()

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
    def __init__(self, parent, Name):
        super().__init__(parent.GUI)
        self.Name = Name
        self.Source = parent.Source
        self.Label = self.label(Name)
        self.Data = self.Source[Name]
        self.addTo(parent)

    def setActive(self, value):
        self.setProperty("active",value)
        self.updateStyle()

    def mousePressEvent(self, event):
        self.GUI.Tiles.setActive(self)

class DictList(ListElement):
    def __init__(self, *args):
        super().__init__(*args)

    def getData(self):
        return [self.Source[self.Name][title] for title in self.Source[self.Name]]

class ArrayList(ListElement):
    def __init__(self, *args):
        super().__init__(*args)

    def getData(self):
        return self.Source[self.Name]

class List(VBox):
    def __init__(self, parent, ID, Class, width):
        super().__init__(parent.GUI)

        self.ID = ID[:-1]
        self.List = {}

        self.Label = self.label(ID, 5)
        self.Label.setAlignment(Qt.AlignCenter)
        self.Label.setObjectName("list-header")

        self.ScrollBox = VScroll(parent.GUI)
        self.ScrollBox.addTo(self, 95)

        self.Class = Class
        self.Source = getattr(parent.GUI.Manager, ID)
        [Class(self, name) for name in self.Source]
        self.ScrollBox.Layout.addStretch()

        self.addTo(parent, width)

    def add(self, widget, *args):
        if hasattr(widget,'Name'):
            self.List[widget.Name] = widget
            self.ScrollBox.add(widget, *args)
        else:
            super().add(widget, *args)

class Authors(List):
    def __init__(self, parent):
        super().__init__(parent, "Authors", DictList, 4)

class Tags(List):
    def __init__(self, parent):
        super().__init__(parent, "Tags", ArrayList, 3)

class Lists(List):
    def __init__(self, parent):
        super().__init__(parent, "Lists", ArrayList, 3)

class Groups(HBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Lists = Lists(self)
        self.Authors = Authors(self)
        self.Tags = Tags(self)
        self.addTo(GUI, 15)

class GameQueue(HBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.label(gameGUI.Game.name)
        self.addTo(self.GUI.Queue.ListGUI)

    def mousePressEvent(self, event):
        self.GUI.Panel.setActive(self.GameGUI)

    def update(self):
        self.setVisible(self.GameGUI.Game in self.GUI.Queue.List)

class GameTile(VBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.Name = self.label(gameGUI.Game.name)
        self.Artwork = self.label('<Artwork>')
        self.Title = self.label(gameGUI.Game.title)
        self.Author = self.label(gameGUI.Game.author)
        self.addTo(self.GUI.Tiles.Content)

    def mousePressEvent(self, event):
        self.GUI.Panel.setActive(self.GameGUI)

    def update(self):
        self.setVisible( self.GUI.Tiles.contains(self.GameGUI.Game) )

class Field(HBox):
    def __init__(self, parent, left, right):
        super().__init__(parent.GUI)
        self.Left = self.label(left+':')
        self.Right = self.label(right)
        self.addTo(parent)

class GamePanel(VBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.Artwork = self.label("<Artwork>")
        self.Title = Field(self, 'Title', gameGUI.Game.title)
        self.Author = Field(self, 'Author', gameGUI.Game.author)
        if gameGUI.Game.url:
            self.Website = Field(self, 'Website', 'Github')
            self.Website.Right.mousePressEvent = self.openURL
        self.Tags = Field(self, 'Tags', ','.join(gameGUI.Game.tags))
        self.Builds = Field(self, 'Builds', '\n'.join(gameGUI.Game.builds.keys()))
        # TODO - each specific ROM within each build (expand.collapse)
        # - Can click on ROM to launch in emulator

        # if git repo
        self.Branch = Field(self, 'Branch', '<Change Branch>')
        self.Commit = Field(self, 'Commit', '<Change Commit>')
        self.Make = Field(self, 'Make', '<Specific Make Commands>')
        self.SetRGBDSVersion = Field(self, 'RGBDS', '<Change RGBDS Version>')

        # if IPS
        self.BaseROM = Field(self, 'Base', '<Select Base ROM>')

        self.addTo(self.GUI.Panel.Display, 0, 0)

    def openURL(self, event):
        webbrowser.open(self.GameGUI.Game.url)

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

    def setActive(self, value):
        self.Queue.setProperty("active",value)
        self.Tile.setProperty("active",value)
        self.Queue.updateStyle()
        self.Tile.updateStyle()

    def setProcessing(self, value):
        self.Queue.setProperty("processing",value)
        self.Tile.setProperty("processing",value)
        self.Queue.updateStyle()
        self.Tile.updateStyle()

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

class Queue(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.List = []

        self.Header = HBox(GUI)
        self.Header.setObjectName("header-frame")

        self.HeaderLabel = self.Header.label('Queue')
        self.HeaderLabel.setObjectName("header")
        self.HeaderLabel.setAlignment(Qt.AlignCenter)
        self.Header.addTo(self, 5)

        self.Clear = Button(self.Header, 'Clear', self.clear)
        self.Process = Button(self.Header, 'Process', self.process)
        self.Save = Button(self.Header, 'Save', self.save)

        self.ListContainer = VScroll(GUI)
        self.ListContainer.addTo(self, 95)

        self.ListGUI = VBox(GUI)
        self.ListGUI.addTo(self.ListContainer)
        self.ListContainer.addStretch()
        
        self.addTo(GUI.RightCol, 65)

    def addGame(self, gameGUI):
        if gameGUI not in self.List:
            self.List.append(gameGUI)
            # add again so it appears at bottom of queue
            gameGUI.Queue.addTo(self.ListGUI)
            gameGUI.Queue.setVisible(True)

    def addGames(self, games):
        [self.addGame(game.GUI) for game in games]

    def removeGame(self, gameGUI):
        if gameGUI in self.List:
            self.List.pop( self.List.index(gameGUI) )
            gameGUI.Queue.setVisible(False)

    def removeGames(self, games):
        [self.removeGame(game.GUI) for game in games]

    def clear(self, event):
        self.removeGames([gameGUI.Game for gameGUI in self.List])

    def process(self, event):
        self.GUI.startProcess([gameGUI.Game for gameGUI in self.List])

    def save(self, event):
        pass

class TileContent(Flow):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName('Tiles')
        self.Scroll.setObjectName('Tiles')
        self.Layout.setSpacing(10)
        self.addTo(parent, 95)

class TilesHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")
        self.Type = self.label()
        self.Type.setObjectName("header")
        self.Name = self.label()
        self.Name.setObjectName("header")
        self.AddToQueue = Button(self, 'Add All', parent.addToQueue)
        self.RemoveFromQueue = Button(self, 'Remove All', parent.removeFromQueue)
        self.Process = Button(self, 'Process All', parent.process)
        self.addTo(parent, 5)

    def setText(self, type, name=''):
        self.Type.setText(type)
        self.Name.setText(name)

class Tiles(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Active = None
        self.List = [] # List of Games (not GameGUIs)
        self.Header = TilesHeader(self)
        self.Content = TileContent(self)
        self.addTo(GUI, 25)

    def setActive(self, instance):
        [game.GUI.Tile.setVisible(False) for game in self.List]

        if self.Active:
            self.Active.setActive(False)

        self.Active = None if instance == self.Active else instance

        if self.Active:
            self.Header.setText(self.Active.Parent.ID, self.Active.Name)
            self.List = self.Active.getData()
            self.Active.setActive(True)
        else:
            self.Header.setText('All Games')
            self.List = [game.Game for game in self.GUI.Games.All]

        [game.GUI.Tile.setVisible(True) for game in self.List]

    def addToQueue(self, event):
        self.GUI.Queue.addGames(self.List)

    def removeFromQueue(self, event):
        self.GUI.Queue.removeGames(self.List)

    def process(self, event):
        self.GUI.startProcess([game for game in self.List])

    def contains(self, game):
        if self.Active:
            return game in self.Active.getData()
        else:
            return False

class Button(QLabel):
    def __init__(self, parent, text, click):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.mousePressEvent = click
        parent.add(self)

class ToggleButton(HBox):
    def __init__(self, parent, text, click):
        super().__init__(None)
        self.Label = self.label(text)
        self.Label.setAlignment(Qt.AlignCenter)
        self.mousePressEvent = click
        parent.add(self)

    def setActive(self, value):
        self.setProperty("active",value)
        self.updateStyle()

class PanelHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")

        self.Left = HBox(parent.GUI)
        self.Label = self.Left.label()
        self.Label.setObjectName("header")
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
        self.addTo(GUI, 25)

    def setActive(self, game):
        if self.Active:
            self.Active.setActive(False)
            self.Active.Panel.setVisible(False)

        self.Active = None if game == self.Active else game

        if self.Active:
            self.Active.setActive(True)
            self.Active.Panel.setVisible(True)
            self.Header.setText(self.Active.Game.name)
        else:
            self.Header.setText("Select a Game")

        self.Footer.setVisible(bool(self.Active))
        self.Header.Right.setVisible(bool(self.Active))

    def addToQueue(self, event):
        if self.Active:
            self.GUI.Queue.addGame(self.Active)

    def removeFromQueue(self, event):
        if self.Active:
            self.GUI.Queue.removeGame(self.Active)

    def process(self, event):
        if self.Active:
            self.GUI.startProcess([self.Active.Game])

    def favorite(self, event):
        pass

    def exclude(self, event):
        pass

    def applyPatch(self, event):
        pass

class Process(QRunnable):
    def __init__(self, GUI):
        super().__init__()
        self.GUI = GUI

    def run(self):
        self.GUI.Manager.run()
        self.GUI.endProcess()


class Status(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)

        self.Header = HBox(GUI)
        self.Header.setObjectName("status-header")
        self.HeaderLabel = self.Header.label("Process")
        self.HeaderLabel.setAlignment(Qt.AlignCenter)

        self.ToggleUpdate = ToggleButton(self.Header, 'Update', self.toggleUpdate)
        self.ToggleBuild = ToggleButton(self.Header, 'Build', self.toggleBuild)
        self.ToggleClean = ToggleButton(self.Header, 'Clean', self.toggleClean)
        self.ToggleUpdate.setActive(False)
        self.ToggleBuild.setActive(False)
        self.ToggleClean.setActive(False)

        self.Header.addTo(self, 10)

        self.ContentContainer = VScroll(GUI)
        self.Content = VBox(GUI)
        self.Content.addTo(self.ContentContainer)
        self.ContentContainer.addTo(self, 90)
        self.Content.Label = self.Content.label()
        self.Content.addStretch()

        self.AtMax = True
        self.ContentContainer.Scroll.verticalScrollBar().valueChanged.connect(self.checkAtMax)

        self.ContentContainer.setObjectName("status")

        self.addTo(GUI.RightCol, 35)

    def toggleUpdate(self, event):
        self.GUI.Manager.doUpdate = not self.GUI.Manager.doUpdate
        self.ToggleUpdate.setActive(self.GUI.Manager.doUpdate)

    def toggleBuild(self, event):
        if self.GUI.Manager.doBuild == None:
            self.GUI.Manager.doBuild = []
        else:
            self.GUI.Manager.doBuild = None
        self.ToggleBuild.setActive(self.GUI.Manager.doBuild != None)

    def toggleClean(self, event):
        self.GUI.Manager.doClean = not self.GUI.Manager.doClean
        self.ToggleClean.setActive(self.GUI.Manager.doClean)

    def checkAtMax(self, event):
        self.AtMax = self.ContentContainer.Scroll.verticalScrollBar().value() == self.ContentContainer.Scroll.verticalScrollBar().maximum()

    def addStatus(self, msg):
        self.Content.Label.setText(self.Content.Label.text() + msg + '\n')
        if self.AtMax:
            self.ContentContainer.Scroll.verticalScrollBar().setValue(self.ContentContainer.Scroll.verticalScrollBar().maximum())

class MainContents(HBox):
    def __init__(self, window):
        super().__init__(self)
        self.Window = window
        self.Manager = window.Manager
        self.Groups = Groups(self)
        self.Tiles = Tiles(self)
        self.Panel = Panel(self)

        self.RightCol = VBox(self)
        self.RightCol.addTo(self, 20)

        self.Queue = Queue(self)
        self.Status = Status(self)

        self.Games = Games(self)
        self.Tiles.setActive(None)
        self.addTo(window.Widget)

    def startProcess(self, games):
        if not self.Window.Process:
            self.GUI.Manager.add_to_selection(games)
            self.Window.Process = Process(self)
            threadpool.start(self.Window.Process)

    def endProcess(self):
        self.Window.Process = None

class PRET_Manager_GUI(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.Process = None
        self.Manager = manager
        self.setWindowTitle("pret manager")
        #self.setWindowIcon(QIcon('./assets/icon.png'))
        self.Widget = VBox(self)
        self.Content = MainContents(self)
        self.setCentralWidget(self.Widget)
        
        with open('./assets/style.qss') as f:
            self.setStyleSheet(f.read())

        self.show()

    def addStatus(self, msg):
        self.Content.Status.addStatus(msg)

def init(manager):
    return QApplication(sys.argv), PRET_Manager_GUI(manager)
