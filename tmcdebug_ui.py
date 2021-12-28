from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt6 import uic
from helper import res_path,classlistToIds
from PyQt6.QtCore import QTimer
import main
from base_ui import WidgetUI

class TMCDebugUI(WidgetUI):
    
    def __init__(self, main=None, unique=1):
        WidgetUI.__init__(self, main,'tmcdebug.ui')
        self.main = main #type: main.MainUi

        self.init_ui()


    def init_ui(self):
        pass
    
