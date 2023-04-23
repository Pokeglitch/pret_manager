from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QObject, QUrl, QThreadPool, QRunnable, QMargins, QPoint, QRect, QSize
from PyQt5.QtWidgets import QAction, QMenu, QSlider, QStackedWidget, QLineEdit, QSplashScreen, QComboBox, QHeaderView, QTreeWidgetItem, QFileDialog, QTreeWidget, QApplication, QStyleOption, QStyle, QLabel, QMainWindow, QLayout, QSizePolicy, QVBoxLayout, QGridLayout, QHBoxLayout, QScrollArea, QWidget
from PyQt5.QtGui import QPixmap, QDesktopServices, QIcon, QPainter
import time

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

class Button(QLabel):
    def __init__(self, parent, text, click):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.mousePressEvent = click
        parent.add(self)

    def updateStyle(self):
        self.style().polish(self)

    def setDisabled(self, isDisabled):
        self.setProperty('disabled', isDisabled)
        self.updateStyle()

    def setProcessing(self, isProcessing):
        self.setProperty('processing', isProcessing)
        self.updateStyle()

class ToggleButton(HBox):
    def __init__(self, parent, text, click):
        super().__init__(None)
        self.Label = self.label(text)
        self.Label.setAlignment(Qt.AlignCenter)
        self.mousePressEvent = click
        parent.add(self)

    def setActive(self, value):
        self.setProperty("active",value)
        self.updateStyle()

class Faded(QPixmap):
    def __init__(self, pixmap):
        super().__init__(pixmap.size())
        self.fill(Qt.transparent)
        painter = QPainter(self)
        painter.setOpacity(0.4)
        painter.drawPixmap(QPoint(), pixmap)
        painter.end()

class Field(HBox):
    def __init__(self, parent, left, right):
        super().__init__(parent.GUI)
        self.Left = self.label(left+':')
        self.Right = self.label(right)
        self.addTo(parent)

class Icon(HBox):
    def __init__(self, parent, image, dim):
        super().__init__(parent.GUI)
        self.Label = self.label()
        self.Label.setAlignment(Qt.AlignCenter)
        self.Pixmap = QPixmap(image).scaled(dim, dim)
        self.Label.setPixmap(self.Pixmap)
        self.addTo(parent)

    def setActive(self, value):
        self.setProperty("active",value)
        self.updateStyle()

class ContextMenu(QMenu):
    def __init__(self, parent, event, isQueued=None, isFavorite=None, isExcluding=None):
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

        # todo - handle new list
        # qdialog to input name, confirmation if already exists
        self.addAction("New List")

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

        # todo - handle new list
        # qdialog to input name, confirmation if already exists
        self.addAction("New List")

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

class EraseList(Action):
    def __init__(self, parent):
        super().__init__(parent, 'Erase List', parent.erase)
