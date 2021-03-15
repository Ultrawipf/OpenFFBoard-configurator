from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI

class PwmDriverUI(WidgetUI):
    
    def __init__(self, main=None, unique=1):
        WidgetUI.__init__(self, main,'pwmdriver_ui.ui')
        self.main = main #type: main.MainUi

        self.initUi()
        self.pushButton_apply.clicked.connect(self.apply)

    def initUi(self):
        self.main.comms.serialGetAsync("pwm_mode!",self.pwmmode_cb)
        self.main.comms.serialGetAsync("pwm_speed!",self.freq_cb)
    
    def freq_cb(self,modes):
        self.comboBox_freq.clear()
        modes = [m.split(":") for m in modes.split("\n") if m]
        for m in modes:
            self.comboBox_freq.addItem(m[0],m[1])
        self.main.comms.serialGetAsync("pwm_speed?",self.comboBox_freq.setCurrentIndex,int)

    def pwmmode_cb(self,modes):
        self.comboBox_mode.clear()
        modes = [m.split(":") for m in modes.split("\n") if m]
        for m in modes:
            self.comboBox_mode.addItem(m[0],m[1])
        self.main.comms.serialGetAsync("pwm_mode?",self.comboBox_mode.setCurrentIndex,int)

 
    def apply(self):

        self.main.comms.serialWrite("pwm_mode="+str(self.comboBox_mode.currentData()))
        self.main.comms.serialWrite("pwm_speed="+str(self.comboBox_freq.currentData()))
        self.initUi() # Update UI

