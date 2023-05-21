import re, webbrowser
from enum import Enum
from src.gamebase import *

class GamePanelArtworkPixmap(Scaled):
    def __init__(self, game):
        super().__init__(game.Boxart, 300)
        self.Game = game
        self.Faded = Faded(self)

# TODO - right click context menu
class GamePanelArtwork(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)

        self.GUI = parent.GUI
        self.Game = parent.Game
        self.Pixmap = GamePanelArtworkPixmap(self.Game)

        self.Game.on('Excluding', self.updateExcluding)

        parent.add(self)

    def updateExcluding(self, excluding):
        if excluding:
            self.setPixmap(self.Pixmap.Faded)
        else:
            self.setPixmap(self.Pixmap)

class GameTags(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game
        self.addTo(parent)
        self.addStretch()
        self.Tags = [TagGUI(self, tag) for tag in self.Game.tags]
        self.addStretch()

class GameDescription(QLabel):
    def __init__(self, parent):
        self.Game = parent.Game
        super().__init__(self.Game.Description)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        parent.add(self)

class GamePanelBody(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game
        self.addTo(parent)

class RepositoryBody(GamePanelBody):
    def __init__(self, parent):
        super().__init__(parent)
        self.Author = AuthorField(self)
        self.Repository = RepositoryField(self)
        self.Basis = BasisField(self)
        self.RGBDS = GameRGBDSVersion(self)
        self.Trees = GameTrees(self)

class AuthorField(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Left = self.label('Author:', 1)

        self.Right = HBox(self.GUI)

        self.Author = self.Right.label(self.Game.author)
        self.Author.setAlignment(Qt.AlignCenter)
        self.Author.setObjectName('PanelClickable')
        self.Author.mousePressEvent = self.selectAuthor

        self.Folder = Icon(self.Right, 'assets/images/folder_15.png', 15)
        self.Folder.mouseDoubleClickEvent = self.openFolder

        self.URL = Icon(self.Right, 'assets/images/new_window.png', 15)
        self.URL.mouseDoubleClickEvent = self.openURL
        
        self.Right.addStretch()
        self.Right.addTo(self, 1)

        self.addTo(parent)

    def selectAuthor(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Manager.Catalogs.Authors.get(self.Game.author).GUI.handleClick()

    def openFolder(self, event):
        if event.button() == Qt.LeftButton:
            open_path(self.GUI.Manager.Directory + self.Game.author)

    def openURL(self, event):
        if event.button() == Qt.LeftButton:
            webbrowser.open(self.Game.author_url)

class RepositoryField(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Left = self.label('Repository:', 1)

        self.Right = HBox(self.GUI)

        self.Author = self.Right.label(self.Game.title)
        self.Author.setAlignment(Qt.AlignCenter)

        self.Folder = Icon(self.Right, 'assets/images/folder_15.png', 15)
        self.Folder.mouseDoubleClickEvent = self.openFolder

        self.URL = Icon(self.Right, 'assets/images/new_window.png', 15)
        self.URL.mouseDoubleClickEvent = self.openURL
        
        self.Right.addStretch()
        self.Right.addTo(self, 1)

        self.addTo(parent)

    def openFolder(self, event):
        if event.button() == Qt.LeftButton:
            open_path(self.Game.path["repo"])

    def openURL(self, event):
        if event.button() == Qt.LeftButton:
            webbrowser.open(self.Game.url)

class BasisField(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Left = self.label('Basis:', 1)

        hasBasis = 'basis' in self.Game.Data
        basis = self.Game.Data["basis"] if hasBasis else '-'

        self.Right = HBox(self.GUI)
        self.Basis = self.Right.label(basis)
        self.Basis.setAlignment(Qt.AlignCenter)
        self.Right.addStretch()
        self.Right.addTo(self, 1)

        self.BasisGame = None
        if hasBasis:
            self.Basis.setObjectName('PanelClickable')
            self.Basis.mousePressEvent = self.selectBasis
            [author, title] = basis.split('/')
            self.BasisGame = self.GUI.Manager.Catalogs.Authors.get(author).getGame(title)

        self.addTo(parent)

    def selectBasis(self, event):
        if self.BasisGame and event.button() == Qt.LeftButton:
            self.GUI.Panel.setActive(self.BasisGame.GUI)
class GameRGBDSVersion(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game
        
        self.Label = self.label("RGBDS:", 1)
        self.ComboBox = QComboBox()
        
        items = ["None"]
        default_index = 0
        
        for version in self.Game.Manager.RGBDS.ReleaseIDs:
            version = version[1:]
            if version == self.Game.rgbds and not default_index:
                default_index = len(items)
            # Custom takes priority
            if version == self.Game.RGBDS:
                default_index = len(items)

            items.append(version)

        items[default_index] += ' *'

        self.ComboBox.addItems(items)
        self.ComboBox.setCurrentIndex(default_index)

        self.ComboBox.currentTextChanged.connect(self.handleRGBDSSelected)

        self.ComboBoxContainer = HBox(self.GUI)
        self.ComboBoxContainer.addTo(self, 1)
        self.ComboBoxContainer.add(self.ComboBox)
        self.ComboBoxContainer.addStretch()

        self.addTo(parent)

    def handleRGBDSSelected(self, version):
        self.Game.set_RGBDS(version.split(' ')[0])

class GameTrees(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game
        
        self.Builds = BranchesTree(self)
        self.Tags = TagsTree(self)

        self.addTo(parent)

class GameTree(VBox):
    def __init__(self, parent, keys, label, delegate, contextMenus):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Tree = QTreeWidget()
        self.Tree.setFocusPolicy(Qt.NoFocus)
        self.Tree.header().setStretchLastSection(False)
        self.Tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.Tree.header().hide()
        self.Tree.setIndentation(10)
        self.Tree.setMouseTracking(True)

        self.TreeDelegate = delegate(self.Tree)
        self.Tree.setItemDelegateForColumn(0, self.TreeDelegate)
        self.TreeDelegate.RightClickSignal.connect(self.onRightClick)
        
        self.Types = Enum('Types', ['None', *contextMenus.keys()], start=1000)

        self.ContextMenus = {}
        for type, contextMenu in contextMenus.items():
            self.ContextMenus[self.Types[type].value] = contextMenu

        for key in keys:
            self.Game.on(key, self._draw, False)

        self.Game.PrimaryGameSignal.connect(self.onPrimaryGame)
        
        self._draw()

        self.Label = self.label(label + ':')
        self.add(self.Tree)
        self.addTo(parent, 1)

    def onPrimaryGame(self, path, item):
        if item == self.PrimaryGame:
            if not path:
                if self.PrimaryGame:
                    self.PrimaryGame.setIcon(0, QIcon())
            
                self.PrimaryGame = None
        else:
            if self.PrimaryGame:
                self.PrimaryGame.setIcon(0, QIcon())

            if path and item.Tree == self.Tree:
                item.setIcon(0, QIcon('assets/images/library_14.png'))
                self.PrimaryGame = item
            else:
                self.PrimaryGame = None

    def _draw(self):
        self.PrimaryGame = None
        self.Tree.blockSignals(True)
        self.Tree.clear()
        self.draw()
        self.Tree.blockSignals(False)

    def addItem(self, parent, type, text, path=None):
        item = QTreeWidgetItem(parent, self.Types[type].value)
        item.setText(0, text)
        item.path = path
        item.Tree = self.Tree
        return item
    
    def process(self, branch):
        self.GUI.startProcess([self.Game], branch)

    def specificProcess(self, branch, sequence):
        self.GUI.startSpecificProcess(sequence, [self.Game], branch)

    def downloadRelease(self, tag):
        self.GUI.downloadRelease(self.Game, tag)

    def onRightClick(self, event, item):
        type  = item.type()
        
        if type in self.ContextMenus:
            contextMenu = self.ContextMenus[type]
            contextMenu(self, item, event)

class OpenAction(Action):
    def __init__(self, parent, label, path):
        super().__init__(parent, label, lambda: open_path(path))

class OpenFolder(OpenAction):
    def __init__(self, parent, path):
        super().__init__(parent, "Open Folder", path)

class LaunchFile(OpenAction):
    def __init__(self, parent, path):
        super().__init__(parent, "Launch File", path)

class SwitchTo(Action):
    def __init__(self, parent, menu):
        super().__init__(parent, "Switch To", menu.switchTo)

class TreeContextMenu(ContextMenu):
    def __init__(self, parent, item, event):
        self.Item = item
        self.Name = item.text(0)
        self.Widget = parent
        self.Game = parent.Game
        self.Parent = parent.Tree.viewport()
        self.GUI = parent.GUI
        super().__init__(self.Parent, event)

class BranchContextMenu(TreeContextMenu):
    def __init__(self, *args):
        super().__init__(*args)

        self.addLabel(self.Name)
        if self.Name in self.Game.Branches and 'LastUpdate' in self.Game.Branches[self.Name]:
            self.addLabel(self.Game.Branches[self.Name]['LastUpdate'][:19])

        self.addSeparator()
        
        if self.canSwitchTo():
            self.addAction(SwitchTo(self.Parent, self))

        if self.Item.path and os.path.exists(self.Item.path):
            self.addAction( OpenFolder(self.Parent, self.Item.path) )

        if not self.GUI.Window.Process:
            self.addAction( Action(self.Parent, 'Build', lambda: self.Widget.specificProcess(self.Name, 'b')))

        self.start()

    def canSwitchTo(self):
        return not self.Item.isSelected() and not self.Game.Missing and not self.GUI.Window.Process and self.Name != self.Game.CurrentBranch
    
    def switchTo(self):
        if self.canSwitchTo():
            self.GUI.switchBranch(self.Game, self.Name)

class TagContextMenu(TreeContextMenu):
    def __init__(self, *args):
        super().__init__(*args)
        
        self.addLabel(self.Name)

        if hasattr(self.Item, 'date'):
            self.addLabel(self.Item.date)

        self.addSeparator()
        
        if not self.GUI.Window.Process:
            self.addAction( Action(self.Parent, 'Build', lambda: self.Widget.specificProcess(self.Item.commit, 'b')))
        
        self.start()

class FolderContextMenu(TreeContextMenu):
    def __init__(self, *args):
        super().__init__(*args)
        
        if self.Item.path and os.path.exists(self.Item.path):
            self.addAction( OpenFolder(self.Parent, self.Item.path) )

        self.start()

class ReleaseContextMenu(TreeContextMenu):
    def __init__(self, *args):
        super().__init__(*args)
        
        self.addLabel(self.Name)
        self.addLabel(self.Item.date)
        self.addSeparator()

        if self.Item.path and os.path.exists(self.Item.path):
            self.addAction( OpenFolder(self.Parent, self.Item.path) )

        if not self.GUI.Window.Process:
            self.addAction( Action(self.Parent, 'Download', lambda: self.Widget.downloadRelease(self.Item.text(0)) ))
            self.addAction( Action(self.Parent, 'Build', lambda: self.Widget.specificProcess(self.Item.commit, 'b')))
        
        self.start()

class FileContextMenu(TreeContextMenu):
    def __init__(self, *args):
        super().__init__(*args)
        
        if self.Item.path and os.path.exists(self.Item.path):
            self.addAction( LaunchFile(self.Parent, self.Item.path) )

            if self.Item.path == self.Game.PrimaryGame:
                self.addAction( Action(self.Parent, "Remove as Primary", lambda: self.Game.setPrimaryGame(None, self.Item)) )
            else:
                self.addAction( Action(self.Parent, "Set as Primary", lambda: self.Game.setPrimaryGame(self.Item.path, self.Item) ) )

        self.start()

class BranchesTree(GameTree):
    def __init__(self, parent):
        super().__init__(parent, ['Build','Branch'], 'Branches', BranchesTreeDelegate, {
            'Branch' : BranchContextMenu,
            'Build' : FolderContextMenu,
            'File' : FileContextMenu
        })

        self.Tree.itemChanged.connect(self.onItemChanged)

    def onItemChanged(self, item, col):
        if item.type() == self.Types["Branch"].value:
            self.Game.set_branch_tracking(item.text(0), True if item.checkState(col) == Qt.Checked else False)

    def draw(self):
        if self.Game.Branches:
            for branchName in self.Game.Branches:
                branchItem = self.addItem(self.Tree, 'Branch', branchName, self.Game.path['builds'] + branchName)
                branchItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

                if branchName == self.Game.CurrentBranch:
                    branchItem.setSelected(True)

                branchItem.setCheckState(0, Qt.Checked if self.Game.check_branch_tracking(branchName) else Qt.Unchecked)

                if os.path.exists(branchItem.path) and branchName in self.Game.builds:
                    branchBuilds = self.Game.builds[branchName]
                    builds = list(branchBuilds.keys())
                    builds.sort()

                    for buildName in reversed(builds):
                        buildItem = self.addItem(branchItem, 'Build', buildName, self.Game.path['builds'] + branchName + '/' + buildName)

                        for fileName, path in branchBuilds[buildName].items():
                            path = str(path)
                            fileItem = self.addItem(buildItem, 'File', fileName, path)
                            if path == self.Game.PrimaryGame:
                                self.onPrimaryGame(path, fileItem)
        else:
            noneItem = self.addItem(self.Tree, 'None', "None")
            noneItem.setFlags(Qt.NoItemFlags)

class TreeDelegate(QStyledItemDelegate):
    RightClickSignal = pyqtSignal(QEvent, QTreeWidgetItem)

    def __init__(self, tree, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Tree = tree

class BranchesTreeDelegate(TreeDelegate):
    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonDblClick:
            return True
        
        if event.type() == QEvent.MouseButtonPress:
            # rect does not include the side arrow or whitespace
            labelRect = self.Tree.style().subElementRect(QStyle.SE_TreeViewDisclosureItem, option)
            
            # rect will not include the checkbox
            textOnlyRect = self.Tree.style().subElementRect(QStyle.SE_CheckBoxContents, option)

            # rect will include checkbox
            checkboxRect = self.Tree.style().subElementRect(QStyle.SE_CheckBoxIndicator, option)
            checkboxRect.setLeft(checkboxRect.left() + 4) # for some reason, this rect includes are left of checkbox
            
            pos = event.pos()
            item = self.Tree.itemFromIndex(index)

            clickableRect = None

            if not (item.flags() & Qt.ItemIsUserCheckable):
                clickableRect = labelRect
            elif pos not in checkboxRect:
                clickableRect = textOnlyRect
                    
            if clickableRect:
                if pos in clickableRect:
                    # toggle expanded on left click
                    if event.button() == Qt.LeftButton:
                        if item.childCount():
                            item.setExpanded(not item.isExpanded())
                    # emit signal on right click
                    elif event.button() == Qt.RightButton:
                        self.RightClickSignal.emit(event, item)
                return True
            
            # Ignore right clicks outside of clickable rect
            if event.button() == Qt.RightButton:
                return True

        return super().editorEvent(event, model, option, index)

class TagsTree(GameTree):
    def __init__(self, parent):
        super().__init__(parent, ['Release'], 'Tags', TagsTreeDelegate, {
            'Tag' : TagContextMenu,
            'Release' : ReleaseContextMenu,
            'Build' : FolderContextMenu,
            'File' : FileContextMenu
        })

    def draw(self):
        if self.Game.GitTags:
            tags = list(self.Game.GitTags.keys())
            tags.sort()

            for tagName in reversed(tags):
                tagData = self.Game.GitTags[tagName]
                
                releaseName = None

                if 'release' in tagData:
                    releaseName = tagData['release']
                    tagItem = self.addItem(self.Tree, 'Release', tagName, self.Game.path['releases'] + releaseName)
                    tagItem.date = re.match(r'^(\d{4}-\d{2}-\d{2}) - .* \(.*\)$', releaseName).group(1)                
                else:
                    tagItem = self.addItem(self.Tree, 'Tag', tagName)

                tagItem.commit = tagData["commit"]
                if 'date' in tagData:
                    tagItem.date = tagData['date'][:19]

                if tagData["commit"] in self.Game.commits:
                    if not releaseName:
                        releaseName = tagData['date'][:10] + ' - ' + tagName + ' (' + tagName + ')'
                    
                    commitBuilds = self.Game.commits[tagData["commit"]]
                    builds = list(commitBuilds.keys())
                    builds.sort()
                    for buildName in reversed(builds):
                        buildItem = self.addItem(tagItem, 'Build', buildName, self.Game.path['releases'] + releaseName + '/' + buildName)

                        for fileName, path in commitBuilds[buildName].items():
                            path = str(path)
                            fileItem = self.addItem(buildItem, 'File', fileName, path)
                            if path == self.Game.PrimaryGame:
                                self.onPrimaryGame(path, fileItem)

                if 'release' in tagData:
                    if releaseName in self.Game.releases:
                        for fileName, path in self.Game.releases[releaseName].items():
                            path = str(path)
                            fileItem = self.addItem(tagItem, 'File', fileName, path)
                            if path == self.Game.PrimaryGame:
                                self.onPrimaryGame(path, fileItem)
        else:
            noneItem = self.addItem(self.Tree, 'None', "None")
            noneItem.setFlags(Qt.NoItemFlags)
            
class TagsTreeDelegate(TreeDelegate):
    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.MouseButtonDblClick:
            return True
        
        if event.type() == QEvent.MouseButtonPress:
            # rect does not include the side arrow or whitespace
            labelRect = self.Tree.style().subElementRect(QStyle.SE_TreeViewDisclosureItem, option)
            
            pos = event.pos()
            item = self.Tree.itemFromIndex(index)

            if pos in labelRect:
                # toggle expanded on left click
                if event.button() == Qt.LeftButton:
                    if item.childCount():
                        item.setExpanded(not item.isExpanded())
                # emit signal on right click
                elif event.button() == Qt.RightButton:
                    self.RightClickSignal.emit(event, item)
            return True

        return super().editorEvent(event, model, option, index)

class PatchBody(GamePanelBody):
    def __init__(self, parent):
        super().__init__(parent)
        self.BaseROM = Field(self, 'Base', '<Select Base ROM>')

class PanelIcon(QLabel):
    def __init__(self, parent, name):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.GUI = parent.GUI
        self.Game = parent.Game
        self.Pixmap = Scaled('assets/images/{}.png'.format(name.lower()), 35)
        self.Faded = Faded(self.Pixmap)

        self.Game.on(name, self.update)

        CenterH(self).addTo(parent)

    def update(self, value):
        self.setPixmap(self.Pixmap if value else self.Faded)
        
class PanelIconFavorites(PanelIcon):
    def __init__(self, parent):
        super().__init__(parent, 'Favorites')

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.Game.setFavorites(not self.Game.Favorites)

class PanelIconFolder(Icon):
    def __init__(self, parent):
        super().__init__(parent, 'assets/images/folder.png', 35)
        self.GUI = parent.GUI
        self.Game = parent.Game
        CenterH(self).addTo(parent)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            open_path(self.Game.path['base'])
        
class PanelIconLibrary(PanelIcon):
    def __init__(self, parent):
        super().__init__(parent, 'Library')
        self.isDoubleClick = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pass
            # TODO - launch most recent build, or preset build
        
class PanelIconOutdated(PanelIcon):
    def __init__(self, parent):
        super().__init__(parent, 'Outdated')

    # TODO - either check for updated, or download update?
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pass

class IconsRight(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Favorites = PanelIconFavorites(self)
        self.Library = PanelIconLibrary(self)
        self.Outdated = PanelIconOutdated(self)

        self.addStretch()
        CenterH(self).addTo(parent)

class IconsLeft(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Folder = PanelIconFolder(self)

        self.addStretch()
        CenterH(self).addTo(parent)

class ArtworkIconContainer(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.IconsLeft = IconsLeft(self)
        self.Artwork = GamePanelArtwork(self)
        self.IconsRight = IconsRight(self)
        self.addTo(parent)


# TODO - way to open directory to game
class GamePanel(VBox):
    def __init__(self, gameGUI):
        super().__init__(gameGUI.GUI)
        self.GameGUI = gameGUI
        self.Game = gameGUI.Game

        self.ArtworkIconContainer = ArtworkIconContainer(self)
        self.Tags = GameTags(self)
        self.Description = GameDescription(self)
        
        # If a git repository
        if "repo" in self.Game.path:
            self.Body = RepositoryBody(self)
        # if a patch:
        else:
            self.Body = PatchBody(self)
