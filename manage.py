#!/usr/bin/env python

import os, re, argparse, json
from pathlib import Path
import gui
from src.base import *
from src.Environment import *
from src.Files import *
from PyQt5.QtCore import pyqtSignal, QObject

build_extensions = ['gb','gbc','pocket','patch']
release_extensions = build_extensions + ['ips','bps','bsp','zip']
repo_metadata_properties = ['Branches','GitTags','CurrentBranch','RGBDS','Excluding','Favorites']
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
            self.Manager.print('No games found for Author: ' + self.Name)
            self.Manager.print('Removing directory: ' + author_dir)
            rmdir(author_dir)

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
                game.removeFromList(self)
            else:
                game.addToList(self)

        self.addToFilter()

        if games:
            self.write()

    def removeFromFilter(self):
        if self.GUI and self.GUI.Mode:
            self.Manager.GUI.Content.Tiles.remove(self.GUI, False)

    def addToFilter(self):
        if self.GUI and self.GUI.Mode:
            getattr(self.Manager.GUI.Content.Tiles, 'add' + self.GUI.Mode.upper())(self.GUI, False)
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
        self.ExcludedGames = []
        self.addGames(self.Manager.All)

        self.PreviousText = ""

    def build_GUI(self):
        return gui.SearchBox(self)

    def onTextChanged(self, text):
        text_lower = text.lower()
        # if the search term was added to:
        if self.PreviousText in text:
            gamesToExclude = []
            for game in self.GameList:
                if text_lower not in game.name.lower():
                    gamesToExclude.append(game)
                    self.ExcludedGames.append(game)
            self.removeGames(gamesToExclude)
        # if the search term was reduced:
        elif text in self.PreviousText:
            gamesToAdd = []
            for game in self.ExcludedGames[:]:
                if text_lower in game.name.lower():
                    gamesToAdd.append(game)
                    self.ExcludedGames.pop(self.ExcludedGames.index(game))
            self.addGames(gamesToAdd)
        # text changed complete:
        else:
            gamesToToggle = []
            for game in self.ExcludedGames[:]:
                if text_lower in game.name.lower():
                    gamesToToggle.append(game)
                    self.ExcludedGames.pop(self.ExcludedGames.index(game))

            for game in self.GameList:
                if text_lower not in game.name.lower():
                    gamesToToggle.append(game)
                    self.ExcludedGames.append(game)

            self.toggleGames(gamesToToggle)

        self.PreviousText = text

class Catalog:
    def __init__(self, catalogs, name, entryClass):
        self.Catalogs = catalogs
        self.Manager = catalogs.Manager
        self.Name = name
        self.EntryClass = entryClass
        self.Entries = {}
        self.GUI = gui.CatalogGUI(self) if self.Manager.GUI else None

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
            
            if type(value) != type(target[key]):
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

    def __init__(self):
        super().__init__(['Outdated','AutoRefresh','AutoUpdate','AutoRestart'])
        self.Manager = self
        self.Directory = games_dir
        
        self.All = []
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
        
    def setOutdated(self, outdated):
        if self.Outdated != outdated:
            print(outdated)
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
                list = json.loads(f.read())
            
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

    def run(self, processes, build_options=[]):
        if not self.Queue:
            self.print('Queue is empty')
        elif processes:
            for repo in self.Queue:
                if repo.Excluding:
                    self.print('Excluding ' + repo.name)
                    continue

                if repo.GUI:
                    repo.GUI.setProcessing(True)

                self.print('Processing ' + repo.name)

                for process in processes:
                    if process == 'b':
                        repo.build(*build_options)
                    elif process == 'c':
                        repo.clean()
                    elif process == 'r':
                        repo.refresh()
                    elif process == 'u':
                        repo.update()

                    repo.updateMetaData()

                self.print('Finished Processing ' + repo.name)
                if repo.GUI:
                    repo.GUI.setProcessing(False)
        else:
            self.print('No actions to process')

        self.clear_queue()

    def load(self, filepath):
        if not os.path.exists(filepath):
            error(filepath + ' not found')

        with open(filepath,"r") as f:
            data = json.loads(f.read())

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

    def __init__(self, manager, author, title, data):
        super().__init__(repo_metadata_properties)
        self.manager = manager
        self.Manager = manager

        self.author = author
        self.title = title
        self.GUI = None
        self.Lists = []

        self.Branches = {}
        self.GitTags = {}
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

        self.git = Git(self)
        self.github = Github(self)
        self.make = Make(self)

        self.Boxart = 'assets/artwork/{0}.png'.format(self.name)
        if not os.path.exists(self.Boxart):
            self.Boxart = 'assets/images/gb.png'

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

        self.Initialized = True

        # if meta data includes a current branch, but it was detected as missing, then update
        if self.Missing and self.CurrentBranch:
            self.CurrentBranch = None
            for branch in self.Branches:
                if "LastCommit" in self.Branches[branch]:
                    del self.Branches[branch]["LastCommit"]
                    
                if "LastUpdate" in self.Branches[branch]:
                    del self.Branches[branch]["LastUpdate"]

            self.updateMetaData()
                

        if self.manager.GUI:
            self.init_GUI()

######### GUI Methods
    def init_GUI(self):
        self.GUI = gui.GameGUI(self.manager.GUI.Content, self)

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
        self.print('Cleaning')
        return self.make.clean()

######### Git Methods

    def fetch(self):
        self.print('Fetching')
        return self.git.fetch()

    def pull(self):
        self.git.pull()
        self.get_current_branch_info()

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

    def parse_builds(self):
        self.builds = {}
        if os.path.exists(self.path['builds']):
            for branch in get_dirs(self.path['builds']):
                branch_dir = self.path['builds'] + branch
                for dirname in get_dirs(branch_dir):
                    build_path = branch_dir + '/' + dirname
                    # if the dir name matches the template, then it is a build
                    if re.match(r'^\d{4}-\d{2}-\d{2} [a-fA-F\d]{8} \([^)]+\)$',dirname):
                        builds = get_builds(build_path)
                        # if builds exist in the directory:
                        if builds:
                            if branch not in self.builds:
                                self.builds[branch] = {}

                            self.builds[branch][dirname] = {}
                            for build in builds:
                                self.builds[branch][dirname][build.name] = build

                            self.setLibrary(True)
                        else:
                            self.print('Missing valid build files in pre-existing directory: ' + branch + '/' + dirname)
                            self.print('Removing directory: ' + build_path)
                            rmdir(build_path)
                    else:
                        self.print('Invalid build directory name: ' + dirname)
                        self.print('Removing directory: ' + build_path)
                        rmdir(build_path)

                # if the branch directory is empty, then delete
                if not get_dirs(branch_dir):
                    self.print('Branch directory has no builds: ' + branch)
                    self.print('Removing directory: ' + branch_dir)
                    rmdir(branch_dir)
            
            # if the builds directory is empty, then delete
            if not get_dirs(self.path['builds']):
                self.print('Build directory is empty. Removing: ' + self.path['builds'])
                rmdir(self.path['builds'])

    def set_branch(self, branch):
        if branch != self.CurrentBranch:
            self.switch(branch)
            # TODO - handle if failed
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

        if self.check_branch_outdated(starting_branch):
            self.pull()

        for branchName in self.Branches:
            if self.check_branch_outdated(branchName):
                self.switch(branchName)
                self.pull()
        
        if self.CurrentBranch != starting_branch:
            self.switch(starting_branch)

        # TODO - only if a new branch was found?
        self.BranchSignal.emit()

    def switch(self, *args):
        self.print('Switching to branch/commit: ' + ' '.join(args))

        # todo - move to Git class
        self.git.run('clean -f')
        self.git.run('reset --hard')

        result = self.git.switch(*args)

        if result.returncode:
            self.print('Failed to switch to ' + ' '.join(args))
        else:
            self.print('Switched to ' + ' '.join(args))
            self.get_current_branch_info()

        return result
    
    def get_current_branch_info(self):
        # todo - move to Git class
        branch = self.git.run('rev-parse --abbrev-ref HEAD', CaptureOutput=True)[0]
        lastUpdate = self.get_date()
        lastCommit = self.get_commit()

        if branch not in self.Branches:
            self.Branches[branch] = {}
            
        if "LastCommit" not in self.Branches[branch] or lastCommit != self.Branches[branch]["LastCommit"]:
            self.Branches[branch]["LastCommit"] = lastCommit
            self.Branches[branch]["LastUpdate"] = lastUpdate

        self.CurrentBranch = branch

######### Refresh Methods

    def refresh(self):
        self.refresh_branches()
        self.refresh_tags()
        self.refresh_releases()

        self.clean_directory()

    def clean_directory(self):
        self.clean_releases()

######### Branch Methods

    def get_branch_data(self, branch):
        if branch not in self.Branches:
            self.Branches[branch] = {}

        return self.Branches[branch]

    def refresh_branches(self):
        for branch, commit in self.list('head'):
            data = self.get_branch_data(branch)
            data['LastRemoteCommit'] = commit

            if 'LastCommit' not in data or data['LastCommit'] != commit:
                self.setOutdated(True)

    def parse_branches(self):
        if not self.Branches or any([self.check_branch_outdated(branch) for branch in self.Branches]):
            self.setOutdated(True)

    # only track branchs that exist locally
    def check_branch_outdated(self, branch):
        data = self.get_branch_data(branch)

        if "LastRemoteCommit" in data and "LastCommit" in data:
            return data["LastRemoteCommit"] != data["LastCommit"]

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
        for release in releases:
            # ignore empty lines
            if release:
                [title, isLatest, tag, datetime] = release.split('\t')

                data = self.get_tag_data(tag)

                if "release" not in data:
                    data["release"] = legal_name(datetime.split('T')[0] + ' - ' + title + ' (' + tag + ')')
    
    def parse_releases(self):
        self.releases = {}

        for tag, data in self.GitTags.items():
            if "release" in data:
                release_name = data["release"]
                release_dir = self.path['releases'] + release_name

                if os.path.exists(release_dir):
                    files = self.check_releases(release_dir)
                    if files:
                        self.store_release(tag, files)
    
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

    def get_releases(self, release_id=None):
        release_found = False

        self.print('Checking releases')

        for tag, data in self.GitTags.items():
            if not release_id or tag == release_id:
                if "release" in data and data["release"] not in self.releases:
                    self.print('Downloading release: ' + tag)

                    release_dir = self.path['releases'] + data["release"]

                    temp_dir = temp_mkdir(release_dir)
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
        self.build_name = date[:10] + ' ' + commit[:8] + ' (' + version + ')'
        self.build_dir = self.path['builds'] + self.CurrentBranch + '/' + self.build_name + '/'

    def build(self, *args):
        # if the repository doesnt exist, then update
        if not os.path.exists(self.path['repo']):
            self.update()

        if len(args):
            self.switch(*args)

        version = self.RGBDS or self.rgbds
        self.get_build_info(version)

        # if the build directory exists but doesnt contain valid files, then remove
        if os.path.exists(self.build_dir) and not get_builds(self.build_dir):
            self.print('Missing valid build files in pre-existing directory: ' + self.build_name)
            self.print('Removing directory: ' + self.build_dir)
            rmdir(self.build_dir)

        # only build if commit not already built
        if os.path.exists(self.build_dir):
            self.print('Commit has already been built: ' + self.build_name)
        # if rgbds version is known and configured, switch to and make:
        elif version and version != "None": 
            self.print('Building with RGBDS v' + version)
            self.build_rgbds(version)

        if len(args):
            self.print('Switching back to previous branch/commit')
            self.git.switch('-')
    
    def update_repo(self):
        self.print("Updating repository")
        url = self.get_url()
        if url != self.url:
            self.print("Local repo origin path is \"" + url + "\" \"" + self.url + "\"")
        
        self.refresh()
        
        if self.Outdated:
            self.update_branches()

    def init_repo(self):
        self.print("Initializing repository")
        self.git.clone()
        self.get_current_branch_info()
        self.refresh()
        self.BranchSignal.emit()

    def update(self, release_id=None):
        mkdir(self.path['base'])

        if not os.path.exists(self.path['repo']):
            self.init_repo()
        else:
            self.update_repo()
    
        # check the shortcut
        shortcut = self.path['base'] + self.name + ' Repository.url'
        if not os.path.exists(shortcut):
            with open(shortcut,'w') as f:
                f.write('[InternetShortcut]\nURL=' + self.url + '\n')

        releases_found = self.get_releases(release_id=release_id)
        self.get_submodules()

        self.updateMetaData()

        self.setMissing(False)
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
                self.print('Placed build file(s) in ' + self.CurrentBranch + '/' + self.build_name + ': ' + ', '.join(names))
                
                if self.CurrentBranch not in self.builds:
                    self.builds[self.CurrentBranch] = {}

                self.builds[self.CurrentBranch][self.build_name] = {}
                for file in files:
                    self.builds[self.CurrentBranch][self.build_name][file.name] = self.build_dir + file.name

                if self.GUI:
                    self.BuildSignal.emit()

                self.setLibrary(True)

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

class RGBDS(repository):
    def __init__(self, *args):
        super().__init__(*args)

        # TODO - instead, have this stored in data.json....
        if not self.GitTags:
            self.refresh()
            self.updateMetaData()

    def init_GUI(self):
        pass

    def check_releases(self, dir):
        return get_all_files(dir)
    
    def store_release(self, tag, files):
        self.releases[tag] = files[0].parts[-2]

    def parse_releases(self):
        super().parse_releases()

        self.ReleaseIDs = []
        for tag, data in self.GitTags.items():
            if "release" in data:
                self.ReleaseIDs.insert(0, tag)

    def parse_builds(self):
        self.builds = {
            'linux' : {},
            'win64' : {},
            'win32' : {}
        }
        
        if os.path.exists(self.path['builds']):
            for version in get_dirs(self.path['builds']):
                version_dir = self.path['builds'] + version + '/'
                for type in get_dirs(version_dir):
                    build_dir = version_dir + type
                    # if the bulid dir doesnt have the expected files, then delete
                    if get_all_files(build_dir):
                        self.builds[type][version] = build_dir
                    else:
                        self.print('Missing valid build files in pre-existing directory: ' + version + '/' + type)
                        self.print('Removing directory: ' + build_dir)
                        rmdir(build_dir)

                if not get_dirs(version_dir):
                    self.print('Version directory has no builds: ' + version)
                    self.print('Removing directory: ' + version_dir)
                    rmdir(version_dir)

            if not get_dirs(self.path['builds']):
                self.print('Build directory is empty. Removing: ' + self.path['builds'])
                rmdir(self.path['builds'])


    def build(self, version):
        # If the version is not in the list of releases, then update
        if version not in self.releases:
            self.print('RGBDS version not found: ' + version)

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
                self.print('Missing keyfile in pre-extracted directory: ' + keyfile)
                self.print('Removing directory: ' + extraction_dir)
                rmdir(extraction_dir)
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
                self.print('Missing keyfile in extraction directory: ' + keyfile)
                self.print('Removing directory: ' + extraction_dir)
                rmdir(extraction_dir)
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
            self.print('RGBDS version not found: ' + version)
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

    print("--- %s seconds ---" % (time.time() - start_time))
    if pret_manager.App:
        pret_manager.App.init()
else:
    pret_manager.init()
