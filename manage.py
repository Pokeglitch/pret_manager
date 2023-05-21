#!/usr/bin/env python

import os, re, argparse, json, signal
from pathlib import Path
import gui
from src.base import *
from src.Environment import *
from src.Files import *
from PyQt5.QtCore import pyqtSignal

build_extensions = ['gb','gbc','pocket','patch']
release_extensions = build_extensions + ['ips','bps','bsp','zip']
repo_metadata_properties = ['PrimaryGame','Branches','GitTags','CurrentBranch','RGBDS','Excluding','Favorites']
rgbds_files = ['rgbasm','rgbfix','rgblink','rgbgfx']

def error(msg):
    raise Exception('Error:\t' + msg)

def get_files(path):
    return next(os.walk(path))[2]

def get_releases(path):
    return [file for file in Path(path).iterdir() if file.suffix[1:] in release_extensions]

def get_builds(path):
    return [file for file in Path(path).iterdir() if file.suffix[1:] in build_extensions]

def get_rgbds(path):
    return [file for file in Path(path).iterdir() if file.name in rgbds_files]

# remove invalid windows path chars from name
def legal_name(name):
    return re.sub(r'[<>:"/\|?*]', '', name)

# Ensure all necessary base directories exist
games_dir = 'games/'
data_dir = 'data/'
list_dir = data_dir + 'lists/'
mkdir(games_dir, list_dir)

class CatalogEntry:
    def __init__(self, catalog, name):
        self.Catalog = catalog
        self.Manager = catalog.Manager
        self.Name = name
        self.GameStructure = {}
        self.GameList = []
        self.GUI = self.build_GUI() if catalog.GUI else None

    def build_GUI(self):
        return gui.CatalogEntryGUI(self)

    def has(self, game):
        return game in self.GameList

    def reset(self):
        self.GameStructure = {}
        self.GameList = []

    def addGame(self, game):
        if game not in self.GameList:
            self.GameList.append(game)

    def removeGame(self, game):
        if game in self.GameList:
            self.GameList.pop(self.GameList.index(game))

class AuthorEntry(CatalogEntry):
    def __init__(self, *args):
        super().__init__(*args)

        author_dir = games_dir + self.Name
        # if the author directory exists, but is empty, remove
        if os.path.exists(author_dir) and not get_dirs(author_dir):
            self.rmdir(author_dir, 'No games found for Author: ' + self.Name)

    def getGame(self, title):
        return self.GameStructure[title]

    def addGame(self, game):
        if game.title not in self.GameStructure:
            self.GameStructure[game.title] = game
        super().addGame(game)

    def removeGame(self, game):
        if game.title in self.GameStructure:
            del self.GameStructure[game.title]
        super().removeGame(game)

class TagEntry(CatalogEntry):
    def build_GUI(self):
        GUI = super().build_GUI()
        GUI.Label.setParent(None)
        GUI.TagGUI = gui.TagGUI(GUI, self.Name)
        return GUI

class BaseListEntry(CatalogEntry):
    def reset(self, isPermanent=False):
        self.removeGames(self.GameList[:], isPermanent)

    def addGame(self, game):
        super().addGame(game)
        if game.author not in self.GameStructure:
            self.GameStructure[game.author] = [game.title]
        else:
            self.GameStructure[game.author].append(game.title)

    def addGames(self, games):
        self.removeFromFilter()

        isChanged = False
        for game in games:
            if game not in self.GameList:
                isChanged = True
                self.addGame(game)
                
        self.addToFilter()

        if isChanged:
            self.write()

    def removeGame(self, game):
        super().removeGame(game)
        self.GameStructure[game.author].pop( self.GameStructure[game.author].index(game.title) )
        if not self.GameStructure[game.author]:
            del self.GameStructure[game.author]

    def removeGames(self, games, isPermanent=False):
        self.removeFromFilter()

        isChanged = False
        for game in games:
            if game in self.GameList:
                isChanged = True
                self.removeGame(game)
                
        if isPermanent:
            self.GUI.setMode(None)
            self.Manager.GUI.Content.Tiles.refresh()
        else:
            self.addToFilter()

        if isChanged:
            self.write()

    def toggleGames(self, games):
        self.removeFromFilter()

        for game in games:
            if game in self.GameList:
                self.removeGame(game)
            else:
                self.addGame(game)

        self.addToFilter()

        if games:
            self.write()

    def removeFromFilter(self):
        if self.GUI and self.GUI.Mode:
            self.Manager.GUI.Content.Tiles.remove(self.GUI, False)

    def addToFilter(self):
        if self.GUI and self.GUI.Mode:
            mode = self.GUI.Mode.upper()
            # dont add as new since it will erase other filters
            if mode == 'NEW':
                mode = 'OR'
            getattr(self.Manager.GUI.Content.Tiles, 'add' + mode)(self.GUI, False)
            self.Manager.GUI.Content.Tiles.refresh()

    def write(self):
        pass

class ListEntry(BaseListEntry):
    def build_GUI(self):
        return gui.ListEntryGUI(self)
    
    def addGame(self, game):
        super().addGame(game)
        game.addToList(self)

    def removeGame(self, game):
        super().removeGame(game)
        game.removeFromList(self)

    def write(self):
        with open(list_dir + self.Name + '.json', 'w') as f:
            f.write(json.dumps(self.GameStructure, indent=4))

    def erase(self):
        self.reset(True)
        os.remove(list_dir + self.Name + '.json')

class FlagListEntry(BaseListEntry):
    def build_GUI(self):
        return gui.FlagListEntryGUI(self)
    
    def addGame(self, game):
        super().addGame(game)
        game.setFlag(self, True)

    def removeGame(self, game):
        super().removeGame(game)
        game.setFlag(self, False)

class SearchEntry(BaseListEntry):
    def __init__(self, manager):
        super().__init__(manager, "Search")
        self.Queue = []
        self.Active = False

        self.ExcludedGames = []
        self.addGames(self.Manager.All)

        self.PreviousText = ""

    def build_GUI(self):
        return gui.SearchBox(self)

    def onTextChanged(self, text):
        self.Queue.append(text)
        # if not currently active, then process
        if not self.Active:
            self.processQueue()

    def processQueue(self):
        self.Active = len(self.Queue)
        while( self.Active ):
            text = self.Queue[0]

            text_lower = text.lower()

            # if the search term was added to:
            if self.PreviousText in text:
                gamesToExclude = []
                for game in self.GameList:
                    if not game.search(text_lower):
                        gamesToExclude.append(game)
                        self.ExcludedGames.append(game)
                self.removeGames(gamesToExclude)
            # if the search term was reduced:
            elif text in self.PreviousText:
                gamesToAdd = []
                for game in self.ExcludedGames[:]:
                    if game.search(text_lower):
                        gamesToAdd.append(game)
                        self.ExcludedGames.pop(self.ExcludedGames.index(game))
                self.addGames(gamesToAdd)
            # text changed completely:
            else:
                gamesToToggle = []
                for game in self.ExcludedGames[:]:
                    if game.search(text_lower):
                        gamesToToggle.append(game)
                        self.ExcludedGames.pop(self.ExcludedGames.index(game))

                for game in self.GameList:
                    if not game.search(text_lower):
                        gamesToToggle.append(game)
                        self.ExcludedGames.append(game)

                self.toggleGames(gamesToToggle)


            self.PreviousText = text
            self.Queue.pop(0)
            self.Active = len(self.Queue)

class Catalog:
    def __init__(self, catalogs, name, entryClass):
        self.Catalogs = catalogs
        self.Manager = catalogs.Manager
        self.Name = name
        self.EntryClass = entryClass
        self.Entries = {}
        self.GUI = self.build_GUI() if self.Manager.GUI else None

    def build_GUI(self):
        return gui.CatalogGUI(self)

    def get(self, entry):
        return self.Entries[entry] if self.has(entry) else None

    def add(self, name):
        self.Entries[name] = self.EntryClass(self, name)

    def has(self, name):
        return name in self.Entries
    
    def isChild(self, child):
        return child in self.Entries.values()
    
    def remove(self, child):
        del self.Entries[child.Name]

class ListCatalog(Catalog):
    def __init__(self, catalogs):
        super().__init__(catalogs, 'Lists', ListEntry)

class FlagCatalog(Catalog):
    def __init__(self, catalogs):
        super().__init__(catalogs, 'Flags', FlagListEntry)

class AuthorCatalog(Catalog):
    def __init__(self, catalogs):
        super().__init__(catalogs, 'Authors', AuthorEntry)

class TagCatalog(Catalog):
    def __init__(self, catalogs):
        super().__init__(catalogs, 'Tags', TagEntry)

    def build_GUI(self):
        return gui.TagCatalogGUI(self)

class Catalogs:
    def __init__(self, manager):
        self.Manager = manager
        self.Flags = FlagCatalog(self)
        self.Authors = AuthorCatalog(self)
        self.Tags = TagCatalog(self)
        self.Lists = ListCatalog(self)

class Settings:
    def __init__(self, manager):
        self.Manager = manager
        # load base settings
        self.loadBase()
        self.reset()

        # try to load user settings
        self.load('data/settings.json')

        # validate the paths if windows
        if platform.system() == 'Windows':
            cygwinPath = self.get('Environment.cygwin')
            if cygwinPath and not os.path.exists(cygwinPath):
                self.set('Environment.cygwin', None)

            w64devkitPath = self.get('Environment.w64devkit')
            if w64devkitPath and not os.path.exists(w64devkitPath):
                self.set('Environment.w64devkit', None)

    def loadBase(self):
        self.Base = {}
        self.load('assets/settings.json', True)

    def load(self, path, isBase=False):
        if os.path.exists(path):
            target = self.Base if isBase else self.Active
            source = read_json(path)
            self.store_values(target, source, isBase)

    def store_values(self, target, source, isBase, fullname=''):
        for key, value in source.items():
            self.store_value(target, key, value, isBase, fullname)

    # todo - complete validation
    def store_value(self, target, key, value, isBase, fullname):
        fullname += key
        if not isBase:
            if key not in target:
                self.Manager.print('Invalid Settings key: ' + fullname)
                return
            
            # Expect same type, or None
            if type(value) != type(target[key]) and value is not None:
                self.Manager.print('Invalid Settings value for "' + fullname + '". Expected: ' + str(type(target[key])) + ', Received: ' + str(type(value)))
                return

        if isinstance(value, dict):
            if key not in target:
                target[key] = {}
            
            fullname += '.'
            self.store_values(target[key], value, isBase, fullname)
        else:
            target[key] = value

    def reset(self):
        self.Active = {}
        self.store_values(self.Active, self.Base, True)

    def get(self, fullpath):
        paths = fullpath.split('.')
        data = self.Active
        for path in paths:
            data = data[path]
        return data

    def set(self, fullpath, value):
        paths = fullpath.split('.')
        data = self.Active
        for path in paths[:-1]:
            data = data[path]
        
        if data[paths[-1]] != value:
            data[paths[-1]] = value
            with open('data/settings.json', 'w') as f:
                f.write(json.dumps(self.Active, indent=4))
            
            self.Manager.print('Updated Settings for {0}'.format(fullpath))

class PRET_Manager(MetaData):
    OutdatedSignal = pyqtSignal(bool)
    CygwinPathSignal = pyqtSignal(str)
    w64devkitPathSignal = pyqtSignal(str)

    def __init__(self):
        super().__init__(['Outdated','AutoRefresh','AutoUpdate','AutoRestart'])
        self.Manager = self
        self.Directory = games_dir
        
        self.All = []
        self.Process = None
        self.GUI = None
        self.App = None
        self.Search = None
        self.url = 'https://github.com/Pokeglitch/pret_manager'

        self.FlagLists = ["Library", "Favorites", "Excluding", "Outdated", "Missing"]

        self.Queue = []

        self.path = {
            'repo' : '.',
            'base' : 'data/'
        }

        self.Settings = Settings(self)
        self.Environments = Environments(self)

        self.Outdated = False
        self.AutoRefresh = False
        self.AutoUpdate = False
        self.AutoRestart = False
        self.readMetaData(False)
        self.Initialized = True
        
    def setw64devkitPath(self, path):
        self.Settings.set('Environment.w64devkit', path)
        self.w64devkitPathSignal.emit( str(path) )
        
    def setCygwinPath(self, path):
        self.Settings.set('Environment.cygwin', path)
        self.CygwinPathSignal.emit( str(path) )

    def terminateProcess(self):
        self.print('Terminating Process')
        
        if self.Process:
            if platform.system() == 'Windows':
                sig = signal.CTRL_BREAK_EVENT
            else:
                sig = signal.SIGBREAK

            os.kill(self.Process.pid, sig)
            self.setProcess(None)

    def setProcess(self, process, msg=''):
        self.Process = process
        if msg:
            self.print(msg)

    def setOutdated(self, outdated):
        if self.Outdated != outdated:
            self.Outdated = outdated
            self.OutdatedSignal.emit(self.Outdated)

    def addFlagList(self, name):
        self.Catalogs.Flags.add(name)

    def addList(self, name, list):
        if self.Catalogs.Lists.has(name):
            self.Catalogs.Lists.get(name).reset()
        else:
            self.Catalogs.Lists.add(name)

        games = []
        for author in list:
            for title in list[author]:
                games.append(self.Catalogs.Authors.get(author).getGame(title))

        self.Catalogs.Lists.get(name).addGames(games)

    def init_GUI(self):
        self.App, self.GUI = gui.init(self)

        self.init()
        self.Search = SearchEntry(self)

    def list(self, which):
        obj = {}

        data = self.git.list(which, self.url, Directory = '.')

        for row in data:
            # skip empty rows
            if row:
                row = row.split('\t')
                commit = row[0]
                name = row[1].split('/')[-1]

                obj[name] = commit

        return obj.items()
    
    def refresh(self):
        if not self.Outdated:
            self.print('Refreshing pret-manager')
            self.checkForUpdate()

        if self.Outdated:
            self.print('Update available')
            self.Manager.GUI.UpdateFoundSignal.emit()
        else:
            self.print('Already up to date')

    def update(self):
        if self.Outdated:
            self.print('Updating pret-manager')
            self.git.pull()
            self.checkForUpdate()
            if self.Outdated:
                self.print('Failed to update')
            else:
                self.print('Updated successful. Restart to load changes')
                self.Manager.GUI.UpdateAppliedSignal.emit()
        else:
            self.print('Already up to date')

    def checkForUpdate(self):
        data = dict(self.list('head'))
        outdated = data["master"] != self.git.head()
        self.setOutdated(outdated)
        self.updateMetaData()

    def print(self, msg):
        msg = 'pret-manager:\t' + str(msg)
        print(msg)

        if self.GUI:
            self.GUI.Logger.emit(msg)

    def init(self):
        self.Catalogs = Catalogs(self)

        # Initialize the Flag Lists
        for name in self.FlagLists:
            self.addFlagList(name)

        self.load('data.json')

        # Load lists
        for file in get_files(list_dir):
            with open(list_dir + file, 'r') as f:
                list = json.loads(f.read() or '{}')
            
            self.addList(file.split('.')[0], list)

    def handle_args(self):
        args = parser.parse_args()

        if args.env:
            environment = args.env[0]
            del args.env
        else:
            environment = 'wsl'

        self.git = Git(self)
        
        # if no args launch the gui
        if not any(vars(args).values()):
            return self.init_GUI()

        if args.process is None:
            return
        
        if args.process:
            processes = ''
            for process in args.process:
                if re.search(r'[^ubcr]',process):
                    error('Only r, u, b, and c are valid process arguments. Received: ' + process)
                processes += process
        else:
            processes = 'ucbc'

        self.init()

        if not args.authors and not args.repos:
            self.add_all()
        
        if args.authors:
            self.add_authors(args.authors)
        
        if args.repos:
            self.add_repos(args.repos)

        if args.tags:
            self.keep_tags(args.tags)

        if args.exclude_authors:
            self.remove_authors(args.exclude_authors)

        if args.exclude_repos:
            self.remove_repos(args.exclude_repos)

        if args.exclude_tags:
            self.remove_tags(args.exclude_tags)

        if args.build is None:
            args.build = []
        
        self.run(processes, args.build)

    def run(self, sequence, *build_options):
        if not self.Queue:
            self.print('Queue is empty')
        elif sequence:
            for repo in self.Queue:
                repo.process(sequence, build_options)
        else:
            self.print('No actions to process')

        self.clear_queue()

    def load(self, filepath):
        if not os.path.exists(filepath):
            error(filepath + ' not found')

        with open(filepath,"r") as f:
            data = json.loads(f.read() or '{}')

        # do rgbds first
        if 'gbdev' in data and 'rgbds' in data['gbdev']:
            self.RGBDS = RGBDS(self, 'gbdev', 'rgbds', data['gbdev']['rgbds'])
            del data['gbdev']

        authors = list(data.keys())
        authors.sort(key=str.casefold)

        for author in authors:
            self.Catalogs.Authors.add(author)

            for title in data[author]:
                repo = repository(self, author, title, data[author][title])
                self.All.append(repo)

                self.Catalogs.Authors.get(author).addGame(repo)

                for tag in repo.tags:
                    self.add_repo_tag(repo, tag)

    def add_repo_tag(self, repo, tag):
        if not self.Catalogs.Tags.has(tag):
            self.Catalogs.Tags.add(tag)

        self.Catalogs.Tags.get(tag).addGame(repo)

    def add_to_queue(self, repos):
        for repo in repos:
            if repo not in self.Queue:
                self.Queue.append(repo)

    def remove_from_queue(self, repos):
        for repo in repos:
            if repo in self.Queue:
                self.Queue.pop( self.Queue.index(repo) )
    
    def keep_in_queue(self, repos):
        self.remove_from_queue([repo for repo in self.Queue if repo not in repos])

    def add_all(self):
        self.add_to_queue(self.All)

    def clear_queue(self):
        self.Queue = []

    def add_repos(self, repos):
        for repo in repos:
            [author, title] = repo.split('/')
            self.add_to_queue([self.Catalogs.Authors.get(author).getGame(title)])

    def remove_repos(self, repos):
        for repo in repos:
            [author, title] = repo.split('/')
            self.remove_from_queue([self.Catalogs.Authors.get(author).getGame(title)])

    def add_authors(self, authors):
        for author in authors:
            self.add_to_queue(self.Catalogs.Authors.get(author).GameList)

    def remove_authors(self, authors):
        for author in authors:
            self.remove_from_queue(self.Catalogs.Authors.get(author).GameList)
    
    def keep_authors(self, authors):
        repos = []
        for author in authors:
            repos += [self.Catalogs.Authors.get(author).GameList]
        
        self.keep_in_queue(repos)

    def add_tags(self, tags):
        for tag in tags:
            if self.Catalogs.Tags.has(tag):
                self.add_to_queue(self.Catalogs.Tags.get(tag).GameList)

    def remove_tags(self, tags):
        for tag in tags:
            if self.Catalogs.Tags.has(tag):
                 self.remove_from_queue(self.Catalogs.Tags.get(tag).GameList)

    def keep_tags(self, tags):
        for tag in tags:
            if self.Catalogs.Tags.has(tag):
                self.keep_in_queue(self.Catalogs.Tags.get(tag).GameList)

class repository(MetaData):
    MissingSignal = pyqtSignal(bool)
    OutdatedSignal = pyqtSignal(bool)
    ExcludingSignal = pyqtSignal(bool)
    FavoritesSignal = pyqtSignal(bool)
    LibrarySignal = pyqtSignal(bool)
    BranchSignal = pyqtSignal()
    BuildSignal = pyqtSignal()
    ReleaseSignal = pyqtSignal()
    ProcessingSignal = pyqtSignal(bool)
    PrimaryGameSignal = pyqtSignal(str, QTreeWidgetItem)

    def __init__(self, manager, author, title, data):
        super().__init__(repo_metadata_properties)
        self.manager = manager
        self.Manager = manager

        self.author = author
        self.title = title
        self.GUI = None
        self.Lists = []

        self.Data = data
        self.Branches = {}
        self.GitTags = {}
        self.commits = {}
        self.CurrentBranch = None

        self.name = self.title + ' (' + self.author + ')'
        self.author_url = 'https://github.com/' + author + '/'
        self.url = self.author_url + title

        self.rgbds = data["rgbds"] if "rgbds" in data else ""
        self.RGBDS = None
        
        if "tags" in data:
            if isinstance(data["tags"], list):
                self.tags = data["tags"]
            else:
                self.tags = [data["tags"]]
        else:
            self.tags = []

        if "title" in data:
            self.FullTitle = data["title"]
        else:
            self.FullTitle = self.name

        if "description" in data:
            self.Description = data["description"]
        else:
            self.Description = ""
        
        dir = self.manager.Directory + self.author + '/' + self.title + '/'
        self.path = {
            'base' : dir,
            'repo' : dir + self.title,
            'releases' : dir + 'releases/',
            'builds' : dir + 'builds/'
        }

        self.resetSequence()

        self.git = Git(self)
        self.github = Github(self)
        self.make = Make(self)

        self.Boxart = 'assets/artwork/{0}.png'.format(self.name)
        if not os.path.exists(self.Boxart):
            self.Boxart = 'assets/images/gb.png'

        self.PrimaryGame = None

        self.Missing = None
        self.Outdated = None
        self.Excluding = False
        self.Favorites = False
        self.Library = False

        self.setMissing(not os.path.exists(self.path['repo']))
        self.setOutdated(self.Missing)

        self.readMetaData()

        self.parse_branches()
        self.parse_builds()
        self.parse_releases()

        self.setLibrary(bool(self.releases or self.builds or self.commits))

        self.Initialized = True

        modified_metadata = False

        # if meta data includes a current branch, but it was detected as missing, then update
        if self.Missing and self.CurrentBranch:
            self.CurrentBranch = None
            for branch in self.Branches:
                if "LastCommit" in self.Branches[branch]:
                    del self.Branches[branch]["LastCommit"]
                    
                if "LastUpdate" in self.Branches[branch]:
                    del self.Branches[branch]["LastUpdate"]

            modified_metadata = True

        if self.PrimaryGame and not os.path.exists(self.PrimaryGame):
            self.print('Primary File does not exist: ' + self.PrimaryGame)
            self.PrimaryGame = None
            modified_metadata = True

        if modified_metadata:
            self.updateMetaData()

        if self.manager.GUI:
            self.init_GUI()

######### GUI Methods
    def init_GUI(self):
        self.GUI = gui.GameGUI(self.manager.GUI.Content, self)

    def search(self, string):
        return string in self.FullTitle.lower() or string in self.Description.lower()

######### Processing Methods
    def setProcessing(self, processing):
        if self.Processing and not processing:
            self.updateMetaData()

        self.Processing = processing
        self.ProcessingSignal.emit(processing)
        self.resetSequence()

    def resetSequence(self):
        self.Refreshed = False
        self.Cleaned = False
        self.Updated = False
        self.Processing = False

    def process(self, sequence, build_options):
        if self.Excluding:
            self.print('Excluding ' + self.name)
            return
        
        self.print('Processing Starting')
        self.setProcessing(True)

        if len(sequence) and sequence[0] == 'r':
            self.refresh()
            sequence = sequence[1:]

        if len(sequence) and sequence[0] == 'u':
            self.update()
            sequence = sequence[1:]

        if len(sequence) and ('b' in sequence or 'c' in sequence):
            if not self.validate_repo():
                self.print('Cannot run \'make\' on missing repository')
            # if no specific build options, then build for all branches
            elif not build_options:
                starting_branch = self.CurrentBranch

                if self.check_branch_tracking(starting_branch):
                    self.process_make(sequence)

                for branch in self.Branches:
                    if branch != starting_branch and self.check_branch_tracking(branch):
                        if self.switch(branch):
                            self.process_make(sequence)

                if self.CurrentBranch != starting_branch:
                    self.switch(starting_branch)
                
                self.get_current_branch_info()
            else:
                if self.switch(*build_options):
                    self.process_make(sequence)
                    self.print('Switching back to previous branch/commit')
                    self.git.switch('-')
                    self.get_current_branch_info()

        self.updateMetaData()
        self.print('Processing Finished')
        self.setProcessing(False)

    def process_make(self, sequence):
        self.Cleaned = False
        for process in sequence:
            if process == 'b':
                self.build()
            elif process == 'c':
                self.clean()


######### IO Methods
    def rmdir(self, path, msg=''):
        self.print(msg)
        self.print('Removing directory: ' + path)
        rmdir(path)
        
    def print(self, msg):
        if msg:
            msg = self.name + ":\t" + str(msg)
            print(msg)

            if self.Manager.GUI:
                self.Manager.GUI.Logger.emit(msg)

######### Catalog Methods

    def addToList(self, list):
        if list not in self.Lists:
            self.Lists.append(list)

    def removeFromList(self, list):
        if list in self.Lists:
            self.Lists.pop(self.Lists.index(list))

######### Make Methods

    def clean(self):
        if not self.Cleaned:
            if self.validate_repo():
                self.print('Cleaning')
                self.make.clean()
            else:
                self.print('Cannot clean missing repository')

            self.Cleaned = True

######### Git Methods

    def fetch(self):
        self.print('Fetching')
        return self.git.fetch()

    def pull(self):
        success = not self.git.pull().returncode
        if success:
            self.get_current_branch_info()

        return success

    def get_url(self):
        return self.git.get('remote.origin.url')[0]

    def get_date(self):
        return self.git.date()

    def get_commit(self):
        return self.git.head()

    def list(self, which):
        obj = {}

        if not os.path.exists(self.path["repo"]):
            data = self.git.list(which, self.url, Directory = '.')
        else:
            data = self.git.list(which)

        for row in data:
            # skip empty rows
            if row:
                row = row.split('\t')
                commit = row[0]
                name = row[1].split('/')[-1]

                obj[name] = commit

        return obj.items()

######### Builds Methods
    def get_build_data(self, branchName, dirName):
        if branchName == "HEAD":
            lastCommit = self.get_commit()
            
            if lastCommit not in self.commits:
                self.commits[lastCommit] = {}

            if dirName not in self.commits[lastCommit]:
                self.commits[lastCommit][dirName] = {}

            return self.commits[lastCommit][dirName]
        else:
            if branchName not in self.builds:
                self.builds[branchName] = {}
            
            if dirName not in self.builds[branchName]:
                self.builds[branchName][dirName] = {}

            return self.builds[branchName][dirName]

    def parse_builds(self):
        self.builds = {}

        for branchName in get_dirs(self.path['builds']):
            branch_dir = self.path['builds'] + branchName
            
            for dirName in get_dirs(branch_dir):
                # if the dir name matches the template, then it is a build
                if re.match(r'^\d{4}-\d{2}-\d{2} [a-fA-F\d]{8} \([^)]+\)$',dirName):
                    build_dir = branch_dir + '/' + dirName
                    files = get_builds(build_dir)
                    # if builds exist in the directory:
                    if files:
                        self.store_build(branchName, dirName, files)

    def store_build(self, branchName, dirName, files):
        data = self.get_build_data(branchName, dirName)

        for file in files:
            data[file.name] = file
        
        self.setLibrary(True)

    def clean_builds(self):
        if os.path.exists(self.path['builds']):
            for branchName in get_dirs(self.path['builds']):
                branch_dir = self.path['builds'] + branchName
                for dirname in get_dirs(branch_dir):
                    build_dir = branch_dir + '/' + dirname
                    error_message = ''

                    # if the dir name matches the template, then it is a build
                    if re.match(r'^\d{4}-\d{2}-\d{2} [a-fA-F\d]{8} \([^)]+\)$',dirname):
                        # if no builds exist in the directory:
                        if not get_builds(build_dir):
                            error_message = 'Missing valid build files in pre-existing directory: ' + branchName + '/' + dirname
                    else:
                        error_message = 'Invalid build directory name: ' + dirname
                    
                    if error_message:
                        self.rmdir(build_dir, error_message)

                # if the branch directory is empty, then delete
                if not get_dirs(branch_dir):
                    self.rmdir(branch_dir, 'Branch directory has no builds: ' + branchName)
            
            # if the builds directory is empty, then delete
            if not get_dirs(self.path['builds']):
                self.rmdir(self.path['builds'], 'Build directory is empty')

    def set_branch(self, branch):
        if branch != self.CurrentBranch:
            if self.switch(branch):
                self.updateMetaData()
                self.BranchSignal.emit()

    def set_RGBDS(self, RGBDS):
        if RGBDS != self.RGBDS:
            # If setting to default, then erase
            if RGBDS == self.rgbds:
                RGBDS = None
            
            self.RGBDS = RGBDS
            self.updateMetaData()

    def update_branches(self):
        starting_branch = self.CurrentBranch

        updateSuccess = True
        branchUpdated = False

        if self.check_branch_outdated(starting_branch):
            if self.pull():
                self.print('Updated ' + starting_branch)
                branchUpdated = True
            else:
                self.print('Failed to update ' + starting_branch)
                updateSuccess = False

        for branchName in self.Branches:
            if self.check_branch_outdated(branchName):
                if self.switch(branchName):
                    if self.pull():
                        self.print('Updated ' + branchName)
                        branchUpdated = True
                    else:
                        self.print('Failed to update ' + branchName)
                        updateSuccess = False
        
        if self.CurrentBranch != starting_branch:
            self.switch(starting_branch)

        if branchUpdated:
            self.BranchSignal.emit()

        return updateSuccess

    def switch(self, *args):
        # if its a commit, use the detach flag
        if len(args) == 1 and args[0] not in self.Branches:
            cmds = ['-d', args[0]]
        else:
            cmds = args[:]

        self.print('Switching to: ' + ' '.join(args))

        result = self.git.switch(*cmds)

        if result.returncode:
            self.print('Failed to switch to ' + ' '.join(args))
        else:
            self.print('Switched to ' + ' '.join(args))
            self.get_current_branch_info()

        return not result.returncode
    
    def get_current_branch_info(self):
        # todo - move to Git class
        branch = self.git.run('rev-parse --abbrev-ref HEAD', CaptureOutput=True)[0]

        lastUpdate = self.get_date()
        lastCommit = self.get_commit()

        if branch == 'HEAD':
            # Get the corresponding GitTag data
            data = [self.GitTags[tag] for tag in self.GitTags if self.GitTags[tag]['commit'] == lastCommit][0]
            data['date'] = lastUpdate
        elif branch:
            if branch not in self.Branches:
                self.Branches[branch] = {}
                
            if "LastCommit" not in self.Branches[branch] or lastCommit != self.Branches[branch]["LastCommit"]:
                self.Branches[branch]["LastCommit"] = lastCommit
                self.Branches[branch]["LastUpdate"] = lastUpdate

        self.CurrentBranch = branch

######### Refresh Methods

    def refresh(self):
        if not self.Refreshed:
            self.print("Refreshing repository")
            branchesOutdated = self.refresh_branches()
            self.refresh_tags()
            releasesOutdated = self.refresh_releases()

            self.clean_directory()

            isOutdated = branchesOutdated or releasesOutdated or self.Missing
            self.setOutdated(isOutdated)

            self.Refreshed = True

    def clean_directory(self):
        self.clean_releases()
        self.clean_builds()

######### Branch Methods

    def get_branch_data(self, branch):
        if branch not in self.Branches:
            self.Branches[branch] = {}

        return self.Branches[branch]

    def refresh_branches(self):
        newBranch = False
        isOutdated = False
        for branch, commit in self.list('head'):
            data = self.get_branch_data(branch)

            if not data:
                newBranch = True

            data['LastRemoteCommit'] = commit

            if self.check_branch_outdated(branch):
                isOutdated = True
                
        if newBranch:
            self.BranchSignal.emit()

        return isOutdated

    def parse_branches(self):
        if not self.Branches or any([self.check_branch_outdated(branch) for branch in self.Branches]):
            self.setOutdated(True)

    def set_branch_tracking(self, branch, value):
        data = self.get_branch_data(branch)
        data["Tracking"] = value
        self.updateMetaData()

    def check_branch_tracking(self, branch):
        data = self.get_branch_data(branch)

        # If 'Tracking' is explicitly set, use that value
        if "Tracking" in data:
            return data["Tracking"]
        
        # Otherwise, see if the data includes both a Remote and Local commit value
        return "LastRemoteCommit" in data and "LastCommit" in data

    # only track branchs that exist locally
    def check_branch_outdated(self, branch):
        # if tracking:
        if self.check_branch_tracking(branch):
            data = self.get_branch_data(branch)
            if "LastRemoteCommit" in data and "LastCommit" in data:
                return data["LastRemoteCommit"] != data["LastCommit"]
            
            return True

        return False

######### Git Tags & Releases Methods

    def get_tag_data(self, tag):
        if tag not in self.GitTags:
            self.GitTags[tag] = {}

        return self.GitTags[tag]
    
    def refresh_tags(self):
        for tag, commit in self.list('tags'):
            if tag not in self.GitTags:
                data = self.get_tag_data(tag)
                data["commit"] = commit
  
    def refresh_releases(self):
        releases = self.github.list()
        isOutdated = False
        for release in releases:
            # ignore empty lines
            if release:
                [title, isLatest, tag, datetime] = release.split('\t')

                data = self.get_tag_data(tag)

                if "release" not in data:
                    data["release"] = legal_name(datetime.split('T')[0] + ' - ' + title + ' (' + tag + ')')
                    isOutdated = True
        return isOutdated
    
    def parse_releases(self):
        self.releases = {}

        for tag, data in self.GitTags.items():
            release_dir = None

            if "release" in data:
                release_name = data["release"]
                release_dir = self.path['releases'] + release_name

                if os.path.exists(release_dir):
                    files = self.check_releases(release_dir)
                    if files:
                        self.store_release(tag, files)

            elif "date" in data:
                release_name = data['date'][:10] + ' - ' + tag + ' (' + tag + ')'
                release_dir = self.path['releases'] + release_name

            if release_dir:
                for dirName in get_dirs(release_dir):
                    files = get_builds(release_dir + '/' + dirName)
                    if files:
                        if data["commit"] not in self.commits:
                            self.commits[data["commit"]] = {}

                        self.commits[data["commit"]][dirName] = {}

                        for file in files:
                            self.commits[data["commit"]][dirName][file.name] = file
    
    def store_release(self, tag, files):
        release_name = self.GitTags[tag]["release"]

        self.releases[release_name] = {}
        for file in files:
            self.releases[release_name][file.name] = file
        
    def check_releases(self, dir):
        return get_releases(dir)
     
    def clean_releases(self):
        if os.path.exists(self.path['releases']):
            for dirname in get_dirs(self.path['releases']):
                release_dir = self.path['releases'] + dirname
                error_message = ''

                # if the dir name matches the template, then it is a release
                match = re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', dirname)
                if match:
                    tag = match.group(1)

                    if tag not in self.GitTags:
                        error_message = 'Tag does not exist: ' + tag
                    else:
                        build_dirs = get_dirs(release_dir)
                        if build_dirs:
                            for build_dir_name in build_dirs:
                                build_dir = release_dir + '/' + build_dir_name
                                build_error_message = ''
                                
                                # if the dir name matches the template, then it is a build
                                if re.match(r'^\d{4}-\d{2}-\d{2} [a-fA-F\d]{8} \([^)]+\)$', build_dir_name):
                                    # if no builds exist in the directory:
                                    if not get_builds(build_dir):
                                        build_error_message = 'Missing valid build files in pre-existing directory: ' + build_dir
                                else:
                                    build_error_message = 'Invalid build directory name: ' + build_dir_name

                                if build_error_message:
                                    self.rmdir(build_dir, build_error_message)

                        if not self.check_releases(release_dir) and not get_dirs(release_dir):
                            error_message = 'Missing release files for tag: ' + tag
                else:
                    error_message = 'Invalid release directory name: ' + dirname
                    
                if error_message:
                    self.rmdir(release_dir, error_message)

            # if the releases directory is empty, then delete
            if not get_dirs(self.path['releases']):
                self.rmdir(self.path['releases'], 'Release directory is empty')

    def get_releases(self, release_id=None):
        release_found = False

        self.print('Checking releases')

        for tag, data in self.GitTags.items():
            if not release_id or tag == release_id:
                if "release" in data and data["release"] not in self.releases:
                    self.print('Downloading release: ' + tag)

                    release_dir = self.path['releases'] + data["release"]

                    temp_dir = temp_mkdir(release_dir)
                    # TODO - handle error
                    self.github.download(tag, release_dir)

                    files = self.check_releases(release_dir)
                    if files:
                        self.store_release(tag, files)
                        release_found = True
                    else:
                        self.rmdir(temp_dir, 'Release does not have valid content: ' + data["release"])

        if release_found:
            if self.GUI:
                self.ReleaseSignal.emit()
            
            self.setLibrary(True)
        else:
            self.print('No new releases found')
        
        return release_found
     
    def setPrimaryGame(self, path, item):
        if path != self.PrimaryGame:
            self.PrimaryGame = path
            self.updateMetaData()
            
            self.PrimaryGameSignal.emit(path, item)

    def findNewestGame(self):
        all_releases = [*self.releases.keys()]
        newest_release = max(all_releases) if all_releases else None

        all_builds = {}
        for branch in self.builds:
            branch_builds = list(self.builds[branch].keys())
            if branch_builds:
                build = max(branch_builds)
                all_builds[build] = branch

        newest_build = max(all_builds.keys()) if all_builds else None

        if newest_build and newest_release:
            if newest_release < newest_build:
                newest_release = None
            else:
                newest_build = None

        newest_dir = None

        if newest_build:
            newest_dir = self.path['builds'] + all_builds[newest_build] + '/' + newest_build
        elif newest_release:
            newest_dir = self.path['releases'] + newest_release
        
        if newest_dir:
            files = get_releases(newest_dir)
            files.sort(key=os.path.getmtime)
            return str(files[-1])
        else:
            return None



######### Flag Methods

    # TODO - all these gui update should be emitters?

    def setFlag(self, flagList, value):
        getattr(self, 'set' + flagList.Name)(value, False)

    def setLibrary(self, library, addToList=True):
        if self.Library != library:
            self.Library = library

            if addToList:
                if library:
                    self.Manager.Catalogs.Flags.get('Library').addGames([self])
                else:
                    self.Manager.Catalogs.Flags.get('Library').removeGames([self])

            self.LibrarySignal.emit(self.Library)

    def setOutdated(self, outdated, addToList=True):
        if self.Outdated != outdated:
            self.Outdated = outdated

            if addToList:
                if outdated:
                    self.Manager.Catalogs.Flags.get('Outdated').addGames([self])
                else:
                    self.Manager.Catalogs.Flags.get('Outdated').removeGames([self])
            
            self.OutdatedSignal.emit(self.Outdated)

    def setMissing(self, missing, addToList=True):
        if self.Missing != missing:
            self.Missing = missing

            if addToList:
                if missing:
                    self.Manager.Catalogs.Flags.get('Missing').addGames([self])
                else:
                    self.Manager.Catalogs.Flags.get('Missing').removeGames([self])

            self.MissingSignal.emit(self.Missing)

    def setExcluding(self, excluding, addToList=True):
        if self.Excluding != excluding:
            self.Excluding = excluding

            if addToList:
                if excluding:
                    self.Manager.Catalogs.Flags.get('Excluding').addGames([self])
                else:
                    self.Manager.Catalogs.Flags.get('Excluding').removeGames([self])
            
            self.ExcludingSignal.emit(self.Excluding)

            self.updateMetaData()

    def setFavorites(self, favorite, addToList=True):
        if self.Favorites != favorite:
            self.Favorites = favorite

            if addToList:
                if favorite:
                    self.Manager.Catalogs.Flags.get('Favorites').addGames([self])
                else:
                    self.Manager.Catalogs.Flags.get('Favorites').removeGames([self])
            
            self.FavoritesSignal.emit(self.Favorites)
            self.updateMetaData()

######### TODO Methods

    def get_build_info(self, version):
        commit = self.get_commit()
        date = self.get_date()

        if self.CurrentBranch == 'HEAD':
            tag = [tag for tag in self.GitTags if self.GitTags[tag]['commit'] == commit][0]
            data = self.GitTags[tag]

            if "release" in data:
                dirName = data["release"]
            else:
                dirName = date[:10] + ' - ' + tag + ' (' + tag + ')'

            self.build_name = date[:10] + ' ' + commit[:8] + ' (' + version + ')'
            self.build_dir = self.path['releases'] + dirName + '/' + self.build_name + '/'
        else:
            self.build_name = date[:10] + ' ' + commit[:8] + ' (' + version + ')'
            self.build_dir = self.path['builds'] + self.CurrentBranch + '/' + self.build_name + '/'

    def validate_repo(self):
        # if the repository doesnt exist, then update
        if self.Missing:
            if not self.Updated:
                self.print('Repository not found. Updating')
                self.update()

        return not self.Missing

    def build(self, *args):
        if not self.validate_repo():
            self.print('Cannot build missing repository')
            return

        # Unset the cleaned flag
        self.Cleaned = False

        if len(args):
            if not self.switch(*args):
                return

        version = self.RGBDS or self.rgbds

        if not self.CurrentBranch:
            self.get_current_branch_info()

            if not self.CurrentBranch:
                self.print("Failed to obtain current branch information")
                return
            
        self.get_build_info(version)

        if self.CurrentBranch == 'HEAD':
            lastCommit = self.get_commit()
            alreadyBuilt = lastCommit in self.commits and self.build_name in self.commits[lastCommit] and self.commits[lastCommit][self.build_name]
        else:
            alreadyBuilt = self.CurrentBranch in self.builds and self.build_name in self.builds[self.CurrentBranch]

        # only build if commit not already built
        if  alreadyBuilt:
            self.print('Commit has already been built: ' + self.build_name)
        # if rgbds version is known and configured, then utilize for make
        elif version and version != "None": 
            self.print('Building with RGBDS v' + version)
            self.build_rgbds(version)

        if len(args):
            self.print('Switching back to previous branch/commit')
            self.git.switch('-')
            self.get_current_branch_info()
    
    def update_repo(self):
        self.print("Updating repository")
        url = self.get_url()
        if url != self.url:
            self.print("Local repo origin path is \"" + url + "\" \"" + self.url + "\"")
        
        self.refresh()
        
        updateSuccess = self.Outdated

        if self.Outdated:
            branchUpdateSuccess = self.update_branches()

        return updateSuccess and branchUpdateSuccess

    def init_repo(self):
        self.print("Initializing repository")
        result = self.git.clone()
        if result.returncode:
            self.print('Could not clone repository')
            return False
        else:
            self.get_current_branch_info()
            self.refresh()
            self.setMissing(False)
            return True

    def update(self, release_id=None):
        self.Updated = True

        mkdir(self.path['base'])

        if self.Missing:
            repoUpdateSuccess = self.init_repo()
        else:
            repoUpdateSuccess = self.update_repo()
    
        # check the shortcut
        shortcut = self.path['base'] + self.name + ' Repository.url'
        if not os.path.exists(shortcut):
            with open(shortcut,'w') as f:
                f.write('[InternetShortcut]\nURL=' + self.url + '\n')

        releases_found = self.get_releases(release_id=release_id)
        self.get_submodules()

        self.updateMetaData()

        if repoUpdateSuccess:
            self.setOutdated(False)

        return releases_found
    
    def get_submodules(self):
        submodules = {}

        if os.path.exists(self.path['repo'] + '/.gitmodules'):
            self.print('Checking submodules')
            with open(self.path['repo'] + '/.gitmodules', 'r') as f:
                content = f.read()
            
            # replace all 'git://github.com' with 'https://github.com'
            for match in re.finditer(r"\W*\[\W*submodule\W+[\"']([^\"]+)[\"']\W*][^[]+url\W*=\W*(.*)", content):
                name = match.group(1)
                url = match.group(2).replace('git://github.com', 'https://github.com')

                # update the 'extras' repo
                if name == 'extras':
                    url = url.replace('/kanzure/pokemon-reverse-engineering-tools.git','/pret/pokemon-reverse-engineering-tools.git')

                self.git.sub_url(name, url)

                submodules[name] = url

            self.git.sub_update()

        for name in submodules:
            dir = self.path['repo'] + '/' + name
            # if it exists, and is empty, then remove
            if os.path.exists(dir) and is_empty(dir):
                rmdir(dir)

            if not os.path.exists(dir):
                self.git.sub_add(submodules[name], name)

    def build_rgbds(self, version):
        # if new, successful build, copy any roms to build dir
        rgbds_dir = self.manager.RGBDS.use('v' + version)
        if not rgbds_dir or self.make.run(input='PATH="' + rgbds_dir + '":/root/.pyenv/shims:/root/.pyenv/bin:$PATH').returncode:
            self.print('Build failed for: ' + self.build_name)
            return False
        else:
            files = get_builds(self.path['repo'])
            if files:
                names = copy_files(files, self.build_dir)
                self.print('Placed build file(s) in ' + self.build_dir + ': ' + ', '.join(names))
                
                self.store_build(self.CurrentBranch, self.build_name, files)

                if self.GUI:
                    if self.CurrentBranch == "HEAD":
                        self.ReleaseSignal.emit()
                    else:
                        self.BuildSignal.emit()

                return True
            else:
                self.print('No valid files found after build')
                return False

    def find_build(self, *args):
        if len(args):
            self.git.switch(*args)

        self.rgbds = ''
        releases = [version[1:] for version in self.manager.RGBDS.ReleaseIDs]

        # If there is a .rgbds-version file, try that first
        if os.path.exists(self.path['repo'] + '/.rgbds-version'):
            with open(self.path['repo'] + '/.rgbds-version', 'r') as f:
                id = f.read().split("\n")[0]
                releases.pop( releases.index(id) )
                releases = [id] + releases

        for release in releases:
            self.clean()
            self.get_build_info(release)
            if self.build_rgbds(release):
                self.rgbds = release
                break

        if len(args):
            self.git.switch('-')
            self.get_current_branch_info()

class RGBDS(repository):
    def __init__(self, *args):
        super().__init__(*args)

        if not self.GitTags:
            self.GitTags = self.Data['releases']
            self.parse_releases()
            self.updateMetaData()

    # dont add to any list
    def setOutdated(self, outdated, addToList=True):
        super().setOutdated(outdated, False)

    def setMissing(self, missing, addToList=True):
        super().setMissing(missing, False)

    def setLibrary(self, library, addToList=True):
        super().setLibrary(library, False)

    def setExcluding(self, excluding, addToList=True):
        super().setExcluding(excluding, False)

    def setFavorites(self, favorites, addToList=True):
        super().setFavorites(favorites, False)

    def refresh(self):
        result = super().refresh()
        self.Refreshed = False
        return result

    def update(self, *args):
        result = super().update(*args)
        self.Updated = False
        return result

    def init_GUI(self):
        pass

    def check_releases(self, dir):
        return get_all_files(dir)
    
    def store_release(self, tag, files):
        self.releases[tag] = files[0].parts[-2]

    def parse_releases(self):
        self.clean_releases()

        super().parse_releases()

        self.ReleaseIDs = []
        for tag, data in self.GitTags.items():
            if "release" in data:
                self.ReleaseIDs.insert(0, tag)

    def clean_releases(self):
        if os.path.exists(self.path['releases']):
            for dirname in get_dirs(self.path['releases']):
                release_dir = self.path['releases'] + dirname
                error_message = ''

                # if the dir name matches the template, then it is a release
                match = re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', dirname)
                if match:
                    tag = match.group(1)

                    if tag not in self.GitTags:
                        error_message = 'Tag does not exist: ' + tag

                    elif "release" not in self.GitTags[tag]:
                        error_message = 'Tag does not have associated release: ' + tag

                    elif not self.check_releases(release_dir):
                        error_message = 'Missing release files for tag: ' + tag
                else:
                    error_message = 'Invalid release directory name: ' + dirname
                    
                if error_message:
                    self.rmdir(release_dir, error_message)

            # if the releases directory is empty, then delete
            if not get_dirs(self.path['releases']):
                self.rmdir(self.path['releases'], 'Release directory is empty')

    def parse_builds(self):
        self.clean_builds()

        self.builds = {
            'linux' : {},
            'win64' : {},
            'win32' : {}
        }
        
        for version in get_dirs(self.path['builds']):
            version_dir = self.path['builds'] + version

            for type in get_dirs(version_dir):
                if type in self.builds:
                    build_dir = version_dir + '/' + type

                    if get_all_files(build_dir):
                        self.builds[type][version] = build_dir

    def clean_builds(self):
        if os.path.exists(self.path['builds']):
            for version in get_dirs(self.path['builds']):
                version_dir = self.path['builds'] + version
                for type in get_dirs(version_dir):
                    build_dir = version_dir + '/' + type
                    error_message = ''

                    if type not in ['linux', 'win64', 'win32']:
                        error_message = 'Invalid build type: ' + type
                    elif not get_all_files(build_dir):
                        error_message = 'Missing valid build files in pre-existing directory: ' + version + '/' + type
                    
                    if error_message:
                        self.rmdir(build_dir, error_message)

                if not get_dirs(version_dir):
                    self.rmdir(version_dir, 'Version directory has no builds: ' + version)

            if not get_dirs(self.path['builds']):
                self.rmdir(self.path['builds'], 'Build directory is empty')

    def build(self, version):
        # If the version is not in the list of releases, then update
        if version not in self.releases:
            self.print('RGBDS release not found: ' + version)

            # update and get the specific release
            if not self.update(version):
                self.print('RGBDS version still not found: ' + version)
                return False

        name = self.releases[version]
        type = self.Manager.Environments.get('make').Type
        build_dir = self.path['builds'] + version + '/' + type + '/'
        release_dir = self.path['releases'] + name
        extraction_dir = release_dir + '/' + type

        if type == "linux":
            extension = '.tar.gz'
            keyfile = 'Makefile'
        else:
            extension = type + '.zip'
            keyfile = 'rgbasm.exe'

        extraction_dir_path = find(extraction_dir)
        
        # if the extraction directory exists, check for the key file
        if extraction_dir_path:
            keyfile_path = find(extraction_dir + '/**/' + keyfile, recursive=True)

            # if the keyfile is not found, delete the directory so it will re-extract
            if not keyfile_path:
                self.rmdir(extraction_dir, 'Missing keyfile in pre-extracted directory: ' + keyfile)
                extraction_dir_path = []
        
        # if the extraction dir doesnt exist, then extract
        if not extraction_dir_path:
            archives = find(release_dir + '/*' + extension)

            if not archives:
                self.print("Asset not found with extension: " + extension)
                # TODO - remove dir and redownload release?
                return False

            archive_names = [path.split('/')[-1] for path in archives]
            
            if len(archives) > 1:
                self.print('Multiple archives found: ' + ', '.join(archive_names) )

            self.print('Extracting ' + name + ' from ' + archive_names[0])

            if not Tar(self.Manager.Environments).extract(archives[0], extraction_dir):
                self.print("Failed to extract " + archives[0])
                return False

            # If the extraction was successful, check for the keyfile
            keyfile_path = find(extraction_dir + '/**/' + keyfile, recursive=True)

            # if the keyfile is not found, delete the directory so it will re-extract
            if not keyfile_path:
                self.rmdir(extraction_dir, 'Missing keyfile in extraction directory: ' + keyfile)
                # TODO - redownload release?
                return False

        # get the directory containing the keyfile
        keyfile_dir = dir_only(keyfile_path[0])

        if type == "linux":
            self.print('Building ' + name)

            if self.make.run(Directory=keyfile_dir).returncode:
                self.print("Failed to build " + name)
                return False
            
            files = get_rgbds(keyfile_dir)
            if not files:
                self.print('No RGBDS files found after build')
                return False
        else:
            files = get_all_files(keyfile_dir)

        copy_files(files, build_dir)
        self.print('Placed RGBDS ' + version + ' files into ' + build_dir)
        self.builds[type][version] =  build_dir
        return True

    def use(self, version):
        environment = self.Manager.Environments.get('make')
        if version not in self.builds[environment.Type]:
            self.print('RGBDS build not found: ' + version)
            self.print('Building RGBDS version: ' + version)

            if not self.build(version):
                self.print('Version {0} is not available'.format(version))
                return ''
        
        return environment.path(self.builds[environment.Type][version])

pret_manager = PRET_Manager()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='pret_manager', description='Manage various pret related projects')
    parser.add_argument('-repos', '-r', nargs='+', help='Repo(s) to manage')
    parser.add_argument('-env', '-e', nargs=1, choices=['wsl','cygwin','w64devkit'], help='Linux Environment for building')
    parser.add_argument('-exclude-repos', '-xr', nargs='+', help='Repo(s) to not manage')
    parser.add_argument('-authors', '-a', nargs='+', help='Author(s) to manage')
    parser.add_argument('-exclude-authors', '-xa', nargs='+', help='Author(s) to not manage')
    parser.add_argument('-tags', '-t', nargs='+', help='Tags(s) to manage')
    parser.add_argument('-exclude-tags', '-xt', nargs='+', help='Tags(s) to not manage')
    parser.add_argument('-process', '-p', nargs='*', help='The processes to run on the managed repositories')
    parser.add_argument('-build', '-b', nargs='*', help='Build options')

    import time
    start_time = time.time()

    pret_manager.handle_args()

    #print("--- %s seconds ---" % (time.time() - start_time))
    if pret_manager.App:
        pret_manager.App.init()
else:
    pret_manager.init()
