from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QGroupBox
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QHBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox,QFormLayout
from PyQt6 import uic
import main
from PyQt6.QtCore import QObjectCleanupHandler
from helper import res_path,classlistToIds,updateListComboBox
from base_ui import CommunicationHandler

class EncoderOptions(QGroupBox):
    def __init__(self,main,id):
        QGroupBox.__init__(self,main)
        self.widget = None
        self.main = main
        self.setType(id)


    def setType(self,id):
        layout = QVBoxLayout()

        found = True
        self.setTitle("Encoder settings")
        if(id == 2): # local encoder
            self.widget = (LocalEncoderConf(self,self.main))
            self.setTitle("Local Encoder")
        elif(id == 1): # tmc
            layout.addWidget(QLabel("Configure in TMC tab"))
            found = False
        elif(id == 4): # MT SPI
            self.widget = (MtEncoderConf(self,self.main))
            self.setTitle("SPI Settings (port SPI3)")
        elif(id == 5): # BISS-C
            self.widget = (BissEncoderConf(self,self.main))
            self.setTitle("BISS Settings (port SPI3 - exclusif usage)")
        elif(id == 6): # SSI
            self.widget = (SsiEncoderConf(self,self.main))
            self.setTitle("SSI Settings (port SPI3 - exclusif usage)")
        else:
            layout.addWidget(QLabel("No settings"))

        layout.setContentsMargins(5,0,5,0)
        layout.setStretch(0,0)
        layout.addWidget(self.widget)
        self.setLayout(layout)
        
        if self.widget:            
            self.applyBtn = QPushButton("Apply")
            self.applyBtn.clicked.connect(self.widget.apply)
            footer = QHBoxLayout()
            footer.setContentsMargins(0,0,0,0)
            footer.addStretch(5)
            footer.addWidget(self.applyBtn)
            footer.addStretch(5)
            layout.addLayout(footer)
 

class EncoderOption(QWidget):
    def __init__(self,parent):
        super().__init__(parent)

    def apply(self):
        pass

    def hideEvent(self, a0) -> None:
        self.onclose()
        return super().hideEvent(a0)

    def showEvent(self, a0) -> None:
        self.onshown()
        return super().showEvent(a0)

    def onshown(self):
        pass

    def onclose(self):
        pass

class LocalEncoderConf(EncoderOption,CommunicationHandler):
    def __init__(self,parent,main):
        self.main = main
        EncoderOption.__init__(self,parent)
        CommunicationHandler.__init__(self)
        self.initUI()
        

    def initUI(self):
        layout = QFormLayout()
        layout.setContentsMargins(0,0,0,0)

        self.spinBox_cpr = QSpinBox()
        self.spinBox_cpr.setRange(0,0xffff)
        layout.addRow(QLabel("CPR = 4x PPR"))
        layout.addRow(QLabel("CPR:"),self.spinBox_cpr)

        self.checkBox_index = QCheckBox("Use index homing")
        layout.addRow(QLabel("Index:"),self.checkBox_index)

        self.setLayout(layout)

    def onshown(self):
        self.get_value_async("localenc","cpr",self.spinBox_cpr.setValue,0,int)
        self.get_value_async("localenc","index",self.checkBox_index.setChecked,0,int)

    def apply(self):
        val = self.spinBox_cpr.value()
        self.send_value("localenc","cpr",val=val)
        self.send_value("localenc","index",val = 1 if self.checkBox_index.isChecked() else 0)


class MtEncoderConf(EncoderOption,CommunicationHandler):
    def __init__(self,parent,main):
        self.main = main
        EncoderOption.__init__(self,parent)
        CommunicationHandler.__init__(self)
        self.initUI()
        

    def initUI(self):
        layout = QFormLayout()
        layout.setContentsMargins(0,0,0,0)

        self.spinBox_cs = QSpinBox()
        self.spinBox_cs.setRange(1,3)
        layout.addRow(QLabel("CS pin"),self.spinBox_cs)

        self.comboBox_mode = QComboBox()
        layout.addRow(QLabel("Type"),self.comboBox_mode)

        self.comboBox_spispeed = QComboBox()
        layout.addRow(QLabel("SPI speed"),self.comboBox_spispeed)

        self.setLayout(layout)

    def updateModes(self,reply):
        updateListComboBox(self.comboBox_mode,reply,entrySep='\n')

    def updateSpeeds(self,reply):
        def f(data):
            data = str(f"{float(data)/1000000:.5g}MHz")
            return data
        updateListComboBox(self.comboBox_spispeed,reply,entrySep='\n',labelconv=f)

    def onshown(self):
        self.get_value_async("mtenc","mode",self.updateModes,typechar='!')
        self.get_value_async("mtenc","speed",self.updateSpeeds,typechar='!')
        self.get_value_async("mtenc","cs",self.spinBox_cs.setValue,0,int)
        self.get_value_async("mtenc","mode",self.comboBox_mode.setCurrentIndex,0,int)
        self.get_value_async("mtenc","speed",self.comboBox_spispeed.setCurrentIndex,0,int)

    def apply(self):
        val = self.spinBox_cs.value()
        self.send_value("mtenc","cs",val=val)
        self.send_value("mtenc","mode",val=self.comboBox_mode.currentData())
        self.send_value("mtenc","speed",val=self.comboBox_spispeed.currentData())

class BissEncoderConf(EncoderOption,CommunicationHandler):
    def __init__(self,parent,main):
        self.main = main
        EncoderOption.__init__(self,parent)
        CommunicationHandler.__init__(self)
        self.initUI()
        

    def initUI(self):
        layout = QFormLayout()
        layout.setContentsMargins(0,0,0,0)

        self.checkBox_direction = QCheckBox("Reverse direction (default)")
        self.spinBox_bits = QSpinBox()
        self.spinBox_bits.setRange(1,32)
        layout.addRow(QLabel("Bits"),self.spinBox_bits)
        layout.addWidget(self.checkBox_direction)
        self.setLayout(layout)

    def onshown(self):
        self.get_value_async("bissenc","bits",self.spinBox_bits.setValue,0,int)
        self.get_value_async("bissenc","dir",self.checkBox_direction.setChecked,0,int)

    def apply(self):
        self.send_value("bissenc","bits",val=self.spinBox_bits.value())
        self.send_value("bissenc","dir",val= 1 if self.checkBox_direction.isChecked() else 0)

class SsiEncoderConf(EncoderOption,CommunicationHandler):
    def __init__(self,parent,main):
        self.main = main
        EncoderOption.__init__(self,parent)
        CommunicationHandler.__init__(self)
        self.initUI()
        

    def initUI(self):
        layout = QFormLayout()
        layout.setContentsMargins(0,0,0,0)

        self.spinBox_cs = QSpinBox()
        self.spinBox_cs.setRange(1,3)
        self.spinBox_bits = QSpinBox()
        self.spinBox_bits.setRange(1,32)
        self.comboBox_mode = QComboBox()
        self.comboBox_speed = QComboBox()

        layout.addRow(QLabel("Bits"),self.spinBox_bits)
        layout.addRow(QLabel("Mode"),self.comboBox_mode)
        layout.addRow(QLabel("SPI speed"),self.comboBox_speed)
        self.setLayout(layout)

    def updateSpeeds(self,reply):
        updateListComboBox(self.comboBox_speed,reply,entrySep='\n')

    def updateModes(self,reply):
        updateListComboBox(self.comboBox_mode,reply,entrySep='\n')

    def onshown(self):
        self.get_value_async("ssienc","bits",self.spinBox_bits.setValue,0,int)
        self.get_value_async("ssienc","speed",self.updateSpeeds,0,typechar="!")
        self.get_value_async("ssienc","mode",self.updateModes,0,typechar="!")
        self.get_value_async("ssienc","speed",self.comboBox_speed.setCurrentIndex,0,int,typechar="?")
        self.get_value_async("ssienc","mode",self.comboBox_mode.setCurrentIndex,0,int,typechar="?")
        

    def apply(self):
        self.send_value("ssienc","bits",val=self.spinBox_bits.value())
        self.send_value("ssienc","speed",val=self.comboBox_speed.currentData())
        self.send_value("ssienc","mode",val=self.comboBox_mode.currentData())
