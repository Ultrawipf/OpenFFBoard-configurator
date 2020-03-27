from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main

class TMC4671Ui(QWidget):
    
    phiE_ids = {3:("ABN",0),4:("HALL",1)}
    phiE_idx = [3,4]
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.main = parent #type: main.MainUi
        uic.loadUi(res_path('tmc4671_ui.ui'), self)

        self.pushButton_align.clicked.connect(self.alignEnc)
        self.initUi()

        self.spinBox_tp.valueChanged.connect(lambda v : self.main.serialWrite("torqueP="+str(v)+";"))
        self.spinBox_ti.valueChanged.connect(lambda v : self.main.serialWrite("torqueI="+str(v)+";"))
        self.spinBox_fp.valueChanged.connect(lambda v : self.main.serialWrite("fluxP="+str(v)+";"))
        self.spinBox_fi.valueChanged.connect(lambda v : self.main.serialWrite("fluxI="+str(v)+";"))
        self.spinBox_fluxoffset.valueChanged.connect(lambda v : self.main.serialWrite("fluxoffset="+str(v)+";"))

        self.pushButton_submitmotor.clicked.connect(self.submitMotor)
    def __del__(self):
        pass

    def submitMotor(self):
        cmd = ""
        mtype = self.comboBox_mtype.currentIndex()
        cmd+="mtype="+str(mtype)+";"

        poles = self.spinBox_poles.value()
        cmd+="poles="+str(poles)+";"

        phiE = self.phiE_idx[self.comboBox_phie.currentIndex()]
        cmd+="phiesrc="+str(phiE)+";"

        if(phiE == 3):
            cmd+="phiesrc="+str(self.spinBox_ppr.value())+";"

        self.main.serialWrite(cmd)

    def initUi(self):
        self.comboBox_phie.clear()
        for s in self.phiE_ids.values():
            self.comboBox_phie.addItem(s[0])

        self.getMotor()
        self.getPids()

    def alignEnc(self):
        res = self.main.serialGet("encalign\n",2000)
        if(res):
            msg = QMessageBox(QMessageBox.Information,"Encoder align",res)
            msg.exec_()

    def getMotor(self):
        res = self.main.serialGet("mtype?;poles?;phiesrc?;")
        mtype,poles,phiE = [int(s) for s in res.split("\n")]
        if(mtype):
            self.comboBox_mtype.setCurrentIndex((mtype))
        if(poles):
            self.spinBox_poles.setValue((poles))
        if(phiE):
            if(phiE not in self.phiE_ids):
                print("Communication error.")
                self.main.reconnect()
                return
            self.comboBox_phie.setCurrentIndex(self.phiE_ids[(phiE)][1])
            self.spinBox_ppr.setEnabled(phiE == 3)
            self.spinBox_ppr.setValue(int(self.main.serialGet("ppr?\n")))
                

    def getPids(self):
        pids = [int(s) for s in self.main.serialGet("torqueP?;torqueI?;fluxP?;fluxI?;fluxoffset?;").split("\n")]
        self.spinBox_tp.setValue(pids[0])
        self.spinBox_ti.setValue(pids[1])
        self.spinBox_fp.setValue(pids[2])
        self.spinBox_fi.setValue(pids[3])

        self.spinBox_fluxoffset.setValue(pids[4])
        
