import time, json, copy, os, math

from src.qt.qt import *
from src.Files import *
from src.menus import *
from src.core.functions import *

OfficialTags = ['red','green','blue','yellow','gold','silver','crystal','spaceworld','tcg1','tcg2','official','binary','disasm','vc-patch','analogue','debug','extras']

class MetaData(Emitter):
    def __init__(self, properties):
        super().__init__()
        self.MetaData = {}
        self.MetaDataProperties = properties
        self.Initialized = False

    def readMetaData(self, autoSetOutdated=True):
        path = self.path['base'] + 'metadata.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.loads(f.read() or '{}')

            self.MetaData = {}
            for prop in self.MetaDataProperties:
                if prop in data:
                    self.MetaData[prop] = data[prop]
        elif autoSetOutdated:
            self.setOutdated(True)

        for prop in self.MetaDataProperties:
            self.getMetaDataProperty(prop)

    def getMetaDataProperty(self, name):
        if name in self.MetaData:
            value = copy.deepcopy(self.MetaData[name])
            if name in self.Manager.FlagLists and hasattr(self, 'set' + name):
                getattr(self, "set" + name)(value)
            else:
                setattr(self, name, value)

    def updateMetaData(self):
        # dont update meta data if triggered during initialization
        # (since some parameters are not assigned properly yet)
        if self.Initialized:
            metadataChanged = [self.updateMetaDataProperty(prop) for prop in self.MetaDataProperties]

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

class MenuIcon(Icon):
    def __init__(self, parent):
        super().__init__(parent, 'assets/images/menu.png', 36)

class SaveListDialog(Dialog):
    Title = "Save List"

    log = pyqtSignal(str)

    def init(self, GUI, list):
        self.List = list
        self.GUI = GUI
        self.Container = VBox(GUI)
        
        self.log.connect(GUI.print)
        
        self.ListName = QLineEdit()
        self.ListName.setPlaceholderText("List Name")
        self.ListName.textChanged.connect(self.onTextChanged)
        self.ListName.returnPressed.connect(self.accept)

        self.Buttons = HBox(GUI)
        self.Save = Button(self.Buttons, 'Save', self.accept)
        self.Cancel = Button(self.Buttons, 'Cancel', self.reject )

        self.Save.setProperty('bg','green')
        self.Save.updateStyle()
        self.Cancel.setProperty('bg','red')
        self.Cancel.updateStyle()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.ListName)
        self.layout.addWidget(self.Buttons)
        self.setLayout(self.layout)
        
        with open('./assets/style.qss') as f:
            self.setStyleSheet(f.read())

        self.exec()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.reject()
        elif e.key() == Qt.Key.Key_Enter:
            self.accept()

    def onTextChanged(self, text):
        self.Save.setDisabled(not text)

    def accept(self):
        name = self.ListName.text()
        if not name:
            return
        
        if self.GUI.Manager.Catalogs.Lists.has(name):
            if not OverwriteMessage(self.GUI, name).exec():
                return

        data = listToDict(self.List)

        path = 'data/lists/{0}.json'.format(name)
        with open(path, 'w') as f:
            f.write(json.dumps(data, indent=4))

        self.GUI.Manager.addList(name, data)
        self.log.emit('Saved List to ' + path)
        super().accept()

class OverwriteMessage(Dialog):
    Title = "Overwrite"

    def init(self, GUI, name):
        self.Message = QLabel(name + " Already Exists. Proceed?")

        self.Buttons = HBox(GUI)
        self.Overwrite = Button(self.Buttons, 'Overwrite', self.accept )
        self.Cancel = Button(self.Buttons, 'Cancel', self.reject )

        self.Overwrite.setProperty('bg','green')
        self.Overwrite.updateStyle()
        self.Cancel.setProperty('bg','red')
        self.Cancel.updateStyle()

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.Message)
        self.layout.addWidget(self.Buttons)
        self.setLayout(self.layout)
        
        with open('./assets/style.qss') as f:
            self.setStyleSheet(f.read())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape or e.key() == Qt.Key.Key_N:
            self.reject()
        elif e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Y:
            self.accept()

class TagGUI(HBox):
    def __init__(self, parent, name):
        super().__init__(parent.GUI)
        self.setObjectName('Tag')
        self.Name = name
        self.setProperty('which',name)
        self.Label = self.label(name)
        self.Label.setAlignment(Qt.AlignCenter)

        self.addTo(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Manager.Catalogs.Tags.get(self.Name).GUI.handleClick()
