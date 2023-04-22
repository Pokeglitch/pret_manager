import sys, webbrowser, json, re

'''
TODO:
- give games keywords, which are different from tags and only used in search

CLI:
- use -o for order, combination of any of following (in any order, can be multiple times):
-- f u b c
- use -l to filter by list
- use -s for search option
- use the same 'filter' function that the GUI current uses...
-- -a, -ao, -aa, -an, etc

GUI:
- combo-boxes
- Catalog/Tile/Queue Sorting:
-- date of last update, alphabet, etc

Filter:
- Show number of items in filter

** - Add way to Save the filter options (catalogs for each mode & search term)
-- Add way to load a filter

Browser:
** - Instead of the buttons at bottom:
-- Have a dropdown which includes all Queue (default), all lists + New
--- Have buttons for: Add to/Remove From/Toggle In
- (True for Game Panel as well, though Fav/Exclude are also quick clicks)

Lists:
- Way to load a list, delete a list
- show size of each list next to name
** - Update Outdated list
** - 'Library' list for game that have builds
    -- likewise, a list for games that dont have builds
    - Also one for downlaoaded, not downloaded

- Game Tile:
-- Show if missing or outdated
-- title above boxart
-- Pokeball in top left corner for favorite (over boxart)
-- Double click to launch

- Game Panel:
-- Empty panel shows credits
-- can open a new panel if want to open multiple game details
--- can close panels
-- fix down arrow in Trees
-- Show when game is in queue
-- show if game is missing or out of date

-------

'Missing' should search for rom files in the builds or releases
-- What about if releases are in an archive? (zip, etc)

- Make theme independent ?
- Another auto list where there are no builds/releases with a game in them

Way to launch most recent build/release
- or, set which is the default 'launch'

Have the directory be database (if shortcut, then git, etc)
- folder title is name of game
- data file in each (for which rgbds, tags, etc)
-- separate from metadata
--- meta data should include successful/failed commit attempts

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

from src.base import *
from src.catalogs import *
from src.process import *

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
        #self.Name = self.label(gameGUI.Game.name)


        self.Artwork = self.label()
        self.Pixmap = QPixmap(self.GameGUI.Game.Boxart).scaled(100, 100)
        self.Faded = Faded(self.Pixmap)

        self.Title = self.label(gameGUI.Game.title)
        self.Title.setAlignment(Qt.AlignCenter)
        self.isQueued = False

    def updateExcluding(self, excluding):
        if excluding:
            self.Artwork.setPixmap(self.Faded)
        else:
            self.Artwork.setPixmap(self.Pixmap)
        

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Panel.setActive(self.GameGUI)
        elif event.button() == Qt.RightButton:
            if self.isQueued:
                self.GUI.Queue.removeGame(self.GameGUI)
            else:
                self.GUI.Queue.addGame(self.GameGUI)

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
        self.setProperty('which',name)
        self.Label = self.label(name)
        self.Label.setAlignment(Qt.AlignCenter)
        self.addTo(parent)

class GamePanelArtwork(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Label = self.label()
        self.Label.setAlignment(Qt.AlignCenter)
        
        self.Pixmap = QPixmap(parent.GameGUI.Game.Boxart).scaled(300, 300)
        self.Faded = Faded(self.Pixmap)

        self.Container = HBox(self.GUI)
        self.Container.addTo(parent)
        self.addTo(self.Container)

    def updateExcluding(self, excluding):
        if excluding:
            self.Label.setPixmap(self.Faded)
        else:
            self.Label.setPixmap(self.Pixmap)

class GamePanel(VBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.Artwork = GamePanelArtwork(self)
        self.Tags = TagsGUI(self, gameGUI.Game.tags)
        

        # if git repo
        self.GitOptions = VBox(self.GUI)
        self.GitOptions.setObjectName('PanelOptions')
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
            if version == self.GameGUI.Game.rgbds and not default_index:
                default_index = len(items)
            # Custom takes priority
            if version == self.GameGUI.Game.RGBDS:
                default_index = len(items)

            items.append(version)

        items[default_index] += ' *'

        self.RGBDSComboBox.addItems(items)
        self.RGBDSComboBox.setCurrentIndex(default_index)

        self.RGBDSComboBox.currentTextChanged.connect(self.handleRGBDSSelected)
        self.SetRGBDSVersion.add(self.RGBDSComboBox)
        self.SetRGBDSVersion.addTo(self.GitOptions)

        self.updateBranchDetails()
        
        self.Trees = HBox(self.GUI)
        self.Trees.addTo(self)
        self.Trees.setObjectName("Trees")

        self.Builds = VBox(self.GUI)
        self.Builds.addTo(self.Trees, 1)
        self.BuildTree = QTreeWidget()
        self.BuildTree.header().setStretchLastSection(False)
        self.BuildTree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.BuildTree.header().hide()
        self.BuildTree.setIndentation(10)
        self.Builds.add(self.BuildTree)
        self.BuildTree.itemDoubleClicked.connect(lambda e: hasattr(e,"Path") and QDesktopServices.openUrl(e.Path))
        self.drawBuilds()

        self.Releases = VBox(self.GUI)
        self.Releases.addTo(self.Trees, 1)
        self.ReleaseTree = QTreeWidget()
        self.ReleaseTree.header().setStretchLastSection(False)
        self.ReleaseTree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
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

            releases = list(self.GameGUI.Game.releases.keys())
            releases.sort()

            for releaseName in reversed(releases):
                roms = self.GameGUI.Game.releases[releaseName]
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

                builds = list(branchBuilds.keys())
                builds.sort()

                for buildName in reversed(builds):
                    roms = branchBuilds[buildName]
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
        self.updateExcluding(self.Game.Excluding)

    def updateExcluding(self, excluding):
        self.Tile.updateExcluding(excluding)
        self.Panel.Artwork.updateExcluding(excluding)

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
            self.Panel.addTo(None)

    def setProcessing(self, value):
        self.Queue.setProperty("processing",value)
        self.Tile.setProperty("processing",value)
        self.Queue.updateStyle()
        self.Tile.updateStyle()

class QueueHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")

        self.Label = self.label('Queue')
        self.Label.setObjectName("header")
        self.Label.setAlignment(Qt.AlignCenter)
        self.addTo(parent, 5)

class Queue(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.List = []
        self.isEmpty = True

        self.Header = QueueHeader(self)

        self.Clear = Button(self.Header, 'Clear', self.clear)

        self.Process = Button(self.Header, 'Process', self.process)
        self.GUI.addProcessButton(self.Process)

        self.SaveList = Button(self.Header, 'Save', self.saveList)
        self.SaveList.setProperty('disabled', self.isEmpty)

        self.ListContainer = VScroll(GUI)
        self.ListContainer.addTo(self, 95)

        self.ListGUI = VBox(GUI)
        self.ListGUI.addTo(self.ListContainer)
        self.ListContainer.addStretch()
        
        self.addTo(GUI.Col1, 1)

    def updateIsEmpty(self):
        if self.isEmpty == bool(self.List):
            self.isEmpty = not bool(self.List)
            self.SaveList.setProperty('disabled', self.isEmpty)
            self.SaveList.updateStyle()

    def addGame(self, gameGUI):
        if gameGUI not in self.List:
            self.List.append(gameGUI)
            gameGUI.setQueued(True)
            gameGUI.Queue.addTo(self.ListGUI)

            self.updateIsEmpty()

    def addGames(self, games):
        [self.addGame(game.GUI) for game in games]

    def removeGame(self, gameGUI):
        if gameGUI in self.List:
            self.List.pop( self.List.index(gameGUI) )
            gameGUI.setQueued(False)
            gameGUI.Queue.addTo(None)

            self.updateIsEmpty()

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
        self.GUI.addProcessButton(self.Process)

        self.Exclude = Button(self, 'Exclude', parent.exclude)
        self.addTo(parent, 10)

class Tiles(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = TilesHeader(self)
        self.Content = TileContent(self)
        self.Footer = PanelFooter(self)
        self.reset()
        self.addTo(GUI.Col2, 2)

    def reset(self):
        self.OR_Lists = []
        self.OR_Games = []
        self.AND_Lists = []
        self.AND_Games = []
        self.NOT_Lists = []
        self.NOT_Games = []
        self.All_Games = []
        self.isEmpty = False
        self.updateIsEmpty()

    def updateIsEmpty(self):
        if self.isEmpty == bool(self.All_Games):
            self.isEmpty = not bool(self.All_Games)
            self.Header.SaveList.setDisabled(self.isEmpty)
            self.Footer.AddToQueue.setDisabled(self.isEmpty)
            self.Footer.RemoveFromQueue.setDisabled(self.isEmpty)
            self.Footer.Exclude.setDisabled(self.isEmpty)
            self.Footer.Process.setDisabled(self.isEmpty)

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

    def compile(self, updateGUI = True):
        for game in self.All_Games[:]:
            if not self.is_game_valid(game):
                self.All_Games.pop(self.All_Games.index(game))
                if updateGUI: game.GUI.Tile.addTo(None)

        if self.OR_Lists:
            for game in self.OR_Games:
                if self.is_game_valid(game):
                    if game not in self.All_Games:
                        self.All_Games.append(game)
                    if updateGUI and game.GUI.Tile.Parent != self.Content: game.GUI.Tile.addTo(self.Content)
        elif self.AND_Lists:
            for game in self.AND_Games:
                if self.is_game_valid(game):
                    if game not in self.All_Games:
                        self.All_Games.append(game)
                    if updateGUI and game.GUI.Tile.Parent != self.Content: game.GUI.Tile.addTo(self.Content)

        self.updateIsEmpty()

    def refresh(self):
        for game in self.GUI.Manager.All:
            if game not in self.All_Games:
                if game.GUI.Tile.Parent == self.Content:
                    game.GUI.Tile.addTo(None)
            else:
                if game.GUI.Tile.Parent != self.Content:
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

    def removeAND(self, list):
        self.removeList(list, 'OR')

    def remove(self, list, updateGUI=True):
        self.removeList(list, 'OR')
        self.removeList(list, 'AND')
        self.removeList(list, 'NOT')
        self.compile(updateGUI)

    def addAND(self, list, updateGUI=True):
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

        self.compile(updateGUI)

    def addNEW(self, list, updateGUI=True):
        for game in self.All_Games:
            game.GUI.Tile.addTo(None)

        for other_list in self.OR_Lists + self.AND_Lists + self.NOT_Lists:
            if other_list != self.GUI.Manager.Search.GUI:
                other_list.setMode(None)

        self.reset()
        self.addOR(list, False)
        self.addAND(self.GUI.Manager.Search.GUI, updateGUI)

    def addNOT(self, list, updateGUI=True):
        self.removeAND(list)
        self.removeOR(list)

        if list in self.NOT_Lists:
            return

        self.NOT_Lists.append(list)

        for game in list.getData():
            if game not in self.NOT_Games:
                self.NOT_Games.append(game)

        self.compile(updateGUI)

    def addOR(self, list, updateGUI=True):
        self.removeAND(list)
        self.removeNOT(list)

        if list in self.OR_Lists:
            return

        self.OR_Lists.append(list)

        for game in list.getData():
            if game not in self.OR_Games:
                self.OR_Games.append(game)

        self.compile(updateGUI)

    def addToQueue(self, event):
        self.GUI.Queue.addGames(self.All_Games[:])

    def removeFromQueue(self, event):
        self.GUI.Queue.removeGames(self.All_Games[:])

    def process(self, event):
        self.GUI.startProcess([game for game in self.All_Games])

    def favorite(self, event):
        if self.All_Games:
            self.GUI.Manager.Catalogs.Lists.get('Favorites').addGames(self.All_Games[:])

    def exclude(self, event):
        if self.All_Games:
            self.GUI.Manager.Catalogs.Lists.get('Excluding').addGames(self.All_Games[:])

class PanelHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")

        self.Right = HBox(parent.GUI)

        self.Favorite =  self.Right.label()
        self.Favorite.mousePressEvent = parent.favorite
        self.StarPixmap = QPixmap('assets/images/favorite.png').scaled(35, 35)
        self.FadedStar = Faded(self.StarPixmap)
        self.Right.addTo(self)

        self.Label = self.label()
        self.Label.setObjectName("header")

        self.addStretch()

        self.addTo(parent, 10)

    def updateFavorite(self, isFavorite):
        self.Favorite.setPixmap(self.StarPixmap if isFavorite else self.FadedStar)

    def setText(self, text):
        self.Label.setText(text)

class PanelFooter(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("footer")
        self.AddToQueue = Button(self, 'Add', parent.addToQueue)
        self.RemoveFromQueue = Button(self, 'Remove', parent.removeFromQueue)
        self.Process = Button(self, 'Process', parent.process)
        self.GUI.addProcessButton(self.Process)

        self.Exclude = Button(self, 'Exclude', parent.exclude)
        self.addTo(parent, 10)

class Panel(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = PanelHeader(self)

        self.Display = VScroll(GUI)
        self.Display.setObjectName('PanelDisplay')
        self.Display.addTo(self, 80)
        
        self.Footer = PanelFooter(self)

        self.Active = None
        self.setActive(None)
        self.addTo(GUI, 3)

    def setActive(self, game):
        if self.Active:
            self.Active.setActive(False)

        self.Active = None if game == self.Active else game

        if self.Active:
            self.Active.setActive(True)
            self.Header.setText(self.Active.Game.name)
            self.Header.updateFavorite(self.GUI.Manager.Catalogs.Lists.get('Favorites').has(self.Active.Game))
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
            favorites = self.GUI.Manager.Catalogs.Lists.get('Favorites')
            favorites.toggleGames([self.Active.Game])

            self.Header.updateFavorite(favorites.has(self.Active.Game))

    def exclude(self, event):
        if self.Active:
            self.GUI.Manager.Catalogs.Lists.get('Excluding').toggleGames([self.Active.Game])

    def applyPatch(self, event):
        pass

class ProcessSignals(QObject):
    doBuild = pyqtSignal(object)
    doRelease = pyqtSignal(object)
    finished = pyqtSignal()
    newStatusMessage = pyqtSignal(str)

class ExecuteProcess(QRunnable):
    def __init__(self, GUI):
        super().__init__()
        self.GUI = GUI
        self.ProcessSignals = ProcessSignals()
        self.ProcessSignals.doBuild.connect(GUI.handleBuildSignal)
        self.ProcessSignals.doRelease.connect(GUI.handleReleaseSignal)
        self.ProcessSignals.finished.connect(GUI.processFinished)
        self.ProcessSignals.newStatusMessage.connect(GUI.addStatus)

    def run(self):
        self.GUI.Manager.run()
        self.ProcessSignals.finished.emit()


class MainContents(HBox):
    def __init__(self, window):
        super().__init__(self)
        self.Window = window
        self.Manager = window.Manager

        self.ProcessButtons = []
        
        self.Col1 = VBox(self)
        self.Col1.addTo(self, 1)

        self.Catalogs = Catalogs(self)
        self.Queue = Queue(self)
        
        self.Col2 = VBox(self)
        self.Col2.addTo(self, 4)

        self.Tiles = Tiles(self)
        self.Process = Process(self)

        self.Panel = Panel(self)

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
            [button.setProcessing(True) for button in self.ProcessButtons]
            self.Window.Process = ExecuteProcess(self)
            threadpool.start(self.Window.Process)

    def processFinished(self):
        self.Window.Process = None
        [button.setProcessing(False) for button in self.ProcessButtons]

    def handleBuildSignal(self, game):
        game.GUI.Panel.drawBuilds()

    def handleReleaseSignal(self, game):
        game.GUI.Panel.drawReleases()

    def addProcessButton(self, button):
        self.ProcessButtons.append(button)

    def addStatus(self, msg):
        self.Process.Body.addStatusMessage(msg)

class PRET_Manager_GUI(QMainWindow):
    def __init__(self, manager):
        super().__init__()
        self.Process = None
        self.Manager = manager
        self.setWindowTitle("pret manager")
        self.setWindowIcon(QIcon('assets/images/icon.png'))
        self.Widget = VBox(self)
        self.Content = MainContents(self)
        self.setCentralWidget(self.Widget)
        
        with open('./assets/style.qss') as f:
            self.setStyleSheet(f.read())

class PRET_Manager_App(QApplication):
    def __init__(self, manager, *args):
        self.Manager = manager
        super().__init__(*args)

        # Create splashscreen
        splash_pix = QPixmap('assets/images/logo.png')
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setPixmap(splash_pix)

        # add fade to splashscreen 
        opaqueness = 0.0
        step = 0.05
        splash.setWindowOpacity(opaqueness)
        splash.show()

        while opaqueness < 1:
            splash.setWindowOpacity(opaqueness)
            time.sleep(0.05) # Gradually appears
            opaqueness+=step
            
        self.Splash = splash

    def init(self):
        self.Splash.close()
        self.Manager.GUI.show()
        self.exec()

def init(manager):
    return PRET_Manager_App(manager, sys.argv), PRET_Manager_GUI(manager)
