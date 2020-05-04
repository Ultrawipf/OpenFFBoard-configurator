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
    
    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'pwmdriver_ui.ui')
        self.main = main #type: main.MainUi

        self.initUi()
        self.pushButton_apply.clicked.connect(self.apply)

    def initUi(self):
        self.comboBox_mode.clear()
        modes = self.main.serialGet("pwm_mode!\n").split("\n")
        modes = [m.split(":") for m in modes]
        for m in modes:
            self.comboBox_mode.addItem(m[0],m[1])
        self.comboBox_mode.setCurrentIndex(int(self.main.serialGet("pwm_mode?\n")))

        self.comboBox_freq.clear()
        modes = self.main.serialGet("pwm_speed!\n").split("\n")
        modes = [m.split(":") for m in modes]
        for m in modes:
            self.comboBox_freq.addItem(m[0],m[1])
        self.comboBox_freq.setCurrentIndex(int(self.main.serialGet("pwm_speed?\n")))

 
    def apply(self):
        cmd = "pwm_mode="+str(self.comboBox_mode.currentData())+";"
        cmd+= "pwm_speed="+str(self.comboBox_freq.currentData())+";"

        self.main.serialWrite(cmd)
        self.initUi() # Update UI

