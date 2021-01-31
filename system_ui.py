from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QWidget,QDialog,QVBoxLayout
from PyQt5 import uic
from helper import res_path
from PyQt5.QtCore import QTimer
from base_ui import WidgetUI

class SystemUI(WidgetUI):
    
    mainID = None
    def __init__(self, main=None):

        WidgetUI.__init__(self, main,'baseclass.ui')
        self.setEnabled(False)
        self.pushButton_reboot.clicked.connect(self.reboot)
        self.pushButton_dfu.clicked.connect(self.dfu)
        self.pushButton_reset.clicked.connect(self.factoryResetBtn)
        self.pushButton_save.clicked.connect(self.saveClicked)


    def saveClicked(self):
        def f(res):
            self.main.log("Save: "+ str(res))
        self.main.comms.serialGetAsync("save\n",f)
        
    def setSaveBtn(self,on):
        self.pushButton_save.setEnabled(on)


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


  