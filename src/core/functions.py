import os

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

def open_path(path):
    if path and os.path.exists(path):
        url = QUrl.fromLocalFile(path)
        QDesktopServices.openUrl(url)

def listToDict(list):
    data = {}
    for game in list:
        if game.author in data:
            data[game.author].append(game.title)
        else:
            data[game.author] = [game.title]
    return data
