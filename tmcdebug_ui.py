from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI

class TMCDebugUI(WidgetUI):
    
    def __init__(self, main=None, unique=1):
        WidgetUI.__init__(self, main,'tmcdebug.ui')
        self.main = main #type: main.MainUi

        self.initUi()


    def initUi(self):
        pass
    
