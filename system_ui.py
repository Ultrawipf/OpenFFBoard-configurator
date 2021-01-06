from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QWidget,QDialog,QVBoxLayout
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
from base_ui import WidgetUI

class SystemUI(WidgetUI):
    classes = []
    classIds = {}
    mainID = None
    def __init__(self, main=None):

        WidgetUI.__init__(self, main,'baseclass.ui')
        self.setEnabled(False)
        self.pushButton_ok.clicked.connect(self.mainBtn)
        self.pushButton_reboot.clicked.connect(self.reboot)
        self.pushButton_dfu.clicked.connect(self.dfu)
        self.pushButton_reset.clicked.connect(self.factoryResetBtn)


    def serialConnected(self,connected):
        if(connected):
            self.getMainClasses()
        else:
            self.setEnabled(False)


    def mainBtn(self):
        id = self.classes[self.comboBox_main.currentIndex()][0]
        self.main.comms.serialWrite("main="+str(id)+"\n")
        self.main.resetPort()
        msg = QMessageBox(QMessageBox.Information,"Main class changed","Please reconnect.\n Depending on the main class the serial port may have changed.")
        msg.exec_()
  
    def reboot(self):
        self.main.comms.serialWrite("reboot\n")
        self.main.reconnect()
    
    def dfu(self):
        self.main.comms.serialWrite("dfu\n")
        self.main.log("Entering DFU...")
        self.main.resetPort()
        self.main.dfuUploader()

    def factoryReset(self, btn):
        cmd = btn.text()
        if(cmd=="OK"):
            self.main.comms.serialWrite("format=1\n")
            self.main.comms.serialWrite("reboot\n")
            self.main.resetPort()

    def factoryResetBtn(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Format flash and reset?")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.buttonClicked.connect(self.factoryReset)
        msg.exec_()

    def getMainClasses(self):
        def updateMains(dat):
            self.comboBox_main.clear()
            self.classIds,self.classes = classlistToIds(dat)
            
            if(self.mainID == None):
                #self.main.resetPort()
                self.setEnabled(False)
                return
            self.setEnabled(True)
            for c in self.classes:
                self.comboBox_main.addItem(c[1])
            self.comboBox_main.setCurrentIndex(self.classIds[self.mainID][0])
            self.main.log("Detected mode: "+self.comboBox_main.currentText())
            self.main.updateTabs()

        def f(i):
            self.mainID = i
        self.main.comms.serialGetAsync("id?",f,int)
        self.main.comms.serialGetAsync("lsmain",updateMains)
        