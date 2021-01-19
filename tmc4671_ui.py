from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI

#for graph here, need pyqtgraph and numpy
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg


class TMC4671Ui(WidgetUI):

    amp_gain = 60
    shunt_ohm = 0.0015
    max_datapoints = 1000
    
    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'tmc4671_ui.ui')
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
        self.timer_status = QTimer(self)
    
        self.pushButton_align.clicked.connect(self.alignEnc)
        self.initUi()
        

        self.main.setSaveBtn(True)
        
        self.timer.timeout.connect(self.updateTimer)
        self.timer_status.timeout.connect(self.updateStatus)

        self.curveAmp = self.graphWidget_Amps.plot(pen='y')
        self.curveAmpData = [0]

    def __del__(self):
        pass

    def showEvent(self,event):
        self.timer.start(50)
        self.timer_status.start(250)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()
        self.timer_status.stop()
        
    def updateCurrent(self,current):
   
        try:
            current = float(abs(current))
            v = (2.5/0x7fff) * current
            amps = round((v / self.amp_gain) / self.shunt_ohm,3)
            self.label_Current.setText(str(amps)+"A")

            self.progressBar_power.setValue(current)

            self.curveAmpData = self.curveAmpData[max(len(self.curveAmpData)-self.max_datapoints,0):]
            self.curveAmpData.append(amps)
            self.curveAmp.setData(self.curveAmpData)

        except Exception as e:
            self.main.log("TMC update error: " + str(e)) 

    def updateTemp(self,t):
        if(t > 150 or t < -20):
            return
        self.label_Temp.setText(str(round(t,2)) + "°C")
    
    def updateVolt(self,v):
        t = "Mot: {:2.2f}V".format(v[0]/1000)
        t += "\nIn: {:2.2f}V".format(v[1]/1000)
        self.label_volt.setText(t)

    def updateTimer(self):
        self.main.comms.serialGetAsync("acttrq",self.updateCurrent)
        
    def updateStatus(self):
        self.main.comms.serialGetAsync("tmctemp",self.updateTemp,float)
        self.main.comms.serialGetAsync(["vint","vext"],self.updateVolt,float)

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

