import subprocess, os, re, glob, platform, shutil, argparse, json
from pathlib import Path

build_extensions = ['gb','gbc','pocket','patch']

def get_dirs(path):
    return next(os.walk(path))[1]

def get_builds(path):
    return [file for file in Path(path).iterdir() if file.suffix[1:] in build_extensions]

authors = {}
tags = {}

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

def add_by_dir(dir, repo):
    repository.by_dir[clean_dir(dir)] = repo

class repository:
    def __init__(self, url, rgbds=''):
        repository.all.append(self)

        self.rgbds = rgbds        
        self.release_order = []

        self.url = url
        [self.author, self.title] = self.url.split('/')[-2:]
        self.name = self.title + ' (' + self.author + ')'

        self.dir = 'data/' + self.author + '/' + self.title + '/'

        add_by_dir(self.dir, self)

        self.dir_repo = self.dir + self.title
        self.dir_releases = self.dir + 'releases/'
        self.dir_roms = self.dir + 'roms/'

        self.parse_builds()
        self.parse_releases()

        # todo - debug only
        if self.rgbds and not self.builds:
            self.print(self.rgbds)

    def parse_builds(self):
        self.builds = {}
        if os.path.exists(self.dir_roms):
            for dirname in get_dirs(self.dir_roms):
                # if the dir name matches the template, then it is a build
                if re.match(r'^\d{4}-\d{2}-\d{2} [a-fA-F\d]{8}$',dirname):
                    self.builds[dirname] = get_builds(self.dir_roms + dirname)
                else:
                    self.print('Invalid build directory name: ' + dirname)

    def parse_releases(self):
        self.releases = {}
        if os.path.exists(self.dir_releases):
            for dirname in get_dirs(self.dir_releases):
                # if the dir name matches the template, then it is a build
                match = re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', dirname)
                if match:
                    self.releases[match.group(1)] = dirname
                else:
                    self.print('Invalid release directory name: ' + dirname)

    def print(self, msg, doPrint=None):
        if not doPrint:
            doPrint = verbose
        if doPrint:
            print(self.name + ":\t" + msg)

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

    def get_build_info(self):
        commit = self.git('rev-parse','HEAD', capture_output=True)[0]
        date = self.git('--no-pager','log','-1','--format=%ai', capture_output=True)[0]
        self.build_name = date[:10] + ' ' + commit[:8]
        self.build_dir = self.dir_roms + self.build_name + '/'

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
            command = ['(', RGBDS.repo.use(version), '&&'] + command + [')']

        command = ' '.join(wsl(command))
        return self.run(command, capture_output, cwd if cwd else self.dir_repo, shell=True)

    def clean(self):
        return self.make('clean', capture_output=verbose)

    def build(self):
        return

    def download(self, overwrite=False):
        self.print('Checking releases', True)
        releases = self.gh('release','list','-R', self.url)

        # if any exist, then download
        if len(releases) > 1:
            for release in releases:
                # ignore empty lines
                if release:
                    [title, isLatest, id, datetime] = release.split('\t')

                    date = datetime.split('T')[0]
                    name = legal_name(date + ' - ' + title + ' (' + id + ')')
                    path = self.dir_releases + name

                    if not os.path.exists(path) or overwrite:
                        self.print('Downloading ' + title, True)
                        self.gh('release','download', id, '-R', self.url, '-D', path, '-p', '*', '--clobber')
                        self.gh('release','download', id, '-R', self.url, '-D', path, '-A','zip','--clobber')
                        self.releases[id] = name

                    else:
                        self.print('Skipping ' + path)
        else:
            self.print('No releases found')
         
    def update(self):
        mkdir(self.dir)

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
        self.submodules()

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

repository.all = []
repository.by_dir = {}

class disassembly(repository):
    def update(self):
        super().update()
        
        # todo - this is only necessary when adding a brand new repo
        if os.path.exists(self.dir_repo + '/.rgbds-version'):
            with open(self.dir_repo + '/.rgbds-version', 'r') as f:
                self.rgbds = f.read().split("\n")[0]

    def build_rgbds(self, version):
        # if new, successful build, copy any roms to build dir
        if self.make(version=version).returncode:
            self.print('Build failed for: ' + self.build_name)
            return False
        else:
            mkdir(self.dir_roms, self.build_dir)
            roms = get_builds(self.dir_repo)
            if roms:
                names = [rom.name for rom in roms]
                for rom, name in zip(roms, names):
                    shutil.copyfile(rom, self.build_dir + name)

                self.print('Placed rom(s) in ' + self.build_name + ': ' + ', '.join(names), True)
                
                self.builds[self.build_name] = roms
                return True
            else:
                self.print('No roms found after build', True)
                return False

    def build(self, *args):
        # if the repository doesnt exist, then update
        if not os.path.exists(self.dir_repo):
            self.update()

        if len(args):
            self.git(*(['checkout'] + [*args]))
        
        self.get_build_info()

        # only build if commit not already built
        if os.path.exists(self.build_dir):
            self.print('Commit has already been built: ' + self.build_name, True)
        # if rgbds version is known, switch to and make:
        elif self.rgbds:
            self.print('Building', True)
            self.build_rgbds(self.rgbds)

        if len(args):
            self.git('switch','-')

    def try_build(self, *args):
        if len(args):
            self.git(*(['checkout'] +[*args]))
        
        self.get_build_info()
        self.rgbds = ''

        for release in reversed(list(RGBDS.repo.releases.keys())):
            self.clean()
            if self.build_rgbds(release[1:]):
                self.rgbds = release[1:]
                break

        if len(args):
            self.git('switch','-')

class RGBDS(repository):
    def build_version(self, version):
        # If the version is not in the list of releases, then update
        if 'v'+version not in self.releases:
            self.update()

        # If the version is still not a release, then its invalid
        if 'v'+version not in self.releases:
            error('Invalid RGBDS version: ' + version)

        name = self.releases['v' + version]

        cwd = self.dir_releases + name

        if not len(glob.glob(cwd + '/rgbds')):
            os.mkdir(cwd + '/rgbds')
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

        # get the absolute path
        self.builds[version] = self.run(wsl(['pwd']), cwd=path, capture_output=True)[0]

    def use(self, version):
        if version not in self.builds:
            self.build_version(version)

        return 'PATH="' + self.builds[version] + ':/root/.pyenv/shims:/root/.pyenv/bin:$PATH"'

def add_target(*repos):
    for repo in repos:
        if repo not in targets:
            targets.append(repo)

def validate_glob():
    if args.glob:
        dirs = glob.glob(args.glob + '/')
        if dirs:
            for dir in dirs:
                dir = clean_dir(dir)

                # clean any pattern that matches the git repository within an instances main directory
                dir = clean_repo_dir(dir)

                # if dir is an author, add all
                if dir in sets["authors"].keys():
                    add_target(*sets["authors"][dir])
                elif dir in repository.by_dir:
                    add_target(repository.by_dir[dir])
                else:
                    error('Directory not a valid target: ' + dir)
        else:
            error('No matches for glob pattern: ' + args.glob)

mkdir('data')

def load(filepath):
    if not os.path.exists(filepath):
        error(filepath + ' not found')

    with open(filepath,"r") as f:
        data = json.loads(f.read())

    for author in data:
        author_url = 'https://github.com/' + author + '/'
        mkdir('data/' + author)

        for title in data[author]:
            url = author_url + title
            o = data[author][title]
            rgbds = o["rgbds"] if "rgbds" in o else ""
            repo_tags = o["tags"] if "tags" in o else []
            repo_tags = repo_tags if isinstance(repo_tags, list) else [repo_tags]

            if "disasm" in repo_tags:
                repo = disassembly(url, rgbds)
            elif title == "rgbds":
                repo = RGBDS(url, rgbds)
                RGBDS.repo = repo
            else:
                repo = repository(url, rgbds)

            if author not in authors:
                authors[author] = {}
            authors[author][title] = repo

            for tag in repo_tags:
                if tag not in tags:
                    tags[tag] = []
                tags[tag].append(repo)

def init():
    load('data.json')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='pret_manager',
        description='Manage various pret related projects'
    )

    # todo - -t for tags
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

        validate_glob()

        if not targets:
            targets = repository.all

        # assign defaults if none are submitted
        if args.build is None and not args.update and not args.clean:
            args.update = True
            args.build = []

        if args.build is not None:
            rgbds.build()

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
    init()