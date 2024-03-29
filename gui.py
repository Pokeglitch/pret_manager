import sys

'''
TODO:
'tar' in linux wont extract a zip file
-- only permit 'tar' to be used with wsl, otherwise it uses main

Bugs:
- Pure RGB still has the overwrite local files issues when updating...
- Dont mark as updated if it any failed...

Check remaining TODOs throughout source
------
Need to update submodules when switching branches?

Game Panel:
- Folder icons should be faded if folder does not exist
-------
Update README, Tutorial

Compile to executable for release:
https://nuitka.net/
'''
from src.panel import *
from src.gametile import *
from src.gamepanel import *
from src.base import *
from src.catalogs import *
from src.process import *

class GameQueue(HBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.Game = gameGUI.Game
        self.label(gameGUI.Game.FullTitle)

        self.Game.on('Processing', self.setProcessing)

    def getData(self):
        return [self.Game]

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Panel.setActive(self.GameGUI)

    def setProcessing(self, value):
        self.setProperty("processing",value)
        self.updateStyle()
            
    def contextMenuEvent(self, event):
        GameContextMenu(self, event)

class GameGUI(QWidget):
    def __init__(self, GUI, game):
        super().__init__()
        self.GUI = GUI
        self.Game = game

        # TODO
        self.isIPS = False
        self.isGit = True
        
        self.isQueued = False
        
        self.Queue = GameQueue(self)
        self.Tile = GameTile(self)
        self.Panel = None

        # TODO - these should also connect to signals
        self.setQueued(False)

    # todo - emitter
    def setQueued(self, queued):
        self.isQueued = queued
        self.Tile.setProperty('queued', queued)
        self.Tile.updateStyle()

    # todo - emitter
    def setActive(self, value):
        self.Queue.setProperty("active",value)
        self.Tile.setProperty("active",value)
        self.Queue.updateStyle()
        self.Tile.updateStyle()

        if not self.Panel:
            self.Panel = GamePanel(self)

    def process(self):
        self.GUI.startProcess([self.Game])

    def specificProcess(self, sequence, *args):
        self.GUI.startSpecificProcess(sequence, [self.Game], *args)

    def addToQueueHandler(self):
        self.GUI.Queue.addGame(self)

    def removeFromQueueHandler(self):
        self.GUI.Queue.removeGame(self)

    def addToFavoritesHandler(self):
        self.Game.setFavorites(True)

    def removeFromFavoritesHandler(self):
        self.Game.setFavorites(False)
        
    def toggleFavoritesHandler(self):
        if self.Game.Favorites:
            self.removeFromFavoritesHandler()
        else:
            self.addToFavoritesHandler()

    def addToExcludingHandler(self):
        self.Game.setExcluding(True)

    def removeFromExcludingHandler(self):
        self.Game.setExcluding(False)

    def toggleExcludingHandler(self):
        if self.Game.Excluding:
            self.removeFromExcludingHandler()
        else:
            self.addToExcludingHandler()

    def saveList(self):
        self.GUI.saveList([self.Game])

class QueueContextMenu(ContextMenu):
    def __init__(self, queue, event):
        super().__init__(queue, event)

        self.addMenu( FavoritesMenu(queue) )
        self.addMenu( ExcludingMenu(queue) )
        
        # Add to list/ remove from list (except itself)
        lists = []

        for list in queue.GUI.Manager.Catalogs.Lists.Entries.values():
            lists.append(list)

        self.addMenu(ListsMenu(queue, lists))
        
        if queue.List and not queue.GUI.Window.Process:
            self.addMenu( ProcessesMenu(queue) )

        self.addAction( SetAsDefaultQueue(queue) )
        self.addAction( ClearQueue(queue) )

        self.Coords = queue.ListContainer.Scroll.mapToGlobal(QPoint(0, 0))
        self.start()

class QueueHeaderMenuIcon(MenuIcon):
    def __init__(self, parent):
        super().__init__(parent)
        self.Queue = parent.Queue

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.Queue.isEmpty:
            QueueContextMenu(self.Queue, event)

class QueueHeaderMenu(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Queue = parent.Queue
        self.Menu = QueueHeaderMenuIcon(self)
        self.addStretch()
        self.addTo(parent, 1, 1)

class QueueHeader(Grid):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Queue = parent

        self.setObjectName("header-frame")

        self.Label = self.label('Queue', 1, 1)
        self.Label.setAlignment(Qt.AlignCenter)
        self.Label.setObjectName("header")

        self.Menu = QueueHeaderMenu(self)

        self.addTo(parent, 5)

class Queue(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.List = []
        self.isEmpty = False

        self.Header = QueueHeader(self)

        self.ListContainer = VScroll(GUI)
        self.ListContainer.addTo(self, 95)

        self.ListGUI = VBox(GUI)
        self.ListGUI.addTo(self.ListContainer)
        self.ListContainer.addStretch()
        
        self.Footer = HBox(GUI)
        self.Footer.setObjectName("QueueFooter")
        self.Process = Button(self.Footer, 'Process', self.process)
        self.GUI.Window.Processing.connect(self.Process.setProcessing)
        self.Footer.addTo(self)

        self.updateIsEmpty()

        self.addTo(GUI.Col1, 1)

        self.GUI.Window.InitializedSignal.connect(self.loadDefault)

    def updateIsEmpty(self):
        if self.isEmpty == bool(self.List):
            self.isEmpty = not bool(self.List)
            self.Header.Menu.setVisible(bool(self.List))
            self.Process.setProperty('disabled', self.isEmpty)
            self.Process.updateStyle()

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

    def erase(self):
        self.removeGames(self.getData())

    def process(self, isAuto=False):
        if self.List:
            self.GUI.startProcess(self.getData(), isAuto=isAuto)
            
    def specificProcess(self, sequence, *args):
        if self.List:
            self.GUI.startSpecificProcess(sequence, self.getData(), *args)

    def loadDefault(self):
        if os.path.exists('data/queue.json'):
            with open('data/queue.json', 'r') as f:
                list = json.loads(f.read() or '{}')
                
            games = []
            for author in list:
                for title in list[author]:
                    games.append(self.GUI.Manager.Catalogs.Authors.get(author).getGame(title))

            self.addGames(games)

        self.GUI.Panel.Body.Options.setQueueReady()

    def setAsDefault(self):
        structure = listToDict(self.getData())
        with open('data/queue.json', 'w') as f:
            f.write(json.dumps(structure, indent=4))

    def saveList(self):
        self.GUI.saveList(self.getData())
    
    def getData(self):
        return [gameGUI.Game for gameGUI in self.List]

    def addToFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Favorites').addGames(self.getData())

    def removeFromFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Favorites').removeGames(self.getData())
            
    def addToExcludingHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Excluding').addGames(self.getData())
            
    def removeFromExcludingHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Excluding').removeGames(self.getData())
            
class TilesContextMenu(ContextMenu):
    def __init__(self, parent, event):
        super().__init__(parent, event)

        tiles = parent.GUI.Tiles

        if not tiles.isEmpty:
            self.addMenu(QueueMenu(tiles))
            self.addMenu(FavoritesMenu(tiles))
            self.addMenu(ExcludingMenu(tiles))

            lists = []

            for list in parent.GUI.Manager.Catalogs.Lists.Entries.values():
                lists.append(list)

            self.addMenu(ListsMenu(tiles, lists))

        if not tiles.isEmpty and not tiles.GUI.Window.Process:
            self.addMenu( ProcessesMenu(tiles) )

        if [tiles.GUI.Manager.Search.GUI] != tiles.OR_Lists + tiles.AND_Lists + tiles.NOT_Lists:
            self.addAction( ClearBrowser(tiles) )

        self.Coords = tiles.Content.Scroll.mapToGlobal(QPoint(0, 0))
        self.start()

class TileContent(Flow):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName('Tiles')
        self.Layout.setSpacing(5)
        self.Scroll.setObjectName('Tiles')
        self.addTo(parent, 95)

class TilesHeaderMenuIcon(MenuIcon):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.Menu = TilesContextMenu(self, event)

class TilesHeaderMenu(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Menu = TilesHeaderMenuIcon(self)
        self.addStretch()
        self.addTo(parent, 1, 1)

class TilesHeader(Grid):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")
        
        self.Label = self.label('Browser', 1, 1)
        self.Label.setAlignment(Qt.AlignCenter)
        self.Label.setObjectName("header")

        self.Menu = TilesHeaderMenu(self)

        self.addTo(parent, 5)

class Tiles(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = TilesHeader(self)
        self.Content = TileContent(self)
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

    def addToFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Favorites').addGames(self.getData())

    def removeFromFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Favorites').removeGames(self.getData())
            
    def addToExcludingHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Excluding').addGames(self.getData())
            
    def removeFromExcludingHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Excluding').removeGames(self.getData())
            
    def addToQueueHandler(self):
        self.GUI.Queue.addGames(self.getData())

    def removeFromQueueHandler(self):
        self.GUI.Queue.removeGames(self.getData())

    def erase(self):
        for game in self.All_Games:
            game.GUI.Tile.addTo(None)

        for list in self.OR_Lists + self.AND_Lists + self.NOT_Lists:
            if list != self.GUI.Manager.Search.GUI:
                list.setMode(None)

        self.reset()
        self.addAND(self.GUI.Manager.Search.GUI, True)

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

        self.GUI.Manager.App.processEvents()

    def saveList(self):
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

    def getData(self):
        return self.All_Games[:]

    def process(self, event):
        if self.All_Games:
            self.GUI.startProcess(self.getData())
            
    def specificProcess(self, sequence, *args):
        if self.All_Games:
            self.GUI.startSpecificProcess(sequence, self.getData(), *args)

class ManagerThread(QThread):
    def __init__(self, GUI):
        super().__init__()
        self.GUI = GUI
        self.Window = GUI.Window
        self.Window.Processing.emit(True)
        self.finished.connect(self.finish)
        self.start()

    def finish(self):
        self.Window.Processing.emit(False)

class RefreshPRETManager(ManagerThread):
    def run(self):
        self.GUI.Manager.refresh()

class UpdatePRETManager(ManagerThread):
    def run(self):
        self.GUI.Manager.update()

class SwitchBranch(ManagerThread):
    def __init__(self, GUI, game, branch):
        self.Game = game
        self.Branch = branch

        super().__init__(GUI)

    def run(self):
        self.Game.set_branch(self.Branch)

class DownloadRelease(ManagerThread):
    def __init__(self, GUI, game, tag):
        self.Game = game
        self.Tag = tag

        super().__init__(GUI)

    def run(self):
        self.Game.get_release(self.Tag)


class DownloadGuides(ManagerThread):
    def __init__(self, GUI, game):
        self.Game = game

        super().__init__(GUI)

    def run(self):
        self.Game.get_guides()

class ExecuteProcess(ManagerThread):
    def __init__(self, GUI, sequence, games, build_options=[]):
        self.Games = games
        self.Game = None
        self.Sequence = sequence
        self.BuildOptions = build_options

        super().__init__(GUI)

    def run(self):
        if not self.Games:
            self.GUI.Manager.print('No games to process')
        elif self.Sequence:
            for game in self.Games:
                self.Game = game
                game.process(self.Sequence, self.BuildOptions)
        else:
            self.GUI.Manager.print('No actions to process')

    def finish(self):
        if self.Game:
            self.Game.setProcessing(False)

        super().finish()

class MainContents(HBox):
    def __init__(self, window):
        super().__init__(self)
        self.Window = window
        self.Manager = window.Manager

        self.Col1 = VBox(self)
        self.Col1.addTo(self, 2)

        self.Catalogs = Catalogs(self)
        self.Queue = Queue(self)
        
        self.Col2 = VBox(self)
        self.Col2.addTo(self, 4)

        self.Tiles = Tiles(self)
        self.Process = Process(self)

        self.Panel = Panel(self)

        self.Window.Logger.connect(self.addStatus)
        self.Window.Processing.connect(self.onProcessing)

        self.addTo(window.Widget)

    def saveList(self, list):
        SaveListDialog(self, list)

    def switchBranch(self, game, branch):
        if not self.Window.Process:
            self.Window.Process = SwitchBranch(self, game, branch)

    def restartPRETManager(self, isAuto=False):
        if not self.Window.Process or isAuto:
            QCoreApplication.quit()
            QProcess.startDetached(sys.executable, sys.argv)

    def refreshPRETManager(self, isAuto=False):
        if not self.Window.Process or isAuto:
            self.Window.Process = RefreshPRETManager(self)

    def updatePRETManager(self, isAuto=False):
        if not self.Window.Process or isAuto:
            self.Window.Process = UpdatePRETManager(self)

    def startProcess(self, games, *build_options, isAuto=False):
        if not self.Window.Process or isAuto:
            sequence = self.Process.Options.compile()
            self.Window.Process = ExecuteProcess(self, sequence, games[:], build_options)

    def startSpecificProcess(self, sequence, games, *build_options):
        if not self.Window.Process:
            self.Window.Process = ExecuteProcess(self, sequence, games[:], build_options)

    def downloadRelease(self, game, tag):
        if not self.Window.Process:
            self.Window.Process = DownloadRelease(self, game, tag)

    def downloadGuides(self, game):
        if not self.Window.Process:
            self.Window.Process = DownloadGuides(self, game)

    def onProcessing(self, processing):
        if not processing:
            self.Window.Process = None

    def addStatus(self, msg):
        self.Process.Body.addStatusMessage(msg)

    def print(self, msg):
        self.Process.Body.addStatusMessage('pret-manager:\t' + msg)

class PRET_Manager_GUI(QMainWindow):
    Logger = pyqtSignal(str)
    Processing = pyqtSignal(bool)
    InitializedSignal = pyqtSignal()
    UpdateFoundSignal = pyqtSignal(bool)
    UpdateAppliedSignal = pyqtSignal(bool)

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

        self.TerminateProcess = TerminateProcess(self)

    def terminateProcess(self):
        if self.Process:
            self.Process.terminate()
            self.Manager.terminateProcess()

class PRET_Manager_App(QApplication):
    def __init__(self, manager, *args):
        self.Manager = manager
        super().__init__(*args)
        self.Splash = SplashScreen('assets/images/logo.png')

    def init(self):
        self.Splash.close()
        self.Manager.GUI.show()
        self.Manager.GUI.InitializedSignal.emit()
        self.exec()

def init(manager):
    return PRET_Manager_App(manager, sys.argv), PRET_Manager_GUI(manager)
