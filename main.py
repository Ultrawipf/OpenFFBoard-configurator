#from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QWidget,QGroupBox,QDialog,QVBoxLayout,QMessageBox
from PyQt5.QtCore import QIODevice,pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5 import uic
from PyQt5.QtSerialPort import QSerialPort,QSerialPortInfo 
import sys

from helper import res_path
import serial_ui
version = "0.1"

# UIs
import system_ui
import ffb_ui
import tmc4671_ui
import pwmdriver_ui


class MainUi(QMainWindow):
    serial = None
    curId = 0
    save = pyqtSignal()
    mainClassUi = None
    def __init__(self):
        super(MainUi, self).__init__()
        uic.loadUi(res_path('MainWindow.ui'), self)
        self.serial = QSerialPort(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)
        self.tabWidget_main.currentChanged.connect(self.tabChanged)

        self.setup()
        self.lastSerial = None
        self.activeClasses = {}
        
        
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
        self.systemUi.pushButton_save.clicked.connect(self.saveClicked)
        self.setSaveBtn(False)

        self.actionFFB_Wheel_TMC_wizard.triggered.connect(self.ffbwizard)

        layout = QVBoxLayout()
        layout.addWidget(self.systemUi)
        self.groupBox_main.setLayout(layout)

    def ffbwizard(self):
        msg = QMessageBox(QMessageBox.Information,"Wizard","Not implemented")
        msg.exec_()

    def openAbout(self):
        AboutDialog().exec_()

    def updateTimer(self):
        if(self.serial.isOpen()):
            if(not self.serialGet("id?\n",1000)):
                self.resetPort()
                self.log("Timeout. Please reconnect")
            

    def log(self,s):
        self.logBox.append(s)


    def setSaveBtn(self,enabled):
        self.systemUi.pushButton_save.setEnabled(enabled)

    def saveClicked(self):
        self.log("Save")
        self.save.emit()

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
        self.setSaveBtn(False)
        self.activeClasses = {}
        for i in range(self.tabWidget_main.count()-1,0,-1):
            self.delTab(self.tabWidget_main.widget(i))
    
    def updateTabs(self):
        lines = [l.split(":") for l in self.serialGet("lsactive\n").split("\n")]
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
            if name == "TMC4671":
                c = tmc4671_ui.TMC4671Ui(main = self)
                self.activeClasses[name] = c
                self.addTab(c,name)
            if name == "PWM":
                c = pwmdriver_ui.PwmDriverUI(main = self)
                self.activeClasses[name] = c
                self.addTab(c,name)

        #self.resetTabs()
        # if(id == 1):
        #     # FFB
        #     self.mainClassUi = ffb_ui.FfbUI(main = self)
        #     pass

    def reconnect(self):
        self.resetPort()
        QTimer.singleShot(3000,self.serialchooser.serialConnect)
        #self.serialchooser.serialConnect()

    def resetPort(self):
        self.log("Reset port")
        self.systemUi.setEnabled(False)
        self.serial.waitForBytesWritten(500)
        self.serial.close()
        self.serialchooser.getPorts()
        self.resetTabs()

    def serialConnected(self,connected):
        if(connected):
            if(self.serialGet("id\n")):
                # self.tabWidget_main.addTab(SystemUI(parent = self),"System")
                # self.tabWidget_main.setCurrentIndex(1)
                self.log("Connected")
            else:
                self.log("Can't detect board")
                self.resetPort()
        else:
            self.log("Disconnected")
            self.resetTabs()

    def serialWrite(self,cmd):
        if(self.serial.isOpen()):
            #self.serialchooser.serialLog("->"+cmd)
            self.serialchooser.write(bytes(cmd,"utf-8"))
            if(not self.serial.waitForBytesWritten(1000)):
                self.log("Error writing "+cmd)
    
    def serialGet(self,cmd,timeout = 500):
        self.lastSerial = None
        if(not self.serial.isOpen()):
            self.log("Error: Serial closed")
            return None
        self.serialchooser.setLog(False) # Disable serial log
        self.serialWrite(cmd)
        if(not self.serial.waitForReadyRead(timeout)):
            self.log("Error: Serial timeout")
            return None
        self.serialchooser.setLog(True)
        data = self.serial.readAll()
        self.lastSerial = data.data().decode("utf-8")
        
        if(self.lastSerial and self.lastSerial[-1] == "\n"):
            self.lastSerial=self.lastSerial[0:-1]

        return self.lastSerial


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        uic.loadUi(res_path('about.ui'), self)
        self.version.setText("Version: " + version)
        
            

if __name__ == '__main__':
    #appctxt = ApplicationContext()       # 1. Instantiate ApplicationContext

    app = QApplication(sys.argv)
    window = MainUi()
    window.setWindowTitle("Open FFBoard Configurator")
    window.show()
    #exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    #sys.exit(exit_code)
    sys.exit(app.exec_())