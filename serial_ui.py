from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtSerialPort import QSerialPort,QSerialPortInfo 
from PyQt5.QtCore import QIODevice,pyqtSignal
from PyQt5 import uic
from helper import res_path
import main
class SerialChooser(QWidget):
    connected = pyqtSignal(bool)
    port = None
    def __init__(self,serial, parent : main.MainUi=None):
        QWidget.__init__(self, parent)
        uic.loadUi(res_path('serialchooser.ui'), self)
        self.serial = serial
        self.main = parent #type: main.MainUi
        self.pushButton_refresh.clicked.connect(self.getPorts)
        self.pushButton_connect.clicked.connect(self.serialConnect)
        self.comboBox_port.currentIndexChanged.connect(self.selectPort)
        self.pushButton_send.clicked.connect(self.sendLine)
        self.lineEdit_cmd.returnPressed.connect(self.sendLine)
        
        self.getPorts()

        self.ports = []
        self.update()

    def serialLog(self,txt):
        self.serialLogBox.append(txt)

    def sendLine(self):
        cmd = self.lineEdit_cmd.text()+"\n"
        self.serialLog(cmd)
        self.serial.write(bytes(cmd,"utf-8"))

    def update(self):
        if(self.serial.isOpen()):
            self.pushButton_connect.setText("Disconnect")
            self.comboBox_port.setEnabled(False)
            self.pushButton_refresh.setEnabled(False)
            self.pushButton_send.setEnabled(True)
            self.lineEdit_cmd.setEnabled(True)
            self.connected.emit(True)
        else:
            self.pushButton_connect.setText("Connect")
            self.comboBox_port.setEnabled(True)
            self.pushButton_refresh.setEnabled(True)
            self.pushButton_send.setEnabled(False)
            self.lineEdit_cmd.setEnabled(False)
            self.connected.emit(False)


    def serialConnect(self):
        self.port = self.ports[self.comboBox_port.currentIndex()]
           
        if(not self.serial.isOpen()):
            self.main.log("Connecting...")
            self.serial.setPort(self.port)
            self.serial.open(QIODevice.ReadWrite)
        else:
            self.serial.close()
            
        self.update()
        
        
    def selectPort(self,id):
        self.port = self.ports[self.comboBox_port.currentIndex()]
   
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
        self.port = self.ports[self.comboBox_port.currentIndex()]