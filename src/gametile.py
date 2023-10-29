from src.gamebase import *
cartridges = ['red', 'blue', 'redblue', 'green', 'yellow', 'gold', 'silver', 'goldsilver', 'crystal', 'tcg', 'tcg2']

CartridgePixmaps = {}

def getCartridgePixmap(color):
    if color not in CartridgePixmaps:
        CartridgePixmaps[color] = CartridgePixmap('cartridge_' + color)

    return CartridgePixmaps[color]

class CartridgePixmap(Scaled):
    def __init__(self, name):
        super().__init__([135, 150], 'assets/images/{0}.png'.format(name))
        self.Faded = Faded(self)
        self.Darkened = Darkened(self)

# todo - skipping green for now
games = ['red', 'blue', 'yellow', 'gold', 'silver', 'crystal', 'tcg1', 'tcg2']

class CartridgeImage(Label):
    def __init__(self, cartridge):
        super().__init__()
        self.Cartridge = cartridge
        self.Game = cartridge.Game

        color = ''

        for game in games:
            if game in self.Game.tags:
                color += game

        if not color:
            color = 'gray'
        
        self.Cartridge.setProperty('color', color)

        self.LibraryPixmap = getCartridgePixmap(color) #CartridgePixmap('cartridge_' + color)
        self.NotLibraryPixmap =  self.LibraryPixmap.Darkened

        self.Game.on('Library', self.update)
        self.Game.on('Excluding', self.update)

        self.Cartridge.add(self, 1, 1)

    def update(self, _):
        pixmap = self.LibraryPixmap if self.Game.Library else self.NotLibraryPixmap

        if self.Game.Excluding:
            pixmap = pixmap.Faded
            
        self.setPixmap(pixmap)

class LabelPixmap(Pixmap):
    def __init__(self, parent):
        dim = 92
        super().__init__(dim)
        self.Game = parent.Game
        
        pixmap = Scaled(dim, self.Game.Boxart)

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, QPainter.SmoothPixmapTransform)
        painter.setBrush(QBrush(pixmap))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 5, 5)
        painter.end()

        self.Faded = Faded(self)

class LabelImage(Label):
    def __init__(self, cartridge, text=''):
        super().__init__(text)
        self.Game = cartridge.Game
        
        self.Pixmap = LabelPixmap(self)
        self.Game.on('Excluding', self.update)
        
        VHCenter(self).addTo(cartridge, 1, 1)

    def update(self, _):
        self.setPixmap(self.Pixmap.Faded if self.Game.Excluding else self.Pixmap)

class GameTileTitle(Label):
    def __init__(self, parent):
        self.Game = parent.Game
        super().__init__(self.Game.FullTitle)

        self.setWordWrap(True)
        self.setGraphicsEffect(OutlineShadow())
        HCenter(self).addTo(parent)
        
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
        self.Pixmap = Scaled(20, 'assets/images/favorites.png')
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
        self.Pixmap = Scaled(25, 'assets/images/outdated.png')

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
