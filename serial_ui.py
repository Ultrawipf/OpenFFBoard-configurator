from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtSerialPort import QSerialPort,QSerialPortInfo 
from PyQt5.QtCore import QIODevice,pyqtSignal
import main
from base_ui import WidgetUI
from helper import classlistToIds
from PyQt5.QtWidgets import QMessageBox

class SerialChooser(WidgetUI):
    connected = pyqtSignal(bool)
    classes = []
    classIds = {}
    port = None
    mainID = None
    def __init__(self,serial, main):
        WidgetUI.__init__(self, main,'serialchooser.ui')
        
        self.serial = serial
        self.pushButton_refresh.clicked.connect(self.getPorts)
        self.pushButton_connect.clicked.connect(self.serialConnect)
        self.comboBox_port.currentIndexChanged.connect(self.selectPort)
        self.pushButton_send.clicked.connect(self.sendLine)
        self.lineEdit_cmd.returnPressed.connect(self.sendLine)
        self.pushButton_ok.clicked.connect(self.mainBtn)
        
        self.getPorts()

        self.ports = []
        self.update()

    def serialLog(self,txt):
        if(type(txt) == list):
            txt = "\n".join(txt)
        else:
            txt = str(txt)
        self.serialLogBox.append(txt)


    def sendLine(self):
        cmd = self.lineEdit_cmd.text()+"\n"
        self.serialLog(cmd)
        self.main.comms.serialGetAsync(cmd,self.serialLog)

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


    def serialConnect(self):
        self.selectPort(self.comboBox_port.currentIndex())
           
        if(not self.serial.isOpen() and self.port != None):
            self.main.log("Connecting...")
            self.serial.setPort(self.port)
            self.serial.open(QIODevice.ReadWrite)
        else:
            self.serial.close()
            
        self.update()
        
        
    def selectPort(self,id):
        if(id != -1):
            self.port = self.ports[id]
        else:
            self.port = None
   
    def getPorts(self):
        oldport = self.port.portName() if self.port else None
        
        self.ports = QSerialPortInfo().availablePorts()
        self.comboBox_port.clear()
        for port in self.ports:
            self.comboBox_port.addItem(port.portName() + " : " + port.description())
        self.update()
        plist = [p.portName() for p in self.ports]
        if oldport in plist:
            self.comboBox_port.setCurrentIndex(plist.index(oldport))
        self.selectPort(self.comboBox_port.currentIndex())


    def getMainClasses(self):
        def updateMains(dat):
            self.comboBox_main.clear()
            self.classIds,self.classes = classlistToIds(dat)
            
            if(self.mainID == None):
                #self.main.resetPort()
                self.groupBox_system.setEnabled(False)
                return
            self.groupBox_system.setEnabled(True)
            for c in self.classes:
                self.comboBox_main.addItem(c[1])
            self.comboBox_main.setCurrentIndex(self.classIds[self.mainID][0])
            self.main.log("Detected mode: "+self.comboBox_main.currentText())
            self.main.updateTabs()

        def f(i):
            self.mainID = i
        self.main.comms.serialGetAsync("id?",f,int)
        self.main.comms.serialGetAsync("lsmain",updateMains)

    def mainBtn(self):
        id = self.classes[self.comboBox_main.currentIndex()][0]
        self.main.comms.serialWrite("main="+str(id)+"\n")
        self.main.reconnect()
        msg = QMessageBox(QMessageBox.Information,"Main class changed","Chip is rebooting. Please reconnect.")
        msg.exec_()