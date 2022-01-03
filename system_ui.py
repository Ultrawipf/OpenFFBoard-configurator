from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QWidget,QDialog,QVBoxLayout,QMessageBox
from PyQt6 import uic
from helper import res_path
from PyQt6.QtCore import QTimer
from base_ui import WidgetUI,CommunicationHandler
import re

class SystemUI(WidgetUI,CommunicationHandler):
    
    mainID = None
    def __init__(self, main=None):

        WidgetUI.__init__(self, main,'baseclass.ui')
        CommunicationHandler.__init__(self)
        self.setEnabled(False)
        self.pushButton_reboot.clicked.connect(self.reboot)
        self.pushButton_dfu.clicked.connect(self.dfu)
        self.pushButton_reset.clicked.connect(self.factoryResetBtn)
        self.pushButton_save.clicked.connect(self.saveClicked)

    def updateRamUse(self,reply):
        usage = reply.split(":")
        use = int(usage[0])
        minuse = None
        if(len(usage) == 2):
            minuse = int(usage[1])
        if use:
            use = round(int(use)/1000.0,2)
            if minuse:
                minuse = round(int(minuse)/1000.0,2)
                self.label_ramUse.setText("{}k ({}k min)".format(use,minuse))
            else:
                self.label_ramUse.setText("{}k".format(use))

    def saveClicked(self):
        def f(res):
            self.main.log("Save: "+ str(res))
        self.getValueAsync("sys","save",callback=f)
        
    def setSaveBtn(self,on):
        self.pushButton_save.setEnabled(on)


    def reboot(self):
        self.sendCommand("sys","reboot")
        self.main.reconnect()
    
    def dfu(self):
        self.sendCommand("sys","dfu")
        self.main.log("Entering DFU...")
        self.main.resetPort()
        self.main.dfuUploader()

    def factoryReset(self, btn):
        cmd = btn.text()
        if(cmd=="OK"):
            self.sendValue("sys","format",1)
            self.sendCommand("sys","reboot")
            self.main.resetPort()

    def factoryResetBtn(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Format flash and reset?")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        msg.buttonClicked.connect(self.factoryReset)
        msg.exec()


  