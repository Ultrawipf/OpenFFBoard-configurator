from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI
from base_ui import CommunicationHandler

class PwmDriverUI(WidgetUI,CommunicationHandler):
    
    def __init__(self, main=None, unique=1):
        WidgetUI.__init__(self, main,'pwmdriver_ui.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi
        
        self.pushButton_apply.clicked.connect(self.apply)

        self.registerCallback("pwmdrv","freq",self.freq_cb,0,str,typechar='!')
        self.registerCallback("pwmdrv","freq",self.comboBox_freq.setCurrentIndex,0,int,typechar='?')

        self.registerCallback("pwmdrv","mode",self.pwmmode_cb,0,str,typechar='!')
        self.registerCallback("pwmdrv","mode",self.comboBox_mode.setCurrentIndex,0,int,typechar='?')

        self.initUi()

    def initUi(self):
        # Fill menus
        self.sendCommand("pwmdrv","freq",0,'!')
        self.sendCommand("pwmdrv","mode",0,'!')
    
    def freq_cb(self,modes):
        self.comboBox_freq.clear()
        modes = [m.split(":") for m in modes.split("\n") if m]
        for m in modes:
            self.comboBox_freq.addItem(m[0],m[1])
        self.sendCommand("pwmdrv","freq",0,'?')

    def pwmmode_cb(self,modes):
        self.comboBox_mode.clear()
        modes = [m.split(":") for m in modes.split("\n") if m]
        for m in modes:
            self.comboBox_mode.addItem(m[0],m[1])
        self.sendCommand("pwmdrv","mode",0,'?')

 
    def apply(self):
        self.sendValue("pwmdrv","mode",self.comboBox_mode.currentData())
        self.sendValue("pwmdrv","freq",self.comboBox_freq.currentData())
        self.initUi() # Update UI

