import sys, webbrowser, json, re

'''
TODO:

- build should have subdirectorie for branch

- Display in log when process is successful or failed

- Add releases to panel
- finish rgbds dropdowns

- click on author to go to their github
-- instead of separate website link, have the 'title' be link to github

- meta data for each game about branches, successful/failed commit attempts, etc

- Disable all process buttons when process is active
- Disable save buttons when queue/filter is empty

Filter:
- Add title text for Filter
- Update Filter when game is added/removed to List
- Show number of items in filter
- When no filters, show All
- Save filter separately from list
- Instead of the buttons at bottom:
-- Have a dropdown which includes all Queue (default), all lists + New
--- Have buttons for: Add to/Remove From/Toggle In
- (True for Game Panel as well, though Fav/Exclude are also quick clicks)

Lists:
- show in Tile, Panel if in favorite/excluded
- Way to load a list, delete a list
- Add lists as option to CLI
- show size of each list next to name

- Detect if downloaded/missing, up to date/out of date
-- Add to corresponding list
-- Show in Panel, Tile

Group/Tile/Queue Sorting:
- date of last update, alphabet, etc
---------
Finish Game Panel
- Show when game is in queue (just use a single button and change the text...)
- show when game is being processed (disable the process button?)

- make tags individual widgets
-- click Tag display in Tiles panel (?)
--- or, treat it as if the 'tag' in the catalog is clicked
--- Way to add extra tags?

Way to copy selected builds to another location
---------
Extra functionality:
- And invert filter (for all tiles, for easy 'excluding')
- Add Search Filter (can use glob patterns?)

Way to create/handle Groups of Tags (i.e. Gen1, Gen2, TCG)
- tag can be a list, or an object
-- if object, the sub tags will be the exact same array at the real tag
--- can have nested subtags

New column:
- RGBDS panel ?
-Way to check if this program has updates/apply update
-Way to Modify Settings:
    - default emulator (or, per game or file type)
    - custom tags
    - default process actions
    - different path for rgbds builds
    - default List to display

IPS classes and applying

Option to change commit to build
Option for specific Make commands to build
- Need to parse makefile...

Option to build multiple branches within a single 'update'
Associate Authors with a Team
'''

from PyQt5.QtCore import Qt, pyqtSignal, QObject, QUrl, QThreadPool, QRunnable, QMargins, QPoint, QRect, QSize
from PyQt5.QtWidgets import QComboBox, QTreeWidgetItem, QFileDialog, QTreeWidget, QApplication, QStyleOption, QStyle, QLabel, QMainWindow, QLayout, QSizePolicy, QVBoxLayout, QGridLayout, QHBoxLayout, QScrollArea, QWidget
from PyQt5.QtGui import QDesktopServices, QIcon, QPainter

threadpool = QThreadPool()

def listToDict(list):
    data = {}
    for game in list:
        if game.author in data:
            data[game.author].append(game.title)
        else:
            data[game.author] = [game.title]
    return data

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

class CatalogEntryGUI(HBox):
    def __init__(self, data):
        parent = data.Catalog.GUI
        super().__init__(parent.GUI)
        self.Data = data
        self.Name = data.Name
        self.Label = self.label(data.Name)
        self.Mode = None
        self.addTo(parent)

    def getData(self):
        return self.Data.GameList

    def setMode(self, mode):
        self.Mode = mode
        self.setProperty("mode",mode)
        self.updateStyle()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            mode = self.Data.Catalog.Catalogs.GUI.Mode
            if mode == self.Mode:
                self.GUI.Tiles.remove(self)
                self.setMode(None)
            else:
                getattr(self.GUI.Tiles,'add' + mode.upper())(self)
                self.setMode(mode)
        elif event.button() == Qt.RightButton:
            self.GUI.Queue.addGames(self.getData())

class CatalogGUI(VBox):
    def __init__(self, data):
        parent = data.Catalogs.GUI
        self.Data = data
        ID = data.Name
        super().__init__(parent.GUI)

        self.ID = ID[:-1]
        self.List = {}

        self.Label = self.label(ID, 5)
        self.Label.setAlignment(Qt.AlignCenter)
        self.Label.setObjectName("list-header")

        self.ListContainer = VScroll(parent.GUI)
        self.ListContainer.addTo(self)

        self.ListGUI = VBox(parent.GUI)
        self.ListGUI.addTo(self.ListContainer)
        self.ListContainer.addStretch()

        self.addTo(parent.Body)

    def addElement(self, name):
        self.Class(self, name)

    def add(self, widget, *args):
        if hasattr(widget,'Name'):
            self.List[widget.Name] = widget
            self.ListGUI.add(widget, *args)
        else:
            super().add(widget, *args)

class CatalogsToggleButton(ToggleButton):
    def __init__(self, parent, mode):
        super().__init__(parent, mode, lambda e: parent.Catalogs.setMode(mode))
        self.setProperty('active',False)

class CatalogsFooter(HBox):
    def __init__(self, catalogs):
        super().__init__(catalogs.GUI)
        self.setObjectName('footer')
        self.Catalogs = catalogs
        self.New = CatalogsToggleButton(self, 'New')
        self.Or = CatalogsToggleButton(self, 'Or')
        self.And = CatalogsToggleButton(self, 'And')
        self.Not = CatalogsToggleButton(self, 'Not')
        self.addTo(catalogs)

class CatalogsGUI(VBox):
    def __init__(self, data):
        self.Data = data
        GUI = data.Manager.GUI.Content
        GUI.Catalogs = self

        super().__init__(GUI)
        self.Mode = None
        self.Body = HBox(GUI)
        self.Body.addTo(self)

        self.Footer = CatalogsFooter(self)
        self.setMode('New')
        
        self.addTo(GUI.Col1, 20)

    def setMode(self, mode):
        if self.Mode:
            getattr(self.Footer, self.Mode).setActive(False)
        
        self.Mode = mode
        getattr(self.Footer, mode).setActive(True)

class GameQueue(HBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.label(gameGUI.Game.name)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Panel.setActive(self.GameGUI)
        elif event.button() == Qt.RightButton:
            self.GUI.Queue.removeGame(self.GameGUI)

class GameTile(VBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.setObjectName("Tile")
        self.GameGUI = gameGUI
        self.Name = self.label(gameGUI.Game.name)
        self.Artwork = self.label('<Artwork>')
        self.Title = self.label(gameGUI.Game.title)
        self.Author = self.label(gameGUI.Game.author)
        self.isQueued = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Panel.setActive(self.GameGUI)
        elif event.button() == Qt.RightButton:
            if self.isQueued:
                self.GUI.Queue.removeGame(self.GameGUI)
            else:
                self.GUI.Queue.addGame(self.GameGUI)

class Field(HBox):
    def __init__(self, parent, left, right):
        super().__init__(parent.GUI)
        self.Left = self.label(left+':')
        self.Right = self.label(right)
        self.addTo(parent)

class TagsGUI(HBox):
    def __init__(self, parent, tags):
        super().__init__(parent.GUI)
        self.setObjectName('PanelTags')
        self.addTo(parent)
        self.addStretch()
        self.Tags = [TagGUI(self, tag) for tag in tags]
        self.addStretch()

class TagGUI(HBox):
    def __init__(self, parent, name):
        super().__init__(parent.GUI)
        self.setObjectName('Tag')
        self.Label = self.label(name)
        self.Label.setAlignment(Qt.AlignCenter)
        self.addTo(parent)

class GamePanelArtwork(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Label = self.label("<Artwork>")
        self.Label.setAlignment(Qt.AlignCenter)

        self.Container = HBox(self.GUI)
        self.Container.addTo(parent)
        self.addTo(self.Container)

class GamePanel(VBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.Artwork = GamePanelArtwork(self)
        self.Tags = TagsGUI(self, gameGUI.Game.tags)
        

        # if git repo
        self.GitOptions = VBox(self.GUI)
        self.GitOptions.addTo(self)

        self.Repository = Field(self.GitOptions, 'Repository', gameGUI.Game.title)
        self.Repository.Right.setObjectName('url')
        self.Repository.Right.mouseDoubleClickEvent = self.openRepositoryURL

        self.Author = Field(self.GitOptions, 'Author', gameGUI.Game.author)
        self.Author.Right.setObjectName('url')
        self.Author.Right.mouseDoubleClickEvent = self.openAuthorURL

        self.Branch = HBox(self.GUI)
        self.Branch.label("Branch:")
        self.BranchComboBox = QComboBox()
        self.ignoreComboboxChanges = False
        self.BranchComboBox.currentTextChanged.connect(self.handleBranchSelected)

        self.Branch.add(self.BranchComboBox)
        self.Branch.addTo(self.GitOptions)

        self.Commit = Field(self.GitOptions, 'Commit', '-')
        self.LastUpdate = Field(self.GitOptions, 'Last Update', '-')

        self.SetRGBDSVersion = HBox(self.GUI)
        self.SetRGBDSVersion.label("RGBDS:")
        self.RGBDSComboBox = QComboBox()
        
        items = ["None"]
        default_index = 0
        
        for version in reversed(list(self.GameGUI.Game.manager.RGBDS.releases.keys())):
            version = version[1:]
            if version == self.GameGUI.Game.rgbds:
                version += ' *'
                if not default_index:
                    default_index = len(items)
            # Custom takes priority
            if version == self.GameGUI.Game.RGBDS:
                default_index = len(items)

            items.append(version)

        self.RGBDSComboBox.addItems(items)
        self.RGBDSComboBox.setCurrentIndex(default_index)

        self.RGBDSComboBox.currentTextChanged.connect(self.handleRGBDSSelected)
        self.SetRGBDSVersion.add(self.RGBDSComboBox)
        self.SetRGBDSVersion.addTo(self.GitOptions)

        self.updateBranchDetails()
        
        self.Trees = VBox(self.GUI)
        self.Trees.addTo(self)

        self.Builds = VBox(self.GUI)
        self.Builds.addTo(self.Trees, 1)
        self.BuildTree = QTreeWidget()
        self.BuildTree.header().setStretchLastSection(True)
        self.BuildTree.header().hide()
        self.BuildTree.setIndentation(10)
        self.Builds.add(self.BuildTree)
        self.BuildTree.itemDoubleClicked.connect(lambda e: hasattr(e,"Path") and QDesktopServices.openUrl(e.Path))
        self.drawBuilds()

        self.Releases = VBox(self.GUI)
        self.Releases.addTo(self.Trees, 1)
        self.ReleaseTree = QTreeWidget()
        self.ReleaseTree.header().setStretchLastSection(True)
        self.ReleaseTree.header().hide()
        self.ReleaseTree.setIndentation(10)
        self.Releases.add(self.ReleaseTree)
        self.ReleaseTree.itemDoubleClicked.connect(lambda e: hasattr(e,"Path") and QDesktopServices.openUrl(e.Path))
        self.drawReleases()

        # if IPS
        self.IPSOptions = VBox(self.GUI)
        self.BaseROM = Field(self.IPSOptions, 'Base', '<Select Base ROM>')
        #self.IPSOptions.addTo(self)

        #self.addStretch()

    def drawReleases(self):
        self.ReleaseTree.clear()
        releasesItem = QTreeWidgetItem(self.ReleaseTree)
        releasesItem.setText(0, "Releases:")
        releasesItem.setExpanded(True)

        if self.GameGUI.Game.releases.keys():
            releasesItem.Path = QUrl.fromLocalFile(self.GameGUI.Game.path['releases'])

            for releaseName, roms in self.GameGUI.Game.releases.items():
                releaseItem = QTreeWidgetItem(releasesItem)
                releaseItem.setText(0, re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', releaseName).group(1))
                releaseItem.Path = QUrl.fromLocalFile(self.GameGUI.Game.path['releases'] + releaseName)

                for romName, path in roms.items():
                    romItem = QTreeWidgetItem(releaseItem)
                    romItem.setText(0, romName)
                    romItem.Path = QUrl.fromLocalFile(str(path))
        else:
            noneItem = QTreeWidgetItem(releasesItem)
            noneItem.setText(0, "None")

    def drawBuilds(self):
        self.BuildTree.clear()

        buildsItem = QTreeWidgetItem(self.BuildTree)
        buildsItem.setText(0, "Builds:")
        buildsItem.setExpanded(True)
        
        if self.GameGUI.Game.builds.keys():
            buildsItem.Path = QUrl.fromLocalFile(self.GameGUI.Game.path['builds'])

            for branchName, branchBuilds in self.GameGUI.Game.builds.items():
                branchItem = QTreeWidgetItem(buildsItem)
                branchItem.setText(0, branchName)
                branchItem.Path = QUrl.fromLocalFile(self.GameGUI.Game.path['builds'] + branchName)

                for buildName, roms in branchBuilds.items():
                    buildItem = QTreeWidgetItem(branchItem)
                    buildItem.setText(0, buildName)
                    buildItem.Path = QUrl.fromLocalFile(self.GameGUI.Game.path['builds'] + branchName + '/' + buildName)

                    for romName, path in roms.items():
                        romItem = QTreeWidgetItem(buildItem)
                        romItem.setText(0, romName)
                        romItem.Path = QUrl.fromLocalFile(str(path))
        else:
            noneItem = QTreeWidgetItem(buildsItem)
            noneItem.setText(0, "None")

    def openRepositoryURL(self, event):
        webbrowser.open(self.GameGUI.Game.url)

    def openAuthorURL(self, event):
        webbrowser.open(self.GameGUI.Game.author_url)
    
    def updateBranchCommitDate(self):
        if self.GameGUI.Game.CurrentBranch:
            data = self.GameGUI.Game.Branches[self.GameGUI.Game.CurrentBranch]
            self.Commit.Right.setText(data['LastCommit'][:8])
            self.LastUpdate.Right.setText(data['LastUpdate'][:19])
        else:
            self.Commit.Right.setText('-')
            self.LastUpdate.Right.setText('-')

    def updateBranchDetails(self):
        self.updateBranchCommitDate()

        self.ignoreComboboxChanges = True

        self.BranchComboBox.clear()
        self.BranchComboBox.addItems(self.GameGUI.Game.Branches.keys())

        if self.GameGUI.Game.CurrentBranch:
            self.BranchComboBox.setCurrentText(self.GameGUI.Game.CurrentBranch)

        self.ignoreComboboxChanges = False
        
    def handleBranchSelected(self, branch):
        if not self.ignoreComboboxChanges and branch != self.GameGUI.Game.CurrentBranch:
            # todo - should be in separate process
            self.GameGUI.Game.set_branch(branch)
            self.updateBranchCommitDate()

            # todo - if it failed, change selection back to previous branch

    def handleRGBDSSelected(self, rgbds):
        self.GameGUI.Game.set_RGBDS(rgbds.split(' ')[0])


class GameGUI:
    def __init__(self, GUI, game):
        self.GUI = GUI
        self.Game = game

        # TODO
        self.isIPS = False
        self.isGit = True
        
        self.Queue = GameQueue(self)
        self.Tile = GameTile(self)
        self.Panel = GamePanel(self)

        self.setQueued(False)

    def setQueued(self, queued):
        self.Tile.isQueued = queued
        self.Tile.setProperty('queued', queued)
        self.Tile.updateStyle()

    def setActive(self, value):
        self.Queue.setProperty("active",value)
        self.Tile.setProperty("active",value)
        self.Queue.updateStyle()
        self.Tile.updateStyle()
        if value:
            self.Panel.addTo(self.GUI.Panel.Display)
        else:
            self.Panel.setParent(None)

    def setProcessing(self, value):
        self.Queue.setProperty("processing",value)
        self.Tile.setProperty("processing",value)
        self.Queue.updateStyle()
        self.Tile.updateStyle()

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
        # todo - disable when queue is empty
        self.SaveList = Button(self.Header, 'Save', self.saveList)

        self.ListContainer = VScroll(GUI)
        self.ListContainer.addTo(self, 95)

        self.ListGUI = VBox(GUI)
        self.ListGUI.addTo(self.ListContainer)
        self.ListContainer.addStretch()
        
        self.addTo(GUI.RightCol, 65)

    def addGame(self, gameGUI):
        if gameGUI not in self.List:
            self.List.append(gameGUI)
            gameGUI.setQueued(True)
            gameGUI.Queue.addTo(self.ListGUI)

    def addGames(self, games):
        [self.addGame(game.GUI) for game in games]

    def removeGame(self, gameGUI):
        if gameGUI in self.List:
            self.List.pop( self.List.index(gameGUI) )
            gameGUI.setQueued(False)
            gameGUI.Queue.setParent(None)

    def removeGames(self, games):
        [self.removeGame(game.GUI) for game in games]

    def clear(self, event):
        self.removeGames([gameGUI.Game for gameGUI in self.List])

    def process(self, event):
        self.GUI.startProcess([gameGUI.Game for gameGUI in self.List])

    def saveList(self, event):
        if event.button() == Qt.LeftButton and self.List:
            self.GUI.saveList([gameGUI.Game for gameGUI in self.List])

class TileContent(Flow):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName('Tiles')
        self.Layout.setSpacing(10)
        self.Scroll.setObjectName('Tiles')
        self.addTo(parent, 95)

class TilesHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")
        self.Type = self.label()
        self.Type.setObjectName("header")
        self.Name = self.label()
        self.Name.setObjectName("header")
        # todo - disable when list is empty
        self.SaveList = Button(self, 'Save', parent.saveList)
        self.addTo(parent, 5)

    def setText(self, type, name=''):
        self.Type.setText(type)
        self.Name.setText(name)

class PanelFooter(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("footer")
        self.AddToQueue = Button(self, 'Add', parent.addToQueue)
        self.RemoveFromQueue = Button(self, 'Remove', parent.removeFromQueue)
        self.Process = Button(self, 'Process', parent.process)
        self.Favorite = Button(self, 'Favorite', parent.favorite)
        self.Exclude = Button(self, 'Exclude', parent.exclude)
        self.addTo(parent, 10)

class Tiles(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = TilesHeader(self)
        self.Content = TileContent(self)
        self.Footer = PanelFooter(self)
        self.reset()
        self.addTo(GUI, 25)

    def reset(self):
        self.OR_Lists = []
        self.OR_Games = []
        self.AND_Lists = []
        self.AND_Games = []
        self.NOT_Lists = []
        self.NOT_Games = []
        self.All_Games = []
    
    def is_game_valid(self, game):
        if self.OR_Lists:
            if self.AND_Lists:
                return game in self.OR_Games and game in self.AND_Games and game not in self.NOT_Games
            else:
                return game in self.OR_Games and game not in self.NOT_Games
        elif self.AND_Lists:
            return game in self.AND_Games and game not in self.NOT_Games
        else:
            return False

    def compile(self):
        for game in self.All_Games[:]:
            if not self.is_game_valid(game):
                self.All_Games.pop(self.All_Games.index(game))
                game.GUI.Tile.setParent(None)

        if self.OR_Lists:
            for game in self.OR_Games:
                if self.is_game_valid(game):
                    self.All_Games.append(game)
                    game.GUI.Tile.addTo(self.Content)
        elif self.AND_Lists:
            for game in self.AND_Games:
                if self.is_game_valid(game):
                    self.All_Games.append(game)
                    game.GUI.Tile.addTo(self.Content)

    def saveList(self, event):
        if event.button() == Qt.LeftButton and self.All_Games:
            self.GUI.saveList(self.All_Games)

    def removeList(self, list, type):
        lists = getattr(self, type + '_Lists')
        if list not in lists:
            return

        lists.pop(lists.index(list))

        # Recompile games list
        games = []
        setattr(self, type + '_Games', games)
        
        if type == 'AND':
            firstList = True
            for list in lists:
                if firstList:
                    games += list.getData()
                    firstList = False
                else:
                    data = list.getData()
                    for game in games[:]:
                        if game not in data:
                            games.pop(games.index(game))
        else:
            for list in lists:
                for game in list.getData():
                    if game not in games:
                        games.append(game)

    def removeNOT(self, list):
        self.removeList(list, 'NOT')

    def removeAND(self, list):
        self.removeList(list, 'AND')

    def removeOR(self, list):
        self.removeList(list, 'OR')

    def remove(self, list):
        self.removeList(list, 'OR')
        self.removeList(list, 'AND')
        self.removeList(list, 'NOT')
        self.compile()

    def addAND(self, list):
        self.removeOR(list)
        self.removeNOT(list)

        if list in self.AND_Lists:
            return

        self.AND_Lists.append(list)

        data = list.getData()
        if len(self.AND_Lists) == 1:
            self.AND_Games += data
        else:
            for game in self.AND_Games[:]:
                if game not in data:
                    self.AND_Games.pop(self.AND_Games.index(game))

        self.compile()

    def addNEW(self, list):
        for game in self.All_Games:
            game.GUI.Tile.setParent(None)

        for other_list in self.OR_Lists + self.AND_Lists + self.NOT_Lists:
            other_list.setMode(None)

        self.reset()
        self.addOR(list)

    def addNOT(self, list):
        self.removeAND(list)
        self.removeOR(list)

        if list in self.NOT_Lists:
            return

        self.NOT_Lists.append(list)

        for game in list.getData():
            if game not in self.NOT_Games:
                self.NOT_Games.append(game)

        self.compile()

    def addOR(self, list):
        self.removeAND(list)
        self.removeNOT(list)

        if list in self.OR_Lists:
            return

        self.OR_Lists.append(list)

        for game in list.getData():
            if game not in self.OR_Games:
                self.OR_Games.append(game)

        self.compile()

    def addToQueue(self, event):
        self.GUI.Queue.addGames(self.All_Games)

    def removeFromQueue(self, event):
        self.GUI.Queue.removeGames(self.All_Games)

    def process(self, event):
        self.GUI.startProcess([game for game in self.All_Games])

    def favorite(self, event):
        if self.All_Games:
            self.GUI.Manager.Catalogs.Lists.get('Favorites').addGames(self.All_Games)

    def exclude(self, event):
        if self.All_Games:
            self.GUI.Manager.Catalogs.Lists.get('Excluding').addGames(self.All_Games)

class PanelHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")

        self.Label = self.label()
        self.Label.setObjectName("header")

        self.Right = HBox(parent.GUI)
        self.Right.addTo(self)

        self.addTo(parent, 10)

    def setText(self, text):
        self.Label.setText(text)

class PanelFooter(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("footer")
        self.AddToQueue = Button(self, 'Add', parent.addToQueue)
        self.RemoveFromQueue = Button(self, 'Remove', parent.removeFromQueue)
        self.Process = Button(self, 'Process', parent.process)
        self.Favorite = Button(self, 'Favorite', parent.favorite)
        self.Exclude = Button(self, 'Exclude', parent.exclude)
        self.addTo(parent, 10)

class Panel(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = PanelHeader(self)

        self.Display = VScroll(GUI)
        self.Display.addTo(self, 80)
        
        self.Footer = PanelFooter(self)

        self.Active = None
        self.setActive(None)
        self.addTo(GUI, 25)

    def setActive(self, game):
        if self.Active:
            self.Active.setActive(False)

        self.Active = None if game == self.Active else game

        if self.Active:
            self.Active.setActive(True)
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
        if self.Active:
            self.GUI.Manager.Catalogs.Lists.get('Favorites').toggleGames([self.Active.Game])

    def exclude(self, event):
        if self.Active:
            self.GUI.Manager.Catalogs.Lists.get('Excluding').toggleGames([self.Active.Game])

    def applyPatch(self, event):
        pass

class ProcessSignals(QObject):
    doBuild = pyqtSignal(object)

class Process(QRunnable):
    def __init__(self, GUI):
        super().__init__()
        self.GUI = GUI
        self.ProcessSignals = ProcessSignals()
        self.ProcessSignals.doBuild.connect(GUI.handleBuildSignal)

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
        self.ToggleUpdate.setActive(self.GUI.Manager.doUpdate)
        self.ToggleBuild.setActive(self.GUI.Manager.doBuild != None)
        self.ToggleClean.setActive(self.GUI.Manager.doClean)

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
        
        self.Col1 = VBox(self)
        self.Col1.addTo(self)

        self.Tiles = Tiles(self)
        self.Panel = Panel(self)

        self.RightCol = VBox(self)
        self.RightCol.addTo(self, 20)

        self.Queue = Queue(self)
        self.Status = Status(self)

        self.addTo(window.Widget)

    def saveList(self, list):
        fileName, ext = QFileDialog.getSaveFileName(self, 'Save List As', 'data/lists','*.json')
        if fileName:
            name = fileName.split('/')[-1].split('.')[0]

            data = listToDict(list)
            with open(fileName,'w') as f:
                f.write(json.dumps(data))

            self.Manager.addList(name, data)

    def startProcess(self, games):
        if not self.Window.Process:
            self.GUI.Manager.add_to_queue(games)
            self.Window.Process = Process(self)
            threadpool.start(self.Window.Process)

    def endProcess(self):
        self.Window.Process = None

    def handleBuildSignal(self, game):
        game.GUI.Panel.drawBuilds()

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
