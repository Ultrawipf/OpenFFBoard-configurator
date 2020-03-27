from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer

class SystemUI(QWidget):
    classes = []
    classIds = {}
    def __init__(self, parent=None):
        self.parent = parent
        QWidget.__init__(self, parent)
        self.main = parent
        uic.loadUi(res_path('baseclass.ui'), self)
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
        self.main.serialWrite("main="+str(id)+"\n")
        self.main.resetPort()
        msg = QMessageBox(QMessageBox.Information,"Main class changed","Please reconnect.\n Depending on the main class the serial port may have changed.")
        msg.exec_()
  
    def reboot(self):
        self.main.serialWrite("reboot\n")
        self.main.reconnect()
    
    def dfu(self):
        self.parent.serialWrite("dfu\n")
        self.main.resetPort()
        msg = QMessageBox(QMessageBox.Information,"DFU","Switched to DFU mode.\nConnect with DFU programmer")
        msg.exec_()

    def factoryReset(self, btn):
        cmd = btn.text()
        if(cmd=="OK"):
            self.main.serialWrite("format=1\n")
            self.main.serialWrite("reboot\n")
            self.main.resetPort()

    def factoryResetBtn(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Format flash and reset?")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.buttonClicked.connect(self.factoryReset)
        msg.exec_()

    def getMainClasses(self):
        dat = self.main.serialGet("lsmain\n")
        self.comboBox_main.clear()
        self.classIds,self.classes = classlistToIds(dat)
        id = self.main.serialGet("id?\n")
        if(id == None):
            #self.main.resetPort()
            self.setEnabled(False)
            return

        self.setEnabled(True)
        id = int(id)

        for c in self.classes:
            self.comboBox_main.addItem(c[1])
        self.comboBox_main.setCurrentIndex(self.classIds[id][0])

        self.main.chooseMain(id)
