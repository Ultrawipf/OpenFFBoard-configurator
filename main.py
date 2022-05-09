from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QWidget,QGroupBox,QDialog,QVBoxLayout,QMessageBox,QStyleFactory
from PyQt6.QtCore import QIODevice,pyqtSignal
from PyQt6.QtCore import QTimer,QThread
from PyQt6.QtGui import QPalette, QColor, QIcon
from PyQt6 import uic
from PyQt6.QtSerialPort import QSerialPort,QSerialPortInfo 
import sys,itertools
import config 
from helper import res_path
import serial_ui
from dfu_ui import DFUModeUI
from base_ui import CommunicationHandler
from dark_palette import PALETTE_DARK

# This GUIs version
version = "1.8.6"

# Minimal supported firmware version. 
# Major version of firmware must match firmware. Minor versions must be higher or equal
min_fw = "1.8.5"

# UIs
import system_ui
import ffb_ui
import axis_ui
import tmc4671_ui
import pwmdriver_ui
import serial_comms
import midi_ui
import errors
import activelist
import tmcdebug_ui
import odrive_ui
import vesc_ui
import portconf_ui



class MainUi(QMainWindow,CommunicationHandler):
    serial = None
    mainClassUi = None
    timeouting = False
    connected = False

    def __init__(self):
        QMainWindow.__init__(self)
        uic.loadUi(res_path('MainWindow.ui'), self)
        
        #self.serialThread = QThread()
        global serialport
        self.serial = QSerialPort()
        serialport = self.serial
        CommunicationHandler.comms = serial_comms.SerialComms(self,self.serial)
        #self.serial.moveToThread(self.serialThread)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)
        self.tabWidget_main.currentChanged.connect(self.tabChanged)
        self.errorsDialog = errors.ErrorsDialog(self)
        self.activeClassDialog = activelist.ActiveClassDialog(self)
        self.setup()
        self.activeClasses = {}
        self.fwverstr = None
        
        
    def setup(self):
        self.serialchooser = serial_ui.SerialChooser(serial=self.serial,main = self)
        self.tabWidget_main.addTab(self.serialchooser,"Serial")
        
        #self.serial.readyRead.connect(self.serialReceive)
        self.serialchooser.getPorts()
        self.actionAbout.triggered.connect(self.openAbout)
        self.serialchooser.connected.connect(self.serialConnected)
        self.timer.start(5000)
        self.systemUi = system_ui.SystemUI(main = self)
        self.serialchooser.connected.connect(self.systemUi.setEnabled)

        self.serialchooser.connected.connect(self.errorsDialog.setEnabled)
        self.errorsDialog.setEnabled(False)

        # Toolbar menu items
        self.actionDFU_Uploader.triggered.connect(self.dfuUploader)

        self.actionErrors.triggered.connect(self.errorsDialog.show) # Open error list
        self.serialchooser.connected.connect(self.actionErrors.setEnabled)

        self.actionActive_features.triggered.connect(self.activeClassDialog.show) # Open active classes list
        self.serialchooser.connected.connect(self.actionActive_features.setEnabled)

        self.actionRestore_chip_config.triggered.connect(self.loadConfig)
        self.serialchooser.connected.connect(self.actionRestore_chip_config.setEnabled)

        self.actionSave_chip_config.triggered.connect(self.saveConfig)
        self.serialchooser.connected.connect(self.actionSave_chip_config.setEnabled)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.systemUi)
        self.groupBox_main.setLayout(layout)


    def dfuUploader(self):
        msg = QDialog()
        msg.setWindowTitle("DFU Mode")
        dfu = DFUModeUI(msg)
        l = QVBoxLayout()
        l.addWidget(dfu)
        msg.setLayout(l)
        msg.exec()
        dfu.deleteLater()

    def openAbout(self):
        AboutDialog(self).exec()

    def saveConfig(self):
        self.getValueAsync("sys","flashdump",config.saveDump)

    def loadConfig(self):
        dump = config.loadDump()
        if not dump:
            return
        for e in dump["flash"]:
            self.comms.sendValue(self,"sys","flashraw",e["val"],e["addr"],0)
        # Message
        msg = QMessageBox(QMessageBox.Icon.Information,"Restore flash dump","Uploaded flash dump.\nPlease reboot.")
        msg.exec()


    def timeoutCheckCB(self,i):
        #print("Timeoutcheck",i)
        if i != self.serialchooser.mainID:
            self.resetPort()       
            self.log("Communication error. Please reconnect")
        else:
            self.timeouting = False

    def updateTimer(self):
        if(self.serial.isOpen()):
            if self.timeouting:
                self.timeouting = False
                self.resetPort()
                self.log("Timeout. Please reconnect")
                return
            else:
                self.timeouting = True
                #print("Timeouting")
                self.getValueAsync("main","id",self.timeoutCheckCB,conversion=int)
                self.getValueAsync("sys","heapfree",self.systemUi.updateRamUse)
                
            

    def log(self,s):
        self.systemUi.logBox_1.append(s)

    def tabChanged(self,id):
        pass

    def addTab(self,widget,name):
        #print("Newtab!!",name)
        return self.tabWidget_main.addTab(widget,name)

    def delTab(self,widget):
        self.tabWidget_main.removeTab(self.tabWidget_main.indexOf(widget))
        CommunicationHandler.removeCallbacks(widget)
        del widget
        

    def selectTab(self,idx):
        self.tabWidget_main.setCurrentIndex(idx)

    def hasTab(self,name) -> bool:
        names = [self.tabWidget_main.tabText(i) for i in range(self.tabWidget_main.count())]
        return(name in names)

    def resetTabs(self):
        self.activeClasses = {}
        self.systemUi.setSaveBtn(False)
        for i in range(self.tabWidget_main.count()-1,0,-1):
            self.delTab(self.tabWidget_main.widget(i))
        self.comms.removeAllCallbacks()
    
    def updateTabs(self):
        def updateTabs_cb(active):
            #print(f"tabs:{active}")
            lines = [l.split(":") for l in active.split("\n") if l]
            newActiveClasses = {i[1]+":"+i[2]:{"name":i[0],"clsname":i[1],"id":int(i[3]),"unique":int(i[2]),"ui":None,"cmdaddr":[4]} for i in lines}
            deleteClasses = [(c,name) for name,c in self.activeClasses.items() if name not in newActiveClasses]
            #print(newActiveClasses)
            
            for c,name in deleteClasses:
                self.delTab(c)
                del self.activeClasses[name]
            for name,cl in newActiveClasses.items():
                if name in self.activeClasses:
                    continue
                classname = cl["name"]
                if cl["id"] == 1 or cl["id"] == 2:
                    self.mainClassUi = ffb_ui.FfbUI(main = self,title=classname)
                    self.activeClasses[name] = self.mainClassUi
                    self.systemUi.setSaveBtn(True)
                elif  cl["id"] == 0xA01:
                    c = axis_ui.AxisUI(main = self,unique = cl["unique"])
                    n = cl["name"]+':'+chr(c.axis+ord('0'))
                    self.activeClasses[name] = c
                    self.addTab(c,n)
                    self.systemUi.setSaveBtn(True)
                elif cl["id"] == 0x81 or cl["id"] == 0x82 or cl["id"] == 0x83:
                    c = tmc4671_ui.TMC4671Ui(main = self,unique = cl["unique"])
                    n = cl["name"]+':'+chr(c.axis+ord('0'))
                    self.activeClasses[name] = c
                    self.addTab(c,n)
                    self.systemUi.setSaveBtn(True)
                elif cl["id"] == 0x84:
                    c = pwmdriver_ui.PwmDriverUI(main = self)
                    self.activeClasses[name] = c
                    self.addTab(c,cl["name"])
                    self.systemUi.setSaveBtn(True)
                elif cl["id"] == 0xD:
                    c = midi_ui.MidiUI(main = self)
                    self.activeClasses[name] = c
                    self.addTab(c,cl["name"])
                elif cl["id"] == 0xB:
                    c = tmcdebug_ui.TMCDebugUI(main = self)
                    self.activeClasses[name] = c
                    self.addTab(c,cl["name"])
                elif cl["id"] == 0x85 or cl["id"] == 0x86:
                    c = odrive_ui.OdriveUI(main = self,unique = cl["unique"])
                    n = cl["name"]
                    self.activeClasses[name] = c
                    self.addTab(c,n)
                    self.systemUi.setSaveBtn(True)
                elif cl["id"] == 0x87 or cl["id"] == 0x88:
                    c = vesc_ui.VescUI(main = self,unique = cl["unique"])
                    n = cl["name"]
                    self.activeClasses[name] = c
                    self.addTab(c,n)
                    self.systemUi.setSaveBtn(True)

                    
        self.getValueAsync("sys","lsactive",updateTabs_cb,delete=True)
        self.getValueAsync("sys","heapfree",self.systemUi.updateRamUse,delete=True)

    def reconnect(self):
        self.resetPort()
        QTimer.singleShot(1000,self.serialchooser.serialConnect)

    def resetPort(self):
        self.log("Reset port")
        
        self.systemUi.setEnabled(False)
        self.serial.waitForBytesWritten(500)
        self.serial.close()
        self.comms.reset()
        self.timeouting = False
        self.serialchooser.getPorts()
        self.resetTabs()
        

    def versionCheck(self,ver):
        self.fwverstr = ver.replace("\n","")
        if not self.fwverstr:
            self.log("Communication error")
            self.resetPort()
        
        fwver = [int(i) for i in self.fwverstr.split(".")]
        min_fw_t = [int(i) for i in min_fw.split(".")]
        guiVersion = [int(i) for i in version.split(".")]

        self.log("FW v" + self.fwverstr)
        fwoutdated = False
        guioutdated = False

        fwoutdated = min_fw_t[0] > fwver[0] or min_fw_t[1] > fwver[1] or min_fw_t[2] > fwver[2]
        guioutdated = min_fw_t[0] < fwver[0] or min_fw_t[1] < fwver[1]

        if guioutdated:
            msg = QMessageBox(QMessageBox.Icon.Information,"Incompatible GUI","The GUI you are using ("+ version +") may be too old for this firmware.\nPlease make sure both firmware and GUI are up to date if you encounter errors.")
            msg.exec()
        elif fwoutdated:
            msg = QMessageBox(QMessageBox.Icon.Information,"Incompatible firmware","The firmware you are using ("+ self.fwverstr +") is too old for this GUI.\n("+min_fw+" required)\nPlease make sure both firmware and GUI are up to date if you encounter errors.")
            msg.exec()


    def serialConnected(self,connected):
        self.serialTim = QTimer()
        def t():
            if not self.connected:
                self.log("Can't detect board")
                self.resetPort()

        def f(id):
            if(id):
                self.connected = True
                self.serialTim.stop()
                  
        if(connected):
            self.serialTim.singleShot(500,t)
            self.getValueAsync("main","id",f,0)
            #self.comms.serialGetAsync("id?",f)  
            self.errorsDialog.registerCallbacks()

        else:
            self.connected = False
            self.log("Disconnected")
            self.resetTabs()
 
        self.getValueAsync("sys","swver",self.versionCheck)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        uic.loadUi(res_path('about.ui'), self)
        verstr = "Version: " + version
        if parent.fwverstr:
            verstr += " / Firmware: " + parent.fwverstr

        self.version.setText(verstr)

def windowsThemeIsLight(): # detect if the user is using Dark Mode in Windows
    # Registry will return 0 if Windows is in Dark Mode and 1 if Windows is in Light Mode. This dictionary converts that output into the text that the program is expecting.
    # 0 = Dark, 1 = Light
    # In HKEY_CURRENT_USER, get the Personalisation Key.
    try:
        key = getKey(hkey, "Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize")
        # In the Personalisation Key, get the AppsUseLightTheme subkey. This returns a tuple.
        # The first item in the tuple is the result we want (0 or 1 indicating Dark Mode or Light Mode); the other value is the type of subkey e.g. DWORD, QWORD, String, etc.
        subkey = getSubkeyValue(key, "AppsUseLightTheme")[0]
    except FileNotFoundError:
        # some headless Windows instances (e.g. GitHub Actions or Docker images) do not have this key
        return None
    return subkey

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    window = MainUi()
    if (sys.platform == 'win32' or "Windows" in sys.platform):  #only on windows, for macOS and linux use system palette. windows server is not called win32
        from winreg import HKEY_CURRENT_USER as hkey, QueryValueEx as getSubkeyValue, OpenKey as getKey
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'openFFB.configurator') # set the app id, so the taskbar using correct icon
        if (windowsThemeIsLight() == 0): # system is in dark mode
            app.setStyle("Fusion")
            app.setPalette(PALETTE_DARK)
    window.setWindowTitle("Open FFBoard Configurator")
    window.setWindowIcon(QIcon('res/app.ico'))
    window.show()
    global mainapp
    mainapp = window

    sys.exit(app.exec())
