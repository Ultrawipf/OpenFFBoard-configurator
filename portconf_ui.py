from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QGroupBox
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt6 import uic
import main
from helper import res_path,classlistToIds
from optionsdialog import OptionsDialog,OptionsDialogGroupBox
from base_ui import CommunicationHandler

class CanOptionsDialog(OptionsDialog):
    class CanOptionsDialogBox(OptionsDialogGroupBox,CommunicationHandler):
        def __init__(self,name,main,instance):
            self.instance = instance
            OptionsDialogGroupBox.__init__(self,name,main)
            CommunicationHandler.__init__(self)

        def initUI(self):
            layout = QVBoxLayout()
            self.speedBox = QComboBox()
            layout.addWidget(QLabel("CAN baud rate:"))
            layout.addWidget(self.speedBox)
            self.getValueAsync("can","speed",self.updateSpeedCb,self.instance,typechar='!')
            self.getValueAsync("can","speed",self.speedBox.setCurrentIndex,self.instance,typechar='?',conversion=int)
            self.setLayout(layout)

        def updateSpeedCb(self,val):
            self.speedBox.clear()
            for entry in val.split("\n"):
                name,id = entry.split(":")
                self.speedBox.addItem(name,id)

        def apply(self):
            self.sendValue("can","speed",self.speedBox.currentData(),instance=self.instance)

        def onclose(self):
            self.removeCallbacks()

    def getSpeedName(self):
        return self.conf_ui.speedBox.currentText()

    def __init__(self,instance,name, main):
        self.main = main
        self.name = name
        OptionsDialog.__init__(self,self.CanOptionsDialogBox(name,main,instance),main)


class I2COptionsDialog(OptionsDialog):
    class I2COptionsDialogBox(OptionsDialogGroupBox,CommunicationHandler):
        def __init__(self,name,main,instance):
            self.instance = instance
            OptionsDialogGroupBox.__init__(self,name,main)
            CommunicationHandler.__init__(self)

        def initUI(self):
            layout = QVBoxLayout()
            self.speedBox = QComboBox()
            layout.addWidget(QLabel("I2C baud rate:"))
            layout.addWidget(self.speedBox)
            self.getValueAsync("i2c","speed",self.updateSpeedCb,self.instance,typechar='!')
            self.getValueAsync("i2c","speed",self.speedBox.setCurrentIndex,self.instance,typechar='?',conversion=int)
            self.setLayout(layout)

        def updateSpeedCb(self,val):
            self.speedBox.clear()
            for entry in val.split("\n"):
                name,id = entry.split(":")
                self.speedBox.addItem(name,id)

        def apply(self):
            self.sendValue("i2c","speed",self.speedBox.currentData(),instance=self.instance)

        def onclose(self):
            self.removeCallbacks()

    def __init__(self,instance,name, main):
        self.main = main
        self.name = name
        OptionsDialog.__init__(self,self.I2COptionsDialogBox(name,main,instance),main)