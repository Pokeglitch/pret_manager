import subprocess, os, re, glob, platform, shutil, argparse, json
from pathlib import Path

build_extensions = ['gb','gbc','pocket','patch']

def error(msg):
    raise Exception('Error:\t' + msg)

def mkdir(*dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

class PRET_Manager:
    def __init__(self):
        self.Directory = 'data/'
        mkdir(self.Directory)
        
        self.All = []
        self.Authors = {}
        self.Tags = {}
        self.Verbose = False
        self.reset()

    def reset(self):
        self.clear_selection()
        self.doUpdate = False
        self.doBuild = None
        self.doClean = False

    def print(self, msg):
        print('pret-manager:\t' + str(msg))

    def update(self):
        self.print('Updating repository')
        subprocess.run(['git', 'pull'], capture_output=True)

    def init(self):
        self.load('data.json')
        # todo - load 'custom.json' which has additional tags (ignore, favorite, etc)

    def handle_args(self):
        args = parser.parse_args()
        self.Verbose = args.verbose

        # assign defaults if none are submitted
        if args.build is None and not args.update and not args.clean:
            self.doUpdate = True
            self.doBuild = []
        else:
            self.doUpdate = args.update
            self.doBuild = args.build
            self.doClean = args.clean

        if self.doUpdate:
            self.update()

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
        
        self.run()

    def run(self):
        if not self.Selection:
            self.print('No repos to manage')
        else:
            for repos in self.Selection:
                if self.doUpdate:
                    repos.update()

                if self.doBuild is not None:
                    repos.build(*self.doBuild)

                if self.doClean:
                    repos.clean()

        self.reset()


    def load(self, filepath):
        if not os.path.exists(filepath):
            error(filepath + ' not found')

        with open(filepath,"r") as f:
            data = json.loads(f.read())

        for author in data:
            self.Authors[author] = {}
            mkdir(self.Directory + author)

            for title in data[author]:
                if title == "rgbds":
                    repo = RGBDS(self, author, title, data[author][title])
                    self.RGBDS = repo
                else:
                    repo = repository(self, author, title, data[author][title])
                    self.All.append(repo)

                self.Authors[author][title] = repo

                for tag in repo.tags:
                    self.add_repo_tag(repo, tag)

    def add_repo_tag(self, repo, tag):
        if tag not in self.Tags:
            self.Tags[tag] = []
        self.Tags[tag].append(repo)

    def add_to_selection(self, repos):
        for repo in repos:
            if repo not in self.Selection:
                self.Selection.append(repo)

    def remove_from_selection(self, repos):
        for repo in repos:
            if repo in self.Selection:
                self.Selection.pop( self.Selection.index(repo) )
    
    def keep_in_selection(self, repos):
        self.remove_from_selection([repo for repo in self.Selection if repo not in repos])

    def add_all(self):
        self.add_to_selection(self.All)

    def clear_selection(self):
        self.Selection = []

    def add_repos(self, repos):
        for repo in repos:
            [author, title] = repo.split('/')
            self.add_to_selection([self.Authors[author][title]])

    def remove_repos(self, repos):
        for repo in repos:
            [author, title] = repo.split('/')
            self.remove_from_selection([self.Authors[author][title]])

    def add_authors(self, authors):
        for author in authors:
            self.add_to_selection([self.Authors[author][title] for title in self.Authors[author]])

    def remove_authors(self, authors):
        for author in authors:
            self.remove_from_selection([self.Authors[author][title] for title in self.Authors[author]])
    
    def keep_authors(self, authors):
        repos = []
        for author in authors:
            repos += [self.Authors[author][title] for title in self.Authors[author]]
        
        self.keep_in_selection(repos)

    def add_tags(self, tags):
        for tag in tags:
            if tag in self.Tags:
                self.add_to_selection(self.Tags[tag])

    def remove_tags(self, tags):
        for tag in tags:
            if tag in self.Tags:
                 self.remove_from_selection(self.Tags[tag])

    def keep_tags(self, tags):
        for tag in tags:
            if tag in self.Tags:
                self.keep_in_selection(self.Tags[tag])

def get_dirs(path):
    return next(os.walk(path))[1]

def get_builds(path):
    return [file for file in Path(path).iterdir() if file.suffix[1:] in build_extensions]

# prepend wsl if platform is windows
def wsl(commands):
    return ['wsl'] + commands if platform.system() == 'Windows' else commands

# remove invalid windows path chars from name
def legal_name(name):
    return re.sub(r'[<>:"/\|?*]', '', name)

class repository:
    def __init__(self, manager, author, title, data):
        self.manager = manager
        self.author = author
        self.title = title
        self.name = self.title + ' (' + self.author + ')'
        self.url = 'https://github.com/' + author + '/' + title

        self.rgbds = data["rgbds"] if "rgbds" in data else ""
        
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

        self.parse_builds()
        self.parse_releases()

    def parse_builds(self):
        self.builds = {}
        if os.path.exists(self.path['builds']):
            for dirname in get_dirs(self.path['builds']):
                # if the dir name matches the template, then it is a build
                if re.match(r'^\d{4}-\d{2}-\d{2} [a-fA-F\d]{8}$',dirname):
                    self.builds[dirname] = get_builds(self.path['builds'] + dirname)
                else:
                    self.print('Invalid build directory name: ' + dirname)

    def parse_releases(self):
        self.releases = {}
        if os.path.exists(self.path['releases']):
            for dirname in get_dirs(self.path['releases']):
                # if the dir name matches the template, then it is a build
                match = re.match(r'^\d{4}-\d{2}-\d{2} - .* \((.*)\)$', dirname)
                if match:
                    self.releases[match.group(1)] = dirname
                else:
                    self.print('Invalid release directory name: ' + dirname)

    def print(self, msg, doPrint=None):
        if not doPrint:
            doPrint = self.manager.Verbose
        if doPrint:
            print(self.name + ":\t" + str(msg))

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

    def get_url(self):
        return self.git('config','--get','remote.origin.url', capture_output=True)[0]

    def gh(self, *args, capture_output=True):
        return self.run(['gh'] + [*args], capture_output, '.')

    def git(self, *args, capture_output=False):
        return self.run(['git'] + [*args], capture_output, self.path['repo'])

    def pull(self):
        return self.git('pull')

    def make(self, *args, capture_output=False, cwd=None, version=None):
        command = ['make'] + [*args]

        if version is not None:
            command = ['(', self.manager.RGBDS.use(version), '&&'] + command + [')']

        command = ' '.join(wsl(command))
        return self.run(command, capture_output, cwd if cwd else self.path['repo'], shell=True)

    def clean(self):
        self.print('Cleaning', True)
        return self.make('clean', capture_output=not self.manager.Verbose)

    def get_build_info(self):
        commit = self.git('rev-parse','HEAD', capture_output=True)[0]
        date = self.git('--no-pager','log','-1','--format=%ai', capture_output=True)[0]
        self.build_name = date[:10] + ' ' + commit[:8]
        self.build_dir = self.path['builds'] + self.build_name + '/'

    def build(self, *args):
        # if the repository doesnt exist, then update
        if not os.path.exists(self.path['repo']):
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

    def get_releases(self, overwrite=False):
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
                    path = self.path['releases'] + name

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
        mkdir(self.path['base'])

        self.print("Updating local repository", True)
        if not os.path.exists(self.path['repo']):
            self.git('clone', self.url, self.path['repo'])
        else:
            self.print(self.path['repo'] + ' already exists')

            url = self.get_url()
            if url != self.url:
                self.print("Local repo origin path is \"" + url + "\" \"" + self.url + "\"", True)

            self.pull()
    
        # check the shortcut
        shortcut = self.path['base'] + self.name + ' Repository.url'
        if not os.path.exists(shortcut):
            with open(shortcut,'w') as f:
                f.write('[InternetShortcut]\nURL=' + self.url + '\n')

        self.get_releases()
        self.get_submodules()

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

                self.git('submodule','set-url', name, url)

                submodules[name] = url

            self.git('submodule','update','--init')

        for name in submodules:
            dir = self.path['repo'] + '/' + name
            # if it exists, and is empty, then remove
            if os.path.exists(dir) and not os.listdir(dir):
                os.rmdir(dir)

            if not os.path.exists(dir):
                self.git('submodule','add','-f', submodules[name], name)

    def build_rgbds(self, version):
        # if new, successful build, copy any roms to build dir
        if self.make(version=version).returncode:
            self.print('Build failed for: ' + self.build_name)
            return False
        else:
            mkdir(self.path['builds'], self.build_dir)
            roms = get_builds(self.path['repo'])
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

    def find_build(self, *args):
        if len(args):
            self.git(*(['checkout'] +[*args]))

        self.get_build_info()
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
            if self.build_rgbds(release):
                self.rgbds = release
                break

        if len(args):
            self.git('switch','-')

class RGBDS(repository):
    def build(self, *versions):
        # If no version provided, then build all
        if not versions:
            versions = [version[1:] for version in self.releases.keys()]

        for version in versions:
            # If the version is not in the list of releases, then update
            if 'v'+version not in self.releases:
                self.update()

            # If the version is still not a release, then its invalid
            if 'v'+version not in self.releases:
                error('Invalid RGBDS version: ' + version)

            name = self.releases['v' + version]

            cwd = self.path['releases'] + name

            # TODO - need to check it contains rgbasm...
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

            # TODO - copy the built files to builds directory instead of using the extracted release directory?

            # get the absolute path
            self.builds[version] = self.run(wsl(['pwd']), cwd=path, capture_output=True)[0]

    def use(self, version):
        if version not in self.builds:
            self.build(version)

        # TODO - add way to set python version (can set for this directory only?)
        return 'PATH="' + self.builds[version] + ':/root/.pyenv/shims:/root/.pyenv/bin:$PATH"'

pret_manager = PRET_Manager()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='pret_manager',
        description='Manage various pret related projects'
    )

    parser.add_argument('-repos', '-r', nargs='+', help='Repo(s) to manage')
    parser.add_argument('-exclude-repos', '-xr', nargs='+', help='Repo(s) to not manage')
    parser.add_argument('-authors', '-a', nargs='+', help='Author(s) to manage')
    parser.add_argument('-exclude-tags', '-xt', nargs='+', help='Tags(s) to not manage')
    parser.add_argument('-tags', '-t', nargs='+', help='Tags(s) to manage')
    parser.add_argument('-exclude-authors', '-xa', nargs='+', help='Author(s) to not manage')
    parser.add_argument('-update', '-u', action='store_true', help='Pull the managed repositories')
    parser.add_argument('-build', '-b', nargs='*', help='Build the managed repositories')
    parser.add_argument('-clean', '-c', action='store_true', help='Clean the managed repositories')
    parser.add_argument('-verbose', '-v', action='store_true', help='Display all log messages')
    
    try:        
        pret_manager.handle_args()
    except Exception as e:
        print(e)
else:
    pret_manager.init()