from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QGroupBox
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QHBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox,QFormLayout
from PyQt6 import uic
import main
from PyQt6.QtCore import QObjectCleanupHandler
from helper import res_path,classlistToIds
from base_ui import CommunicationHandler

class EncoderOptions(QGroupBox):
    def __init__(self,main,id):
        super().__init__()
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
            self.setTitle("SPI Settings")
        elif(id == 5): # BISS-C
            self.widget = (BissEncoderConf(self,self.main))
            self.setTitle("BISS Settings")
        else:
            layout.addWidget(QLabel("No settings"))

        
        layout.setContentsMargins(0,0,0,0)
        if self.widget:
            layout.addWidget(self.widget)
            self.applyBtn = QPushButton("Apply")
            self.applyBtn.clicked.connect(self.widget.apply)
            footer = QHBoxLayout()
            footer.setContentsMargins(0,0,0,0)
            footer.addStretch(5)
            footer.addWidget(self.applyBtn)
            footer.addStretch(5)
            layout.addLayout(footer)
 
        self.setLayout(layout)

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
        layout.addWidget(QLabel("CPR = 4x PPR"))
        layout.addRow(QLabel("CPR"),self.spinBox_cpr)
        self.setLayout(layout)

    def onshown(self):
        self.get_value_async("localenc","cpr",self.spinBox_cpr.setValue,0,int)

    def apply(self):
        val = self.spinBox_cpr.value()
        self.send_value("localenc","cpr",val=val)


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
        layout.addWidget(QLabel("SPI3 extension port"))
        layout.addRow(QLabel("CS pin"),self.spinBox_cs)
        self.setLayout(layout)

    def onshown(self):
        self.get_value_async("mtenc","cs",self.spinBox_cs.setValue,0,int)

    def apply(self):
        val = self.spinBox_cs.value()
        self.send_value("mtenc","cs",val=val)

class BissEncoderConf(EncoderOption,CommunicationHandler):
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
        layout.addWidget(QLabel("SPI3 extension port"))
        layout.addRow(QLabel("Bits"),self.spinBox_bits)
        layout.addWidget(QLabel("Port is used exclusively! CS pins are not usable !"))
        self.setLayout(layout)

    def onshown(self):
        self.get_value_async("bissenc","bits",self.spinBox_bits.setValue,0,int)

    def apply(self):
        self.send_value("bissenc","bits",val=self.spinBox_bits.value())
