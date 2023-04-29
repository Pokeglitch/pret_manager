import re, os, shutil, glob
from pathlib import Path

def find(pattern, **opts):
    paths = glob.glob(pattern, **opts)
    return [clean_path(path) for path in paths]

def copy(files, destination):
    mkdir(destination)
    names = [file.name for file in files]
    for file, name in zip(files, names):
        shutil.copyfile(file, destination + name)
    return names

def is_empty(dir):
    return not os.listdir(dir)

def get_dirs(path):
    return next(os.walk(path))[1]

def get_all_files(path):
    return [file for file in Path(path).iterdir()]

def clean_path(path):
    return re.sub(r'[\\/]+','/', path)

def split_path(path):
    return clean_path(path).split('/')

def rmdir(dir):
    if dir:
        return shutil.rmtree(dir)
    
    return True

def dir_only(path):
    return '/'.join( split_path(path)[:-1] )

def temp_mkdir(dir):
    dirs = split_path(dir)
    path = dirs.pop(0)

    # skip the directories which already exist
    while os.path.exists(path) and dirs:
        path += '/' + dirs.pop(0)

    # make any non-existing directories
    if not os.path.exists(path):
        os.makedirs(dir)
        # return the first new directory
        return path

    return None

def mkdir(*dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
