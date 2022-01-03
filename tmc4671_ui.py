from PyQt6.QtWidgets import QLabel, QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt6 import uic
from helper import res_path,classlistToIds
from PyQt6.QtCore import QTimer
import main
from base_ui import WidgetUI
from optionsdialog import OptionsDialog,OptionsDialogGroupBox
from PyQt6.QtWidgets import QWidget,QGroupBox,QComboBox
#for graph here, need pyqtgraph and numpy
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from base_ui import CommunicationHandler


class TMC4671Ui(WidgetUI,CommunicationHandler):

    max_datapoints = 1000
    adc_to_amps = 0#2.5 / (0x7fff * 60.0 * 0.0015)

    hwversion = 0
    hwversions = []
    versionWarningShow = True
    vext = 0
    vint = 0
    
    def __init__(self, main=None, unique=0):
        self.axis = 0
        WidgetUI.__init__(self, main,'tmc4671_ui.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi

        self.axis = unique

        self.timer = QTimer(self)
        self.timer_status = QTimer(self)
    
        self.pushButton_align.clicked.connect(self.alignEnc)
        #self.initUi()
        
        self.timer.timeout.connect(self.updateTimer)
        self.timer_status.timeout.connect(self.updateStatus)

        self.curveAmp = self.graphWidget_Amps.plot(pen='y')
        self.curveAmpData = [0]

        self.checkBox_advancedpid.stateChanged.connect(self.advancedPidChanged)
        self.lastPrecP = self.checkBox_P_Precision.isChecked()
        self.lastPrecI = self.checkBox_I_Precision.isChecked()
        self.buttonGroup_precision.buttonToggled.connect(self.changePrecision)

        self.pushButton_hwversion.clicked.connect(self.showVersionSelectorPopup)

        self.comboBox_mtype.currentIndexChanged.connect(self.motorselChanged)

        # Callbacks
        self.registerCallback("tmc","temp",self.updateTemp,self.axis,int)
        self.registerCallback("sys","vint",self.vintCb,0,int)
        self.registerCallback("sys","vext",self.vextCb,0,int)
        self.registerCallback("tmc","acttrq",self.updateCurrent,self.axis,int)

        self.registerCallback("tmc","pidPrec",self.precisionCb,self.axis,int)
        self.registerCallback("tmc","torqueP",self.spinBox_tp.setValue,self.axis,int)
        self.registerCallback("tmc","torqueI",self.spinBox_ti.setValue,self.axis,int)
        self.registerCallback("tmc","fluxP",self.spinBox_fp.setValue,self.axis,int)
        self.registerCallback("tmc","fluxI",self.spinBox_fi.setValue,self.axis,int)
        self.registerCallback("tmc","fluxoffset",self.spinBox_fluxoffset.setValue,self.axis,int)
        self.registerCallback("tmc","seqpi",self.checkBox_advancedpid.setChecked,self.axis,int)

        self.registerCallback("tmc","tmctype",self.tmcChipTypeCB,self.axis,str,typechar='?')

        self.registerCallback("tmc","mtype",self.comboBox_mtype.setCurrentIndex,self.axis,int)
        self.registerCallback("tmc","poles",self.spinBox_poles.setValue,self.axis,int)
        self.registerCallback("tmc","encsrc",self.comboBox_enc.setCurrentIndex,self.axis,int)
        self.registerCallback("tmc","cpr",self.spinBox_cpr.setValue,self.axis,int)

        self.registerCallback("tmc","iScale",self.setCurrentScaler,self.axis,float)

        self.registerCallback("tmc","encsrc",self.encsCb,self.axis,str,typechar='!')
        self.registerCallback("tmc","tmcHwType",self.hwVersionsCb,self.axis,str,typechar='!')
        self.registerCallback("tmc","tmcHwType",self.hwtcb,self.axis,int,typechar='?')


    def showEvent(self,event):
        self.initUi()
        if self.isEnabled():
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
            if self.adc_to_amps != 0:
                amps = round(current * self.adc_to_amps,3)
                self.label_Current.setText(str(amps)+"A")
            else:
                amps = round(100*current / 0x7fff,3) # percent
                self.label_Current.setText(str(amps)+"%")

            self.progressBar_power.setValue(int(current))

            self.curveAmpData = self.curveAmpData[max(len(self.curveAmpData)-self.max_datapoints,0):]
            self.curveAmpData.append(amps)
            self.curveAmp.setData(self.curveAmpData)

        except Exception as e:
            self.main.log("TMC update error: " + str(e)) 

    def updateTemp(self,t):
        t = t/100.0
        if(t > 150 or t < -20):
            return
        self.label_Temp.setText(str(round(t,2)) + "°C")
    
    def updateVolt(self):
        t = "Mot: {:2.2f}V".format(self.vint)
        t += "\nIn: {:2.2f}V".format(self.vext)
        self.label_volt.setText(t)

    def vintCb(self,v):
        self.vint = v/1000

    def vextCb(self,v):
        self.vext = v/1000
        self.updateVolt()

    def updateTimer(self):
        self.sendCommand("tmc","acttrq",self.axis)
        
        
    def updateStatus(self):
        self.sendCommand("tmc","temp",self.axis)
        self.sendCommands("sys",["vint","vext"])

    def submitMotor(self):
        mtype = self.comboBox_mtype.currentIndex()
        self.sendValue("tmc","mtype",val=mtype,instance=self.axis)

        poles = self.spinBox_poles.value()
        self.sendValue("tmc","poles",val=poles,instance=self.axis)

        self.sendValue("tmc","cpr",val=self.spinBox_cpr.value(),instance=self.axis)

        enc = self.comboBox_enc.currentIndex()
        self.sendValue("tmc","encsrc",val=enc,instance=self.axis)
        
    def submitPid(self):
        # PIDs
        seq = 1 if self.checkBox_advancedpid.isChecked() else 0
        self.sendValue("tmc","seqpi",val=seq,instance=self.axis)

        tp = self.spinBox_tp.value()
        self.sendValue("tmc","torqueP",val=tp,instance=self.axis)

        ti = self.spinBox_ti.value()
        self.sendValue("tmc","torqueI",val=ti,instance=self.axis)

        fp = self.spinBox_fp.value()
        self.sendValue("tmc","fluxP",val=fp,instance=self.axis)

        fi = self.spinBox_fi.value()
        self.sendValue("tmc","fluxI",val=fi,instance=self.axis)

        prec = self.checkBox_I_Precision.isChecked() | (self.checkBox_P_Precision.isChecked() << 1)
        self.sendValue("tmc","pidPrec",val=prec,instance=self.axis)
        
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
        else:
            self.checkBox_P_Precision.setChecked(False)
            self.checkBox_I_Precision.setChecked(False)
   
    def showVersionSelectorPopup(self):
        selectorPopup = OptionsDialog(TMC_HW_Version_Selector("TMC Version",self,self.axis),self.main)
        selectorPopup.exec()
        self.sendCommand("tmc","tmcHwType",self.axis,'!')
        self.sendCommand("tmc","tmcHwType",self.axis,'?')
       
    def hwVersionsCb(self,v):
        entriesList = v.split("\n")
        entriesList = [m.split(":") for m in entriesList if m]
        self.hwversions = {int(entry[0]):entry[1] for entry in entriesList}
    def hwtcb(self,t):
        self.hwversion = int(t)
        
        self.label_hwversion.setText("HW: " + self.hwversions[self.hwversion])
        # change scaler
        self.sendCommand("tmc","iScale",self.axis) # request scale update
        if self.hwversion == 0 and self.versionWarningShow and len(self.hwversions) > 0:
            # no version set. ask user to select version
            self.versionWarningShow = False
            self.showVersionSelectorPopup()
            
        else:
            self.versionWarningShow = False

    def initUi(self):
        try:
            # Fill encoder source types
            self.comboBox_enc.clear()
            self.sendCommands("tmc",["encsrc","tmcHwType"],self.axis,'!')
            self.sendCommands("tmc",["tmctype","tmcHwType","tmcIscale"],self.axis)
            self.getMotor()
            self.getPids()

            self.spinBox_fluxoffset.valueChanged.connect(lambda v : self.sendValue("tmc","fluxoffset",v,instance=self.axis))
            self.pushButton_submitmotor.clicked.connect(self.submitMotor)
            self.pushButton_submitpid.clicked.connect(self.submitPid)
        except Exception as e:
            self.main.log("Error initializing TMC tab. Please reconnect: " + str(e))
            return False
        return True

    def tmcChipTypeCB(self,type : str):
        if not type.startswith("TMC"):
            self.main.log("Can not find TMC")
            self.groupBox_tmc.setTitle("Driver (not connected)")
            self.setEnabled(False)
            self.timer.stop()
            self.timer_status.stop()
        else:
            self.groupBox_tmc.setTitle(type)
            self.setEnabled(True)


    def encsCb(self,encsrcs):
        for s in encsrcs.split(","):
            e = s.split("=")
            self.comboBox_enc.addItem(e[0],e[1])

    def alignEnc(self):
        self.pushButton_align.setEnabled(False)
        def f(res):
            self.pushButton_align.setEnabled(True)
            if(res):
                msg = QMessageBox(QMessageBox.Icon.Information,"Encoder align",res)
                msg.exec()

        res = self.getValueAsync("tmc","encalign",f,self.axis,typechar='?')
        self.main.log("Started encoder alignment")
        

    def getMotor(self):
        commands=["mtype","poles","encsrc","cpr"]
        self.sendCommands("tmc",commands,self.axis)


    def getPids(self):
        commands = ["pidPrec","torqueP","torqueI","fluxP","fluxI","fluxoffset","seqpi"]
        self.sendCommands("tmc",commands,self.axis)

        

    def setCurrentScaler(self,x):
        if(x != self.adc_to_amps):
            self.curveAmpData.clear()
        self.adc_to_amps = x

class TMC_HW_Version_Selector(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main,instance):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)
        self.typeBox = QGroupBox("Hardware Version")
        self.typeBoxLayout = QVBoxLayout()
        self.typeBox.setLayout(self.typeBoxLayout)
        self.axis = instance

    def initUI(self):
        vbox = QVBoxLayout()
        self.infolabel = QLabel("Warning: Selecting the incorrect hardware version can lead to damage to the hardware or injury.\nSeveral calibration constants and safety features depend on the correct selection.")
        vbox.addWidget(self.infolabel)
        self.combobox = QComboBox()
        vbox.addWidget(self.combobox)
        self.setLayout(vbox)

    def onclose(self):
        self.removeCallbacks()


    def apply(self):
        self.sendValue("tmc","tmcHwType",self.combobox.currentIndex(),instance=self.axis)
    
    def typeCb(self,entries):
        #print("Reply",entries)
        entriesList = entries.split("\n")
        entriesList = [m.split(":") for m in entriesList if m]
        for m in entriesList:
            self.combobox.addItem(m[1],m[0])
        self.getValueAsync("tmc","tmcHwType",self.combobox.setCurrentIndex,self.axis,int)

    def readValues(self):
        self.getValueAsync("tmc","tmcHwType",self.typeCb,self.axis,str,typechar='!')
