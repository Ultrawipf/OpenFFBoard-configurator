import PyQt6
from PyQt6.QtGui import QColor
from PyQt6.QtSerialPort import QSerialPortInfo 
from PyQt6.QtCore import QIODevice,pyqtSignal,Qt
import main
from base_ui import WidgetUI,CommunicationHandler
from helper import classlistToIds,updateClassComboBox
from PyQt6.QtWidgets import QMessageBox

officialVidPids = [(0x1209,0xFFB0)] # Highlighted in serial selector

class SerialChooser(WidgetUI,CommunicationHandler):
    connected = pyqtSignal(bool)
    classes = []
    classIds = {}
    port = None
    mainID = None
    
    def __init__(self,serial, main):
        WidgetUI.__init__(self, main,'serialchooser.ui')
        CommunicationHandler.__init__(main.comms)
        self.serial = serial
        self.pushButton_refresh.clicked.connect(self.getPorts)
        self.pushButton_connect.clicked.connect(self.serialConnectButton)
        self.pushButton_send.clicked.connect(self.sendLine)
        self.lineEdit_cmd.returnPressed.connect(self.sendLine)
        self.pushButton_ok.clicked.connect(self.mainBtn)
        
        self.getPorts()

        self.ports = []
        self.update()

    def showEvent(self,event):
        self.main.comms.rawReply.connect(self.serialLog)

    # Tab is hidden
    def hideEvent(self,event):
        self.main.comms.rawReply.disconnect(self.serialLog)

    def serialLog(self,txt):
        if(type(txt) == list):
            txt = "\n".join(txt)
        else:
            txt = str(txt)
        self.serialLogBox.append(txt)


    def sendLine(self):
        cmd = self.lineEdit_cmd.text()+"\n"
        self.serialLog(">"+cmd)
        self.main.comms.serialWriteRaw(cmd)

    def write(self,data):
        self.serial.write(data)

    def update(self):
        if(self.serial.isOpen()):
            self.pushButton_connect.setText("Disconnect")
            self.comboBox_port.setEnabled(False)
            self.pushButton_refresh.setEnabled(False)
            self.pushButton_send.setEnabled(True)
            self.lineEdit_cmd.setEnabled(True)
            self.connected.emit(True)
            self.getMainClasses()
        else:
            self.pushButton_connect.setText("Connect")
            self.comboBox_port.setEnabled(True)
            self.pushButton_refresh.setEnabled(True)
            self.pushButton_send.setEnabled(False)
            self.lineEdit_cmd.setEnabled(False)
            self.connected.emit(False)
            self.groupBox_system.setEnabled(False)

    def serialConnectButton(self):
        if(not self.serial.isOpen() and self.port != None):
            self.serialConnect()
        else:
            self.serial.close()
            self.update()

    def serialConnect(self):
        self.selectPort(self.comboBox_port.currentIndex())
           
        if(not self.serial.isOpen() and self.port != None):
            self.main.log("Connecting...")
            self.serial.setPort(self.port)
            self.serial.setBaudRate(500000)
            self.serial.open(QIODevice.OpenModeFlag.ReadWrite)
            if(not self.serial.isOpen()):
                self.main.log("Can not open port")
            
        self.update()
        
        
    def selectPort(self,id):
        if(id != -1):
            self.port = self.ports[id]
        else:
            self.port = None
   
    def getPorts(self):
        oldport = self.port if self.port else None
        
        self.ports = QSerialPortInfo().availablePorts()
        self.comboBox_port.clear()
        selIdx = 0
        for i,port in enumerate(self.ports):
            supportedVidPid =  (port.vendorIdentifier() ,port.productIdentifier()) in officialVidPids
            name = port.portName() + " : " + port.description()
            if (supportedVidPid):
                name += " (FFBoard device)"
            else:
                name += " (Unsupported device)"
            self.comboBox_port.addItem(name)
            if(supportedVidPid):
                selIdx = i
                self.comboBox_port.setItemData(i,QColor("green"),Qt.ItemDataRole.ForegroundRole)
            else:
                self.comboBox_port.setItemData(i,QColor("red"),Qt.ItemDataRole.ForegroundRole)

        
        plist = [p.portName() for p in self.ports]
        if (oldport is not None) and ((oldport.vendorIdentifier() ,oldport.productIdentifier()) in officialVidPids) and (oldport.portName() in plist):
            self.comboBox_port.setCurrentIndex(plist.index(oldport.portName()))
        else:
            self.comboBox_port.setCurrentIndex(selIdx) # preselect found entry
        self.selectPort(self.comboBox_port.currentIndex())
        self.update()

    def updateMains(self,dat):
        self.comboBox_main.clear()
        self.classIds,self.classes = classlistToIds(dat)
        
        if(self.mainID == None):
            #self.main.resetPort()
            self.groupBox_system.setEnabled(False)
            return
        self.groupBox_system.setEnabled(True)

        updateClassComboBox(self.comboBox_main,self.classIds,self.classes,self.mainID)

        self.main.log("Detected mode: "+self.comboBox_main.currentText())
        self.main.updateTabs()

    def getMainClasses(self):
    
        def f(i):
            self.mainID = i
        self.getValueAsync("main","id",f,conversion=int,delete=True)
        self.getValueAsync("sys","lsmain",self.updateMains,delete=True)

    def mainBtn(self):
        id = self.classes[self.comboBox_main.currentIndex()][0]
        self.sendValue("sys","main",id)
        self.main.reconnect()
        msg = QMessageBox(QMessageBox.Icon.Information,"Main class changed","Chip is rebooting. Please reconnect.")
        msg.exec()