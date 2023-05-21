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

        games = parent.getData()

        if games:
            self.addMenu(QueueMenu(parent))

            if parent.Data != parent.GUI.Manager.Catalogs.Flags.get('Favorites'):
                self.addMenu( FavoritesMenu(parent) )

            if parent.Data != parent.GUI.Manager.Catalogs.Flags.get('Excluding'):
                self.addMenu( ExcludingMenu(parent) )

            # Add to list/ remove from list (except itself)
            lists = []

            for list in parent.GUI.Manager.Catalogs.Lists.Entries.values():
                if list != parent.Data:
                    lists.append(list)

            self.addMenu(ListsMenu(parent, lists))
        
        if games and not parent.GUI.Window.Process:
            self.addMenu( ProcessesMenu(parent) )

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

        self.ProcessAction = ProcessAction(self)
        self.NewList = NewList(self)

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
            self.handleClick()

    def handleClick(self):
        mode = self.GUI.Catalogs.Mode
        if mode == self.Mode:
            self.GUI.Tiles.remove(self)
            self.setMode(None)
        else:
            getattr(self.GUI.Tiles,'add' + mode.upper())(self)
            self.setMode(mode)

    def process(self):
        if self.Data.GameList:
            self.GUI.startProcess(self.getData())

    def specificProcess(self, sequence):
        if self.Data.GameList:
            self.GUI.startSpecificProcess(sequence, self.getData())

    def addToQueueHandler(self):
        self.GUI.Queue.addGames(self.getData())

    def removeFromQueueHandler(self):
        self.GUI.Queue.removeGames(self.getData())

    def addToFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Favorites').addGames(self.getData())

    def removeFromFavoritesHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Favorites').removeGames(self.getData())
            
    def addToExcludingHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Excluding').addGames(self.getData())
            
    def removeFromExcludingHandler(self):
        self.GUI.Manager.Catalogs.Flags.get('Excluding').removeGames(self.getData())
            
    def saveList(self):
        self.GUI.saveList(self.getData())

class ListEntryGUI(CatalogEntryGUI):
    def __init__(self, *args):
        super().__init__(*args)
        self.EraseAction = EraseList(self)

    def erase(self):
        self.Data.erase()
        self.addTo(None)

class FlagListEntryGUI(CatalogEntryGUI):
    def __init__(self, *args):
        super().__init__(*args)
        self.Icon = Icon(self, 'assets/images/{}_25.png'.format(self.Name.lower()), 25)
        self.add(self.Label)
        self.addStretch()

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
        self.Body = parent

        self.TabCount = 0

        self.Container = VBox(self.GUI)
        self.Container.addTo(self)

        self.addStretch()
        self.Modes = CatalogModes(self)

        self.addTo(parent, 1)

    def addTab(self, name):
        tab = CatalogIcon(self, 'assets/images/{0}.png'.format(name.lower()), self.TabCount )

        if not self.TabCount:
            self.ActiveTab = tab
            tab.setActive(True)
        
        self.TabCount += 1

    def setCatalog(self, tab):
        if tab != self.ActiveTab:
            self.ActiveTab.setActive(None)
            self.Body.Container.Stack.setCurrentIndex(tab.Index)
            self.ActiveTab = tab

class CatalogIcon(Icon):
    def __init__(self, parent, image, index):
        self.Index = index
        self.Tabs = parent

        super().__init__(parent.Container, image, 35)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setActive(True)
            self.Tabs.setCatalog(self)

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

        self.ListContainer = VScroll(self.GUI)
        self.ListContainer.addTo(self)
        self.drawContent()
        self.ListContainer.addStretch()

        self.Tab = data.Manager.GUI.Content.Catalogs.Body.Tabs.addTab(ID)

        parent.Stack.addWidget(self)

    def drawContent(self):
        self.ListContent = VBox(self.GUI)
        self.ListContent.addTo(self.ListContainer)

    def add(self, widget, *args):
        if hasattr(widget,'Name'):
            self.List[widget.Name] = widget
            self.addToContent(widget, *args)
        else:
            super().add(widget, *args)

    def addToContent(self, widget, *args):
        self.ListContent.add(widget, *args)

class TagCatalogGUI(CatalogGUI):   
    def drawContent(self):
        self.ListContent = HBox(self.GUI)
        self.ListContent.addTo(self.ListContainer)

        self.Col1Container = VBox(self.GUI)
        self.Col1 = VBox(self.GUI)
        self.Col1.addTo(self.Col1Container)
        self.Col1Container.addStretch()
        self.Col1Container.addTo(self.ListContent)

        self.Col2Container = VBox(self.GUI)
        self.Col2 = VBox(self.GUI)
        self.Col2.addTo(self.Col2Container)
        self.Col2Container.addStretch()
        self.Col2Container.addTo(self.ListContent)
        
        self.Col1Widgets = [self.Col1.label(tag) for tag in OfficialTags]

    def addToContent(self, widget, *args):
        if widget.Name in OfficialTags:
            index = OfficialTags.index(widget.Name)
            self.Col1.Layout.replaceWidget(self.Col1Widgets[index], widget, *args)
        else:
            self.Col2.add(widget, *args)

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
        if e.button() == Qt.LeftButton:
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
