import re, webbrowser
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
        self.Branches = GameBranches(self)
        self.Commit = Field(self, 'Commit', '-')
        self.LastUpdate = Field(self, 'Last Update', '-')
        self.RGBDS = GameRGBDSVersion(self)
        self.Trees = GameTrees(self)

        self.Game.on("Branch", self.updateCommitData)

    def updateCommitData(self):
        if self.Game.CurrentBranch:
            data = self.Game.Branches[self.Game.CurrentBranch]
            self.Commit.Right.setText(data['LastCommit'][:8] if 'LastCommit' in data else '-')
            self.LastUpdate.Right.setText(data['LastUpdate'][:19] if 'LastUpdate' in data else '-')
        else:
            self.Commit.Right.setText('-')
            self.LastUpdate.Right.setText('-')

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
            openDir(self.GUI.Manager.Directory + self.Game.author)

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
            openDir(self.Game.path["repo"])

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

class GameBranches(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Label = self.label("Branch:")
        self.ComboBox = QComboBox()
        self.ComboBox.currentTextChanged.connect(self.handleBranchSelected)
        self.add(self.ComboBox)

        self.GUI.Window.Processing.connect(self.handleProcessing)

        self.Game.on("Branch", self.updateComboBox)

        self.addTo(parent)
        
    def handleProcessing(self, processing):
        self.ComboBox.setEnabled(not processing)
        self.ComboBox.setProperty('processing', processing)
        self.ComboBox.style().polish(self.ComboBox)

    def handleBranchSelected(self, branch):
        if not self.Game.Missing and not self.GUI.Window.Process and branch != self.Game.CurrentBranch:
            self.GUI.switchBranch(self.Game, branch)

    def updateComboBox(self):
        self.ComboBox.blockSignals(True)

        self.ComboBox.clear()
        self.ComboBox.addItems(self.Game.Branches.keys())

        if self.Game.CurrentBranch:
            self.ComboBox.setCurrentText(self.Game.CurrentBranch)

        self.ComboBox.blockSignals(False)

class GameRGBDSVersion(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game
        
        self.Label = self.label("RGBDS:")
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
        self.add(self.ComboBox)
        self.addTo(parent)

    def handleRGBDSSelected(self, version):
        self.Game.set_RGBDS(version.split(' ')[0])

class GameTrees(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Game = parent.Game
        
        self.Builds = BuildsTree(self)
        self.Releases = ReleasesTree(self)

        self.addTo(parent)

class GameTree(VBox):
    def __init__(self, parent, key):
        super().__init__(parent.GUI)
        self.Game = parent.Game

        self.Tree = QTreeWidget()
        self.Tree.setFocusPolicy(Qt.NoFocus)
        self.Tree.header().setStretchLastSection(False)
        self.Tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.Tree.header().hide()
        self.Tree.setIndentation(10)
        self.Tree.itemDoubleClicked.connect(lambda e: hasattr(e,"Path") and QDesktopServices.openUrl(e.Path))
        
        self.Game.on(key, self.draw)

        self.add(self.Tree)
        self.addTo(parent, 1)

class BuildsTree(GameTree):
    def __init__(self, parent):
        super().__init__(parent, 'Build')

    def draw(self):
        self.Tree.clear()

        buildsItem = QTreeWidgetItem(self.Tree)
        buildsItem.setText(0, "Builds:")
        buildsItem.setExpanded(True)
        
        if self.Game.builds.keys():
            buildsItem.Path = QUrl.fromLocalFile(self.Game.path['builds'])

            for branchName, branchBuilds in self.Game.builds.items():
                branchItem = QTreeWidgetItem(buildsItem)
                branchItem.setText(0, branchName)
                branchItem.Path = QUrl.fromLocalFile(self.Game.path['builds'] + branchName)

                builds = list(branchBuilds.keys())
                builds.sort()

                for buildName in reversed(builds):
                    roms = branchBuilds[buildName]
                    buildItem = QTreeWidgetItem(branchItem)
                    buildItem.setText(0, buildName)
                    buildItem.Path = QUrl.fromLocalFile(self.Game.path['builds'] + branchName + '/' + buildName)

                    for romName, path in roms.items():
                        romItem = QTreeWidgetItem(buildItem)
                        romItem.setText(0, romName)
                        romItem.Path = QUrl.fromLocalFile(str(path))
        else:
            noneItem = QTreeWidgetItem(buildsItem)
            noneItem.setText(0, "None")

class ReleasesTree(GameTree):
    def __init__(self, parent):
        super().__init__(parent, 'Release')

    def draw(self):
        self.Tree.clear()
        releasesItem = QTreeWidgetItem(self.Tree)
        releasesItem.setText(0, "Releases:")
        releasesItem.setExpanded(True)

        if self.Game.releases.keys():
            releasesItem.Path = QUrl.fromLocalFile(self.Game.path['releases'])

            releases = list(self.Game.releases.keys())
            releases.sort()

            for releaseName in reversed(releases):
                releases = self.Game.releases[releaseName]
                releaseItem = QTreeWidgetItem(releasesItem)
                releaseItem.setText(0, re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', releaseName).group(1))
                releaseItem.Path = QUrl.fromLocalFile(self.Game.path['releases'] + releaseName)

                for romName, path in releases.items():
                    romItem = QTreeWidgetItem(releaseItem)
                    romItem.setText(0, romName)
                    romItem.Path = QUrl.fromLocalFile(str(path))
        else:
            noneItem = QTreeWidgetItem(releasesItem)
            noneItem.setText(0, "None")

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
            openDir(self.Game.path['base'])
        
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
