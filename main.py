#from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QWidget,QGroupBox,QDialog,QVBoxLayout,QMessageBox
from PyQt5.QtCore import QIODevice,pyqtSignal
from PyQt5.QtCore import QTimer,QThread
from PyQt5 import uic
from PyQt5.QtSerialPort import QSerialPort,QSerialPortInfo 
import sys,itertools

from helper import res_path
import serial_ui
from dfu_ui import DFUModeUI

# This GUIs version
version = "1.2.2"
# Minimal supported firmware version. 
# Major version of firmware must match firmware. Minor versions must be higher or equal
min_fw = "1.2.3"

# UIs
import system_ui
import ffb_ui
import tmc4671_ui
import pwmdriver_ui
import serial_comms
import midi_ui


class MainUi(QMainWindow):
    serial = None
    mainClassUi = None
    timeouting = False
    
    def __init__(self):
        super(MainUi, self).__init__()
        uic.loadUi(res_path('MainWindow.ui'), self)
        #self.serialThread = QThread()
        self.serial = QSerialPort()
        #self.serial.moveToThread(self.serialThread)

        self.comms = serial_comms.SerialComms(self,self.serial)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)
        self.tabWidget_main.currentChanged.connect(self.tabChanged)

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
        self.serialchooser.connected.connect(self.systemUi.serialConnected)

        self.actionFFB_Wheel_TMC_wizard.triggered.connect(self.ffbwizard)
        self.actionDFU_Uploader.triggered.connect(self.dfuUploader)

        layout = QVBoxLayout()
        layout.addWidget(self.systemUi)
        self.groupBox_main.setLayout(layout)

    def ffbwizard(self):
        msg = QMessageBox(QMessageBox.Information,"Wizard","Not implemented")
        msg.exec_()

    def dfuUploader(self):
        msg = QDialog()#QMessageBox(QMessageBox.Information,"DFU","Switched to DFU mode.\nConnect with DFU programmer")
        msg.setWindowTitle("DFU Mode")
        dfu = DFUModeUI(msg)
        l = QVBoxLayout()
        l.addWidget(dfu)
        msg.setLayout(l)
        msg.exec_()
        dfu.deleteLater()

    def openAbout(self):
        AboutDialog(self).exec_()

    def updateTimer(self):
        def f(i):
            if i != self.systemUi.mainID:
                self.resetPort()       
                self.log("Communication error. Please reconnect")
            else:
                self.timeouting = False
        if(self.serial.isOpen()):
            if self.timeouting:
                self.timeouting = False
                self.resetPort()
                self.log("Timeout. Please reconnect")
                return
            else:
                self.timeouting = True
                self.comms.serialGetAsync("id?",f,int)
                
            

    def log(self,s):
        self.logBox.append(s)

    def tabChanged(self,id):
        pass

    def addTab(self,widget,name):
        return self.tabWidget_main.addTab(widget,name)

    def delTab(self,widget):
        self.tabWidget_main.removeTab(self.tabWidget_main.indexOf(widget))
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
    
    def updateTabs(self):
        def updateTabs_cb(active):
            lines = [l.split(":") for l in active.split("\n") if l]
            newActiveClasses = {i[0]:{"id":i[1],"ui":None} for i in lines}
            deleteClasses = [c for name,c in self.activeClasses.items() if name not in newActiveClasses]
            #print(newActiveClasses)
            for c in deleteClasses:
                self.delTab(c)
            for name,c in newActiveClasses.items():
                if name in self.activeClasses:
                    continue
                
                if name == "FFB Wheel":
                    self.mainClassUi = ffb_ui.FfbUI(main = self)
                    self.activeClasses[name] = self.mainClassUi
                    self.systemUi.setSaveBtn(True)
                if name == "TMC4671":
                    c = tmc4671_ui.TMC4671Ui(main = self)
                    self.activeClasses[name] = c
                    self.addTab(c,name)
                    self.systemUi.setSaveBtn(True)
                if name == "PWM":
                    c = pwmdriver_ui.PwmDriverUI(main = self)
                    self.activeClasses[name] = c
                    self.addTab(c,name)
                    self.systemUi.setSaveBtn(True)
                if name == "MIDI":
                    c = midi_ui.MidiUI(main = self)
                    self.activeClasses[name] = c
                    self.addTab(c,name)
                    
        self.comms.serialGetAsync("lsactive",updateTabs_cb)

    def reconnect(self):
        self.resetPort()
        QTimer.singleShot(4000,self.serialchooser.serialConnect)
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
            
        fwver = [int(i) for i in self.fwverstr.split(".")]
        min_fw_t = [int(i) for i in min_fw.split(".")]
        self.log("FW v" + self.fwverstr)
        fwoutdated = False
        guioutdated = fwver[0] > min_fw_t[0] or fwver[1] > min_fw_t[1]

        for v in itertools.zip_longest(min_fw_t,fwver,fillvalue=0):
            if(v[0] < v[1]): # Newer
                break
            # If same higher version then check minor version
            if(v[0] > v[1]):
                fwoutdated = True
                break
        if guioutdated:
            msg = QMessageBox(QMessageBox.Information,"Incompatible GUI","The GUI you are using ("+ version +") may be too old for this firmware.\nPlease make sure both firmware and GUI are up to date.")
            msg.exec_()
        elif fwoutdated:
            msg = QMessageBox(QMessageBox.Information,"Incompatible firmware","The firmware you are using ("+ self.fwverstr +") is too old for this GUI.\nPlease make sure both firmware and GUI are up to date.")
            msg.exec_()




    def serialConnected(self,connected):
        if(connected):
            if(self.comms.serialGet("id?;")):
                self.log("Connected")
                self.fwverstr = self.comms.serialGetAsync("swver",self.versionCheck)
            else:
                self.log("Can't detect board")
                self.resetPort()
        else:
            self.log("Disconnected")
            self.resetTabs()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        uic.loadUi(res_path('about.ui'), self)
        verstr = "Version: " + version
        if parent.fwverstr:
            verstr += " / Firmware: " + parent.fwverstr

        self.version.setText(verstr)
        
            

if __name__ == '__main__':
    #appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext

    app = QApplication(sys.argv)
    window = MainUi()
    window.setWindowTitle("Open FFBoard Configurator")
    window.show()
    #exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    #sys.exit(exit_code)
    sys.exit(app.exec_())