from PyQt5.QtWidgets import QDialogButtonBox, QHBoxLayout, QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QGroupBox
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5 import uic
import main
from helper import res_path,classlistToIds


class OptionsDialog(QDialog):
    
    def __init__(self,dialog, parent):
        QDialog.__init__(self, parent)
        self.initialized = False
        self.main = parent #type: main.MainUi
        self.layout = QVBoxLayout()
        self.setWindowTitle(dialog.name)

        self.setDialog(dialog)
 
    def initBaseUI(self):
        self.initialized = True
        self.conf_ui.initUI()
        self.layout.addWidget(self.conf_ui)

        okbtn = QPushButton("OK")
        okbtn.clicked.connect(self.ok)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.close)
        applyButton = QPushButton("Apply")
        applyButton.clicked.connect(self.apply)

        btnGroup = QDialogButtonBox()
        btnGroup.addButton(okbtn, QDialogButtonBox.AcceptRole)
        btnGroup.addButton(cancelButton, QDialogButtonBox.RejectRole)
        btnGroup.addButton(applyButton, QDialogButtonBox.ApplyRole)
        self.layout.addWidget(btnGroup)

        self.setLayout(self.layout)

    def ok(self):
        self.apply()
        self.close()

    def apply(self):
        self.conf_ui.apply()

    def closeEvent(self, a0) -> None:
        self.onclose()
        return super().closeEvent(a0)

    def onclose(self):
        self.conf_ui.onclose()

    def exec(self) -> None:
        try:
            if not self.initialized:
                self.initBaseUI()
            self.conf_ui.readValues()
            self.conf_ui.onshown()
        except Exception as e:
            self.main.log("Error getting info")
            print(e)
        return super().exec()

    def setDialog(self,dialog):
        self.conf_ui = dialog

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

    def onshown(self):
        pass

    def onclose(self):
        pass