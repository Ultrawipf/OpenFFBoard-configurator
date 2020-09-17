from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI

class TMC4671Ui(WidgetUI):

    amp_gain = 60
    shunt_ohm = 0.0015
    
    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'tmc4671_ui.ui')
        #QWidget.__init__(self, parent)
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
    
        self.pushButton_align.clicked.connect(self.alignEnc)
        self.initUi()
        

        #self.spinBox_fluxoffset.valueChanged.connect(lambda v : self.main.comms.serialWrite("fluxoffset="+str(v)+";"))

        self.main.setSaveBtn(True)
        
        self.timer.timeout.connect(self.updateTimer)

    def __del__(self):
        pass

    def showEvent(self,event):
        self.timer.start(50)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()
        
    def updateCurrent(self,current):
        try:
            current = float(current)
            v = (2.5/0x7fff) * current
            amps = round((v / self.amp_gain) / self.shunt_ohm,3)
            self.label_Current.setText(str(amps)+"A")

            self.progressBar_power.setValue(current)

        except Exception as e:
            self.main.log("TMC update error: " + str(e)) 

    def updateTimer(self):
        self.main.comms.serialGetAsync("acttorque",self.updateCurrent)
        
    

    def submitMotor(self):
        mtype = self.comboBox_mtype.currentIndex()
        self.main.comms.serialWrite("mtype="+str(mtype))

        poles = self.spinBox_poles.value()
        self.main.comms.serialWrite("poles="+str(poles))

        self.main.comms.serialWrite("cprtmc="+str(self.spinBox_cpr.value()))

        enc = self.comboBox_enc.currentIndex()
        self.main.comms.serialWrite("encsrc="+str(enc))
        
    def submitPid(self):
        # PIDs
        seq = 1 if self.checkBox_advancedpid.isChecked() else 0
        self.main.comms.serialWrite("seqpi="+str(seq))

        tp = self.spinBox_tp.value()
        self.main.comms.serialWrite("torqueP="+str(tp))

        ti = self.spinBox_ti.value()
        self.main.comms.serialWrite("torqueI="+str(ti))

        fp = self.spinBox_fp.value()
        self.main.comms.serialWrite("fluxP="+str(fp))

        fi = self.spinBox_fi.value()
        self.main.comms.serialWrite("fluxI="+str(fi))
        


    def initUi(self):
        try:
            # Fill encoder source types
            self.comboBox_enc.clear()
           
            def encs(encsrcs):
                for s in encsrcs.split(","):
                    e = s.split("=")
                    self.comboBox_enc.addItem(e[0],e[1])
            self.main.comms.serialGetAsync("encsrc!",encs)

            self.getMotor()
            self.getPids()

            self.spinBox_fluxoffset.valueChanged.connect(lambda v : self.main.comms.serialWrite("fluxoffset="+str(v)+";"))
            self.pushButton_submitmotor.clicked.connect(self.submitMotor)
            self.pushButton_submitpid.clicked.connect(self.submitPid)
        except Exception as e:
            self.main.log("Error initializing TMC tab. Please reconnect: " + str(e))
            return False
        return True

    def alignEnc(self):
        def f(res):
            if(res):
                msg = QMessageBox(QMessageBox.Information,"Encoder align",res)
                msg.exec_()
        res = self.main.comms.serialGetAsync("encalign",f)
        

    def getMotor(self):
        commands=["mtype?","poles?","encsrc?","cprtmc?"]
        callbacks = [self.comboBox_mtype.setCurrentIndex,
        self.spinBox_poles.setValue,
        self.comboBox_enc.setCurrentIndex,
        self.spinBox_cpr.setValue]
        self.main.comms.serialGetAsync(commands,callbacks,convert=int)
                

    def getPids(self):
        callbacks = [self.spinBox_tp.setValue,
        self.spinBox_ti.setValue,
        self.spinBox_fp.setValue,
        self.spinBox_fi.setValue,
        self.spinBox_fluxoffset.setValue,
        self.checkBox_advancedpid.setChecked]

        commands = ["torqueP?","torqueI?","fluxP?","fluxI?","fluxoffset?","seqpi?"]
        
        self.main.comms.serialGetAsync(commands,callbacks,convert=int)

