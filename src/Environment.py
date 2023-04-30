import os, subprocess, platform, json
from src.Files import *

def addToInput(options, *inputs):
    if "input" in options:
        options["input"] = options["input"] + ';' + ';'.join(inputs)
    else:
        options["input"] = ';'.join(inputs)

class Environment:
    def __init__(self, environments, type):
        self.Environments = environments
        self.Type = type

    def path(self, path):
        return clean_path(path)
    
    def run(self, command, options):
        process = subprocess.run(command, **options)
        
        if 'capture_output' in options and options['capture_output']:
            return process.stdout.split('\n')
        else:
            return process

class AppEnvironment(Environment):
    def __init__(self, environments, app, type):
        super().__init__(environments, type)
        self.App = app

    def path(self, path):
        return super().path(os.path.abspath(path))

    def run(self, command, options):
        addToInput(options, command)
        return super().run(self.App, options)
 
class Linux(AppEnvironment):
    def __init__(self, environments, app):
        super().__init__(environments, app, 'linux')
    
class WSL(Linux):
    def __init__(self, environments):
        super().__init__(environments, 'wsl')

    def path(self, path):
        return re.sub(r'^([^:]+):/',lambda p: '/mnt/{0}/'.format(p.group(1).lower()), super().path(path))

class Windows(AppEnvironment):
    def __init__(self, environments, app):
        super().__init__(environments, app, environments.WindowsBit)

    def run(self, command, options):
        addToInput(options, 'cd "' + self.path(options['cwd']) + '"')
        return super().run(command, options)

# TODO - customizable cygwin installation directory
# todo - option to build or use windows binaries
class Cygwin(Windows):
    def __init__(self, environments):
        super().__init__(environments, 'c:/cygwin64/bin/bash.exe --login')

    def path(self, path):
        return re.sub(r'^([^:]+):/',lambda p: '/cygdrive/{0}/'.format(p.group(1).lower()), super().path(path))

# TODO - customizable w64devkit installation directory
class w64devkit(Windows):
    def __init__(self, environments):
        super().__init__(environments, 'C:/w64devkit/w64devkit.exe')

class Command:
    def __init__(self, command, environments, **kwargs):
        self.Command = command
        self.Environments = environments

        self.set_parameter("Encoding", kwargs, 'utf-8')
        self.set_parameter("CaptureOutput", kwargs, False)
        self.set_parameter("Directory", kwargs, '.')

    def path(self, path):
        return self.Environments.get(self.Command).path(path)

    def set_parameter(self, key, kwargs, default):
        setattr(self, key, kwargs[key] if key in kwargs else default)

    def get_parameter(self, key, kwargs):
        return kwargs[key] if key in kwargs else getattr(self, key)

    def run(self, *args, **kwargs):
        parameters = {
            'cwd' : self.get_parameter('Directory', kwargs),
            'capture_output' : self.get_parameter('CaptureOutput', kwargs),
            'encoding' : self.get_parameter('Encoding', kwargs)
        }

        if 'input' in kwargs:
            parameters['input']  = kwargs['input'] 

        return self.Environments.get(self.Command).run(self.Command + ' ' + ' '.join(args), parameters)

class GameCommand(Command):
    def __init__(self, command, game, **options):
        self.Game = game
        super().__init__(command, game.Manager.Environments, Directory=game.path['repo'], **options)

class Github(Command):
    def __init__(self, game):
        self.Game = game
        super().__init__('gh', game.Manager.Environments, CaptureOutput=True)

    def list(self):
        return self.run('release list -R {0}'.format(self.Game.url))

    def download(self, id, destination):
        # view assets
        assets = json.loads(self.run('release view --json assets {0} -R {1}'.format(id, self.Game.url))[0])["assets"]
        
        destination = self.path(destination)

        if assets:
            self.run('release download {0} -R {1} -D "{2}" -p "*"'.format(id, self.Game.url, destination))
        else:
            # todo - add option to build
            self.run('release download {0} -R {1} -D "{2}" -A zip'.format(id, self.Game.url, destination))

class Git(GameCommand):
    def __init__(self, game):
        super().__init__('git', game)

    def clone(self, *args, **options):
        path = self.path(self.Game.path['repo'])
        return self.run('clone {0} "{1}"'.format(self.Game.url, path), *args, Directory='.', **options)

    def branch(self, *args, **options):
        return self.run('branch -a', *args, **options)

    def pull(self, *args, **options):
        return self.run('pull --all', *args, **options)
    
    def fetch(self, *args, **options):
        return self.run('fetch', *args, **options)

    def checkout(self, *args, **options):
        return self.run('checkout', *args, **options)

    def compare(self, *args, **options):
        return self.run('ls-remote --heads', *args, CaptureOutput=True, **options)

    def get(self, *args, **options):
        return self.run('config --get', *args, CaptureOutput=True, **options)

    def date(self, *args, **options):
        return self.run('--no-pager log -1 --format=%ai', *args, CaptureOutput=True, **options)[0]

    def head(self, *args, **options):
        return self.run('rev-parse HEAD', *args, CaptureOutput=True, **options)[0]

    def switch(self, *args, **options):
        return self.run('switch', *args, **options)

    def sub_url(self, *args, **options):
        return self.run('submodule set-url', *args, **options)

    def sub_update(self, *args, **options):
        return self.run('submodule update --init', *args, **options)

    def sub_add(self, *args, **options):
        return self.run('submodule add -f', *args, **options)

class Make(GameCommand):
    def __init__(self, game):
        super().__init__('make', game)

    def clean(self, *args, **options):
        return self.run('clean', *args, **options)
    
class Tar(Command):
    def __init__(self, *args):
        super().__init__('tar', *args)

    def extract(self, archive, destination):
        # todo - for wsl, this needs to happen after??
        temp_path = temp_mkdir(destination)

        archive = self.path(archive)
        destination = self.path(destination)
        flags = '-xzvf' if archive.endswith('.tar.gz') else '-xf'

        process = self.run('{0} "{1}" -C "{2}"'.format(flags, archive, destination))
        result = not process.returncode

        if not result:
            rmdir(temp_path)

        return result

class Environments:
    def __init__(self, manager):
        self.Manager = manager

        if platform.system() == 'Windows':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pokeglitch.pretmanager')
            self.Main = 'windows'
            self.WindowsBit = 'win32' if ctypes.sizeof(ctypes.c_voidp) == 4 else 'win64'
        else:
            self.Main = 'linux'
            self.WindowsBit = None

        self.Map = {
            "windows" : Environment(self, self.WindowsBit),
            "linux" : Linux(self, 'sh'),
            "wsl" : WSL(self),
            "cygwin" : Cygwin(self),
            'w64devkit' : w64devkit(self)
        }

    def get(self, command):
        # if main environment is linux, then all commands use Linux environment
        if self.Main == 'linux':
            return self.Map['linux']

        id = self.Manager.Settings.Active["Environment"][command]

        if id == "main":
            id = self.Main
        elif id == "linux":
            id = self.Manager.Settings.Active["Environment"][id]

        return self.Map[id]
