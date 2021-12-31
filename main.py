#from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QWidget,QGroupBox,QDialog,QVBoxLayout,QMessageBox
from PyQt5.QtCore import QIODevice,pyqtSignal
from PyQt5.QtCore import QTimer,QThread, QEvent, Qt, pyqtSlot
from PyQt5 import uic
from PyQt5.QtSerialPort import QSerialPort,QSerialPortInfo 
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QFont, QIcon, QCloseEvent, QActionEvent
import sys,itertools
import config 
from helper import res_path
import serial_ui
from dfu_ui import DFUModeUI
from base_ui import CommunicationHandler

# This GUIs version
version = "1.5.2"

# Minimal supported firmware version. 
# Major version of firmware must match firmware. Minor versions must be higher or equal
min_fw = "1.5.1"

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

class MainUi(QMainWindow,CommunicationHandler):
    serial = None
    mainClassUi = None
    timeouting = False
    connected = False
    notMinimizeAndClose = True
    
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
        msg.exec_()
        dfu.deleteLater()

    def openAbout(self):
        AboutDialog(self).exec_()

    def saveConfig(self):
        self.getValueAsync("sys","flashdump",config.saveDump)

    def loadConfig(self):
        dump = config.loadDump()
        if not dump:
            return
        for e in dump["flash"]:
            self.comms.sendValue(self,"sys","flashraw",e["val"],e["addr"],0)
        # Message
        msg = QMessageBox(QMessageBox.Information,"Restore flash dump","Uploaded flash dump.\nPlease reboot.")
        msg.exec_()


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
        #print("DEL",widget)
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
                
                if cl["id"] == 1:
                    self.mainClassUi = ffb_ui.FfbUI(main = self)
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
        #self.serialchooser.serialConnect()

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
        
        #minVerGui = [int(i) for i in minVerGuiStr.split(".")]
        fwver = [int(i) for i in self.fwverstr.split(".")]
        min_fw_t = [int(i) for i in min_fw.split(".")]
        guiVersion = [int(i) for i in version.split(".")]

        self.log("FW v" + self.fwverstr)
        fwoutdated = False
        guioutdated = False

        fwoutdated = min_fw_t[0] > fwver[0] or min_fw_t[1] > fwver[1] or min_fw_t[2] > fwver[2]
        guioutdated = min_fw_t[0] < fwver[0] or min_fw_t[1] < fwver[1]

        if guioutdated:
            msg = QMessageBox(QMessageBox.Information,"Incompatible GUI","The GUI you are using ("+ version +") may be too old for this firmware.\nPlease make sure both firmware and GUI are up to date if you encounter errors.")
            msg.exec_()
        elif fwoutdated:
            msg = QMessageBox(QMessageBox.Information,"Incompatible firmware","The firmware you are using ("+ self.fwverstr +") is too old for this GUI.\n("+min_fw+" required)\nPlease make sure both firmware and GUI are up to date if you encounter errors.")
            msg.exec_()


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

    #override the changeEffect to detect if the windows is minimized. we ask close event on it
    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                self.showNormal()
                self.notMinimizeAndClose = False
                self.close()
                event.ignore()

    #if minimize before close, we just hide, else quit
    def closeEvent(self, a0: QCloseEvent) -> None:
        if self.notMinimizeAndClose:
            a0.ignore()
            app.quit()
        else:
            self.notMinimizeAndClose = True
            a0.ignore()
            self.hide()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        uic.loadUi(res_path('about.ui'), self)
        verstr = "Version: " + version
        if parent.fwverstr:
            verstr += " / Firmware: " + parent.fwverstr

        self.version.setText(verstr)

def onTrayIconActivated(reason):
    if reason == QSystemTrayIcon.DoubleClick:
        mainapp.show()
            
if __name__ == '__main__':
    #appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext

    app = QApplication(sys.argv)

    window = MainUi()
    window.setWindowTitle("Open FFBoard Configurator")
    window.show()
    global mainapp
    mainapp = window
  
    # Adding an icon
    icon = QIcon("app.png")

    # Adding item on the menu bar
    tray = QSystemTrayIcon()
    tray.setIcon(icon)
    tray.setVisible(True)
    tray.activated.connect(onTrayIconActivated)
    tray.setToolTip("Open FFBoard Configurator")

    # Creating the options
    menu = QMenu()
    option1 = QAction("Open console")
    option1.triggered.connect(mainapp.show)
    menu.addAction(option1)

    menu.addSeparator()

    # To quit the app
    quit = QAction("Quit")
    quit.triggered.connect(app.quit)
    menu.addAction(quit)

    # Adding options to the System Tray
    tray.setContextMenu(menu)

    #exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    #sys.exit(exit_code)
    sys.exit(app.exec_())