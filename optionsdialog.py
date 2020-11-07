from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QGroupBox
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5 import uic
import main
from helper import res_path,classlistToIds


class OptionsDialog(QDialog):
    
    def __init__(self,dialog, parent):
        QDialog.__init__(self, parent)
        self.main = parent #type: main.MainUi
        self.layout = QVBoxLayout()
        self.setWindowTitle(dialog.name)

        self.setDialog(dialog)
 
    def initBaseUI(self):
        self.conf_ui.initUI()
        self.layout.addWidget(self.conf_ui)

        okbtn = QPushButton("OK")
        okbtn.clicked.connect(self.apply)
        self.layout.addWidget(okbtn)
        self.setLayout(self.layout)

    def apply(self):
        self.conf_ui.apply()
        self.close()

    def showEvent(self,event):
        try:
            self.conf_ui.readValues()
        except Exception as e:
            self.main.log("Error getting info")
            return

    def setDialog(self,dialog):
        self.conf_ui = dialog
        self.initBaseUI()

class OptionsDialogGroupBox(QGroupBox):
    name = "Options"
    def __init__(self,name,main):
        self.name = name
        self.main = main
        QGroupBox.__init__(self,name)

    def initUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Error. No dialog for\n" + self.name))
        self.setLayout(vbox)
 
    def apply(self):
        pass
    
    def readValues(self):
        pass