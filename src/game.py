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
            self.addAction( gui.ProcessAction )

        # Todo - way to delete game data from disk
        # - option to keep builds, releases

class GameContextMenu(GameBaseContextMenu):
    def __init__(self, parent, event):
        super().__init__(parent, event)
        self.start()

class CartridgePixmap(Scaled):
    def __init__(self, name):
        super().__init__('assets/images/{0}.png'.format(name), 150)
        self.Faded = Faded(self)

class CartridgeImage(QLabel):
    def __init__(self, cartridge):
        super().__init__()
        self.Cartridge = cartridge
        self.Game = cartridge.Game
        
        self.setAlignment(Qt.AlignCenter)

        self.LibraryPixmap = CartridgePixmap('cartridge')
        self.NotLibraryPixmap =  CartridgePixmap('cartridge_dark')

        self.Game.on('Library', self.update)
        self.Game.on('Excluding', self.update)

        self.Cartridge.add(self, 1, 1)

    def update(self, _):
        pixmap = self.LibraryPixmap if self.Game.Library else self.NotLibraryPixmap

        if self.Game.Excluding:
            pixmap = pixmap.Faded
            
        self.setPixmap(pixmap)

class LabelPixmap(QPixmap):
    def __init__(self, parent):
        dim = 92
        super().__init__(dim, dim)
        self.Game = parent.Game
        
        pixmap = Scaled(self.Game.Boxart, dim)

        self.fill(Qt.transparent)

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, QPainter.SmoothPixmapTransform)
        painter.setBrush(QBrush(pixmap))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 5, 5)

        self.Faded = Faded(self)

class LabelImage(Label):
    def __init__(self, cartridge, text=''):
        super().__init__(cartridge.GUI, text)
        self.Game = cartridge.Game
        
        self.Pixmap = LabelPixmap(self)
        self.Game.on('Excluding', self.update)
        
        CenterVH(self).addTo(cartridge, 1, 1)

    def update(self, _):
        self.setPixmap(self.Pixmap.Faded if self.Game.Excluding else self.Pixmap)

class GameTileTitle(Label):
    def __init__(self, parent):
        self.Game = parent.Game
        super().__init__(parent.GUI, self.Game.FullTitle)

        self.setWordWrap(True)
        CenterH(self).addTo(parent)
        
        self.Game.on('Excluding', self.updateExcluding)
        self.Game.on('Library', self.updateLibrary)

    def updateExcluding(self, excluding):
        self.setProperty("excluding", excluding)
        self.updateStyle()

    def updateLibrary(self, library):
        self.setProperty("library", library)
        self.updateStyle()

class GameTileTitleContainer(VBox):
    def __init__(self, cartridge):
        super().__init__(cartridge.GUI)
        self.Game = cartridge.Game
        self.Title = GameTileTitle(self)
        self.addStretch()
        self.addTo(cartridge, 1, 1)

class GameTileFavorites(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Icon = self.label()
        self.Pixmap = Scaled('assets/images/favorites.png', 20)
        self.Faded = Faded(self.Pixmap)
        self.addStretch()

        self.Game.on('Favorites', self.update)
        self.Game.on('Library', self.update)
        self.Game.on('Excluding', self.update)

        self.addTo(parent)

    def update(self, _):
        if self.Game.Favorites:
            self.Icon.setPixmap(self.Faded if self.Game.Excluding else self.Pixmap)
        else:
            self.Icon.clear()

class GameTileOutdated(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game
        
        self.addStretch()
        self.Icon = self.label()
        self.Pixmap = Scaled('assets/images/outdated.png', 25)

        self.Game.on('Outdated', self.updateOutdated)

        self.addTo(parent)

    def updateOutdated(self, outdated):
        if outdated:
            self.Icon.setPixmap(self.Pixmap)
        else:
            self.Icon.clear()

class GameTileIcons(VBox):
    def __init__(self, cartridge):
        super().__init__(cartridge.GUI)
        self.Game = cartridge.Game
        
        self.Favorites = GameTileFavorites(self)
        self.addStretch()
        self.Outdated = GameTileOutdated(self)
        self.addTo(cartridge, 1, 1)

class GameTile(Grid):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)

        self.GameGUI = gameGUI
        self.Game = gameGUI.Game

        self.Background = CartridgeImage(self)
        self.Label = LabelImage(self)
        self.Title = GameTileTitleContainer(self)
        self.IconContainer = GameTileIcons(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Panel.setActive(self.GameGUI)

    def contextMenuEvent(self, event):
        GameContextMenu(self, event)

