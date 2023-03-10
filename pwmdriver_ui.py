from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt6 import uic
from helper import res_path,classlistToIds
from PyQt6.QtCore import QTimer
import main
from base_ui import WidgetUI
from base_ui import CommunicationHandler

class PwmDriverUI(WidgetUI,CommunicationHandler):
    
    def __init__(self, main=None, unique=1):
        WidgetUI.__init__(self, main,'pwmdriver_ui.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi
        
        self.pushButton_apply.clicked.connect(self.apply)

        self.register_callback("pwmdrv","freq",self.freq_cb,0,str,typechar='!')
        self.register_callback("pwmdrv","freq",self.comboBox_freq.setCurrentIndex,0,int,typechar='?')

        self.register_callback("pwmdrv","mode",self.pwmmode_cb,0,str,typechar='!')
        self.register_callback("pwmdrv","mode",self.comboBox_mode.setCurrentIndex,0,int,typechar='?')
        self.register_callback("pwmdrv","dir",self.checkBox_invert.setChecked,0,int,typechar='?')

        self.init_ui()

    def init_ui(self):
        # Fill menus
        self.send_command("pwmdrv","freq",0,'!')
        self.send_command("pwmdrv","mode",0,'!')
        self.send_command("pwmdrv","dir",0,'?')
    
    def freq_cb(self,modes):
        self.comboBox_freq.clear()
        modes = [m.split(":") for m in modes.split("\n") if m]
        for m in modes:
            self.comboBox_freq.addItem(m[0],m[1])
        self.send_command("pwmdrv","freq",0,'?')

    def pwmmode_cb(self,modes):
        self.comboBox_mode.clear()
        modes = [m.split(":") for m in modes.split("\n") if m]
        for m in modes:
            self.comboBox_mode.addItem(m[0],m[1])
        self.send_command("pwmdrv","mode",0,'?')

 
    def apply(self):
        self.send_value("pwmdrv","mode",self.comboBox_mode.currentData())
        self.send_value("pwmdrv","freq",self.comboBox_freq.currentData())
        self.send_value("pwmdrv","dir",1 if self.checkBox_invert.isChecked() else 0)
        self.init_ui() # Update UI

