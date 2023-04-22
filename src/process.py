from src.base import *

class ProcessToggleSlider(QSlider):
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
        self.setValue(1 - self.sliderPosition())

class ProcessToggleBG(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.addTo(parent, 1, 1)

    def setActive(self, value):
        self.setProperty("active", value)
        self.updateStyle()

class ProcessToggle(Grid):
    def __init__(self, parent, initialValue, handler=None):
        super().__init__(parent.GUI)

        self.Handler = None
        self.BG = ProcessToggleBG(self)
        self.Slider = ProcessToggleSlider(self)
        self.Slider.setValue(int(initialValue))
        self.Handler = handler

        self.addTo(parent)

    def setActive(self, value):
        value = bool(value)

        self.BG.setActive(value)
        self.Slider.setActive(value)

        if self.Handler:
            self.Handler(value)

class ProcessToggleField(HBox):
    def __init__(self, parent, name, initialValue, handler):
        super().__init__(parent.GUI)
        self.Name = name
        self.Label = self.label(name)
        self.Toggle = ProcessToggle(self, initialValue, handler)

        self.addTo(parent)

class ProcessTitle(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Label = self.label("Process")
        self.Label.setAlignment(Qt.AlignCenter)
        self.addTo(parent)

class ProcessOptions(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        
        self.Title = ProcessTitle(self)
        self.ToggleUpdate = ProcessToggleField(self, 'Fetch', self.GUI.Manager.doFetch, self.toggleFetch)
        self.ToggleUpdate = ProcessToggleField(self, 'Update', self.GUI.Manager.doUpdate, self.toggleUpdate)
        self.ToggleClean = ProcessToggleField(self, 'Clean', self.GUI.Manager.doClean, self.toggleClean)
        self.ToggleBuild = ProcessToggleField(self, 'Build', self.GUI.Manager.doBuild != None, self.toggleBuild)
        self.ToggleClean = ProcessToggleField(self, 'Clean', self.GUI.Manager.doClean, self.toggleClean)

        self.addTo(parent, 1)

    def toggleUpdate(self, value):
        self.GUI.Manager.doUpdate = value

    def toggleFetch(self, value):
        self.GUI.Manager.doFetch = value

    def toggleBuild(self, value):
        self.GUI.Manager.doBuild = [] if value else None

    def toggleClean(self, value):
        self.GUI.Manager.doClean = value

class ProcessStatusContent(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        
        self.Label = self.label()
        self.addStretch()

        self.addTo(parent)

    def addStatusMessage(self, msg):
        prev_text = self.Label.text() + '\n' if self.Label.text() else ''
        self.Label.setText(prev_text + msg)

class ProcessStatusList(VScroll):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.AtMax = True
        
        self.Scroll.verticalScrollBar().rangeChanged.connect(self.checkUpdatePosition)
        self.Scroll.verticalScrollBar().valueChanged.connect(self.checkAtMax)

        self.setObjectName("status")
        
        self.Content = ProcessStatusContent(self)

        self.addTo(parent, 3)

    def checkAtMax(self, event):
        self.AtMax = self.Scroll.verticalScrollBar().value() == self.Scroll.verticalScrollBar().maximum()

    def checkUpdatePosition(self, event):
        if self.AtMax:
            self.Scroll.verticalScrollBar().setValue(self.Scroll.verticalScrollBar().maximum())

    def addStatusMessage(self, msg):
        self.Content.addStatusMessage(msg)

class Process(HBox):
    def __init__(self, GUI):
        super().__init__(GUI)

        self.Options = ProcessOptions(self)
        self.Body = ProcessStatusList(self)
        self.addTo(GUI.Col2, 1)