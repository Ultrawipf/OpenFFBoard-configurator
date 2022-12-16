from collections import namedtuple
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLineEdit, QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QGroupBox
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt6 import uic
import helper
from optionsdialog import OptionsDialog,OptionsDialogGroupBox
from helper import res_path,classlistToIds
from base_ui import CommunicationHandler
import portconf_ui

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
        elif(id == 4):
            self.dialog = (PCFButtonsConf(name,self.main))
        elif(id == 5):
            self.dialog = (CANButtonsConf(name,self.main))
        
        OptionsDialog.__init__(self, self.dialog,main)


class LocalButtonsConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)
        self.buttonBox = QGroupBox("Pins")
        self.buttonBoxLayout = QVBoxLayout()
        self.buttonBox.setLayout(self.buttonBoxLayout)

        self.btn_mask=0
        self.prefix=0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)

    def initUI(self):
        vbox = QVBoxLayout()
        self.polBox = QCheckBox("Invert")
        vbox.addWidget(self.polBox)
        self.buttongroup = QButtonGroup()
        self.buttongroup.setExclusive(False)
        vbox.addWidget(self.buttonBox)
        
        self.setLayout(vbox)

    # Tab is currently shown
    def showEvent(self,event):
        self.timer.start(300)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()
        
    def updateTimer(self):
        self.send_commands("dpin",["values"],self.prefix)

    def onclose(self):
        self.remove_callbacks()

    def onshown(self):
        self.register_callback("dpin","values",self.valueCb,self.prefix,int)

    def valueCb(self, val):
        j=0
        for i in range(self.num):
            btn = self.buttongroup.button(i)
            if self.btn_mask & (1<<i):
                if val & (1<<j):
                    btn.setStyleSheet("background-color: yellow")
                else:
                    btn.setStyleSheet("background-color: none")
                j=j+1
            else:
                btn.setStyleSheet("background-color: none")
            
    def initButtons(self,num):
        #delete buttons
        self.num = num

        # Remove buttons
        for i in range(self.buttonBoxLayout.count()):
            b = self.buttonBoxLayout.takeAt(0)
            self.buttonBoxLayout.removeItem(b)
            b.widget().setParent(None)
            #b.widget().deleteLater()
        for b in self.buttongroup.buttons():
            self.buttongroup.removeButton(b)

        self.buttonBox.update()

        for i in range(self.num):
            cb = QCheckBox(str(i+1))
            self.buttongroup.addButton(cb,i)
            self.buttonBoxLayout.addWidget(cb)

        def localcb(mask):
            self.btn_mask = mask
            for i in range(self.num):
                self.buttongroup.button(i).setChecked(mask & (1 << i))
        self.get_value_async("dpin","mask",localcb,0,conversion=int)
        
 
    def apply(self):
        self.btn_mask = 0
        for i in range(self.num):
            if(self.buttongroup.button(i).isChecked()):
                self.btn_mask |= 1 << i
        self.send_value("dpin","mask",self.btn_mask)
        self.send_value("dpin","polarity",(1 if self.polBox.isChecked() else 0))
    
    def readValues(self):
        self.get_value_async("dpin","pins",self.initButtons,0,conversion=int)
        self.get_value_async("dpin","polarity",self.polBox.setChecked,0,conversion=int)
 

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

        vbox.addWidget(QLabel("SPI Speed"))
        self.speedBox = QComboBox()
        vbox.addWidget(self.speedBox)

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
        self.send_value("spibtn","mode",self.modeBox.currentData(),instance=self.id)
        self.send_value("spibtn","btnnum",self.numBtnBox.value(),instance=self.id)
        self.send_value("spibtn","btnpol",1 if self.polBox.isChecked() else 0,instance=self.id)
        self.send_value("spibtn","btn_cs",self.csBox.value(),instance=self.id)
        self.send_value("spibtn","spispeed",self.speedBox.currentData(),instance=self.id)

    def onclose(self):
        self.remove_callbacks()

     
    def readValues(self):

        self.modeBox.clear()
        def modecb(mode):
            modes = helper.splitListReply(mode)
            for m in modes:
                self.modeBox.addItem(m[0],m[1])
            self.get_value_async("spibtn","mode",self.modeBox.setCurrentIndex,self.id,conversion=int)

        self.speedBox.clear()
        def speedcb(mode):
            modes = helper.splitListReply(mode)
            for m in modes:
                self.speedBox.addItem(m[0],m[1])
            self.get_value_async("spibtn","spispeed",self.speedBox.setCurrentIndex,self.id,conversion=int)
            
        self.get_value_async("spibtn","btnnum",self.numBtnBox.setValue,self.id,conversion=int)
        self.get_value_async("spibtn","mode",modecb,self.id,conversion=str,typechar='!')
        self.get_value_async("spibtn","spispeed",speedcb,self.id,conversion=str,typechar='!')
        self.get_value_async("spibtn","btnpol",self.polBox.setChecked,self.id,conversion=int)
        self.get_value_async("spibtn","cs",self.csBox.setValue,self.id,conversion=int)


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
        self.remove_callbacks()

    def modeBoxChanged(self, _):
        mode = self.modeBox.currentData()

        if mode is not None:
            self.revBtnLabel.setVisible(mode.uses_local_reverse)
            self.revBtnBox.setVisible(mode.uses_local_reverse)
            self.csPinLabel.setVisible(mode.uses_spi)
            self.csPinBox.setVisible(mode.uses_spi)
 
    def apply(self):
        self.send_value("shifter","mode",self.modeBox.currentData().index)
        self.send_value("shifter","xchan",self.xChannel.value())
        self.send_value("shifter","ychan",self.yChannel.value())
        self.send_value("shifter","x12",self.x12.value())
        self.send_value("shifter","x56",self.x56.value())
        self.send_value("shifter","y135",self.y135.value())
        self.send_value("shifter","y246",self.y246.value())
        self.send_value("shifter","revbtn",self.revBtnBox.value())
        self.send_value("shifter","cspin",self.csPinBox.value())

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
        self.get_value_async("shifter","vals",updatePosition,0,conversion=str)
        self.get_value_async("shifter","gear",updateGear,0,conversion=str)  

    def readValues(self):
        self.modeBox.clear()
        def modecb(mode):
            modes = mode.split("\n")
            modes = [m.split(":") for m in modes if m]
            for m in modes:
                index, uses_spi, uses_local_reverse = m[1].split(',')
                self.modeBox.addItem(m[0], ShifterButtonsConf.Mode(int(index), m[0], uses_spi == "1", uses_local_reverse == "1"))
            self.get_value_async("shifter","mode",self.modeBox.setCurrentIndex,0,conversion=int)
        self.get_value_async("shifter","mode",modecb,0,conversion=str,typechar = '!')
        self.get_value_async("shifter","xchan",self.xChannel.setValue,0,conversion=int)
        self.get_value_async("shifter","ychan",self.yChannel.setValue,0,conversion=int)

        self.get_value_async("shifter","x12",self.x12.setValue,0,conversion=int)
        self.get_value_async("shifter","x56",self.x56.setValue,0,conversion=int)
        self.get_value_async("shifter","y135",self.y135.setValue,0,conversion=int)
        self.get_value_async("shifter","y246",self.y246.setValue,0,conversion=int)

        self.get_value_async("shifter","revbtn",self.revBtnBox.setValue,0,conversion=int)
        self.get_value_async("shifter","cspin",self.csPinBox.setValue,0,conversion=int)

        self.readXYPosition()


class CANButtonsConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)


    def initUI(self):
        vbox = QVBoxLayout()
        self.polBox = QCheckBox("Invert")
        vbox.addWidget(self.polBox)
        self.polBox.stateChanged.connect(self.amountChanged)

        self.numBtnBox = QSpinBox()
        self.numBtnBox.setMinimum(1)
        self.numBtnBox.setMaximum(64)
        vbox.addWidget(QLabel("Number of buttons"))
        vbox.addWidget(self.numBtnBox)
        self.numBtnBox.valueChanged.connect(self.amountChanged)

        self.canIdBox = QSpinBox()
        self.canIdBox.setMinimum(1)
        self.canIdBox.setMaximum(0x7ff)
        vbox.addWidget(QLabel("CAN frame ID"))
        vbox.addWidget(self.canIdBox)
        self.canIdBox.valueChanged.connect(self.amountChanged)

        self.infoLabel = QLabel("")
        vbox.addWidget(self.infoLabel)
        self.cansettingsbutton = QPushButton("CAN settings")
        self.canOptions = portconf_ui.CanOptionsDialog(0,"CAN",self.main)
        self.cansettingsbutton.clicked.connect(self.canOptions.exec)
        vbox.addWidget(self.cansettingsbutton)
        
        self.setLayout(vbox)

    def amountChanged(self,_):
        amount = self.numBtnBox.value()
        text = ""
        text += f"ID {self.canIdBox.value()}:\n"
        polchar = "0" if self.polBox.isChecked() else "1"
        for value in range(64):
            if value < amount:
                text += polchar
            else:
                text += "x"
            if value < 63:
                if (value+1) % 8 == 0:
                    text += "|"
                if (value+1) % 32 == 0:
                    text += "\n"
                



        self.infoLabel.setText(text)

    def onclose(self):
        self.remove_callbacks()

    def apply(self):
        self.send_value("canbtn","canid",self.canIdBox.value())
        self.send_value("canbtn","btnnum",self.numBtnBox.value())
        self.send_value("canbtn","invert",(1 if self.polBox.isChecked() else 0))
    
    def readValues(self):
        self.get_value_async("canbtn","btnnum",self.numBtnBox.setValue,0,conversion=int)
        self.get_value_async("canbtn","invert",self.polBox.setChecked,0,conversion=int)
        self.get_value_async("canbtn","canid",self.canIdBox.setValue,0,conversion=int)
 
class PCFButtonsConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)


    def initUI(self):
        vbox = QVBoxLayout()
        self.polBox = QCheckBox("Invert")
        vbox.addWidget(self.polBox)
        self.fastBox = QCheckBox("400kHz fast mode")
        vbox.addWidget(self.fastBox)
        vbox.addWidget(QLabel("Requires num/8 PCF8574 w. increasing addresses.\nNumber of buttons:"))
        self.numBtnBox = QSpinBox()
        self.numBtnBox.setMinimum(1)
        self.numBtnBox.setMaximum(64)
        vbox.addWidget(self.numBtnBox)
        
        self.setLayout(vbox)

    def onclose(self):
        self.remove_callbacks()

    def apply(self):

        self.send_value("pcfbtn","btnnum",self.numBtnBox.value())
        self.send_value("pcfbtn","invert",(1 if self.polBox.isChecked() else 0))
        self.send_value("i2c","speed",(1 if self.fastBox.isChecked() else 0))
    
    def readValues(self):
        self.get_value_async("pcfbtn","btnnum",self.numBtnBox.setValue,0,conversion=int)
        self.get_value_async("pcfbtn","invert",self.polBox.setChecked,0,conversion=int)
        self.get_value_async("i2c","speed",self.fastBox.setChecked,0,conversion=int)
 