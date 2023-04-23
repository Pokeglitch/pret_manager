from src.base import *

class SearchBox(QLineEdit):
    def __init__(self, searchList):
        super().__init__()
        self.Mode = "And"
        self.setPlaceholderText("Search")
        self.SearchList = searchList
        self.textChanged.connect(self.SearchList.onTextChanged)
        searchList.Manager.GUI.Content.Catalogs.Header.SearchContainer.add(self)

    def getData(self):
        return self.SearchList.GameList[:]

class CatalogEntryContextMenu(ContextMenu):
    def __init__(self, parent, event):
        super().__init__(parent, event)

        self.addAction( parent.AddToQueue )
        self.addAction( parent.RemoveFromQueue )

        if parent.Data != parent.GUI.Manager.Catalogs.Lists.get('Favorites'):
            self.addAction( parent.AddToFavorites )
            self.addAction( parent.RemoveFromFavorites )

        if parent.Data != parent.GUI.Manager.Catalogs.Lists.get('Excluding'):
            self.addAction( parent.AddToExcluding )
            self.addAction( parent.RemoveFromExcluding )

        # Add to list/ remove from list (except itself)
        lists = []

        for name, list in parent.GUI.Manager.Catalogs.Lists.Entries.items():
            if name not in parent.GUI.Manager.BaseLists and list != parent.Data:
                lists.append(list)

        self.addMenu( AddListToListMenu(parent, lists) )

        if lists:
            self.addMenu( RemoveListFromListMenu(parent, lists) )

        # if list, add Erase option
        if hasattr(parent, 'EraseAction'):
            self.addAction( parent.EraseAction )

        self.start()

class CatalogEntryGUI(HBox):
    def __init__(self, data):
        parent = data.Catalog.GUI
        super().__init__(parent.GUI)
        self.Data = data
        self.Name = data.Name
        self.Label = self.label(data.Name)
        self.Mode = None

        self.AddToQueue = AddToQueue(self)
        self.RemoveFromQueue = RemoveFromQueue(self)

        self.AddToFavorites = AddToFavorites(self)
        self.RemoveFromFavorites = RemoveFromFavorites(self)

        self.AddToExcluding = AddToExcluding(self)
        self.RemoveFromExcluding = RemoveFromExcluding(self)

        self.addTo(parent)

    def getData(self):
        return self.Data.GameList[:]

    def setMode(self, mode):
        self.Mode = mode
        self.setProperty("mode",mode)
        self.updateStyle()

    def contextMenuEvent(self, event):
        CatalogEntryContextMenu(self, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            mode = self.GUI.Catalogs.Mode
            if mode == self.Mode:
                self.GUI.Tiles.remove(self)
                self.setMode(None)
            else:
                getattr(self.GUI.Tiles,'add' + mode.upper())(self)
                self.setMode(mode)

    def addToQueueHandler(self):
        self.GUI.Queue.addGames(self.getData())

    def removeFromQueueHandler(self):
        self.GUI.Queue.removeGames(self.getData())

    def addToFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Lists.get('Favorites').addGames(self.getData())

    def removeFromFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Lists.get('Favorites').removeGames(self.getData())

    def addToExcludingHandler(self):
        self.GUI.Manager.Catalogs.Lists.get('Excluding').addGames(self.getData())

    def removeFromExcludingHandler(self):
        self.GUI.Manager.Catalogs.Lists.get('Excluding').removeGames(self.getData())

class ListEntryGUI(CatalogEntryGUI):
    def __init__(self, *args):
        super().__init__(*args)
        self.EraseAction = EraseList(self)

    def erase(self):
        self.Data.erase()
        if self.Data.Name not in self.GUI.Manager.BaseLists:
            self.addTo(None)

class CatalogModesRow(HBox):
    def __init__(self, parent, mode):
        super().__init__(parent.GUI)
        self.addStretch()
        self.Icon = CatalogsModeIcon(self, mode)
        self.addTo(parent)

class CatalogModes(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)

        self.Or = CatalogModesRow(self, 'Or')
        self.Not = CatalogModesRow(self, 'Not')
        self.And = CatalogModesRow(self, 'And')
        self.addTo(parent)

class CatalogsTabs(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)

        self.ListTab = CatalogIcon(self, 'assets/images/list.png', 0)
        self.AuthorsTab = CatalogIcon(self, 'assets/images/author.png', 1)
        self.TagsTab = CatalogIcon(self, 'assets/images/tag.png', 2)

        self.ActiveTab = self.ListTab
        self.ActiveTab.setActive(True)

        self.addStretch()
        
        self.Modes = CatalogModes(self)

        self.addTo(parent, 1)

    def setCatalog(self, tab):
        if tab != self.ActiveTab:
            self.ActiveTab.setActive(None)
            self.Parent.Container.Stack.setCurrentIndex(tab.Index)
            self.ActiveTab = tab

class CatalogIcon(Icon):
    def __init__(self, parent, image, index):
        super().__init__(parent, image, 35)
        self.Index = index

    def mousePressEvent(self, e):
        self.setActive(True)
        self.Parent.setCatalog(self)

class CatalogsContainer(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Mode = 'New'

        self.Stack = QStackedWidget()
        self.add(self.Stack)
        self.addTo(parent, 2)

class CatalogGUI(VBox):
    def __init__(self, data):
        parent = data.Manager.GUI.Content.Catalogs.Body.Container
        self.Data = data
        ID = data.Name
        super().__init__(parent.GUI)

        self.ID = ID[:-1]
        self.List = {}

        self.ListContainer = VScroll(parent.GUI)
        self.ListContainer.addTo(self)

        self.ListGUI = VBox(parent.GUI)
        self.ListGUI.addTo(self.ListContainer)
        self.ListContainer.addStretch()

        parent.Stack.addWidget(self)

    def addElement(self, name):
        self.Class(self, name)

    def add(self, widget, *args):
        if hasattr(widget,'Name'):
            self.List[widget.Name] = widget
            self.ListGUI.add(widget, *args)
        else:
            super().add(widget, *args)


class CatalogsBody(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)

        self.Tabs = CatalogsTabs(self)
        self.Container = CatalogsContainer(self)

        self.addTo(parent)

class CatalogsHeader(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.setObjectName("header-frame")

        self.Label = self.label("Filter", 1)
        self.Label.setAlignment(Qt.AlignCenter)
        self.Label.setObjectName("header")

        self.SearchContainer = HBox(self)
        self.SearchContainer.addTo(self, 2)

        self.addTo(parent)

class CatalogsModeIcon(Icon):
    def __init__(self, parent, mode):
        super().__init__(parent, 'assets/images/' + mode.lower() + '.png', 15)
        
        self.Mode = mode
        self.setProperty('mode',mode)
        self.setProperty('active',False)

    def mousePressEvent(self, e):
        self.GUI.Catalogs.setMode(self.Mode)

class Catalogs(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Header = CatalogsHeader(self)
        self.Body = CatalogsBody(self)
        self.Mode = 'New'

        self.addTo(parent.Col1, 2)

    def setMode(self, mode):
        if mode == self.Mode:
            getattr(self.Body.Tabs.Modes, self.Mode).Icon.setActive(False)
            self.Mode = 'New'
        else:
            if self.Mode != 'New':
                getattr(self.Body.Tabs.Modes, self.Mode).Icon.setActive(False)
            self.Mode = mode
            getattr(self.Body.Tabs.Modes, mode).Icon.setActive(True)
