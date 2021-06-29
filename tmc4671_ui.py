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

    max_datapoints = 1000
    adc_to_amps = 2.5 / (0x7fff * 60.0 * 0.0015)

    axis = 'x'
    
    def __init__(self, main=None, unique='X'):
        WidgetUI.__init__(self, main,'tmc4671_ui.ui')
        self.main = main #type: main.MainUi

        self.axis = unique

        self.timer = QTimer(self)
        self.timer_status = QTimer(self)
    
        self.pushButton_align.clicked.connect(self.alignEnc)
        self.initUi()
        
        self.timer.timeout.connect(self.updateTimer)
        self.timer_status.timeout.connect(self.updateStatus)

        self.curveAmp = self.graphWidget_Amps.plot(pen='y')
        self.curveTemp = self.graphWidget_Amps.plot(pen='r')
        self.curveAmpData = [0]
        self.curveTempData = [0]

        self.checkBox_advancedpid.stateChanged.connect(self.advancedPidChanged)
        self.lastPrecP = self.checkBox_P_Precision.isChecked()
        self.lastPrecI = self.checkBox_I_Precision.isChecked()
        self.buttonGroup_precision.buttonToggled.connect(self.changePrecision)

        self.comboBox_mtype.currentIndexChanged.connect(self.motorselChanged)

    def __del__(self):
        pass

    def showEvent(self,event):
        self.initUi()
        self.timer.start(50)
        self.timer_status.start(250)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()
        self.timer_status.stop()
        
    def motorselChanged(self,val):
        if(val == 2 or val == 3): # stepper or bldc
            self.spinBox_poles.setEnabled(True)
        else:
            self.spinBox_poles.setEnabled(False)

    def updateCurrent(self,current):
   
        try:
            current = abs(float(current))
            amps = round(current * self.adc_to_amps,3)
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

        self.curveTempData = self.curveTempData[max(len(self.curveTempData) - self.max_datapoints, 0):]
        self.curveTempData.append(t*0.1) # 40°C to 4.0
        self.curveTemp.setData(self.curveTempData)
    
    def updateVolt(self,v):
        t = "Mot: {:2.2f}V".format(v[0]/1000)
        t += "\nIn: {:2.2f}V".format(v[1]/1000)
        self.label_volt.setText(t)

    def updateTimer(self):
        self.serialGetAsync("acttrq",self.updateCurrent)
        
    def updateStatus(self):
        self.serialGetAsync("tmctemp",self.updateTemp,float)
        self.main.comms.serialGetAsync(["vint","vext"],self.updateVolt,float)

    def submitMotor(self):
        mtype = self.comboBox_mtype.currentIndex()
        self.serialWrite("mtype="+str(mtype))

        poles = self.spinBox_poles.value()
        self.serialWrite("poles="+str(poles))

        self.serialWrite("cprtmc="+str(self.spinBox_cpr.value()))

        enc = self.comboBox_enc.currentIndex()
        self.serialWrite("encsrc="+str(enc))
        
    def submitPid(self):
        # PIDs
        seq = 1 if self.checkBox_advancedpid.isChecked() else 0
        self.serialWrite("seqpi="+str(seq))

        tp = self.spinBox_tp.value()
        self.serialWrite("torqueP="+str(tp))

        ti = self.spinBox_ti.value()
        self.serialWrite("torqueI="+str(ti))

        fp = self.spinBox_fp.value()
        self.serialWrite("fluxP="+str(fp))

        fi = self.spinBox_fi.value()
        self.serialWrite("fluxI="+str(fi))

        prec = self.checkBox_I_Precision.isChecked() | (self.checkBox_P_Precision.isChecked() << 1)
        self.serialWrite("pidPrec="+str(prec))
        
    def changePrecision(self,button,checked):
        rescale = (16 if checked else 1/16)
        if(button == self.checkBox_I_Precision):
            if(self.lastPrecI != checked):
                self.spinBox_ti.setValue(self.spinBox_ti.value() * rescale)
                self.spinBox_fi.setValue(self.spinBox_fi.value() * rescale)
        if(button == self.checkBox_P_Precision):
            if(self.lastPrecP != checked):
                self.spinBox_tp.setValue(self.spinBox_tp.value() * rescale)
                self.spinBox_fp.setValue(self.spinBox_fp.value() * rescale)

        self.lastPrecP = self.checkBox_P_Precision.isChecked()
        self.lastPrecI = self.checkBox_I_Precision.isChecked()

    def precisionCb(self,val):
        self.checkBox_I_Precision.setChecked(val & 0x1)
        self.checkBox_P_Precision.setChecked(val & 0x2)

    def advancedPidChanged(self,state):
        self.checkBox_P_Precision.setEnabled(state)
        self.checkBox_I_Precision.setEnabled(state)
        if(state):
            pass
            #self.serialGetAsync("pidPrec?",self.precisionCb,int) #update checkbox
        else:
            self.checkBox_P_Precision.setChecked(False)
            self.checkBox_I_Precision.setChecked(False)
   
    def initUi(self):
        try:
            # Fill encoder source types
            self.comboBox_enc.clear()
           
            def encs(encsrcs):
                for s in encsrcs.split(","):
                    e = s.split("=")
                    self.comboBox_enc.addItem(e[0],e[1])
            self.serialGetAsync("encsrc!",encs)
            self.serialGetAsync("tmctype",self.groupBox_tmc.setTitle)

            self.getMotor()
            self.getPids()
            self.serialGetAsync("tmcIscale?",self.setCurrentScaler,convert=float)

            self.spinBox_fluxoffset.valueChanged.connect(lambda v : self.serialWrite("fluxoffset="+str(v)+";"))
            self.pushButton_submitmotor.clicked.connect(self.submitMotor)
            self.pushButton_submitpid.clicked.connect(self.submitPid)
        except Exception as e:
            self.main.log("Error initializing TMC tab. Please reconnect: " + str(e))
            return False
        return True

    def alignEnc(self):
        self.pushButton_align.setEnabled(False)
        def f(res):
            self.pushButton_align.setEnabled(True)
            if(res):
                msg = QMessageBox(QMessageBox.Information,"Encoder align",res)
                msg.exec_()

        res = self.serialGetAsync("encalign",f)
        self.main.log("Started encoder alignment")
        

    def getMotor(self):
        commands=["mtype?","poles?","encsrc?","cprtmc?"]
        callbacks = [self.comboBox_mtype.setCurrentIndex,
        self.spinBox_poles.setValue,
        self.comboBox_enc.setCurrentIndex,
        self.spinBox_cpr.setValue]
        self.serialGetAsync(commands,callbacks,convert=int)
                

    def getPids(self):
        callbacks = [self.precisionCb,
        self.spinBox_tp.setValue,
        self.spinBox_ti.setValue,
        self.spinBox_fp.setValue,
        self.spinBox_fi.setValue,
        self.spinBox_fluxoffset.setValue,
        self.checkBox_advancedpid.setChecked]

        commands = ["pidPrec?","torqueP?","torqueI?","fluxP?","fluxI?","fluxoffset?","seqpi?"]
        self.serialGetAsync(commands,callbacks,convert=int)

    def setCurrentScaler(self,x):
        if(x):
            self.adc_to_amps = x


    def serialWrite(self,cmd):
        cmd = self.axis+"."+cmd
        self.main.comms.serialWrite(cmd)


    def serialGetAsync(self,cmds,callbacks,convert=None):
        if(type(cmds) == list):
            axis_cmds = list(map(lambda x: self.axis+"."+x, cmds)) # y.torqueP? etc
        else:
            axis_cmds = self.axis+"."+cmds
        self.main.comms.serialGetAsync(axis_cmds,callbacks,convert)

