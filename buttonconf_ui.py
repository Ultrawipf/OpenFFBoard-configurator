from collections import namedtuple
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLineEdit, QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QGroupBox
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5 import uic
import main
from optionsdialog import OptionsDialog,OptionsDialogGroupBox
from helper import res_path,classlistToIds
from base_ui import CommunicationHandler


class ButtonOptionsDialog(OptionsDialog):
    def __init__(self,name,id, main):
        self.main = main
        self.dialog = OptionsDialogGroupBox(name,main)

        if(id == 0): # local buttons
            self.dialog = (LocalButtonsConf(name,self.main))
        elif(id == 1):
            self.dialog = (SPIButtonsConf(name,self.main,0))
        elif(id == 2):
            self.dialog = (SPIButtonsConf(name,self.main,1))
        elif(id == 3):
            self.dialog = (ShifterButtonsConf(name,self.main))
        
        OptionsDialog.__init__(self, self.dialog,main)


class LocalButtonsConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)
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
        self.getValueAsync("dpin","mask",localcb,0,conversion=int)
        
 
    def apply(self):
        mask = 0
        for i in range(self.num):
            if(self.buttongroup.button(i).isChecked()):
                mask |= 1 << i
        self.sendValue("dpin","mask",mask)
        self.sendValue("dpin","polarity",(1 if self.polBox.isChecked() else 0))
    
    def readValues(self):
        self.getValueAsync("dpin","pins",self.initButtons,0,conversion=int)
        #self.main.comms.serialGetAsync("local_btnpins?",self.initButtons,int)
        self.getValueAsync("dpin","polarity",self.polBox.setChecked,0,conversion=int)
        #self.main.comms.serialGetAsync("local_btnpol?",self.polBox.setChecked,int)


class SPIButtonsConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main,id):
        self.main = main
        self.id = id
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)

   
    def initUI(self):
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("Buttons"))
        self.numBtnBox = QSpinBox()
        self.numBtnBox.setMinimum(0)
        self.numBtnBox.setMaximum(64)
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
        self.sendValue("spibtn","mode",self.modeBox.currentData(),instance=self.id)
        self.sendValue("spibtn","btnnum",self.numBtnBox.value(),instance=self.id)
        self.sendValue("spibtn","btnpol",1 if self.polBox.isChecked() else 0,instance=self.id)
        self.sendValue("spibtn","btn_cs",self.csBox.value(),instance=self.id)
     
    def readValues(self):

        self.modeBox.clear()
        def modecb(mode):
            modes = mode.split("\n")
            modes = [m.split(":") for m in modes if m]
            for m in modes:
                self.modeBox.addItem(m[0],m[1])
            self.getValueAsync("spibtn","mode",self.modeBox.setCurrentIndex,self.id,conversion=int)
            
        self.getValueAsync("spibtn","btnnum",self.numBtnBox.setValue,self.id,conversion=int)
        self.getValueAsync("spibtn","mode",modecb,self.id,conversion=str,typechar='!')
        self.getValueAsync("spibtn","btnpol",self.polBox.setChecked,self.id,conversion=int)
        self.getValueAsync("spibtn","cs",self.csBox.setValue,self.id,conversion=int)


class ShifterButtonsConf(OptionsDialogGroupBox,CommunicationHandler):
    class Mode(namedtuple('Mode', ['index', 'name', 'uses_spi', 'uses_local_reverse'])):
        pass

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)
   
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
        self.modeBox.currentIndexChanged.connect(self.modeBoxChanged)
        vbox.addWidget(self.modeBox)

        self.xPos = QLineEdit()
        self.xPos.setReadOnly(True)
        self.yPos = QLineEdit()
        self.yPos.setReadOnly(True)
        self.gear = QLineEdit()
        self.gear.setReadOnly(True)

        posGroup = QGridLayout()
        posGroup.addWidget(QLabel("X"), 1, 1)
        posGroup.addWidget(self.xPos, 1, 2)
        posGroup.addWidget(QLabel("Y"), 1, 3)
        posGroup.addWidget(self.yPos, 1, 4)
        posGroup.addWidget(QLabel("Calculated Gear"), 2, 1, 1, 2)
        posGroup.addWidget(self.gear, 2, 3, 1, 2)
        posGroupBox = QGroupBox()
        posGroupBox.setTitle("Current")
        posGroupBox.setLayout(posGroup)
        vbox.addWidget(posGroupBox)

        vbox.addWidget(QLabel("X Channel"))
        self.xChannel = QSpinBox()
        self.xChannel.setMinimum(1)
        self.xChannel.setMaximum(6)
        vbox.addWidget(self.xChannel)

        vbox.addWidget(QLabel("Y Channel"))
        self.yChannel = QSpinBox()
        self.yChannel.setMinimum(1)
        self.yChannel.setMaximum(6)
        vbox.addWidget(self.yChannel)

        self.x12 = addThreshold("X 1,2 Threshold")
        self.x56 = addThreshold("X 5,6 Threshold")
        self.y135 = addThreshold("Y 1,3,5 Threshold")
        self.y246 = addThreshold("Y 2,4,6 Threshold")

        self.revBtnLabel = QLabel("Reverse Button Digital Input")
        vbox.addWidget(self.revBtnLabel)
        self.revBtnBox = QSpinBox()
        self.revBtnBox.setMinimum(1)
        self.revBtnBox.setMaximum(8)
        vbox.addWidget(self.revBtnBox)

        self.csPinLabel = QLabel("SPI CS Pin Number")
        vbox.addWidget(self.csPinLabel)
        self.csPinBox = QSpinBox()
        self.csPinBox.setMinimum(1)
        self.csPinBox.setMaximum(3)
        vbox.addWidget(self.csPinBox)

        self.setLayout(vbox)

        self.timer = QTimer()
        self.timer.timeout.connect(self.readXYPosition)

    def onshown(self):
        self.timer.start(500)

    def onclose(self):
        self.timer.stop()

    def modeBoxChanged(self, _):
        mode = self.modeBox.currentData()

        if mode is not None:
            self.revBtnLabel.setVisible(mode.uses_local_reverse)
            self.revBtnBox.setVisible(mode.uses_local_reverse)
            self.csPinLabel.setVisible(mode.uses_spi)
            self.csPinBox.setVisible(mode.uses_spi)
 
    def apply(self):
        self.sendValue("spibtn","mode",self.modeBox.currentData().index)
        self.sendValue("spibtn","xchan",self.xChannel.value())
        self.sendValue("spibtn","ychan",self.yChannel.value())
        self.sendValue("spibtn","x12",self.x12.value())
        self.sendValue("spibtn","x56",self.x56.value())
        self.sendValue("spibtn","y135",self.y135.value())
        self.sendValue("spibtn","y246",self.y246.value())
        self.sendValue("spibtn","revbtn",self.revBtnBox.value())
        self.sendValue("spibtn","cspin",self.csPinBox.value())

    def readXYPosition(self):
        def updatePosition(valueStr: str):
            x,y = valueStr.strip().split(":")
            self.xPos.setText(x)
            self.yPos.setText(y)

        def updateGear(value: str):
            value = value.strip()
            if value == "0":
                value = "N"
            elif value == "7":
                value = "R"
            
            self.gear.setText(value)
        self.getValueAsync("shifter","vals",updatePosition,0,conversion=str)
        self.getValueAsync("shifter","gear",updateGear,0,conversion=str)  

    def readValues(self):
        self.modeBox.clear()
        def modecb(mode):
            modes = mode.split("\n")
            modes = [m.split(":") for m in modes if m]
            for m in modes:
                index, uses_spi, uses_local_reverse = m[1].split(',')
                self.modeBox.addItem(m[0], ShifterButtonsConf.Mode(int(index), m[0], uses_spi == "1", uses_local_reverse == "1"))
            self.getValueAsync("shifter","mode",self.modeBox.setCurrentIndex,0,conversion=int)
        self.getValueAsync("shifter","mode",modecb,0,conversion=str,typechar = '!')
        self.getValueAsync("shifter","xchan",self.xChannel.setValue,0,conversion=int)
        self.getValueAsync("shifter","ychan",self.yChannel.setValue,0,conversion=int)

        self.getValueAsync("shifter","x12",self.x12.setValue,0,conversion=int)
        self.getValueAsync("shifter","x56",self.x56.setValue,0,conversion=int)
        self.getValueAsync("shifter","y135",self.y135.setValue,0,conversion=int)
        self.getValueAsync("shifter","y246",self.y246.setValue,0,conversion=int)

        self.getValueAsync("shifter","revbtn",self.revBtnBox.setValue,0,conversion=int)
        self.getValueAsync("shifter","cspin",self.csPinBox.setValue,0,conversion=int)

        self.readXYPosition()

