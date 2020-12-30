from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QMainWindow
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
            self.dialog = (SPIButtonsConf(name,self.main,1))
        elif(id == 2):
            self.dialog = (SPIButtonsConf(name,self.main,2))
        elif(id == 3):
            self.dialog = (ShifterButtonsConf(name,self.main))
        
        OptionsDialog.__init__(self, self.dialog,main)


class LocalButtonsConf(OptionsDialogGroupBox):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        self.buttonBox = QGroupBox("Pins")
        self.buttonBoxLayout = QVBoxLayout()
        self.buttonBox.setLayout(self.buttonBoxLayout)

    def initUI(self):
        vbox = QVBoxLayout()
        self.polBox = QCheckBox("Invert")
        vbox.addWidget(self.polBox)
        self.buttongroup = QButtonGroup()
        self.buttongroup.setExclusive(False)
        vbox.addWidget(self.buttonBox)
        
        self.setLayout(vbox)


    def initButtons(self,num):
        #delete buttons
        self.num = num

        # Remove buttons
        for i in range(self.buttonBoxLayout.count()):
            b = self.buttonBoxLayout.takeAt(0)
            self.buttonBoxLayout.removeItem(b)
            b.widget().deleteLater()
        for b in self.buttongroup.buttons():
            self.buttongroup.removeButton(b)

        self.buttonBox.update()

        for i in range(self.num):
            cb = QCheckBox(str(i+1))
            self.buttongroup.addButton(cb,i)
            self.buttonBoxLayout.addWidget(cb)

        def localcb(mask):
            for i in range(self.num):
                self.buttongroup.button(i).setChecked(mask & (1 << i))
        self.main.comms.serialGetAsync("local_btnmask?",localcb,int)
        
 
    def apply(self):
        mask = 0
        for i in range(self.num):
            if(self.buttongroup.button(i).isChecked()):
                mask |= 1 << i
        self.main.comms.serialWrite("local_btnmask="+str(mask))
        self.main.comms.serialWrite("local_btnpol="+("1" if self.polBox.isChecked() else "0"))
    
    def readValues(self):
        self.main.comms.serialGetAsync("local_btnpins?",self.initButtons,int)
        
        self.main.comms.serialGetAsync("local_btnpol?",self.polBox.setChecked,int)


class SPIButtonsConf(OptionsDialogGroupBox):

    def __init__(self,name,main,id):
        self.main = main
        self.id = id
        OptionsDialogGroupBox.__init__(self,name,main)

    def getPrefix(self):
        return f"spi{self.id}_"
   
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

        vbox.addWidget(QLabel("CS #"))
        self.csBox = QSpinBox()
        self.csBox.setMinimum(1)
        self.csBox.setMaximum(3)
        vbox.addWidget(self.csBox)

    def apply(self):
        self.main.comms.serialWrite(f"{self.getPrefix()}btn_mode="+str(self.modeBox.currentData()))
        self.main.comms.serialWrite(f"{self.getPrefix()}btnnum="+str(self.numBtnBox.value()))
        self.main.comms.serialWrite(f"{self.getPrefix()}btnpol="+("1" if self.polBox.isChecked() else "0"))
        self.main.comms.serialWrite(f"{self.getPrefix()}btn_cs={self.csBox.value()}")

    def readValues(self):
        self.main.comms.serialGetAsync(f"{self.getPrefix()}btnnum?",self.numBtnBox.setValue,int)
        self.modeBox.clear()
        def modecb(mode):
            modes = mode.split("\n")
            modes = [m.split(":") for m in modes if m]
            for m in modes:
                self.modeBox.addItem(m[0],m[1])
            self.main.comms.serialGetAsync(f"{self.getPrefix()}btn_mode?",self.modeBox.setCurrentIndex,int)
        self.main.comms.serialGetAsync(f"{self.getPrefix()}btn_mode!",modecb)
        self.main.comms.serialGetAsync(f"{self.getPrefix()}btnpol?",self.polBox.setChecked,int)
        self.main.comms.serialGetAsync(f"{self.getPrefix()}btn_cs?", self.csBox.setValue, int)

class ShifterButtonsConf(OptionsDialogGroupBox):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
   
    def initUI(self):
        def addThreshold(name):
            vbox.addWidget(QLabel(name))
            numBtnBox = QSpinBox()
            numBtnBox.setMinimum(0)
            numBtnBox.setMaximum(4096)
            vbox.addWidget(numBtnBox)
            return numBtnBox

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Mode"))
        self.modeBox = QComboBox()
        vbox.addWidget(self.modeBox)

        self.xPos = QLineEdit()
        self.xPos.setReadOnly(True)
        self.yPos = QLineEdit()
        self.yPos.setReadOnly(True)

        posGroup = QHBoxLayout()
        posGroup.addWidget(QLabel("X"))
        posGroup.addWidget(self.xPos)
        posGroup.addWidget(QLabel("Y"))
        posGroup.addWidget(self.yPos)
        posGroupBox = QGroupBox()
        posGroupBox.setTitle("Current")
        posGroupBox.setLayout(posGroup)
        vbox.addWidget(posGroupBox)

        self.x12 = addThreshold("X 1,2 Threshold")
        self.x56 = addThreshold("X 5,6 Threshold")
        self.y135 = addThreshold("Y 1,3,5 Threshold")
        self.y246 = addThreshold("Y 2,4,6 Threshold")

        vbox.addWidget(QLabel("Reverse Button Number"))
        self.revBtnBox = QSpinBox()
        self.revBtnBox.setMinimum(0)
        self.revBtnBox.setMaximum(32)
        vbox.addWidget(self.revBtnBox)

        self.setLayout(vbox)

        self.timer = QTimer()
        self.timer.timeout.connect(self.readXYPosition)
        self.timer.start(500)
  
 
    def apply(self):
        self.main.comms.serialWrite(f"shifter_mode={self.modeBox.currentData()}")
        self.main.comms.serialWrite(f"shifter_x_12={self.x12.value()}")
        self.main.comms.serialWrite(f"shifter_x_56={self.x56.value()}")
        self.main.comms.serialWrite(f"shifter_y_135={self.y135.value()}")
        self.main.comms.serialWrite(f"shifter_y_246={self.y246.value()}")
        self.main.comms.serialWrite(f"shifter_rev_btn={self.revBtnBox.value()}")

    def readXYPosition(self):
        def updatePosition(valueStr: str):
            x,y = valueStr.strip().split(",")
            self.xPos.setText(x)
            self.yPos.setText(y)
        self.main.comms.serialGetAsync("shifter_vals?",updatePosition, str)
        

    def readValues(self):
        self.modeBox.clear()
        def modecb(mode):
            modes = mode.split("\n")
            modes = [m.split(":") for m in modes if m]
            for m in modes:
                self.modeBox.addItem(m[0],m[1])
            self.main.comms.serialGetAsync("shifter_mode?",self.modeBox.setCurrentIndex,int)
        self.main.comms.serialGetAsync("shifter_mode!",modecb)
        self.main.comms.serialGetAsync("shifter_x_12?",self.x12.setValue,int)
        self.main.comms.serialGetAsync("shifter_x_56?",self.x56.setValue,int)
        self.main.comms.serialGetAsync("shifter_y_135?",self.y135.setValue,int)
        self.main.comms.serialGetAsync("shifter_y_246?",self.y246.setValue,int)
        self.readXYPosition()

