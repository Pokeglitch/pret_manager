from PyQt5.QtCore import Qt, QCoreApplication, QProcess, QPoint, pyqtSignal, QObject, QUrl, QThreadPool, QRunnable, QMargins, QPoint, QRect, QSize
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QDialog, QAction, QMenu, QSlider, QStackedWidget, QLineEdit, QSplashScreen, QComboBox, QHeaderView, QTreeWidgetItem, QFileDialog, QTreeWidget, QApplication, QStyleOption, QStyle, QLabel, QMainWindow, QLayout, QSizePolicy, QVBoxLayout, QGridLayout, QHBoxLayout, QScrollArea, QWidget
from PyQt5.QtGui import QBrush, QColor, QImage, QPixmap, QDesktopServices, QIcon, QPainter
import time, json, copy, os

from src.Files import *

threadpool = QThreadPool()

def listToDict(list):
    data = {}
    for game in list:
        if game.author in data:
            data[game.author].append(game.title)
        else:
            data[game.author] = [game.title]
    return data

# https://doc.qt.io/qtforpython/examples/example_widgets_layouts_flowlayout.html
class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

class Widget(QWidget):
    def __init__(self, GUI, layout):
        super().__init__()
        self.Parent = None
        self.GUI = GUI
        self.Layout = layout()
        self.setLayout(self.Layout)
        
        self.Layout.setContentsMargins(0,0,0,0)
        self.Layout.setSpacing(0)

    def paintEvent(self, event):
        opt= QStyleOption()
        painter = QPainter(self)
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)
        painter.end()

    def updateStyle(self):
        self.style().polish(self)

    def add(self, widget, *args):
        self.Layout.addWidget(widget, *args)

    def addTo(self, parent, *args):
        self.Parent = parent
        if parent:
            parent.add(self, *args)
        else:
            self.setParent(None)

    def label(self, text='', *args):
        label = QLabel(text)
        self.add(label, *args)
        return label

    def addStretch(self):
        self.Layout.addStretch()

class Grid(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, QGridLayout)

class Flow(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, FlowLayout)
        
        self.Scroll = QScrollArea()
        self.Scroll.setWidgetResizable(True)
        self.Scroll.setWidget(self)

    def addTo(self, parent, *args):
        self.Parent = parent
        if parent:
            parent.add(self.Scroll, *args)
        else:
            self.setParent(None)

class HBox(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, QHBoxLayout)

class VBox(Widget):
    def __init__(self, GUI):
        super().__init__(GUI, QVBoxLayout)

class VScroll(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        
        self.Scroll = QScrollArea()
        self.Scroll.setWidgetResizable(True)
        self.Scroll.setWidget(self)

    def addTo(self, parent, *args):
        self.Parent = parent
        if parent:
            parent.add(self.Scroll, *args)
        else:
            self.setParent(None)

class Emitter(QObject):
    def on(self, key, handler):
        if hasattr(self, key + 'Signal'):
            getattr(self, key + 'Signal').connect(handler)
            if hasattr(self, key):
                handler( getattr(self, key) )
            else:
                handler()

    def off(self, key, handler):
        if hasattr(self, key + 'Signal'):
            getattr(self, key + 'Signal').disconnect(handler)

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
                data = json.loads(f.read())

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
class Button(QLabel):
    def __init__(self, parent, text, handler):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.handler = handler
        parent.add(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.handler()

    def updateStyle(self):
        self.style().polish(self)

    def setDisabled(self, isDisabled):
        self.setProperty('disabled', isDisabled)
        self.updateStyle()

    def setProcessing(self, isProcessing):
        self.setProperty('processing', isProcessing)
        self.updateStyle()

class Scaled(QPixmap):
    def __init__(self, path, dim):
        super().__init__(dim, dim)
        self.fill(Qt.transparent)
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, QPainter.SmoothPixmapTransform)
        painter.drawImage(self.rect(), QImage(path))
        painter.end()

class Faded(QPixmap):
    def __init__(self, pixmap):
        super().__init__(pixmap.size())
        self.fill(Qt.transparent)
        painter = QPainter(self)
        painter.setOpacity(0.4)
        painter.drawPixmap(QPoint(), pixmap)
        painter.end()

class Field(HBox):
    def __init__(self, parent, left, right, right_name='', right_handler=None):
        super().__init__(parent.GUI)
        self.Left = self.label(left+':')
        self.Right = self.label(right)
        
        if right_name:
            self.Right.setObjectName(right_name)
            
        if right_handler:
            self.Right.mouseDoubleClickEvent = right_handler

        self.addTo(parent)

class Icon(HBox):
    def __init__(self, parent, image, dim):
        super().__init__(parent.GUI)
        self.Label = self.label()
        self.Label.setAlignment(Qt.AlignCenter)
        self.Pixmap = Scaled(image, dim)
        self.Label.setPixmap(self.Pixmap)
        self.addTo(parent)

    def setActive(self, value):
        self.setProperty("active",value)
        self.updateStyle()

class CenterH(HBox):
    def __init__(self, center):
        super().__init__(center.GUI)

        self.addStretch()
        self.add(center)
        self.addStretch()

class CenterV(VBox):
    def __init__(self, center):
        super().__init__(center.GUI)

        self.addStretch()
        self.add(center)
        self.addStretch()

class CenterVH(CenterV):
    def __init__(self, center):
        centerH = CenterH(center)
        super().__init__(centerH)

class CenterHV(CenterV):
    def __init__(self, center):
        centerV = CenterV(center)
        super().__init__(centerV)

class Label(QLabel):
    def __init__(self, gui, text=''):
        super().__init__(text)
        self.GUI = gui
        self.setAlignment(Qt.AlignCenter)

    def updateStyle(self):
        self.style().polish(self)

class ContextMenu(QMenu):
    def __init__(self, parent, event):
        super().__init__(parent)
        self.Coords = parent.mapToGlobal(event.pos())

    def start(self):
        self.exec_(self.Coords)

class Action(QAction):
    def __init__(self, parent, name, handler):
        super().__init__(name, parent)
        self.triggered.connect(handler)

class AddToQueue(Action):
    def __init__(self, parent):
        super().__init__(parent, "Add to Queue", parent.addToQueueHandler)

class RemoveFromQueue(Action):
    def __init__(self, parent):
        super().__init__(parent, "Remove From Queue", parent.removeFromQueueHandler)

class AddToFavorites(Action):
    def __init__(self, parent):
        super().__init__(parent, "Add To Favorites", parent.addToFavoritesHandler)

class RemoveFromFavorites(Action):
    def __init__(self, parent):
        super().__init__(parent, "Remove From Favorites", parent.removeFromFavoritesHandler)

class AddToExcluding(Action):
    def __init__(self, parent):
        super().__init__(parent, "Add To Excluding", parent.addToExcludingHandler)

class RemoveFromExcluding(Action):
    def __init__(self, parent):
        super().__init__(parent, "Remove From Excluding", parent.removeFromExcludingHandler)

class AddGameToListMenu(QMenu):
    def __init__(self, parent ,lists):
        super().__init__("Add To List", parent)

        for list in lists:
            self.addAction( AddGameToList(parent, list))

        self.addAction(parent.GameGUI.NewList)

class RemoveGameFromListMenu(QMenu):
    def __init__(self, parent ,lists):
        super().__init__("Remove From List", parent)

        for list in lists:
            self.addAction( RemoveGameFromList(parent, list))

class AddGameToList(Action):
    def __init__(self, parent, list):
        super().__init__(parent, list.Name, lambda: list.addGames([parent.GameGUI.Game]) )

class RemoveGameFromList(Action):
    def __init__(self, parent, list):
        super().__init__(parent, list.Name, lambda: list.removeGames([parent.GameGUI.Game]) )

class AddListToListMenu(QMenu):
    def __init__(self, parent ,lists):
        super().__init__("Add To List", parent)

        for list in lists:
            self.addAction( AddListToList(parent, list))

        self.addAction(parent.NewList)

class RemoveListFromListMenu(QMenu):
    def __init__(self, parent ,lists):
        super().__init__("Remove From List", parent)

        for list in lists:
            self.addAction( RemoveListFromList(parent, list))

class AddListToList(Action):
    def __init__(self, parent, list):
        super().__init__(parent, list.Name, lambda: list.addGames(parent.getData()) )

class RemoveListFromList(Action):
    def __init__(self, parent, list):
        super().__init__(parent, list.Name, lambda: list.removeGames(parent.getData()) )

class NewList(Action):
    def __init__(self, parent):
        super().__init__(parent, 'New List', parent.saveList )

class EraseList(Action):
    def __init__(self, parent):
        super().__init__(parent, 'Erase List', parent.erase)

class ClearBrowser(Action):
    def __init__(self, parent):
        super().__init__(parent, 'Clear Filter', parent.erase)

class ClearQueue(Action):
    def __init__(self, parent):
        super().__init__(parent, 'Clear Queue', parent.erase)

class ProcessAction(Action):
    def __init__(self, parent):
        super().__init__(parent, 'Process', parent.process)
        
class MenuIcon(Icon):
    def __init__(self, parent):
        super().__init__(parent, 'assets/images/menu.png', 36)

class SaveListDialog(QDialog):
    log = pyqtSignal(str)

    def __init__(self, GUI, list):
        super().__init__(None, Qt.WindowCloseButtonHint)

        self.List = list
        self.setWindowTitle('Save List')
        self.setWindowIcon(QIcon('assets/images/icon.png'))

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

class OverwriteMessage(QDialog):
    def __init__(self, GUI, name):
        super().__init__(None, Qt.WindowCloseButtonHint)
        self.setWindowTitle("Overwrite")
        self.setWindowIcon(QIcon('assets/images/icon.png'))

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
        
        # TODO
        #self.Label.setStyleSheet("background-color: #" + hex(abs(hash(name)))[2:8])

        self.addTo(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.GUI.Manager.Catalogs.Tags.get(self.Name).GUI.handleClick()

class ToggleSlider(QSlider):
    def __init__(self, parent):
        super().__init__(Qt.Horizontal)
        self.setMinimum(0)
        self.setMaximum(1)
        self.valueChanged.connect(parent.setActive)

        parent.add(self, 1, 1)

    def setActive(self, value):
        self.setProperty("active", value)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setValue(1 - self.sliderPosition())

class ToggleBG(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.addTo(parent, 1, 1)

    def setActive(self, value):
        self.setProperty("active", value)
        self.updateStyle()

class Toggle(Grid):
    def __init__(self, parent, initialValue, handler=None):
        super().__init__(parent.GUI)

        self.Handler = None
        self.BG = ToggleBG(self)
        self.Slider = ToggleSlider(self)
        self.Slider.setValue(int(initialValue))
        self.Handler = handler

        self.addTo(parent)

    def setActive(self, value):
        value = bool(value)

        self.BG.setActive(value)
        self.Slider.setActive(value)

        if self.Handler:
            self.Handler(value)

class ToggleField(HBox):
    def __init__(self, parent, name, initialValue, handler=None):
        super().__init__(parent.GUI)
        self.Name = name
        self.Label = self.label(name)
        self.Toggle = Toggle(self, initialValue, handler)

        self.addTo(parent)

    def set(self, value):
        self.Toggle.Slider.setValue( int(value) )

    def value(self):
        return self.Toggle.Slider.value()
