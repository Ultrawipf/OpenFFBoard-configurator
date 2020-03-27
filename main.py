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

        self.setup()
        self.lastSerial = None
        
        
    def setup(self):
        self.serialchooser = serial_ui.SerialChooser(serial=self.serial,parent = self)
        self.tabWidget_main.addTab(self.serialchooser,"Serial")
        self.serial.readyRead.connect(self.serialReceive)
        self.serialchooser.getPorts()
        self.actionAbout.triggered.connect(self.openAbout)
        self.serialchooser.connected.connect(self.serialConnected)
        #self.timer.start(500)
        self.systemUi = system_ui.SystemUI(parent = self)
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

    def log(self,s):
        self.logBox.append(s)


    def setSaveBtn(self,enabled):
        self.systemUi.pushButton_save.setEnabled(enabled)

    def saveClicked(self):
        self.log("Save")
        self.save.emit()

    def serialReceive(self):
        data = self.serial.readAll()
        text = data.data().decode("utf-8")
        self.lastSerial = text
        self.serialchooser.serialLog("<-"+text)

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
        for i in range(self.tabWidget_main.count()-1,0,-1):
            self.delTab(self.tabWidget_main.widget(i))
    
    def chooseMain(self,id):
        if(id==self.curId):
            return
        self.resetTabs()
        if(id == 1):
            # FFB
            self.mainClassUi = ffb_ui.FfbUI(parent = self)
            pass
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
            self.serialchooser.serialLog("->"+cmd)
            self.serial.write(bytes(cmd,"utf-8"))
    
    def serialGet(self,cmd,timeout = 50):
        self.lastSerial = None
        if(not self.serial.isOpen()):
            return None
        self.serialWrite(cmd)
        #self.serial.waitForBytesWritten(timeout)
        self.serial.waitForReadyRead(timeout)
        
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