from src.gamebase import *

class PanelContextMenu(GameBaseContextMenu):
    def __init__(self, parent, event):
        super().__init__(parent, event)
        self.Coords = parent.Panel.Body.mapToGlobal(QPoint(0, 0))
        self.start()

class PanelHeaderMenuIcon(MenuIcon):
    def __init__(self, parent):
        super().__init__(parent)
        self.Panel = parent.Panel

    @property
    def GameGUI(self):
        return self.Panel.Active 

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.Panel.Active:
            PanelContextMenu(self, event)

class PanelHeaderMenu(HBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Panel = parent.Panel
        self.Menu = PanelHeaderMenuIcon(self)
        self.addTo(parent)

class PanelHeaderClose(QLabel):
    def __init__(self, parent):
        super().__init__()
        self.GUI = parent.GUI
        self.Panel = parent.Panel

        self.setAlignment(Qt.AlignCenter)
        self.Pixmap = Scaled('assets/images/close.png', 20)
        self.setPixmap(self.Pixmap)
        CenterV(self).addTo(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.Panel.Active:
            self.Panel.setActive(None)

class PanelHeader(HBox):
    def __init__(self, panel):
        super().__init__(panel.GUI)
        self.Panel = panel

        self.setObjectName("header-frame")

        self.Menu = PanelHeaderMenu(self)
        self.addStretch()
        
        self.Label = self.label()
        self.Label.setObjectName("header")
        self.Label.setAlignment(Qt.AlignCenter)

        self.addStretch()
        self.Close = PanelHeaderClose(self)
        
        self.addTo(panel)

    def setText(self, text):
        self.Label.setText(text)

# TODO - attach to Environment? simply disable if Linux
EnvironmentOptions = {
        'Windows' : 'main',
        'Default Linux' : 'linux',
        'WSL' : 'wsl',
        'Cygwin' : 'cygwin',
        'w64devkit' : 'w64devkit'
}

class EnvironmentsRow(HBox):
    def __init__(self, parent, key, skip=[]):
        super().__init__(parent.GUI)
        
        self.Label = self.label(key + ':')
        self.Label.setAlignment(Qt.AlignRight)
        self.ComboBox = EnvironmentComboBox(self, key, skip)

        CenterH(self).addTo(parent)

class EnvironmentComboBox(QComboBox):
    def __init__(self, parent, key, skip=[]):
        super().__init__()
        self.Key = 'Environment.' + key
        self.Settings = parent.GUI.Manager.Settings

        default = self.Settings.get(self.Key)
        for name, value in EnvironmentOptions.items():
            if name not in skip:
                self.addItem(name)
                if value == default:
                    self.setCurrentText(name)

        self.currentTextChanged.connect(self.onTextChanged)
        parent.GUI.Window.Processing.connect(self.handleProcessing)
        parent.add(self)

    def handleProcessing(self, processing):
        self.setEnabled(not processing)
        self.setProperty('processing', processing)
        self.style().polish(self)

    def onTextChanged(self, text):
        self.Settings.set(self.Key, EnvironmentOptions[text])

class PanelHeading(QLabel):
    def __init__(self, parent, text):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        parent.add(self)

class PanelButton(Button):
    def __init__(self, parent, text, handler):
        self.GUI = parent.GUI
        super().__init__(parent, text, handler)
        CenterH(self).addTo(parent)

class ProcessPanelButton(PanelButton):
    def __init__(self, parent, text, handler):
        super().__init__(parent, text, handler)
        self.GUI.Window.Processing.connect(self.setProcessing)

    def mousePressEvent(self, event):
        if not self.property('disabled') and not self.property('processing'):
            super().mousePressEvent(event)

class PanelOptionsWidget(VBox):
    def __init__(self, parent, name):
        super().__init__(parent.GUI)
        self.Panel = parent.Panel
        PanelHeading(self, name)
        self.addTo(parent)

class OptionToggleField(ToggleField):
    def __init__(self, parent, name, key):
        self.Key = key
        super().__init__(parent, name, getattr(parent.GUI.Manager, key), self.onToggle)

    def onToggle(self, value):
        setattr(self.GUI.Manager, self.Key, value)
        self.GUI.Manager.updateMetaData()

class PRETManagerOptions(PanelOptionsWidget):
    def __init__(self, parent):
        super().__init__(parent, 'pret manager')

        container = HBox(self.GUI)
        self.CheckForUpdate = ProcessPanelButton(container, 'Check for Update', self.GUI.refreshPRETManager)
        self.AutoCheckForUpdate = OptionToggleField(container, 'Auto:', 'AutoRefresh')
        CenterH(container).addTo(self)
        self.GUI.Window.InitializedSignal.connect(self.checkAutoRefresh)

        container = HBox(self.GUI)
        self.ApplyUpdate = ProcessPanelButton(container, 'Apply Updates', self.GUI.updatePRETManager)
        self.AutoApplyUpdate = OptionToggleField(container, 'Auto:', 'AutoUpdate')
        CenterH(container).addTo(self)
        self.GUI.Window.UpdateFoundSignal.connect(self.checkAutoApply)

        container = HBox(self.GUI)
        self.Restart = ProcessPanelButton(container, 'Restart', self.GUI.restartPRETManager)
        self.AutoRestart = OptionToggleField(container, 'Auto:', 'AutoRestart')
        CenterH(container).addTo(self)
        self.GUI.Window.UpdateAppliedSignal.connect(self.checkAutoRestart)
        
        self.GUI.Manager.on('Outdated', self.onOutdated)

    def onOutdated(self, outdated):
        self.CheckForUpdate.setDisabled(outdated)
        self.ApplyUpdate.setDisabled(not outdated)
        # TODO
        # show outdated symbol
        # show update applied symbol

    def checkAutoRefresh(self):
        if self.AutoCheckForUpdate.value():
            self.GUI.refreshPRETManager(True)

    def checkAutoApply(self):
        if self.AutoApplyUpdate.value():
            self.GUI.updatePRETManager(True)

    def checkAutoRestart(self):
        if self.AutoRestart.value():
            self.GUI.restartPRETManager(True)

class BrowserOptions(PanelOptionsWidget):
    def __init__(self, parent):
        super().__init__(parent, 'Browser')
        # TODO
        # Always Hide excluded games from Browser
        # Set Current Browser as Default Browser
            # - Restore Default Browser

class ProcessingOptions(PanelOptionsWidget):
    def __init__(self, parent):
        super().__init__(parent, 'Processing')

        # TODO:
        # Auto-refresh on start
        # Auto-update on start
        # Include Releases when 'Update'
        # Remove from Queue after Processed
        # Replace previous builds
        container = HBox(self.GUI)
        self.SaveDefaultProcesses = PanelButton(container, 'Save Current as Default', self.saveDefaultProcesses)
        self.RestoreDefaultProcesses = PanelButton(container, 'Restore Default', self.restoreDefaultProcesses)
        CenterH(container).addTo(self)

    def saveDefaultProcesses(self):
        processes = self.GUI.Process.Options.getSettings()
        self.GUI.Manager.Settings.set("Process", processes)

    def restoreDefaultProcesses(self):
        self.GUI.Process.Options.setSettings()

class EnvironmentsOptions(PanelOptionsWidget):
    def __init__(self, parent):
        super().__init__(parent, 'Environments')

        self.LinuxComboBox = EnvironmentsRow(self, 'linux',['Windows', 'Default Linux'])
        self.GitComboBox = EnvironmentsRow(self, 'git')
        self.GithubComboBox = EnvironmentsRow(self, 'gh')
        self.TarComboBox = EnvironmentsRow(self, 'tar')
        self.MakComboBox = EnvironmentsRow(self, 'make', ['Windows'])

        container = HBox(self.GUI)
        self.CygwinButton = PanelButton(container, 'Select Cygwin Path', self.selectCygwinPath)
        self.CygwinPath = container.label()
        container.addStretch()
        self.setCygwinPath()
        self.GUI.Manager.CygwinPathSignal.connect(self.updateCygwinPath)
        container.addTo(self)

        # TODO
        # Option to have Cygwin build instead of use prebuilt binaries

        container = HBox(self.GUI)
        self.w64devkitButton = PanelButton(container, 'Select w64devkit Path', self.selectw64devkitPath)
        self.w64devkitPath = container.label()
        container.addStretch()
        self.setw64devkitPath()
        self.GUI.Manager.w64devkitPathSignal.connect(self.updatew64devkitPath)
        container.addTo(self)

    def selectCygwinPath(self):
        path = self.GUI.Manager.Settings.get('Environment.cygwin')

        if path:
            dir = '/'.join(path.split('/')[:-1])
        else:
            dir = '.'

        path, _ = QFileDialog.getOpenFileName(self, "Select Cygwin Executable", dir)
        if path:
            self.GUI.Manager.Settings.set('Environment.cygwin', path)
            self.setCygwinPath()

    def setCygwinPath(self):
        path = str(self.GUI.Manager.Settings.get('Environment.cygwin'))
        self.updateCygwinPath(path)

    def updateCygwinPath(self, path):
        if len(path) > 30:
            path = path[:15] + '...' + path[-15:]
        self.CygwinPath.setText(path)

    def selectw64devkitPath(self):
        path = self.GUI.Manager.Settings.get('Environment.w64devkit')

        if path:
            dir = '/'.join(path.split('/')[:-1])
        else:
            dir = '.'

        path, _ = QFileDialog.getOpenFileName(self, "Select w64devkit Executable", dir)
        if path:
            self.GUI.Manager.Settings.set('Environment.w64devkit', path)
            self.setw64devkitPath()

    def setw64devkitPath(self):
        path = str(self.GUI.Manager.Settings.get('Environment.w64devkit'))
        self.updatew64devkitPath(path)

    def updatew64devkitPath(self, path):
        if len(path) > 30:
            path = path[:15] + '...' + path[-15:]
        self.w64devkitPath.setText(path)

class PanelOptions(VBox):
    def __init__(self, parent):
        super().__init__(parent.GUI)
        self.Panel = parent.Panel

        self.PRETManager = PRETManagerOptions(self)
        #self.Browser = BrowserOptions(self)
        self.Processing = ProcessingOptions(self)

        if parent.GUI.Manager.Environments.Main != 'linux':
            self.Environments = EnvironmentsOptions(self)

        self.addStretch()

class PanelBody(VScroll):
    def __init__(self, panel):
        super().__init__(panel.GUI)
        self.Panel = panel
        self.Options = PanelOptions(self)
        self.addTo(panel)

class Panel(VBox):
    def __init__(self, GUI):
        super().__init__(GUI)
        self.Header = PanelHeader(self)
        self.Body = PanelBody(self)
        
        self.Active = None
        self.setActive(None)
        self.addTo(GUI, 3)

    def setActive(self, game):
        if self.Active:
            self.Active.setActive(False)
            self.Active.Panel.addTo(None)

        self.Active = None if game == self.Active else game

        if self.Active:
            self.Active.setActive(True)
            self.Body.Options.addTo(None)
            self.Active.Panel.addTo(self.Body)
            self.Header.setText(self.Active.Game.FullTitle)
        else:
            self.Header.setText("Options")
            self.Body.Options.addTo(self.Body)

        self.Header.Close.setVisible(bool(self.Active))
        self.Header.Menu.setVisible(bool(self.Active))
