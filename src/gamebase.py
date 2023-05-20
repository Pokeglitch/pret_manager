from src.base import *

class GameBaseContextMenu(ContextMenu):
    def __init__(self, parent, event):
        gui = parent.GameGUI
        game = gui.Game
        self.Game = game
        super().__init__(parent, event)

        if game.Library:
            self.addAction( Action(parent, "Launch Game", self.launch_game) )
        
        if gui.isQueued:
            self.addAction( gui.RemoveFromQueue )
        else:
            self.addAction( gui.AddToQueue )

        if game.Favorites:
            self.addAction( gui.RemoveFromFavorites )
        else:
            self.addAction( gui.AddToFavorites )

        if game.Excluding:
            self.addAction( gui.RemoveFromExcluding )
        else:
            self.addAction( gui.AddToExcluding )

        addLists = []
        removeLists = []

        for list in parent.GUI.Manager.Catalogs.Lists.Entries.values():
            if list.has(parent.GameGUI.Game):
                removeLists.append(list)
            else:
                addLists.append(list)

        self.addMenu( AddGameToListMenu(parent, addLists) )

        if removeLists:
            self.addMenu( RemoveGameFromListMenu(parent, removeLists) )

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
