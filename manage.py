#!/usr/bin/env python

import copy, subprocess, os, re, glob, platform, shutil, argparse, json, sys
from pathlib import Path
import gui
from src.Environment import *
from src.Files import *

build_extensions = ['gb','gbc','pocket','patch']
release_extensions = build_extensions + ['ips','bps','bsp','zip']
metadata_properties = ['Branches','CurrentBranch','RGBDS']
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
    def __init__(self, *args):
        super().__init__(*args)
        if self.GUI:
            self.GUI.Label.setParent(None)
            self.GUI.TagGUI = gui.TagGUI(self.GUI, self.Name)

class ListEntry(CatalogEntry):
    def build_GUI(self):
        return gui.ListEntryGUI(self)

    def reset(self, isPermanent=False):
        self.removeGames(self.GameList[:], isPermanent)

    def erase(self):
        self.reset(True)
        
        if self.Name not in self.Manager.BaseLists:
            os.remove(list_dir + self.Name + '.json')

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
                game.addToList(self)
                
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
                game.removeFromList(self)
                
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
        if self.Name not in ["Library","Missing","Outdated","Search"]:
            with open(list_dir + self.Name + '.json', 'w') as f:
                f.write(json.dumps(self.GameStructure))

class SearchEntry(ListEntry):
    def __init__(self, manager):
        self.Manager = manager
        self.GUI = None
        super().__init__(self, "Search")

        if manager.GUI:
            self.GUI = gui.SearchBox(self)

        self.ExcludedGames = []
        self.addGames(self.Manager.All)

        self.PreviousText = ""

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

class AuthorCatalog(Catalog):
    def __init__(self, catalogs):
        super().__init__(catalogs, 'Authors', AuthorEntry)

class TagCatalog(Catalog):
    def __init__(self, catalogs):
        super().__init__(catalogs, 'Tags', TagEntry)

class Catalogs:
    def __init__(self, manager):
        self.Manager = manager
        self.Lists = ListCatalog(self)
        self.Authors = AuthorCatalog(self)
        self.Tags = TagCatalog(self)

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

class PRET_Manager:
    def __init__(self):
        self.Manager = self
        self.Directory = games_dir
        
        self.All = []
        self.GUI = None
        self.App = None
        self.Search = None

        self.BaseLists = ["Library", "Favorites", "Excluding", "Outdated", "Missing"]

        self.Queue = []

        self.path = {
            'repo' : '.'
        }

        self.Settings = Settings(self)
        self.Environments = Environments(self)

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
    
    def fetch(self):
        self.print('Fetching pret-manager')
        self.git.fetch(CaptureOutput=True)

    def print(self, msg):
        msg = 'pret-manager:\t' + str(msg)
        print(msg)

        if self.GUI:
            self.GUI.Logger.emit(msg)

    def update(self):
        self.print('Updating pret-manager')
        self.git.pull()

    def init(self):
        self.Catalogs = Catalogs(self)

        self.load('data.json')

        # Initialize the base lists
        for name in self.BaseLists:
            self.addList(name, [])

        self.Catalogs.Lists.get("Library").addGames([game for game in self.All if game.hasBuild])
        self.Catalogs.Lists.get("Outdated").addGames([game for game in self.All if game.Outdated])
        self.Catalogs.Lists.get("Missing").addGames([game for game in self.All if game.Missing])

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
                if self.Catalogs.Lists.get('Excluding').has(repo):
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

class repository():
    def __init__(self, manager, author, title, data):
        self.manager = manager
        self.Manager = manager

        self.author = author
        self.title = title
        self.GUI = None
        self.MetaData = {}
        self.Lists = []
        self.Branches = {}
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

        self.Missing = not os.path.exists(self.path['repo'])
        self.hasBuild = False
        self.Outdated = False
        self.isExcluding = False
        self.isFavorite = False

        self.readMetaData()

        self.parse_branches()
        self.parse_builds()
        self.parse_releases()

        if self.manager.GUI and self.author != 'gbdev':
            self.init_GUI()

    def init_GUI(self):
        self.GUI = gui.GameGUI(self.manager.GUI.Content, self)

    def readMetaData(self):
        path = self.path['base'] + 'metadata.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.loads(f.read())

            self.MetaData = {}
            for prop in metadata_properties:
                if prop in data:
                    self.MetaData[prop] = data[prop]
        else:
            self.Outdated = True

        for prop in metadata_properties:
            self.getMetaDataProperty(prop)

    def getMetaDataProperty(self, name):
        if name in self.MetaData:
            value = copy.deepcopy(self.MetaData[name])
            setattr(self, name, value)

    def updateMetaData(self):
        metadataChanged = [self.updateMetaDataProperty(prop) for prop in metadata_properties]

        if any(metadataChanged):
            mkdir(self.path['base'])
            with open(self.path['base'] + 'metadata.json', 'w') as f:
                f.write(json.dumps(self.MetaData, indent=4))

    def updateMetaDataProperty(self, name):
        value = copy.deepcopy( getattr(self, name) )

        if name not in self.MetaData:
            self.MetaData[name] = value
            return True

        if value != self.MetaData[name]:
            if value:
                self.MetaData[name] = value
                return True
            elif name in self.MetaData:
                del self.MetaData[name]
                return True
                
        return False

    def addToList(self, list):
        if list not in self.Lists:
            self.Lists.append(list)
            list.addGame(self)

            if list.Name == "Excluding":
                self.isExcluding = True
                if self.GUI:
                    self.GUI.updateExcluding(self.isExcluding)

            if list.Name == "Favorites":
                self.isFavorite = True
                if self.GUI:
                    self.GUI.updateFavorite(self.isFavorite)

    def removeFromList(self, list):
        if list in self.Lists:
            self.Lists.pop(self.Lists.index(list))
            list.removeGame(self)

            if list.Name == "Excluding":
                self.isExcluding = False
                if self.GUI:
                    self.GUI.updateExcluding(self.isExcluding)

            if list.Name == "Favorites":
                self.isFavorite = False
                if self.GUI:
                    self.GUI.updateFavorite(self.isFavorite)

    def parse_branches(self):
        if self.Branches:
            for branchName in self.Branches:
                if self.check_branch_outdated(branchName):
                    self.Outdated = True
        else:
            self.Outdated = True

    # only track branchs that exist locally
    def check_branch_outdated(self, branchName):
        branch = self.Branches[branchName]

        if "LastRemoteCommit" in branch and "LastCommit" in branch:
            return branch["LastRemoteCommit"] != branch["LastCommit"]

        return False
 
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

                            self.hasBuild = True
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

    def parse_releases(self):
        self.releases = {}
        if os.path.exists(self.path['releases']):
            for dirname in get_dirs(self.path['releases']):
                release_dir = self.path['releases'] + dirname
                
                # if the dir name matches the template, then it is a release
                match = re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', dirname)
                if match:
                    release_name = match.group(1)
                    if self.title == 'rgbds':
                        files = get_all_files(release_dir)
                        if files:
                            self.releases[release_name] = dirname
                    else:
                        files = get_releases(release_dir)
                        if files:
                            self.releases[dirname] = {}
                            for file in files:
                                self.releases[dirname][file.name] = file

                    if files:
                        self.hasBuild = True
                    else:
                        self.print('Missing release files in directory: ' + release_name)
                        self.print('Removing directory: ' + release_dir)
                        rmdir(release_dir)
                else:
                    self.print('Invalid release directory name: ' + dirname)
                    self.print('Removing directory: ' + release_dir)
                    rmdir(release_dir)

            # if the releases directory is empty, then delete
            if not get_dirs(self.path['releases']):
                self.print('Release directory is empty. Removing: ' + self.path['releases'])
                rmdir(self.path['releases'])

    def print(self, msg):
        msg = self.name + ":\t" + str(msg)
        print(msg)

        if self.Manager.GUI:
            self.Manager.GUI.Logger.emit(msg)

    def set_branch(self, branch):
        if branch != self.CurrentBranch:
            self.switch(branch)
            # TODO - handle if failed
            self.updateMetaData()
            
            if self.Manager.GUI:
                self.Manager.GUI.Branch.emit(self)

    def set_RGBDS(self, RGBDS):
        if RGBDS != self.RGBDS:
            # If setting to default, then erase
            if RGBDS == self.rgbds:
                RGBDS = None
            
            self.RGBDS = RGBDS
            self.updateMetaData()

    def pull(self):
        self.git.pull()
        self.get_current_branch_info()

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

        if self.GUI:
            self.GUI.Panel.updateBranchDetails()

    def get_url(self):
        return self.git.get('remote.origin.url')[0]

    def switch(self, *args):
        self.print('Switching to branch/commit: ' + ' '.join(args))
        self.git.run('clean -f')
        self.git.run('reset --hard')
        result = self.git.switch(*args)
        # TODO - handle failed switch?
        self.print('Switched to ' + ' '.join(args))
        self.get_current_branch_info()
        return result
    
    def get_current_branch_info(self):
        branch = self.git.run('rev-parse --abbrev-ref HEAD', CaptureOutput=True)[0]
        lastUpdate = self.get_date()
        lastCommit = self.get_commit()

        if branch not in self.Branches:
            self.Branches[branch] = {}
            
        if "LastCommit" not in self.Branches[branch] or lastCommit != self.Branches[branch]["LastCommit"]:
            self.Branches[branch]["LastCommit"] = lastCommit
            self.Branches[branch]["LastUpdate"] = lastUpdate

        self.CurrentBranch = branch

    def clean(self):
        self.print('Cleaning')
        return self.make.clean()

    def fetch(self):
        self.print('Fetching')
        return self.git.fetch()

    # will get remote branch information
    def refresh(self):
        outdated = False

        if not os.path.exists(self.path["repo"]):
            outdated = True
        else:
            heads = self.git.compare()

            for head in heads:
                # skip empty lines
                if head:
                    head = head.split('\t')
                    commit = head[0]
                    branch = head[1].split('/')[-1]

                    if branch not in self.Branches:
                        self.Branches[branch] = {}
                    
                    self.Branches[branch]['LastRemoteCommit'] = commit

                    if 'LastCommit' not in self.Branches[branch] or self.Branches[branch]['LastCommit'] != commit:
                        outdated = True

        if outdated and not self.Outdated:
            self.Outdated = True
            self.manager.Catalogs.Lists.get('Outdated').addGames([self])

    def get_date(self):
        return self.git.date()

    def get_commit(self):
        return self.git.head()

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

    def get_releases(self, release_id=None):
        release_found = False

        self.print('Checking releases')
        # todo - handle failure to list releases?
        releases = self.github.list()

        # if any exist, then download
        if len(releases) > 1:
            for release in releases:
                # ignore empty lines
                if release:
                    release_valid = True

                    [title, isLatest, id, datetime] = release.split('\t')

                    # skip if this not the targeted release
                    if release_id and release_id != id:
                        continue

                    date = datetime.split('T')[0]
                    name = legal_name(date + ' - ' + title + ' (' + id + ')')
                    release_dir = self.path['releases'] + name

                    # if the release directory exists and doesnt contain valid files, then remove
                    if os.path.exists(release_dir):
                        if self.title == 'rgbds':
                            files = get_all_files(release_dir)
                        else:
                            files = get_releases(release_dir)

                        if not files:
                            self.print('Missing release files in pre-existing directory: ' + name)
                            self.print('Removing directory: ' + release_dir)
                            rmdir(release_dir)
                
                    # if the release diretory doesnt exist, then download
                    if not os.path.exists(release_dir):
                        temp_dir = temp_mkdir(release_dir)
                        self.print('Downloading release: ' + title)
                        self.github.download(id, release_dir)

                        if self.title == 'rgbds':
                            files = get_all_files(release_dir)
                            if files:
                                self.releases[id] = name
                            else:
                                release_valid = False
                            
                        else:
                            files = get_releases(release_dir)
                            if files:
                                self.releases[name] = {}
                                for file in files:
                                    self.releases[name][file.name] = file
                            else:
                                release_valid = False

                        if release_valid:
                            release_found = True
                        else:
                            self.print('Release does not have valid content: ' + name)
                            self.print('Removing directory: ' + release_dir)
                            rmdir(temp_dir)

            if release_found:
                if self.GUI:
                    self.manager.GUI.Release.emit(self)
                
                if not self.hasBuild:
                    self.hasBuild = True
                    self.manager.Catalogs.Lists.get('Library').addGames([self])

        else:
            self.print('No releases found')
        
        return release_found
         
    def update(self, release_id=None):
        mkdir(self.path['base'])

        self.print("Updating local repository")
        if not os.path.exists(self.path['repo']):
            self.git.clone()
            self.get_current_branch_info()
            self.refresh()
            if self.GUI:
                self.GUI.Panel.updateBranchDetails()
        else:
            url = self.get_url()
            if url != self.url:
                self.print("Local repo origin path is \"" + url + "\" \"" + self.url + "\"")
            self.refresh()
            if self.Outdated:
                self.update_branches()
    
        # check the shortcut
        shortcut = self.path['base'] + self.name + ' Repository.url'
        if not os.path.exists(shortcut):
            with open(shortcut,'w') as f:
                f.write('[InternetShortcut]\nURL=' + self.url + '\n')

        releases_found = self.get_releases(release_id=release_id)
        self.get_submodules()

        if self.Missing:
            self.manager.Catalogs.Lists.get('Missing').removeGames([self])
            self.Missing = False

        # todo - only if branch is tracked...
        if self.Outdated:
            self.Outdated = False
            self.manager.Catalogs.Lists.get('Outdated').removeGames([self])

        self.updateMetaData()

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
                    self.manager.GUI.Build.emit(self)

                if not self.hasBuild:
                    self.hasBuild = True
                    self.manager.Catalogs.Lists.get('Library').addGames([self])

                return True
            else:
                self.print('No valid files found after build')
                return False

    def find_build(self, *args):
        if len(args):
            self.git.switch(*args)

        self.rgbds = ''
        releases = [version[1:] for version in reversed(list(self.manager.RGBDS.releases.keys()))]

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

    pret_manager.handle_args()
    if pret_manager.App:
        pret_manager.App.init()
else:
    pret_manager.init()
