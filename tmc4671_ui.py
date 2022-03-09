from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QGroupBox,QComboBox,QLabel
from helper import res_path,classlistToIds
from PyQt6.QtCore import QTime, QTimer
from PyQt6.QtCore import Qt,QMargins
from PyQt6.QtGui import QColor
import main
from base_ui import WidgetUI
from optionsdialog import OptionsDialog,OptionsDialogGroupBox

from PyQt6.QtCharts import QChart,QChartView,QLineSeries,QValueAxis
from base_ui import CommunicationHandler

ext_notice = """External encoder forwards the encoder
selection of the Axis (if available).
Please select the encoder there."""

hall_notice = """Using hall sensors as the main position
source is not recommended"""

class TMC4671Ui(WidgetUI,CommunicationHandler):

    states = ["uninitialized","waitPower","Shutdown","Running","EncoderInit","EncoderFinished","HardError","OverTemp","IndexSearch","FullCalibration"]

    max_datapoints = 10000
    max_datapointsVisibleTime = 30
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

   
        # Chart setup
        self.chart = QChart()
        self.chart.setBackgroundRoundness(5)
        self.chart.setMargins(QMargins(0,0,0,0))
        self.chartXaxis = QValueAxis()
        self.chart.addAxis(self.chartXaxis,Qt.AlignmentFlag.AlignBottom)

        self.chartYaxis_Amps = QValueAxis()
        self.chartYaxis_Temps = QValueAxis()

        
        self.chart.addAxis(self.chartYaxis_Amps,Qt.AlignmentFlag.AlignLeft)
        
        self.lines_Amps = QLineSeries()
        self.lines_Amps.setName("Torque A")

        self.chart.addSeries(self.lines_Amps)
        self.lines_Amps.setColor(QColor("cornflowerblue"))
        self.lines_Amps.attachAxis(self.chartYaxis_Amps)
        self.lines_Amps.attachAxis(self.chartXaxis)
        
        self.lines_Flux = QLineSeries()
        self.lines_Flux.setName("Flux A")
        self.lines_Flux.setOpacity(0.5)
        
        self.chart.addSeries(self.lines_Flux)
        self.lines_Flux.setColor(QColor("limegreen"))
        
        self.lines_Flux.attachAxis(self.chartYaxis_Amps)
        self.lines_Flux.attachAxis(self.chartXaxis)
        
        
        self.lines_Temps = QLineSeries()
        self.lines_Temps.setName("Temp °C")
        self.lines_Temps.setColor(QColor("orange"))
        self.lines_Temps.setOpacity(0.5)
        self.chart.addAxis(self.chartYaxis_Temps,Qt.AlignmentFlag.AlignRight)
        self.chart.addSeries(self.lines_Temps)
        self.lines_Temps.attachAxis(self.chartYaxis_Temps)
        self.lines_Temps.attachAxis(self.chartXaxis)
        self.chartYaxis_Temps.setMax(100)

        self.chartXaxis.setMax(10)
        self.chartYaxis_Amps.setMax(20)
        self.graphWidget_Amps.setRubberBand(QChartView.RubberBand.VerticalRubberBand)
        self.graphWidget_Amps.setChart(self.chart) # Set the chart widget
 

        self.checkBox_advancedpid.stateChanged.connect(self.advancedPidChanged)
        self.lastPrecP = self.checkBox_P_Precision.isChecked()
        self.lastPrecI = self.checkBox_I_Precision.isChecked()
        self.buttonGroup_precision.buttonToggled.connect(self.changePrecision)

        self.pushButton_hwversion.clicked.connect(self.showVersionSelectorPopup)
        self.comboBox_mtype.currentIndexChanged.connect(self.motorselChanged)
        self.motor_type_to_index = {}
        self.comboBox_enc.currentIndexChanged.connect(self.encselChanged)
        self.encoder_type_to_index = {}

        self.checkBox_abnpol.stateChanged.connect(self.abnpolClicked)

        self.pushButton_calibrate.clicked.connect(lambda : self.sendCommand("tmc","calibrate",self.axis))

        # Callbacks
        self.registerCallback("tmc","temp",self.updateTemp,self.axis,int)
        self.registerCallback("sys","vint",self.vintCb,0,int)
        self.registerCallback("sys","vext",self.vextCb,0,int)
        self.registerCallback("tmc","acttrq",self.updateCurrent,self.axis,str)

        self.registerCallback("tmc","pidPrec",self.precisionCb,self.axis,int)
        self.registerCallback("tmc","torqueP",self.spinBox_tp.setValue,self.axis,int)
        self.registerCallback("tmc","torqueI",self.spinBox_ti.setValue,self.axis,int)
        self.registerCallback("tmc","fluxP",self.spinBox_fp.setValue,self.axis,int)
        self.registerCallback("tmc","fluxI",self.spinBox_fi.setValue,self.axis,int)
        self.registerCallback("tmc","fluxoffset",self.spinBox_fluxoffset.setValue,self.axis,int)
        self.registerCallback("tmc","seqpi",self.checkBox_advancedpid.setChecked,self.axis,int)

        self.registerCallback("tmc","tmctype",self.tmcChipTypeCB,self.axis,str,typechar='?')
        self.registerCallback("tmc","state",self.stateCb,self.axis,str,typechar='?')

        self.registerCallback("tmc","mtype",lambda x : self.comboBox_mtype.setCurrentIndex(self.motor_type_to_index.get(x,0)),self.axis,int)
        self.registerCallback("tmc","poles",self.spinBox_poles.setValue,self.axis,int)
        self.registerCallback("tmc","encsrc",lambda x : self.comboBox_enc.setCurrentIndex(self.encoder_type_to_index.get(x,0)),self.axis,int)
        self.registerCallback("tmc","cpr",self.spinBox_cpr.setValue,self.axis,int)

        self.registerCallback("tmc","iScale",self.setCurrentScaler,self.axis,float)

        self.registerCallback("tmc","encsrc",self.encsCb,self.axis,str,typechar='!')
        self.registerCallback("tmc","mtype",self.motsCb,self.axis,str,typechar='!')
        self.registerCallback("tmc","tmcHwType",self.hwVersionsCb,self.axis,str,typechar='!')
        self.registerCallback("tmc","tmcHwType",self.hwtcb,self.axis,int,typechar='?')
        self.registerCallback("tmc","abnindex",self.checkBox_abnIndex.setChecked,self.axis,int,typechar='?')
        self.registerCallback("tmc","abnpol",self.checkBox_abnpol.setChecked,self.axis,int,typechar='?')
        self.registerCallback("tmc","combineEncoder",self.checkBox_combineEncoders.setChecked,self.axis,int,typechar='?')
        self.registerCallback("tmc","invertForce",self.checkBox_invertForce.setChecked,self.axis,int,typechar='?')
        
        self.checkBox_combineEncoders.stateChanged.connect(self.extEncoderChanged)

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
        data = self.comboBox_mtype.currentData()
        if(data == 2 or data == 3): # stepper or bldc
            self.spinBox_poles.setEnabled(True)
        else:
            self.spinBox_poles.setEnabled(False)

    def extEncoderChanged(self,val):
        self.checkBox_invertForce.setEnabled(val)
        if not val:
            self.checkBox_invertForce.setChecked(False)
        else:
            self.sendCommand("tmc","invertForce",self.axis)


    def abnpolClicked(self,val):
        if val:
            self.checkBox_abnpol.setText("ABN polarity (HIGH)")
        else:
            self.checkBox_abnpol.setText("ABN polarity (LOW)")

    def encselChanged(self,val):
        data = self.comboBox_enc.currentData()
        self.checkBox_abnIndex.setVisible(data == 1) # abnIndex selectable if ABN encoder selected

        self.checkBox_abnpol.setVisible(data == 1)
        
        if(data == 5):
            self.label_encoder_notice.setText(ext_notice)
        if(data == 4):
            self.label_encoder_notice.setText(hall_notice)

        self.label_encoder_notice.setVisible(data == 5 or data == 4)
        #self.checkBox_abnpol.setEnabled(data == 1)

        self.spinBox_cpr.setVisible(data == 1 or data == 2 or data == 3)
        self.label_cpr.setVisible(data == 1 or data == 2 or data == 3)

        self.checkBox_combineEncoders.setVisible(data == 1 or data == 2 or data == 3 or data == 4)
        self.checkBox_invertForce.setVisible(data == 1 or data == 2 or data == 3 or data == 4)
        

    def updateCurrent(self,torqueflux):
        tflist = [(int(v)) for v in torqueflux.split(":")]
        
        flux = None
        torque = abs(tflist[0])
        if(len(tflist) == 2):
            flux = tflist[1]
        currents = complex(torque,flux)
        try:
            torque = abs(float(torque))
            
            if self.adc_to_amps != 0:
                amps = currents * self.adc_to_amps
                txt = f"Torque: {round(amps.real,3)}A"
                if(flux != None):
                    txt += f"\nFlux: {round(amps.imag,3)}A"
                    txt += f"\nTotal: {round(abs(amps),3)}A"
                self.label_Current.setText(txt)

            else:
                amps = 100*currents / 0x7fff # percent
                self.label_Current.setText(str(round(amps.real,3))+"%")
                
            self.progressBar_power.setValue(int(abs(currents)))

            self.chartLastX = self.startTime.msecsTo(QTime.currentTime()) / 1000
            self.lines_Amps.append(self.chartLastX,amps.real)
            self.lines_Flux.append(self.chartLastX,abs(amps.imag))
            
            if(self.lines_Amps.count() > self.max_datapoints):
                self.lines_Amps.remove(0)
                self.lines_Flux.remove(0)
            scalemax = max(abs(amps.imag),abs(amps.real))
            if(scalemax > self.chartYaxis_Amps.max()):
                self.chartYaxis_Amps.setMax(round(scalemax,2)) # increase range

            self.chartXaxis.setMax(self.chartLastX)
            self.chartXaxis.setMin(max(self.lines_Amps.at(0).x(),max(0,self.chartLastX-self.max_datapointsVisibleTime)))

        except Exception as e:
            self.main.log("TMC update error: " + str(e)) 

    def updateTemp(self,t):
        t = t/100.0
        if(t > 150 or t < -20):
            return
        self.label_Temp.setText(str(round(t,2)) + "°C")

        # Amps updates faster and gives the current timestamp
        self.lines_Temps.append(self.chartLastX+1,t)
        if(self.lines_Temps.count() > self.max_datapoints):
            self.lines_Temps.remove(0)

        
        if(t > self.chartYaxis_Temps.max()):
            self.chartYaxis_Temps.setMax(round(t)) # increase range
    
    def updateVolt(self):
        t = "Mot: {:2.2f}V".format(self.vint)
        t += "\nIn: {:2.2f}V".format(self.vext)
        self.label_volt.setText(t)

    def vintCb(self,v):
        self.vint = v/1000

    def vextCb(self,v):
        self.vext = v/1000
        self.updateVolt()

    def stateCb(self,state):
        intstate = int(state)
        if(len(self.states) > intstate):
            self.label_state.setText(self.states[intstate])
        else:
            self.label_state.setText(state)

    def updateTimer(self):
        self.sendCommand("tmc","acttrq",self.axis)
        
        
    def updateStatus(self):
        self.sendCommand("tmc","temp",self.axis)
        self.sendCommand("tmc","state",self.axis)
        self.sendCommands("sys",["vint","vext"])

    def submitMotor(self):
        mtype = self.comboBox_mtype.currentIndex()
        self.sendValue("tmc","mtype",val=mtype,instance=self.axis)

        poles = self.spinBox_poles.value()
        self.sendValue("tmc","poles",val=poles,instance=self.axis)

        self.sendValue("tmc","cpr",val=self.spinBox_cpr.value(),instance=self.axis)

        enc = self.comboBox_enc.currentIndex()
        self.sendValue("tmc","encsrc",val=enc,instance=self.axis)

        self.sendValue("tmc","abnindex",val = 1 if self.checkBox_abnIndex.isChecked() else 0,instance=self.axis)
        self.sendValue("tmc","abnpol",val = 1 if self.checkBox_abnpol.isChecked() else 0,instance=self.axis)

        self.sendValue("tmc","combineEncoder",val = 1 if self.checkBox_combineEncoders.isChecked() else 0,instance=self.axis)
        self.sendValue("tmc","invertForce",val = 1 if self.checkBox_invertForce.isChecked() else 0,instance=self.axis)
        
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
            QTimer.singleShot(100,self.showVersionSelectorPopup) # return this function but show popup with a tiny delay
             
        else:
            self.versionWarningShow = False

    def initUi(self):
        # clear graph
        self.startTime = QTime.currentTime()
        self.chartLastX = 0
        self.lines_Amps.clear()
        self.lines_Temps.clear()
        self.lines_Flux.clear()
        self.chartYaxis_Amps.setMin(0)
        self.chartYaxis_Temps.setMin(0)
        self.chartYaxis_Temps.setMax(90)
        try:
            # Fill encoder source types
            
            self.sendCommands("tmc",["mtype","encsrc","tmcHwType"],self.axis,'!')
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
        self.comboBox_enc.clear()
        self.encoder_type_to_index.clear()
        i = 0
        for s in encsrcs.split(","):
            e = s.split("=")
            self.comboBox_enc.addItem(e[0],int(e[1]))
            self.encoder_type_to_index[int(e[1])] = i
            i += 1

    def motsCb(self,mots):
        self.comboBox_mtype.clear()
        self.motor_type_to_index.clear()
        i = 0
        for s in mots.split(","):
            e = s.split("=")
            self.comboBox_mtype.addItem(e[0],int(e[1]))
            self.motor_type_to_index[int(e[1])] = i
            i += 1

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
        commands=["mtype","poles","encsrc","cpr","abnindex","abnpol","combineEncoder","invertForce"]
        self.sendCommands("tmc",commands,self.axis)


    def getPids(self):
        commands = ["pidPrec","torqueP","torqueI","fluxP","fluxI","fluxoffset","seqpi"]
        self.sendCommands("tmc",commands,self.axis)

        

    def setCurrentScaler(self,x):
        if(x != self.adc_to_amps):
            self.adc_to_amps = x
            if(x > 0):
                self.chartYaxis_Amps.setMax(round((0x7fff*x) / 10))

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
