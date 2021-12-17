from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QGroupBox
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5 import uic
import main
from helper import res_path,classlistToIds
from optionsdialog import OptionsDialog,OptionsDialogGroupBox
from base_ui import CommunicationHandler

class AnalogOptionsDialog(OptionsDialog):
    def __init__(self,name,id, main):
        self.main = main
        self.dialog = OptionsDialogGroupBox(name,main)

        if(id == 0): # local buttons
            self.dialog = (AnalogInputConf(name,self.main))

        OptionsDialog.__init__(self, self.dialog,main)


class AnalogInputConf(OptionsDialogGroupBox,CommunicationHandler):
    analogbtns = QButtonGroup()
    axes = 0
    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)
        self.analogbtns.setExclusive(False)
        self.buttonBox = QGroupBox("Pins")
        self.buttonBoxLayout = QVBoxLayout()
        self.buttonBox.setLayout(self.buttonBoxLayout)

    def initUI(self):
        layout = QVBoxLayout()
        self.autorangeBox = QCheckBox("Autorange")
        layout.addWidget(self.autorangeBox)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        
    def readValues(self):
        self.getValueAsync("apin","pins",self.createAinButtons,0,conversion=int)
        self.getValueAsync("apin","autocal",self.autorangeBox.setChecked,0,conversion=int)
        

    def createAinButtons(self,axes):
        self.axes = axes
        # remove buttons
        for i in range(self.buttonBoxLayout.count()):
            b = self.buttonBoxLayout.takeAt(0)
            self.buttonBoxLayout.removeItem(b)
            b.widget().deleteLater()
        for b in self.analogbtns.buttons():
            self.analogbtns.removeButton(b)

        # add buttons
        for i in range(axes):
            btn=QCheckBox(str(i+1),self)
            self.analogbtns.addButton(btn,i)
            self.buttonBoxLayout.addWidget(btn)

        def f(axismask):
            for i in range(self.axes):
                self.analogbtns.button(i).setChecked(axismask & (1 << i))
        self.getValueAsync("apin","mask",f,0,conversion=int)

    def apply(self):
        mask = 0
        for i in range(self.axes):
            if (self.analogbtns.button(i).isChecked()):
                mask |= 1 << i

        self.sendValue("apin","mask",mask)
        self.sendValue("apin","autocal",1 if self.autorangeBox.isChecked() else 0)

    def onclose(self):
        self.removeCallbacks()
