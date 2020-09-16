from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5 import uic
import main
from helper import res_path,classlistToIds

class ButtonOptionsDialog(QDialog):
    def __init__(self,name,id, parent):
        self.id = id
        self.name = name
        self.main = parent #type: main.MainUi
        QDialog.__init__(self, parent)
        #uic.loadUi(res_path('buttonoptions.ui'), self)
        self.setWindowTitle(name)
        try:
            self.initUI()
        except Exception as e:
            print(e)


    def initUI(self):
        # Create the user interface depending on the class
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(self.name))
        
        if(self.id == 0): # local buttons
            # Buttonmasks
            self.setMinimumWidth(100)
            self.buttongroup = QButtonGroup()
            self.buttongroup.setExclusive(False)
            vbox.addWidget(QLabel("Active pins:"))
            for i in range(8):
                cb = QCheckBox(str(i+1))
                self.buttongroup.addButton(cb,i)
                vbox.addWidget(cb)

        elif(self.id == 1): # SPI
            self.setMinimumWidth(100)
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

        elif(self.id == 2): #Shifter
            self.setMinimumWidth(200)
            vbox.addWidget(QLabel("Mode"))
            self.modeBox = QComboBox()
            vbox.addWidget(self.modeBox)
        else:
            vbox.addWidget(QLabel("No config options"))

        # Ok Button
        okbtn = QPushButton("OK")
        okbtn.clicked.connect(self.apply)
        vbox.addWidget(okbtn)
        self.setLayout(vbox)

    # When ok is clicked
    def apply(self):
        if(self.id == 0):
            mask = 0
            for i in range(8):
                if(self.buttongroup.button(i).isChecked()):
                    mask |= 1 << i
            self.main.comms.serialWrite("local_btnmask="+str(mask)+"\n")

        elif(self.id == 1):
            self.main.comms.serialWrite("spibtn_mode="+str(self.modeBox.currentData()))
            self.main.comms.serialWrite("spi_btnnum="+str(self.numBtnBox.value()))
            self.main.comms.serialWrite("spi_btnpol="+("1" if self.polBox.isChecked() else "0"))
    
    
        elif(self.id == 2):
            self.main.comms.serialWrite("shifter_mode="+str(self.modeBox.currentData()))
        self.close()

    def showEvent(self,event):
        try:
            self.readValues()
        except Exception as e:
            self.main.log("Error getting button info")
            return

    def readValues(self):
        if(self.id == 0): # Local
            def localcb(mask):
                for i in range(8):
                    self.buttongroup.button(i).setChecked(mask & (1 << i))
            self.main.comms.serialGetAsync("local_btnmask",localcb,int)
            
        # SPI
        elif(self.id == 1):
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
           
            
        # Shifter
        elif(self.id == 2):
            self.modeBox.clear()
            def modecb(mode):
                modes = mode.split("\n")
                modes = [m.split(":") for m in modes if m]
                for m in modes:
                    self.modeBox.addItem(m[0],m[1])
                self.main.comms.serialGetAsync("shifter_mode?",self.modeBox.setCurrentIndex,int)
            self.main.comms.serialGetAsync("shifter_mode!",modecb)