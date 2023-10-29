from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QLabel
from PyQt5.QtGui import QColor, QImage, QPixmap, QPainter

from src.qt.layouts import HBox

class Pixmap(QPixmap):
    Painter: QPainter

    def __init__(self, size, *args):
        size_type = type(size)
        if size_type == int:
            super().__init__(size, size)
        elif size_type == list:
            super().__init__(*size)
        else:
            super().__init__(size)
        
        self.fill(Qt.transparent)

        self.init(*args)

    def init(self, *args):
        painter = QPainter(self)
        self.paint(painter, *args)
        painter.end()

    def paint(self, painter, *args):
        pass

class Scaled(Pixmap):
    def paint(self, painter, path):
        painter.setRenderHints(QPainter.Antialiasing, QPainter.SmoothPixmapTransform)
        painter.drawImage(self.rect(), QImage(path).scaled(self.size(), transformMode=Qt.SmoothTransformation))

class DerivedPixmap(Pixmap):
    Pixmap: Pixmap

    def __init__(self, pixmap):
        self.Pixmap = pixmap
        super().__init__(pixmap.size())

class Faded(DerivedPixmap):
    def paint(self, painter):
        painter.setOpacity(0.4)
        painter.drawPixmap(QPoint(), self.Pixmap)

class Darkened(DerivedPixmap):
    Faded: Faded

    def init(self):
        image = self.toImage()
        pixmapImage = self.Pixmap.toImage()

        for x in range(image.width()):
            for y in range(image.height()):
                color = pixmapImage.pixelColor(x, y)
                image.setPixelColor(x, y, color.darker())

        self.convertFromImage(image)
        self.Faded = Faded(self)

class Icon(HBox):
    Label: QLabel
    Pixmap: Scaled

    def __init__(self, parent, image, dim):
        super().__init__(parent.GUI)
        self.Label = self.label()
        self.Label.setAlignment(Qt.AlignCenter)
        self.Pixmap = Scaled(dim, image)
        self.Label.setPixmap(self.Pixmap)
        self.addTo(parent)

    def setActive(self, value):
        self.setProperty("active",value)
        self.updateStyle()

class OutlineShadow(QGraphicsDropShadowEffect):
    def __init__(self):
        super().__init__()
        self.setBlurRadius(1)
        self.setColor(QColor("#000000"))

    def draw(self, painter):
        self.setOffset(1, 0)
        super().draw(painter)
        self.setOffset(-1, 0)
        super().draw(painter)
        self.setOffset(0, 1)
        super().draw(painter)
        self.setOffset(0, -1)
        super().draw(painter)
