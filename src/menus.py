from src.actions import *
from src.qt.events import *

class AddGameToListMenu(Menu):
    Label = "Add To List"

    def init(self, lists):
        for list in lists:
            self.addAction( AddToList(self.Parent, list) )

        self.addAction( NewList(self.Parent.GameGUI) )

class AddListToListMenu(Menu):
    Label = "Add To List"

    def init(self, lists):
        for list in lists:
            self.addAction( AddToList(self.Parent, list))

        self.addAction( NewList(self.Parent) )

class RemoveFromListMenu(Menu):
    Label = "Remove From List"

    def init(self, lists):
        for list in lists:
            self.addAction( RemoveFromList(self.Parent, list) )

class QueueMenu(Menu):
    Label = "Queue"

    def init(self):
        self.addAction( AddToQueue(self.Parent) )
        self.addAction( RemoveFromQueue(self.Parent) )
        
class ListsMenu(Menu):
    Label = "Lists"

    def init(self, lists):
        self.addMenu( AddListToListMenu(self.Parent, lists) )

        if lists:
            self.addMenu( RemoveFromListMenu(self.Parent, lists) )

class FavoritesMenu(Menu):
    Label = "Favorites"

    def init(self):
        self.addAction( AddToFavorites(self.Parent) )
        self.addAction( RemoveFromFavorites(self.Parent) )

class ExcludingMenu(Menu):
    Label = "Excluding"

    def init(self):
        self.addAction( AddToExcluding(self.Parent) )
        self.addAction( RemoveFromExcluding(self.Parent) )

class ProcessesMenu(Menu):
    Label = "Process"

    def init(self, target=None):
        if target is None:
            target = self.Parent

        self.addAction( ProcessCurrentSequenceAction(target) )
        self.addAction( RefreshProcessAction(self.Parent, target) )
        self.addAction( UpdateProcessAction(self.Parent, target) )
        self.addAction( CleanProcessAction(self.Parent, target) )
        self.addAction( BuildProcessAction(self.Parent, target) )
