from src.base import *

class ProcessContextMenu(ContextMenu):
    def __init__(self, parent, event):
        super().__init__(parent, event)
        self.addAction( parent.GUI.Window.TerminateProcess )
        self.start()

class ProcessTitle(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Label = self.label("Process")
        self.Label.setAlignment(Qt.AlignCenter)

        self.GUI.Window.Processing.connect(self.setProcessing)
        self.addTo(parent)

    def setProcessing(self, value):
        self.setProperty("processing",value)
        self.updateStyle()

    def contextMenuEvent(self, event):
        if self.GUI.Window.Process:
            ProcessContextMenu(self, event)

class ProcessOptions(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)

        self.Title = ProcessTitle(self)

        settings = self.GUI.Manager.Settings.Active["Process"]

        self.Refresh = ToggleField(self, 'Refresh', settings["Refresh"])
        self.Update = ToggleField(self, 'Update', settings["Update"])
        self.CleanBefore = ToggleField(self, 'Clean', settings["CleanBefore"])
        self.Build = ToggleField(self, 'Build', settings["Build"])
        self.CleanAfter = ToggleField(self, 'Clean', settings["CleanAfter"])

        self.addTo(parent, 1)

    def setSettings(self):
        settings = self.GUI.Manager.Settings.Active["Process"]

        for key, value in settings.items():
            getattr(self, key).set(value)

    def getSettings(self):
        settings = {}

        for key in ["Refresh", "Update", "CleanBefore", "Build", "CleanAfter"]:
            settings[key] = bool(getattr(self, key).value())

        return settings

    def compile(self):
        processes = ''
        if self.Refresh.value():
            processes += 'r'
        
        if self.Update.value():
            processes += 'u'

        if self.CleanBefore.value():
            processes += 'c'

        if self.Build.value():
            processes += 'b'

        if self.CleanAfter.value():
            processes += 'c'

        return processes

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