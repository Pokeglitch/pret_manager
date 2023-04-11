import subprocess, os, sys, re, glob, platform, shutil, argparse, shlex
from pathlib import Path

Lists = {}
rgbds = None

# prepend wsl if platform is windows
def wsl(commands):
    return ['wsl'] + commands if platform.system() == 'Windows' else commands

# remove invalid windows path chars from name
def legal_name(name):
    return re.sub(r'[<>:"/\|?*]', '', name)

def clean_url(url):
    match = re.match(r'^(?:(?:(?:https?|git)://)?github.com/)?([^/]+/(?:[^/]+))$', url)
    if not match:
        error("Not a valid github repository: " + url)

    url = match.group(1)
    if url.endswith('.git'):
        url = url[:-4]
    return url

def clean_dir(dir):
    dir = re.sub(r'[/\\]+','/', dir) # replace all slashes with /

    # remove trailing slash
    if dir.endswith('/'):
        dir = dir[:-1]

    return dir
    
# this expects dir has aleady been cleaned
def clean_repo_dir(dir):
    match = re.match(r'(.*/([^(]*) \([^)]*\))/([^/]+)$', dir)
    if match and match.group(2) == match.group(3):
        dir = match.group(1)
    
    return dir

def error(msg):
    raise Exception('Error:\t' + msg)

def mkdir(*dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

def add_version(version):
    if version and version not in repository.versions:
        repository.versions.append(version)

def add_to_group(group, repo):
    group = clean_dir(group)

    if group not in repository.groups:
        repository.groups[group] = []

    repository.groups[group].append(repo)

def add_by_url(url, repo):
    repository.by_url[clean_url(url)] = repo

def add_by_dir(dir, repo):
    repository.by_dir[clean_dir(dir)] = repo
    
def del_by_dir(dir):
    del repository.by_dir[clean_dir(dir)]

class repository:
    def __init__(self, base, url, source='', rgbds=''):
        self.base = ''

        repository.all.append(self)
        self.append_to_base(base)

        self.source = source
        self.rgbds = rgbds
        
        self.first_commit = ''
        self.last_commit = ''
        self.last_commit_date = ''
        self.dir = ''
        self.release_order = []

        self.url = url
        add_by_url(url, self)
        [self.author, self.title] = self.url.split('/')[-2:]
        self.name = self.title + ' (' + self.author + ')'

        # if a source exists, include it in the base
        if self.source:
            self.append_to_base(self.source)

        self.set_dirs()

    def append_to_base(self, addition):
        self.base += addition + '/'
        add_to_group(self.base, self)
        mkdir(self.base)

    def print(self, msg, doPrint=None):
        if not doPrint:
            doPrint = verbose
        if doPrint:
            print(self.name + ":\t" + msg)

    def output(self):
        return ','.join([self.url, self.source, self.rgbds])

    def run(self, args, capture_output, cwd, shell=None):
        if not os.path.exists(cwd):
            cwd = '.'

        if shell:
            description = "'" + args + "'"
        else:
            description = "'" + ' '.join(args) + "'"
        self.print("Executing " + description)
        
        process = subprocess.run(args, capture_output=capture_output, cwd=cwd, shell=None if platform.system() == 'Windows' else shell)

        if process.returncode:
            # print the error if it hasnt already been been displayed
            if capture_output:
                print(process.stderr.decode('utf-8'))
            self.print('Failed with exit code ' + str(process.returncode) + ' | ' + description, True)

        return process.stdout.decode('utf-8').split('\n') if capture_output else process

    def get_commit_data(self):
        commit = self.git('rev-parse','HEAD', capture_output=True)[0]
        date = self.git('--no-pager','log','-1','--format=%ai', capture_output=True)[0]
        return commit, date

    def get_commits(self):
        self.first_commit = self.git('rev-list','--max-parents=0','HEAD', capture_output=True)[0]
        self.last_commit, self.last_commit_date = self.get_commit_data()

    def set_dir(self):
        self.dir = self.base + self.name + '/'

    def get_url(self):
        return self.git('config','--get','remote.origin.url', capture_output=True)[0]

    def gh(self, *args, capture_output=True):
        return self.run(['gh'] + [*args], capture_output, '.')

    def git(self, *args, capture_output=False):
        return self.run(['git'] + [*args], capture_output, self.dir_repo)

    def pull(self):
        return self.git('pull')

    def make(self, *args, capture_output=False, cwd=None, version=None):
        command = ['make'] + [*args]

        if version is not None:
            command = ['(', rgbds.use(version), '&&'] + command + [')']

        command = ' '.join(wsl(command))
        return self.run(command, capture_output, cwd if cwd else self.dir_repo, shell=True)

    def clean(self):
        return self.make('clean', capture_output=verbose)

    def build(self):
        return

    def download(self, overwrite=False):
        self.print('Checking releases', True)
        releases = self.gh('release','list','-R', self.url)

        self.release_order = []

        # if any exist, then download
        if len(releases) > 1:
            for release in releases:
                # ignore empty lines
                if release:
                    [title, isLatest, id, datetime] = release.split('\t')

                    date = datetime.split('T')[0]
                    path = self.dir_releases + date + ' - ' + legal_name(title) + ' (' + legal_name(id) + ')'
                    self.release_order.append(id)

                    if not os.path.exists(path) or overwrite:
                        self.print('Downloading ' + title, True)
                        self.gh('release','download', id, '-R', self.url, '-D', path, '-p', '*', '--clobber')
                        self.gh('release','download', id, '-R', self.url, '-D', path, '-A','zip','--clobber')

                    else:
                        self.print('Skipping ' + path)
        else:
            self.print('No releases found')

    def set_dirs(self):
        if self.dir:
            del_by_dir(self.dir)

        self.set_dir()
        mkdir(self.dir)
        add_by_dir(self.dir, self)

        self.dir_repo = self.dir + self.title
        self.dir_releases = self.dir + 'releases/'
        self.dir_roms = self.dir + 'roms/'
         
    def update(self):
        self.print("Updating local repository", True)
        if not os.path.exists(self.dir_repo):
            self.git('clone', self.url, self.dir_repo)
        else:
            self.print(self.dir_repo + ' already exists')

            url = self.get_url()
            if url != self.url:
                self.print("Local repo origin path is \"" + url + "\" \"" + self.url + "\"", True)

            self.pull()
    
        # check the shortcut
        shortcut = self.dir + self.name + ' Repository.url'
        if not os.path.exists(shortcut):
            with open(shortcut,'w') as f:
                f.write('[InternetShortcut]\nURL=' + self.url + '\n')

        self.download()
        return self

repository.all = []
repository.versions = []
repository.by_dir = {}
repository.by_url = {}
repository.groups = {}

class remote(repository):
    def update(self):
        super().update()
        self.submodules()
        if os.path.exists(self.dir_repo + '/.rgbds-version'):
            with open(self.dir_repo + '/.rgbds-version', 'r') as f:
                self.rgbds = f.read()
        return self
        
    def submodules(self):
        submodules = {}

        if os.path.exists(self.dir_repo + '/.gitmodules'):
            self.print('Checking submodules')
            with open(self.dir_repo + '/.gitmodules', 'r') as f:
                content = f.read()
            
            # replace all 'git://github.com' with 'https://github.com'
            for match in re.finditer(r"\W*\[\W*submodule\W+[\"']([^\"]+)[\"']\W*][^[]+url\W*=\W*(.*)", content):
                name = match.group(1)
                url = match.group(2).replace('git://github.com', 'https://github.com')

                # update the 'extras' repo
                if name == 'extras':
                    url = url.replace('/kanzure/pokemon-reverse-engineering-tools.git','/pret/pokemon-reverse-engineering-tools.git')

                self.git('submodule','set-url', name, url)

                submodules[name] = url

            self.git('submodule','update','--init')

        for name in submodules:
            dir = self.dir_repo + '/' + name
            # if it exists, and is empty, then remove
            if os.path.exists(dir) and not os.listdir(dir):
                os.rmdir(dir)

            if not os.path.exists(dir):
                self.git('submodule','add','-f', submodules[name], name)

class disassembly(remote):
    def build_rgbds(self, version):
        # if new, successful build, copy any roms to build dir
        if self.make(version=version).returncode:
            self.print('Build failed for: ' + self.build_name)
            return False
        else:
            return self.move_roms()

    def move_roms(self):
        mkdir(self.dir_roms, self.build_dir)
        roms = [file for file in Path(self.dir_repo).iterdir() if file.suffix in ['.gb','.gbc','.pocket']]
        if roms:
            names = [rom.name for rom in roms]
            for rom, name in zip(roms, names):
                shutil.copyfile(rom, self.build_dir + name)

            self.print('Placed rom(s) in ' + self.build_name + ': ' + ', '.join(names), True)
            return True
        else:
            self.print('No roms found after build', True)
            return False

    def build(self, *args):
        if len(args):
            self.git(*(['checkout'] + [*args]))
        
        commit, date = self.get_commit_data()
        self.build_name = date[:10] + ' ' + commit[:8]
        self.build_dir = self.dir_roms + self.build_name + '/'

        # only build if commit not already built
        if os.path.exists(self.build_dir):
            self.print('Commit has already been built (' + self.build_name + ')', True)
        # if rgbds version is known, switch to and make:
        elif self.rgbds:
            self.print('Building', True)
            self.build_rgbds(self.rgbds)

        if len(args):
            self.git('switch','-')

    def try_build(self, *args):
        if len(args):
            self.git(*(['checkout'] +[*args]))
        
        commit, date = self.get_commit_data()
        self.build_name = date[:10] + ' ' + commit[:8]
        self.build_dir = self.dir_roms + self.build_name + '/'
        self.rgbds = ''

        for release in rgbds.release_order:
            self.clean()
            if self.build_rgbds(release[1:]):
                self.rgbds = release[1:]
                break

        if len(args):
            self.git('switch','-')

# TODO - see if the name contains pokered/pokeyellow/pokecrystal/pokegold
class fork(disassembly):
    def move(self):
        # dont move if already in correct location
        if self.source:
            if self.base.endswith(self.source + '/'):
                return
        else:
            if not self.first_commit:
                self.get_commits()

            # if a source does not exist, check the hashes
            if not self.source:
                for repo in repository.groups["pret"]:
                    if not repo.first_commit:
                        repo.get_commits()
                    if repo.first_commit == self.first_commit:
                        self.source = repo.title
                        break

            # if a source still doesnt exist, see if it is a fork of any other repo that exists
            if not self.source:
                for repo in repository.groups["forks"]:
                    if not repo.first_commit:
                        repo.get_commits()
                    if repo != self and repo.first_commit == self.first_commit:
                        self.source = repo.source
                        break
        
        if self.source:
            old_dir = self.dir
            self.append_to_base(self.source)
            self.set_dirs() # update the directory members
            self.print("Moving to: " + self.dir)
            shutil.move(old_dir, self.dir)

class RGBDS(repository):
    def __init__(self, update_all_rgbds, *args):
        super().__init__(*args)
        self.releases = {}
        self.update(update_all_rgbds)

    def set_dir(self):
        self.dir = self.base

    def update(self, update_all=False):
        super().update()

        for release in next(os.walk(self.dir_releases))[1]:
            match = re.search('^.* \\(v([^)]+)\\)$', release)
            if not match:
                self.print("Failed to extract version from " + release, True)
            else:
                version = match.group(1)

                # only build required releases
                if version in repository.versions or update_all:
                    self.build(release, version)

    def build(self, name, version):
        cwd = self.dir_releases + name

        if not len(glob.glob(cwd + '/rgbds/')):
            os.mkdir(cwd + '/rgbds/')
            for tarball in glob.glob(cwd + '/*.tar.gz'):
                self.print('Extracting ' + name, True)

                process = subprocess.run(['tar', '-xzvf', tarball, '-C',  cwd + '/rgbds'], capture_output=True) # extract

                if process.returncode:
                    self.print("Failed to extract " + tarball, True)
                    return

        extraction = glob.glob(cwd + '/**/Makefile', recursive=True)
        if not len(extraction):
            self.print("Failed to find Makefile under " + cwd, True)
            return

        path = extraction[0].replace('Makefile','')
        if not os.path.exists(path + 'rgbasm'):
            self.print('Building ' + name, True)
            process = self.make(cwd=path) # make

            if process.returncode:
                self.print("Failed to build " + name, True)
                return

        self.releases[version] = self.run(wsl(['pwd']), cwd=path, capture_output=True)[0]

    def use(self, version):
        return 'PATH="' + self.releases[version] + ':$PATH"'

class List:
    def __init__(self, name, subclass=remote):
        Lists[name] = self
        self.repos = {}
        self.subclass = subclass
        self.name = name
        self.file = name + '.txt'

        if os.path.exists(self.file):
            self.load()

    def load(self):
        print("Loading List: " + self.name)

        # add any new repos from the list
        with open(self.file,'r') as f:
            lines = f.read().split('\n')
            for line in lines:
                if line:
                    data = line.split(',')
                    [url, source, rgbds] = data + ['']*(3-len(data)) # init missing entries with ''
                    add_version(rgbds)
                    self.repos[url] = self.subclass(self.name, url, source, rgbds)

    def foreach(self, fn, *args):
        for url in self.repos:
            getattr(self.repos[url],fn)(*args)

    def update(self):
        self.foreach('update')

    def move(self):
        self.foreach('move')

    def build(self,*args):
        self.foreach('build',*args)

    def try_build(self,*args):
        self.foreach('try_build',*args)

    def clean(self):
        self.foreach('clean')

    def write(self):
        lines = []

        for url in self.repos:
            lines.append(self.repos[url].output())

        # arrange alphabetically
        lines.sort()
        
        with open(self.file,'w') as f:
            f.write('\n'.join(lines))

def add_target(*repos):
    for repo in repos:
        if repo not in targets:
            targets.append(repo)

def validate_dirs(dirs):
    if dirs:
        for dir in dirs:
            dir = clean_dir(dir)

            # clean any pattern that matches the git repository within an instances main directory
            dir = clean_repo_dir(dir)

            # if dir is a group, add the entire group
            if dir in repository.groups.keys():
                add_target(*repository.groups[dir])
            elif dir in repository.by_dir:
                add_target(repository.by_dir[dir])
            else:
                error('Directory not a valid target: ' + dir)

def validate_remote():
    if args.remote:
        for url in args.remote:
            cleaned_url = clean_url(url)
            if cleaned_url in repository.by_url:
                add_target(repository.by_url[cleaned_url])
            else:
                error('Invalid URL: ' + url)

def validate_glob():
    if args.glob:
        dirs = glob.glob(args.glob + '/')
        if dirs:
            validate_dirs(dirs)
        else:
            error('No matches for glob pattern: ' + args.glob)

def init(update_all_rgbds=False):
    global rgbds

    List("pret", disassembly)
    List("forks", fork)
    List("hacks")
    List("extras")
    List("custom")

    rgbds = RGBDS(update_all_rgbds, 'rgbds', 'https://github.com/gbdev/rgbds')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='pret_manager',
        description='Manage various pret related projects'
    )

    parser.add_argument('-dir', '-d', nargs='+', help='Path of directories to manage')
    parser.add_argument('-remote', '-r', nargs='+', help='URL of remote repositories to manage')
    parser.add_argument('-glob', '-g', help='glob pattern of directories to manage')
    parser.add_argument('-verbose', '-v', action='store_true', help='Display all log messages')
    parser.add_argument('-update', '-u', action='store_true', help='Pull the managed repositories')
    parser.add_argument('-build', '-b', nargs='*', help='Build the managed repositories')
    parser.add_argument('-clean', '-c', action='store_true', help='Clean the managed repositories')

    targets = []

    try:
        args = parser.parse_args()
        verbose = args.verbose

        if args.update:
            print('pret-manager:\tUpdating repository')
            subprocess.run(['git', 'pull'], capture_output=True) 
        
        init()

        validate_dirs(args.dir)
        validate_remote()
        validate_glob()


        if not targets:
            targets = repository.all

        # assign defaults if none are submitted
        if args.build is None and not args.update and not args.clean:
            args.update = True
            args.build = []

        for target in targets:
            if target != rgbds:
                if args.update:
                    target.update()

                if args.build is not None:
                    target.build(*args.build)

                if args.clean:
                    target.clean()

    except Exception as e:
        print(e)
else:
    verbose=True
    init(True)