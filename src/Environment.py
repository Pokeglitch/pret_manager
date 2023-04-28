import os, subprocess, platform, json

def addToInput(options, *inputs):
    if "input" in options:
        options["input"] = options["input"] + ';' + ';'.join(inputs)
    else:
        options["input"] = ';'.join(inputs)

class Environment:
    def __init__(self, type):
        self.Type = type

    def path(self, path):
        return path.replace('\\','/')
    
    def run(self, command, options):
        process = subprocess.run(command, **options)
        
        if 'capture_output' in options and options['capture_output']:
            return process.stdout.split('\n')
        else:
            return process

class AppEnvironment(Environment):
    def __init__(self, app, type):
        super().__init__(type)
        self.App = app

    def run(self, command, options):
        addToInput(options, command)
        return super().run(self.App, options)
 
class Linux(AppEnvironment):
    def __init__(self, app):
        super().__init__(app, 'linux')

class Windows(AppEnvironment):
    def __init__(self, app):
        super().__init__(app, windows_bit)

    def path(self, path):
        return super().path(os.path.abspath(path))
    
    def run(self, command, options):
        addToInput(options, 'cd "' + self.path(options['cwd']) + '"')
        return super().run(command, options)

# TODO - customizable cygwin installation directory
# todo - option to build or use windows binaries
class Cygwin(Windows):
    def __init__(self):
        super().__init__('c:/cygwin64/bin/bash.exe --login')

    def path(self, path):
        return super().path(path).replace('C:/','/cygdrive/c/')

# TODO - customizable w64devkit installation directory
class w64devkit(Windows):
    def __init__(self):
        super().__init__('C:/w64devkit/w64devkit.exe')

class Command:
    def __init__(self, command, environments, **kwargs):
        self.Command = command
        self.Environments = environments

        self.set_parameter("Encoding", kwargs, 'utf-8')
        self.set_parameter("CaptureOutput", kwargs, False)
        self.set_parameter("Directory", kwargs, '.')

    def path(self, path):
        return self.Environments[self.Command].path(path)

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

        return self.Environments[self.Command].run(self.Command + ' ' + ' '.join(args), parameters)

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
            self.run('release download {0} -R {1} -D "{2}" -p "*" --clobber'.format(id, self.Game.url, destination))
        else:
            # todo - add option to build
            self.run('release download {0} -R {1} -D "{2}" -A zip --clobber'.format(id, self.Game.url, destination))

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

    def tarball(self, tarball, destination):
        tarball = self.path(tarball)
        destination = self.path(destination)
        return self.run('-xzvf "{0}" -C "{1}"'.format(tarball, destination)).returncode

    def zipball(self, zipball, destination):
        zipball = self.path(zipball)
        destination = self.path(destination)
        return self.run('-xf "{0}" -C "{1}"'.format(zipball, destination)).returncode

if platform.system() == 'Windows':
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pokeglitch.pretmanager')
    main_env = 'windows'
    windows_bit = 'win32' if ctypes.sizeof(ctypes.c_voidp) == 4 else 'win64'
else:
    main_env = 'linux'
    windows_bit = None

Environments = {
    "windows" : Environment(windows_bit),
    "linux" : Linux('sh'),
    "wsl" : Linux('wsl'),
    "cygwin" : Cygwin(),
    'w64devkit' : w64devkit()
}
