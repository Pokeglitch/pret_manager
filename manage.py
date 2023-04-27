#!/usr/bin/env python

import subprocess, os, re, glob, platform, shutil, argparse, json, sys
from pathlib import Path
import gui
from src.Environment import *


build_extensions = ['gb','gbc','pocket','patch','ips']
metadata_properties = ['Branches','CurrentBranch','RGBDS']
rgbds_files = ['rgbasm','rgbfix','rgblink','rgbgfx']

def error(msg):
    raise Exception('Error:\t' + msg)

def mkdir(*dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)

def get_dirs(path):
    return next(os.walk(path))[1]

def get_files(path):
    return next(os.walk(path))[2]

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

        # TODO - only when the game is getting built...
        mkdir(games_dir + self.Name)

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
        if self.Name not in ["Missing","Outdated","Search"]:
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

class PRET_Manager:
    def __init__(self):
        self.Manager = self
        self.Directory = games_dir
        
        self.All = []
        self.GUI = None
        self.App = None
        self.Search = None

        self.BaseLists = ["Favorites", "Excluding", "Outdated", "Missing"]

        self.Queue = []

        self.path = {
            'repo' : '.'
        }

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
            self.GUI.Process.ProcessSignals.log.emit(msg)

    def update(self):
        self.print('Updating pret-manager')
        self.git.pull()

    def init(self):
        self.Catalogs = Catalogs(self)

        self.load('data.json')

        # Initialize the base lists
        for name in self.BaseLists:
            self.addList(name, [])

        self.Catalogs.Lists.get(name).addGames([game for game in self.All if game.Missing])

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

        linux_env = main_env if main_env == 'linux' else environment

        self.Environments = {
            'git' : Environments[main_env],
            'gh' : Environments[main_env],
            'tar' : Environments[main_env],
            'make' : Environments[linux_env],
            'pwd' : Environments[linux_env]
        }
        
        self.git = Git(self)
        
        # if no args launch the gui
        if not any(vars(args).values()):
            return self.init_GUI()

        if args.process is None:
            return
        
        if args.process:
            processes = ''
            for process in args.process:
                if re.search(r'[^ubc]',process):
                    error('Only u, b, and c are valid process arguments. Received: ' + process)
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
                    elif process == 'f':
                        repo.fetch()
                    elif process == 'u':
                        repo.update()

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

        self.parse_builds()
        self.parse_releases()

        self.Missing = not os.path.exists(self.path['repo'])
        self.isExcluding = False
        self.isFavorite = False

        self.readMetaData()

        if self.manager.GUI and self.author != 'gbdev':
            self.init_GUI()

    def init_GUI(self):
        self.GUI = gui.GameGUI(self.manager.GUI.Content, self)

    def readMetaData(self):
        path = self.path['base'] + 'metadata.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.MetaData = json.loads(f.read())

        for prop in metadata_properties:
            self.getMetaDataProperty(prop)

    def getMetaDataProperty(self, name):
        if name in self.MetaData:
            setattr(self, name, self.MetaData[name])

    def updateMetaData(self):
        metadataChanged = [self.updateMetaDataProperty(prop) for prop in metadata_properties]

        if any(metadataChanged):
            with open(self.path['base'] + 'metadata.json', 'w') as f:
                f.write(json.dumps(self.MetaData))

    def updateMetaDataProperty(self, name):
        value = getattr(self, name)
        if name not in self.MetaData or value != self.MetaData[name]:
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

    def parse_builds(self):
        self.builds = {}
        if os.path.exists(self.path['builds']):
            for branch in get_dirs(self.path['builds']):
                for dirname in get_dirs(self.path['builds'] + branch):
                    # if the dir name matches the template, then it is a build
                    if re.match(r'^\d{4}-\d{2}-\d{2} [a-fA-F\d]{8} \([^)]+\)$',dirname):
                        if branch not in self.builds:
                            self.builds[branch] = {}

                        self.builds[branch][dirname] = {}
                        for build in get_builds(self.path['builds'] + branch + '/' + dirname):
                            self.builds[branch][dirname][build.name] = build
                    else:
                        self.print('Invalid build directory name: ' + dirname)

    def parse_releases(self):
        self.releases = {}
        if os.path.exists(self.path['releases']):
            for dirname in get_dirs(self.path['releases']):
                # if the dir name matches the template, then it is a release
                match = re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', dirname)
                if match:
                    if self.title == 'rgbds':
                        self.releases[match.group(1)] = dirname
                    else:
                        roms = get_builds(self.path['releases'] + dirname)
                        if roms:
                            self.releases[dirname] = {}
                            for rom in roms:
                                self.releases[dirname][rom.name] = rom
                else:
                    self.print('Invalid release directory name: ' + dirname)

    def print(self, msg):
        msg = self.name + ":\t" + str(msg)
        print(msg)

        if self.Manager.GUI:
            self.Manager.GUI.Process.ProcessSignals.log.emit(msg)

    def set_branch(self, branch):
        if branch != self.CurrentBranch:
            self.checkout(branch)
            # TODO - handle if failed
            self.CurrentBranch = branch
            self.updateMetaData()

    def set_RGBDS(self, RGBDS):
        if RGBDS != self.RGBDS:
            # If setting to default, then erase
            if RGBDS == self.rgbds:
                RGBDS = None
            
            self.RGBDS = RGBDS
            self.updateMetaData()

    # TODO - use git fetch --all to see if branch commit/date needs to be updated.
    # dont switch if not
    def get_branches(self):
        branches = self.git.branch(CaptureOutput=True)[:-1]

        new_branches = []
        new_current_branch = None
        doUpdate = False

        for line in branches:
            split = line.split(' ')
            name = split[-1]
            # set current branch as first index
            if split[0] == '*':
                new_current_branch = name

            new_branches.append(name)

        # arrange alphanetically
        new_branches.sort()

        new_branch_details = {}
        last_branch = None
        for branch in new_branches:
            if branch != new_current_branch:
                self.checkout(branch)
            lastUpdate = self.get_date()
            lastCommit = self.get_commit()

            new_branch_details[branch] = {
                "LastUpdate" : lastUpdate,
                "LastCommit" : lastCommit
            }

            if branch not in self.Branches or lastCommit != self.Branches[branch]["LastCommit"]:
                doUpdate = True

            last_branch = branch

        # return back to start branch
        if new_current_branch != last_branch:
            self.checkout(new_current_branch)

        # if the branches changed, then update
        if doUpdate or len(new_branch_details.keys()) != len(self.Branches.keys()) or self.CurrentBranch != new_current_branch:
            self.Branches = new_branch_details
            self.CurrentBranch = new_current_branch
            
            if self.GUI:
                self.GUI.Panel.updateBranchDetails()

    def get_url(self):
        return self.git.get('remote.origin.url')[0]

    def checkout(self, *args):
        #self.git.clean('-f')
        # TODO - handle failed checkout?
        self.print('Switching to ' + ' '.join(args))
        result = self.git.checkout(*args)
        self.print('Switched to ' + ' '.join(args))
        return result

    def clean(self):
        self.print('Cleaning')
        return self.make.clean()

    def fetch(self):
        self.print('Fetching')
        return self.git.fetch()

    def get_date(self):
        return self.git.date()

    def get_commit(self):
        return self.git.head()

    def get_build_info(self, version):
        commit = self.get_commit()
        date = self.get_date()
        self.build_name = date[:10] + ' ' + commit[:8] + ' (' + version + ')'
        mkdir(self.path['builds'], self.path['builds'] + self.CurrentBranch)
        self.build_dir = self.path['builds'] + self.CurrentBranch + '/' + self.build_name + '/'

    def build(self, *args):
        # if the repository doesnt exist, then update
        if not os.path.exists(self.path['repo']):
            self.update()

        if len(args):
            self.checkout(*args)

        version = self.RGBDS or self.rgbds
        self.get_build_info(version)

        # only build if commit not already built
        if os.path.exists(self.build_dir):
            self.print('Commit has already been built: ' + self.build_name)
        # if rgbds version is known, switch to and make:
        elif version:
            if version != "None": # custom can have "None" to skip building
                self.print('Building with RGBDS v' + version)
                self.build_rgbds(version)

        if len(args):
            self.print('Switching back')
            self.git.switch('-')


    def get_releases(self, overwrite=False):
        self.print('Checking releases')
        releases = self.github.list()

        # if any exist, then download
        if len(releases) > 1:
            newRelease = False
            for release in releases:
                # ignore empty lines
                if release:
                    [title, isLatest, id, datetime] = release.split('\t')

                    date = datetime.split('T')[0]
                    name = legal_name(date + ' - ' + title + ' (' + id + ')')
                    path = self.path['releases'] + name

                    if not os.path.exists(path) or overwrite:
                        self.print('Downloading ' + title)
                        self.github.download(id, path)
                        if self.title == 'rgbds':
                            self.releases[id] = name
                        else:
                            roms = get_builds(path)
                            if roms:
                                newRelease = True
                                self.releases[name] = {}
                                for rom in roms:
                                    self.releases[name][rom.name] = rom
            
            if newRelease and self.GUI:
                self.manager.GUI.Process.ProcessSignals.doRelease.emit(self)

        else:
            self.print('No releases found')
         
    def update(self):
        mkdir(self.path['base'])

        self.print("Updating local repository")
        if not os.path.exists(self.path['repo']):
            self.git.clone()
        else:
            url = self.get_url()
            if url != self.url:
                self.print("Local repo origin path is \"" + url + "\" \"" + self.url + "\"")

            self.git.pull()
    
        # check the shortcut
        shortcut = self.path['base'] + self.name + ' Repository.url'
        if not os.path.exists(shortcut):
            with open(shortcut,'w') as f:
                f.write('[InternetShortcut]\nURL=' + self.url + '\n')

        self.get_branches()
        self.get_releases()
        self.get_submodules()
        self.updateMetaData()

        if self.Missing:
            self.manager.Catalogs.Lists.get('Missing').removeGames([self])
            self.Missing = False

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
            if os.path.exists(dir) and not os.listdir(dir):
                os.rmdir(dir)

            if not os.path.exists(dir):
                self.git.sub_add(submodules[name], name)

    def build_rgbds(self, version):
        # if new, successful build, copy any roms to build dir
        if self.make.run(input=self.manager.RGBDS.use('v' + version)).returncode:
            self.print('Build failed for: ' + self.build_name)
            return False
        else:
            mkdir(self.path['builds'], self.build_dir)
            roms = get_builds(self.path['repo'])
            if roms:
                names = [rom.name for rom in roms]
                for rom, name in zip(roms, names):
                    shutil.copyfile(rom, self.build_dir + name)

                self.print('Placed rom(s) in ' + self.CurrentBranch + '/' + self.build_name + ': ' + ', '.join(names))
                
                if self.CurrentBranch not in self.builds:
                    self.builds[self.CurrentBranch] = {}

                self.builds[self.CurrentBranch][self.build_name] = {}
                for rom in roms:
                    self.builds[self.CurrentBranch][self.build_name][rom.name] = rom

                if self.GUI:
                    self.manager.GUI.Process.ProcessSignals.doBuild.emit(self)

                return True
            else:
                self.print('No roms found after build')
                return False

    def find_build(self, *args):
        if len(args):
            self.git.checkout(*args)

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
                    self.builds[type][version] = version_dir + type

    def build(self, version):
        # If the version is not in the list of releases, then update
        if version not in self.releases:
            # todo - only download required release, return true/false
            self.update()

        # If the version is still not a release, then its invalid
        if version not in self.releases:
            error('Invalid RGBDS version: ' + version)

        name = self.releases[version]

        type = self.Manager.Environments['make'].Type
        build_dir = self.path['builds'] + version + '/' + type + '/'

        cwd = self.path['releases'] + name
        extraction_dir = cwd + '/' + type

        if type == "linux":
            # if the extration dir doesnt exist, then extract
            if not len(glob.glob(extraction_dir)):
                mkdir(extraction_dir)
                # should only be one...
                for tarball in glob.glob(cwd + '/*.tar.gz'):
                    self.print('Extracting ' + name)

                    if Command('tar', self.Manager.Environments).run('-xzvf "{0}" -C "{1}"'.format(tarball, extraction_dir)).returncode:
                        self.print("Failed to extract " + tarball)
                        return False

            # directory depth is not consistent, so find where the makefile is
            extraction = glob.glob(cwd + '/**/Makefile', recursive=True)
            if not len(extraction):
                self.print("Failed to find Makefile under " + cwd)
                return False

            # simply remove the makefile to get the directory
            path = extraction[0].replace('Makefile','')
            
            self.print('Building ' + name)

            if self.make.run(Directory=path).returncode:
                self.print("Failed to build " + name)
                return False
            
            mkdir(build_dir)
            files = get_rgbds(path)
            if files:
                names = [file.name for file in files]
                for file, name in zip(files, names):
                    shutil.copyfile(file, build_dir + name)
            else:
                self.print('No rgbds files found after build')
                return False
        else:
            if not len(glob.glob(extraction_dir)):
                mkdir(extraction_dir)
                for zipfile in glob.glob(cwd + '/*' + type + '.zip'):
                    self.print('Extracting ' + name)
                    if Command('tar', self.Manager.Environments).run('-xf "{0}" -C "{1}"'.format(zipfile, extraction_dir)).returncode:
                        self.print("Failed to extract " + zipfile)
                        return False

            # directory depth is not consistent, so find where rgbasm.exe is
            extraction = glob.glob(cwd + '/**/rgbasm.exe', recursive=True)
            if not len(extraction):
                self.print("Failed to find rgbasm.exe under " + cwd)
                return False

            # simply remove the file name to get the directory
            path = extraction[0].replace('rgbasm.exe','')

            mkdir(build_dir)
            for file in get_files(path):
                shutil.copyfile(path + file, build_dir + file)

        self.print('Placed RGBDS ' + version + ' files into ' + build_dir)

        self.builds[type][version] =  Command('pwd', self.Manager.Environments, Directory=build_dir, CaptureOutput=True).run()[0]
        return True

    def use(self, version):
        if version not in self.builds:
            self.print('Building ' + version)

            if not self.build(version):
                error('Version {0} is not available'.format(version))

        return 'PATH="' + self.builds[self.Manager.Environments['make'].Type][version] + '":/root/.pyenv/shims:/root/.pyenv/bin:$PATH'

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
