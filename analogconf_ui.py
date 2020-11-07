from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QGroupBox
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5 import uic
import main
from helper import res_path,classlistToIds
from optionsdialog import OptionsDialog,OptionsDialogGroupBox

class AnalogOptionsDialog(OptionsDialog):
    def __init__(self,name,id, main):
        self.main = main
        self.dialog = OptionsDialogGroupBox(name,main)

        if(id == 0): # local buttons
            self.dialog = (AnalogInputConf(name,self.main))

        OptionsDialog.__init__(self, self.dialog,main)


class AnalogInputConf(OptionsDialogGroupBox):
    analogbtns = QButtonGroup()
    axes = 0
    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        self.analogbtns.setExclusive(False)
        #self.analogbtns.buttonClicked.connect(self.axesChanged)

    def initUI(self):
        self.main.comms.serialGetAsync("local_ain_num?",self.createAinButtons,int)
        
    def readValues(self):
        def f(axismask):
            for i in range(self.axes):
                self.analogbtns.button(i).setChecked(axismask & (1 << i))
        self.main.comms.serialGetAsync("local_ain_mask?",f,int)

    def createAinButtons(self,axes):
        self.axes = axes
        layout = QVBoxLayout()

        for b in self.analogbtns.buttons():
            self.analogbtns.removeButton(b)
            del b

        for i in range(axes):
            btn=QCheckBox(str(i+1),self)
            self.analogbtns.addButton(btn,i)
            layout.addWidget(btn)

        self.setLayout(layout)

    def apply(self):
        mask = 0
        for i in range(self.axes):
            if (self.analogbtns.button(i).isChecked()):
                mask |= 1 << i
        self.main.comms.serialWrite("local_ain_mask="+str(mask)+"\n")