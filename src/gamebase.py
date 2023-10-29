from src.base import *

class GameBaseContextMenu(ContextMenu):
    def __init__(self, parent, event):
        gui = parent.GameGUI
        game = gui.Game
        self.Game = game
        super().__init__(parent, event)

        if game.Library:
            self.addAction( LaunchGameAction(parent, self.launch_game) )
        
        if gui.isQueued:
            self.addAction( RemoveFromQueue(gui) )
        else:
            self.addAction( AddToQueue(gui) )

        if game.Favorites:
            self.addAction( RemoveFromFavorites(gui) )
        else:
            self.addAction( AddToFavorites(gui) )

        if game.Excluding:
            self.addAction( RemoveFromExcluding(gui) )
        else:
            self.addAction( AddToExcluding(gui) )

        addLists = []
        removeLists = []

        for list in parent.GUI.Manager.Catalogs.Lists.Entries.values():
            if list.has(parent.GameGUI.Game):
                removeLists.append(list)
            else:
                addLists.append(list)

        self.addMenu( AddGameToListMenu(parent, addLists) )

        if removeLists:
            self.addMenu( RemoveFromListMenu(parent, removeLists) )

        if not gui.GUI.Window.Process:
            self.addMenu( ProcessesMenu(parent, gui) )

    def launch_game(self):
        if self.Game.PrimaryGame and os.path.exists(self.Game.PrimaryGame):
            open_path(self.Game.PrimaryGame)
        else:
            open_path( self.Game.findNewestGame() )

class GameContextMenu(GameBaseContextMenu):
    def __init__(self, parent, event):
        super().__init__(parent, event)
        self.start()
