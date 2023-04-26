import os, subprocess

def addToInput(options, *inputs):
    if "input" in options:
        options["input"] = options["input"] + ';' + ';'.join(inputs)
    else:
        options["input"] = ';'.join(inputs)

class Environment:
    def path(self, path):
        return path.replace('\\','/')
    
    def run(self, command, options):
        process = subprocess.run(command, **options)
        
        if 'capture_output' in options and options['capture_output']:
            return process.stdout.split('\n')
        else:
            return process

class AppEnvironment(Environment):
    def __init__(self, app):
        self.App = app
        self.Type = 'Linux'

    def run(self, command, options):
        addToInput(options, command)
        return super().run(self.App, options)
 
class Shell(AppEnvironment):
    def __init__(self):
        super().__init__('sh')

class WSL(AppEnvironment):
    def __init__(self):
        super().__init__('wsl')

class WindowsAppEnvironment(AppEnvironment):
    def __init__(self, *args):
        super().__init__(*args)
        self.Type = 'Windows'

    def path(self, path):
        return super().path(os.path.abspath(path))
    
    def run(self, command, options):
        addToInput(options, 'cd "' + self.path(options['cwd']) + '"')
        return super().run(command, options)

# TODO - customizable cygwin installation directory
# todo - option to build or use windows binaries
class Cygwin(WindowsAppEnvironment):
    def __init__(self):
        super().__init__('c:/cygwin64/bin/bash.exe --login')

    def path(self, path):
        return super().path(path).replace('C:/','/cygdrive/c/')

# TODO - customizable w64devkit installation directory
class w64devkit(WindowsAppEnvironment):
    def __init__(self):
        super().__init__('C:/w64devkit/w64devkit.exe')

class Command:
    def __init__(self, command, environments, **kwargs):
        self.Command = command
        self.Environments = environments

        self.set_parameter("Encoding", kwargs, 'utf-8')
        self.set_parameter("CaptureOutput", kwargs, False)
        self.set_parameter("Directory", kwargs, '.')

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

    def download(self, id, path):
        self.run('release download {0} -R {1} -D "{2}" -p * --clobber'.format(id, self.Game.url, path))
        self.run('release download {0} -R {1} -D "{2}" -A zip --clobber'.format(id, self.Game.url, path))

class Git(GameCommand):
    def __init__(self, game):
        super().__init__('git', game)

    def clone(self, *args, **options):
        print('clone {0} "{1}"'.format(self.Game.url, self.Game.path['repo']))
        return self.run('clone {0} "{1}"'.format(self.Game.url, self.Game.path['repo']), *args, Directory='.', **options)

    def branch(self, *args, **options):
        return self.run('branch', *args, **options)

    def pull(self, *args, **options):
        return self.run('pull --all', *args, **options)
    
    def fetch(self, *args, **options):
        return self.run('fetch', *args, **options)

    def checkout(self, *args, **options):
        return self.run('checkout', *args, **options)

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
    
    def disasm(self, *args, **options):
        return self.run()
    
    def rgbds(self, *args, **options):
        return self.run()

Environments = {
    "windows" : Environment(),
    "shell" : Shell(),
    "wsl" : WSL(),
    "cygwin" : Cygwin(),
    'w64devkit' : w64devkit()
}