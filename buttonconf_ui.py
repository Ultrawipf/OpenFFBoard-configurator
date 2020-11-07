from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QGroupBox
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5 import uic
import main
from optionsdialog import OptionsDialog,OptionsDialogGroupBox
from helper import res_path,classlistToIds


class ButtonOptionsDialog(OptionsDialog):
    def __init__(self,name,id, main):
        self.main = main
        self.dialog = OptionsDialogGroupBox(name,main)

        if(id == 0): # local buttons
            self.dialog = (LocalButtonsConf(name,self.main))
        elif(id == 1):
            self.dialog = (SPIButtonsConf(name,self.main))
        elif(id == 2):
            self.dialog = (ShifterButtonsConf(name,self.main))
        
        OptionsDialog.__init__(self, self.dialog,main)


class LocalButtonsConf(OptionsDialogGroupBox):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)

    def initUI(self):
        self.main.comms.serialGetAsync("local_btnpins?",self.initButtons,int)

    def initButtons(self,num):
        self.num = num
        vbox = QVBoxLayout()
        self.polBox = QCheckBox("Invert")
        vbox.addWidget(self.polBox)
        self.buttongroup = QButtonGroup()
        self.buttongroup.setExclusive(False)
        vbox.addWidget(QLabel("Active pins:"))
        for i in range(self.num):
            cb = QCheckBox(str(i+1))
            self.buttongroup.addButton(cb,i)
            vbox.addWidget(cb)
        self.setLayout(vbox)


 
    def apply(self):
        mask = 0
        for i in range(self.num):
            if(self.buttongroup.button(i).isChecked()):
                mask |= 1 << i
        self.main.comms.serialWrite("local_btnmask="+str(mask))
        self.main.comms.serialWrite("local_btnpol="+("1" if self.polBox.isChecked() else "0"))
    
    def readValues(self):
        def localcb(mask):
            for i in range(self.num):
                self.buttongroup.button(i).setChecked(mask & (1 << i))
        self.main.comms.serialGetAsync("local_btnmask?",localcb,int)
        self.main.comms.serialGetAsync("local_btnpol?",self.polBox.setChecked,int)


class SPIButtonsConf(OptionsDialogGroupBox):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
   
    def initUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Buttons"))
        self.numBtnBox = QSpinBox()
        self.numBtnBox.setMinimum(0)
        self.numBtnBox.setMaximum(32)
        vbox.addWidget(self.numBtnBox)

        vbox.addWidget(QLabel("Mode"))
        self.modeBox = QComboBox()
        vbox.addWidget(self.modeBox)

        self.polBox = QCheckBox("Invert")
        vbox.addWidget(self.polBox)
        self.setLayout(vbox)

    def apply(self):
        self.main.comms.serialWrite("spibtn_mode="+str(self.modeBox.currentData()))
        self.main.comms.serialWrite("spi_btnnum="+str(self.numBtnBox.value()))
        self.main.comms.serialWrite("spi_btnpol="+("1" if self.polBox.isChecked() else "0"))

    def readValues(self):
        self.main.comms.serialGetAsync("spi_btnnum?",self.numBtnBox.setValue,int)
        self.modeBox.clear()
        def modecb(mode):
            modes = mode.split("\n")
            modes = [m.split(":") for m in modes if m]
            for m in modes:
                self.modeBox.addItem(m[0],m[1])
            self.main.comms.serialGetAsync("spibtn_mode?",self.modeBox.setCurrentIndex,int)
        self.main.comms.serialGetAsync("spibtn_mode!",modecb)
        self.main.comms.serialGetAsync("spi_btnpol?",self.polBox.setChecked,int)

class ShifterButtonsConf(OptionsDialogGroupBox):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
   
    def initUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Mode"))
        self.modeBox = QComboBox()
        vbox.addWidget(self.modeBox)
        self.setLayout(vbox)
  
 
    def apply(self):
        self.main.comms.serialWrite("shifter_mode="+str(self.modeBox.currentData()))

    def readValues(self):
        self.modeBox.clear()
        def modecb(mode):
            modes = mode.split("\n")
            modes = [m.split(":") for m in modes if m]
            for m in modes:
                self.modeBox.addItem(m[0],m[1])
            self.main.comms.serialGetAsync("shifter_mode?",self.modeBox.setCurrentIndex,int)
        self.main.comms.serialGetAsync("shifter_mode!",modecb)
