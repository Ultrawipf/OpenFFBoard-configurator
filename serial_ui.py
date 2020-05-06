from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtSerialPort import QSerialPort,QSerialPortInfo 
from PyQt5.QtCore import QIODevice,pyqtSignal
import main
from base_ui import WidgetUI

class SerialChooser(WidgetUI):
    connected = pyqtSignal(bool)
    port = None
    def __init__(self,serial, main):
        WidgetUI.__init__(self, main,'serialchooser.ui')
        
        self.serial = serial
        self.pushButton_refresh.clicked.connect(self.getPorts)
        self.pushButton_connect.clicked.connect(self.serialConnect)
        self.comboBox_port.currentIndexChanged.connect(self.selectPort)
        self.pushButton_send.clicked.connect(self.sendLine)
        self.lineEdit_cmd.returnPressed.connect(self.sendLine)
        self.serial.readyRead.connect(self.serialReceive)
        self.getPorts()

        self.ports = []
        self.update()

    def serialLog(self,txt):
        self.serialLogBox.append(txt)

    def setLog(self,enabled):
        try:
            if(enabled):
                self.serial.readyRead.connect(self.serialReceive)
            else:
                self.serial.readyRead.disconnect(self.serialReceive)
        except:
            pass

    def serialReceive(self):
        data = self.serial.readAll()
        text = data.data().decode("utf-8")
        self.lastSerial = text
        self.serialLog(text)

    def sendLine(self):
        
        cmd = self.lineEdit_cmd.text()+"\n"
        self.serialLog(cmd)
        self.serial.write(bytes(cmd,"utf-8"))

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
        else:
            self.pushButton_connect.setText("Connect")
            self.comboBox_port.setEnabled(True)
            self.pushButton_refresh.setEnabled(True)
            self.pushButton_send.setEnabled(False)
            self.lineEdit_cmd.setEnabled(False)
            self.connected.emit(False)


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