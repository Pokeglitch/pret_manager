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
    def __init__(self, parent, name, initialValue, handler=None):
        super().__init__(parent.GUI)
        self.Name = name
        self.Label = self.label(name)
        self.Toggle = ProcessToggle(self, initialValue, handler)

        self.addTo(parent)

    def value(self):
        return self.Toggle.Slider.value()

class ProcessTitle(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Label = self.label("Process")
        self.Label.setAlignment(Qt.AlignCenter)
        self.addTo(parent)

class ProcessOptions(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        
        # todo - pull from settings
        self.doFetch = False
        self.doUpdate = True
        self.doCleanBefore = True
        self.doBuild = True
        self.doCleanAfter = True 

        self.Title = ProcessTitle(self)

        # todo - get default values from settings
        self.Fetch = ProcessToggleField(self, 'Fetch', False)
        self.Update = ProcessToggleField(self, 'Update', True)
        self.CleanBefore = ProcessToggleField(self, 'Clean', True)
        self.Build = ProcessToggleField(self, 'Build', True)
        self.CleanAfter = ProcessToggleField(self, 'Clean', True)

        self.addTo(parent, 1)

    def compile(self):
        processes = ''
        if self.Fetch.value():
            processes += 'f'
        
        if self.Update.value():
            processes += 'u'

        if self.CleanBefore.value():
            processes += 'c'

        if self.Build.value():
            processes += 'b'

        if self.CleanAfter.value():
            processes += 'c'

        return processes

    def toggleUpdate(self, value):
        self.doUpdate = value

    def toggleFetch(self, value):
        self.doFetch = value

    def toggleBuild(self, value):
        self.doBuild = value

    def toggleCleanBefore(self, value):
        self.doCleanBefore = value

    def toggleCleanAfter(self, value):
        self.doCleanAfter = value

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