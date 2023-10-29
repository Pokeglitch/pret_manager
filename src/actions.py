from src.qt.events import Action
from src.core.functions import *

class TerminateProcess(Action):
    Label = "Terminate"
    Key = "terminateProcess"

class AddToQueue(Action):
    Label = "Add to Queue"
    Key = "addToQueueHandler"

class RemoveFromQueue(Action):
    Label = "Remove From Queue"
    Key = "removeFromQueueHandler"

class AddToFavorites(Action):
    Label = "Add To Favorites"
    Key = "addToFavoritesHandler"

class RemoveFromFavorites(Action):
    Label = "Remove From Favorites"
    Key = "removeFromFavoritesHandler"

class AddToExcluding(Action):
    Label = "Add To Excluding"
    Key = "addToExcludingHandler"

class RemoveFromExcluding(Action):
    Label = "Remove From Excluding"
    Key = "removeFromExcludingHandler"

class OpenAction(Action):
    def __init__(self, parent, path):
        super().__init__(parent, lambda: open_path(path))

class OpenFolder(OpenAction):
    Label = "Open Folder"

class LaunchFile(OpenAction):
    Label = "Launch File"

class SwitchTo(Action):
    Label = "Switch To"

class EraseAction(Action):
    Key = "erase"

class NewList(Action):
    Label = "New List"
    Key = "saveList"

class EraseList(EraseAction):
    Label = "Erase List"

class ClearBrowser(EraseAction):
    Label = "Clear Filter"

class ClearQueue(EraseAction):
    Label = "Clear Queue"

class SetAsDefaultQueue(Action):
    Label = "Set as Default"
    Key = "setAsDefault"

class ProcessCurrentSequenceAction(Action):
    Label = "Current Sequence"
    Key = "process"

class ListAction(Action):
    def __init__(self, parent, list):
        super().__init__(parent, lambda: getattr(list, self.Key)(parent.getData()), list.Name)

class AddToList(ListAction):
    Key = "addGames"

class RemoveFromList(ListAction):
    Key = "removeGames"

class ProcessAction(Action):
    def __init__(self, parent, target, *args):
        super().__init__(parent, lambda: target.specificProcess(self.Key, *args))

class RefreshProcessAction(ProcessAction):
    Label = "Refresh"
    Key = "r"

class UpdateProcessAction(ProcessAction):
    Label = "Update"
    Key = "u"

class CleanProcessAction(ProcessAction):
    Label = "Clean"
    Key = "c"

class BuildProcessAction(ProcessAction):
    Label = "Build"
    Key = "b"

class ApplyPatchAction(BuildProcessAction):
    Label = "Apply Patch"

class LaunchGameAction(Action):
    Label = "Launch Game"

class DownloadReleaseAction(Action):
    Label = "Download"

class RemovePrimaryAction(Action):
    Label = "Remove as Primary"

class SetPrimaryAction(Action):
    Label = "Set as Primary"

class DownloadGuidesAction(Action):
    Label = "Download"
    Key = "downloadGuides"
