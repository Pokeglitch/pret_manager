from src.base import *

class GameBaseContextMenu(ContextMenu):
    def __init__(self, parent, event):
        gui = parent.GameGUI
        game = gui.Game
        super().__init__(parent, event)
        
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

        # Todo - way to delete game data from disk
        # - option to keep builds, releases

class GameContextMenu(GameBaseContextMenu):
    def __init__(self, parent, event):
        super().__init__(parent, event)
        self.start()
