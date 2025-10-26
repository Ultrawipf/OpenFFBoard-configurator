from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QGroupBox,QComboBox,QLabel,QApplication
from helper import res_path,classlistToIds,updateListComboBox
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

aenc_notice = """Enter CPR as the amount of phases per 
revolution (Single pole SinCos = 1 CPR)"""

class TMC4671Ui(WidgetUI,CommunicationHandler):

    STATES = ["uninitialized","waitPower","Shutdown","Running","EncoderInit","EncoderFinished","HardError","OverTemp","IndexSearch","FullCalibration","ExternalEncoderInit","PI Autotune"]

    def __init__(self, main=None, unique=0):
        WidgetUI.__init__(self, main,'tmc4671_ui.ui')
        CommunicationHandler.__init__(self)
        self.axis = 0
        self.init_done = False
        self.main = main #type: main.MainUi

        self.axis = unique

        self.cogging_data = [0] * 2880
        self.cogging_data_received = [False] * 2880
        self.max_datapoints = 10000
        self.max_datapointsVisibleTime = 30
        self.adc_to_amps = 0#2.5 / (0x7fff * 60.0 * 0.0015)

        self.hwversion = 0
        self.hwversions = []
        self.versionWarningShow = True
        self.vext = 0
        self.vint = 0

        self.startTime = QTime.currentTime()
        self.chartLastX = 0

        self.timer = QTimer(self)
        self.timer_status = QTimer(self)
    
        self.pushButton_align.clicked.connect(self.alignEnc)
        self.pushButton_autotunepid.clicked.connect(self.autotunePid)
        self.pushButton_cogging.clicked.connect(self.coggingDetection)
        self.pushButton_resetCoggingTable.clicked.connect(self.resetCoggingTable)
        self.pushButton_reloadCoggingTable.clicked.connect(self.reloadCoggingTable)
        self.tabWidget.currentChanged.connect(self.tabChanged)
        #self.initUi()
        
        self.timer.timeout.connect(self.updateTimer)
        self.timer_status.timeout.connect(self.updateStatus)

   
        # Chart setup
        self.chart = QChart()
        self.chart.setBackgroundRoundness(5)
        self.chart.setMargins(QMargins(0,0,0,0))
        self.chartXaxis = QValueAxis(self.chart)
        # use Application.instance().palette().dark().color() but with 50% opacity
        self.chartXaxis.setGridLineColor(QColor(QApplication.instance().palette().dark().color().red(),QApplication.instance().palette().dark().color().green(),QApplication.instance().palette().dark().color().blue(),128))
        

        self.chart.addAxis(self.chartXaxis,Qt.AlignmentFlag.AlignBottom)

        self.chartYaxis_Amps = QValueAxis(self.chart)
        self.chartYaxis_Temps = QValueAxis(self.chart)
        # use Application.instance().palette().dark().color() but with 25% opacity
        self.chartYaxis_Amps.setGridLineColor(QColor(QApplication.instance().palette().dark().color().red(),QApplication.instance().palette().dark().color().green(),QApplication.instance().palette().dark().color().blue(),64))
        self.chartYaxis_Temps.setGridLineColor(QColor(QApplication.instance().palette().dark().color().red(),QApplication.instance().palette().dark().color().green(),QApplication.instance().palette().dark().color().blue(),64))
        self.chart.setBackgroundBrush(QApplication.instance().palette().window())
        
        self.chart.addAxis(self.chartYaxis_Amps,Qt.AlignmentFlag.AlignLeft)
        
        self.lines_Amps = QLineSeries(self.chart)
        self.lines_Amps.setName("Torque A")
        self.lines_Amps.setUseOpenGL(True)

        self.chart.addSeries(self.lines_Amps)
        self.lines_Amps.setColor(QColor("cornflowerblue"))
        self.lines_Amps.attachAxis(self.chartYaxis_Amps)
        self.lines_Amps.attachAxis(self.chartXaxis)
        
        self.lines_Flux = QLineSeries(self.chart)
        self.lines_Flux.setName("Flux A")
        self.lines_Flux.setOpacity(0.5)
        self.lines_Flux.setUseOpenGL(True)
        
        self.chart.addSeries(self.lines_Flux)
        self.lines_Flux.setColor(QColor("limegreen"))

        self.lines_Flux.attachAxis(self.chartYaxis_Amps)
        self.lines_Flux.attachAxis(self.chartXaxis)
        
        self.lines_Temps = QLineSeries(self.chart)
        self.lines_Temps.setName("Temp °C")
        self.lines_Temps.setColor(QColor("orange"))
        self.lines_Temps.setOpacity(0.5)
        self.lines_Temps.setUseOpenGL(True)
        self.chart.addAxis(self.chartYaxis_Temps,Qt.AlignmentFlag.AlignRight)
        self.chart.addSeries(self.lines_Temps)
        self.lines_Temps.attachAxis(self.chartYaxis_Temps)
        self.lines_Temps.attachAxis(self.chartXaxis)
        self.chartYaxis_Temps.setMax(100)

        self.chartXaxis.setMax(10)
        self.chartYaxis_Amps.setMax(20)
        self.graphWidget_Amps.setRubberBand(QChartView.RubberBand.VerticalRubberBand)
        self.graphWidget_Amps.setChart(self.chart) # Set the chart widget

        # Set graph theme colors
        self.chart.legend().setLabelBrush(QApplication.instance().palette().text())
        for ax in self.chart.axes():
            ax.setLabelsBrush(QApplication.instance().palette().text())
 

        # Cogging Chart setup
        self.chart_cogging = QChart()
        self.chart_cogging.setBackgroundRoundness(5)
        self.chart_cogging.setMargins(QMargins(0,0,0,0))
        self.chart_cogging_Xaxis = QValueAxis(self.chart_cogging)
        self.chart_cogging_Xaxis.setGridLineColor(QColor(QApplication.instance().palette().dark().color().red(),QApplication.instance().palette().dark().color().green(),QApplication.instance().palette().dark().color().blue(),128))
        self.chart_cogging.addAxis(self.chart_cogging_Xaxis,Qt.AlignmentFlag.AlignBottom)

        self.chart_cogging_Yaxis = QValueAxis(self.chart_cogging)
        self.chart_cogging_Yaxis.setGridLineColor(QColor(QApplication.instance().palette().dark().color().red(),QApplication.instance().palette().dark().color().green(),QApplication.instance().palette().dark().color().blue(),64))
        self.chart_cogging.setBackgroundBrush(QApplication.instance().palette().window())
        
        self.chart_cogging.addAxis(self.chart_cogging_Yaxis,Qt.AlignmentFlag.AlignLeft)
        
        self.lines_cogging = QLineSeries(self.chart_cogging)
        self.lines_cogging.setName("Cogging")
        self.lines_cogging.setUseOpenGL(True)

        self.chart_cogging.addSeries(self.lines_cogging)
        self.lines_cogging.setColor(QColor("cornflowerblue"))
        self.lines_cogging.attachAxis(self.chart_cogging_Yaxis)
        self.lines_cogging.attachAxis(self.chart_cogging_Xaxis)

        self.chart_cogging_Xaxis.setMax(10)
        self.chart_cogging_Yaxis.setMax(20)
        self.graphWidget_Cogging.setRubberBand(QChartView.RubberBand.VerticalRubberBand)
        self.graphWidget_Cogging.setChart(self.chart_cogging)

        self.chart_cogging.legend().setLabelBrush(QApplication.instance().palette().text())
        for ax in self.chart_cogging.axes():
            ax.setLabelsBrush(QApplication.instance().palette().text())


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

        self.pushButton_calibrate.clicked.connect(lambda : self.send_command("tmc","calibrate",self.axis))
        self.checkBox_fluxdissipate.stateChanged.connect(lambda x : self.send_value("tmc","fluxbrake",val=1 if x else 0,instance=self.axis))

        # Callbacks
        self.register_callback("tmc","temp",self.updateTemp,self.axis,int)
        self.register_callback("sys","vint",self.vintCb,0,int)
        self.register_callback("sys","vext",self.vextCb,0,int)
        self.register_callback("tmc","acttrq",self.updateCurrent,self.axis,str)

        self.register_callback("tmc","pidPrec",self.precisionCb,self.axis,int)
        self.register_callback("tmc","torqueP",self.spinBox_tp.setValue,self.axis,int)
        self.register_callback("tmc","torqueI",self.spinBox_ti.setValue,self.axis,int)
        self.register_callback("tmc","fluxP",self.spinBox_fp.setValue,self.axis,int)
        self.register_callback("tmc","fluxI",self.spinBox_fi.setValue,self.axis,int)
        self.register_callback("tmc","fluxoffset",lambda x : self.doubleSpinBox_fluxoffset.setValue(x*self.adc_to_amps),self.axis,int)
        self.register_callback("tmc","seqpi",self.checkBox_advancedpid.setChecked,self.axis,int)

        self.register_callback("tmc","tmctype",self.tmcChipTypeCB,self.axis,str,typechar='?')
        self.register_callback("tmc","state",self.stateCb,self.axis,str,typechar='?')

        self.register_callback("tmc","mtype",lambda x : self.comboBox_mtype.setCurrentIndex(self.motor_type_to_index.get(x,0)),self.axis,int)
        self.register_callback("tmc","poles",self.spinBox_poles.setValue,self.axis,int)
        self.register_callback("tmc","encsrc",lambda x : self.comboBox_enc.setCurrentIndex(self.encoder_type_to_index.get(x,0)),self.axis,int)
        self.register_callback("tmc","cpr",self.spinBox_cpr.setValue,self.axis,int)

        self.register_callback("tmc","iScale",self.setCurrentScaler,self.axis,float)

        self.register_callback("tmc","encsrc",self.encsCb,self.axis,str,typechar='!')
        self.register_callback("tmc","mtype",self.motsCb,self.axis,str,typechar='!')
        self.register_callback("tmc","tmcHwType",self.hwVersionsCb,self.axis,str,typechar='!')
        self.register_callback("tmc","tmcHwType",self.hwtcb,self.axis,int,typechar='?')
        self.register_callback("tmc","abnindex",self.checkBox_abnIndex.setChecked,self.axis,int,typechar='?')
        self.register_callback("tmc","abnpol",self.checkBox_abnpol.setChecked,self.axis,int,typechar='?')
        self.register_callback("tmc","combineEncoder",self.checkBox_combineEncoders.setChecked,self.axis,int,typechar='?')
        self.register_callback("tmc","invertForce",self.checkBox_invertForce.setChecked,self.axis,int,typechar='?')
        self.register_callback("tmc","svpwm",self.checkBox_svpwm.setChecked,self.axis,int,typechar='?')
        self.register_callback("tmc","fluxbrake",self.checkBox_fluxdissipate.setChecked,self.axis,int,typechar='?')

        self.filter_type_to_index = {}
        self.register_callback("tmc","trqbq_mode",self.filtersCb,self.axis,str,typechar='!')
        self.register_callback("tmc","trqbq_mode",self.comboBox_torqueFilter.setCurrentIndex,self.axis,int)
        self.register_callback("tmc","trqbq_f",self.spinBox_torqueFilterFreq.setValue,self.axis,int)
    
        self.register_callback("tmc","coggingTable",self.updateCogging,self.axis,str)
        self.register_callback("tmc","calibrated",self.calibrated,instance=self.axis,conversion=int)
        self.register_callback("tmc","cogging",self.checkBox_cogging.setChecked,self.axis,int,typechar='?')
        
        self.checkBox_combineEncoders.stateChanged.connect(self.extEncoderChanged)


    def torqueFilterChanged(self,v):
        self.spinBox_torqueFilterFreq.setEnabled(v > 0)
        if v in self.filter_type_to_index:
            self.send_value("tmc","trqbq_mode",val=self.filter_type_to_index[v],instance=self.axis)



    # TODO do not send updates when window is moved. Blocks serial port receive on windows
    def showEvent(self,event):
        self.init_ui()
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
            self.doubleSpinBox_fluxoffset.setEnabled(True)
            self.checkBox_fluxdissipate.setEnabled(True)
            self.pushButton_autotunepid.setEnabled(True)
            self.pushButton_cogging.setEnabled(True)
        else:
            self.spinBox_poles.setEnabled(False)
            self.doubleSpinBox_fluxoffset.setEnabled(False)
            self.checkBox_fluxdissipate.setEnabled(False)
            self.pushButton_autotunepid.setEnabled(False)
            self.pushButton_cogging.setEnabled(False)

        if(data == 3):
            self.checkBox_svpwm.setEnabled(True)
        else:
            self.checkBox_svpwm.setEnabled(False)

    def extEncoderChanged(self,idx):
        val = self.comboBox_mtype.currentData()
        self.checkBox_invertForce.setEnabled(val)
        if not val:
            self.checkBox_invertForce.setChecked(False)
        else:
            self.send_command("tmc","invertForce",self.axis)


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
        if(data == 2 or data == 3):
            self.label_encoder_notice.setText(aenc_notice)


        self.label_encoder_notice.setVisible(data == 5 or data == 4 or data == 3 or data == 2) # Visible for ext, hall and aenc
        #self.checkBox_abnpol.setEnabled(data == 1)

        self.spinBox_cpr.setVisible(data == 1 or data == 2 or data == 3)
        self.label_cpr.setVisible(data == 1 or data == 2 or data == 3)

        self.checkBox_combineEncoders.setVisible(data == 1 or data == 2 or data == 3 or data == 4)
        self.checkBox_invertForce.setVisible(data == 1 or data == 2 or data == 3 or data == 4)
        self.checkBox_invertForce.setEnabled(self.checkBox_combineEncoders.isChecked())
        

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
                txt = f"Torque: {amps.real:+.3f}A"
                if(flux != None):
                    txt += f"\nFlux: {amps.imag:+.3f}A"
                    txt += f"\nTotal: {abs(amps):.3f}A"
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

    def updateCogging(self,data):
        try:
            if "data" in data:
                # Correctly parse the "item:X,data:(Y,Z,...)" format
                item_str, data_str = data.split(',', 1)
                start_index = int(item_str.split(':')[1])
                
                # Extract the numbers from within the parentheses
                values_str = data_str.split('(')[1].split(')')[0]
                points = [float(p) for p in values_str.split(',') if p]

                for i, p in enumerate(points):
                    if start_index + i < len(self.cogging_data):
                        self.cogging_data[start_index + i] = p
                        self.cogging_data_received[start_index + i] = True
                
                # Redraw the entire graph with the updated data
                self.lines_cogging.clear()
                degrees_per_point = 360.0 / len(self.cogging_data)
                
                valid_data = []
                for i, p in enumerate(self.cogging_data):
                    if self.cogging_data_received[i]:
                        self.lines_cogging.append(i * degrees_per_point, p)
                        valid_data.append(p)

                self.chart_cogging_Xaxis.setMax(360)
                
                if valid_data:
                    self.chart_cogging_Yaxis.setMax(max(valid_data))
                    self.chart_cogging_Yaxis.setMin(min(valid_data))

        except Exception as e:
            self.main.log("TMC cogging update error: " + str(e))

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
        if(len(self.STATES) > intstate):
            self.label_state.setText(self.STATES[intstate])
        else:
            self.label_state.setText(state)

    def updateTimer(self):
        self.send_command("tmc","acttrq",self.axis)
        
        
    def updateStatus(self):
        self.send_command("tmc","temp",self.axis)
        self.send_command("tmc","state",self.axis)
        self.send_commands("sys",["vint","vext"])

    def submitMotor(self):
        mtype = self.comboBox_mtype.currentData()
        self.send_value("tmc","mtype",val=mtype,instance=self.axis)

        poles = self.spinBox_poles.value()
        self.send_value("tmc","poles",val=poles,instance=self.axis)

        self.send_value("tmc","cpr",val=self.spinBox_cpr.value(),instance=self.axis)

        enc = self.comboBox_enc.currentData()
        self.send_value("tmc","encsrc",val=enc,instance=self.axis)

        self.send_value("tmc","abnindex",val = 1 if self.checkBox_abnIndex.isChecked() else 0,instance=self.axis)
        self.send_value("tmc","abnpol",val = 1 if self.checkBox_abnpol.isChecked() else 0,instance=self.axis)

        self.send_value("tmc","combineEncoder",val = 1 if self.checkBox_combineEncoders.isChecked() else 0,instance=self.axis)
        self.send_value("tmc","invertForce",val = 1 if self.checkBox_invertForce.isChecked() else 0,instance=self.axis)
        self.send_value("tmc","cogging",val = 1 if self.checkBox_cogging.isChecked() else 0,instance=self.axis)
        
    def submitPid(self):
        # PIDs
        seq = 1 if self.checkBox_advancedpid.isChecked() else 0
        self.send_value("tmc","seqpi",val=seq,instance=self.axis)

        tp = self.spinBox_tp.value()
        self.send_value("tmc","torqueP",val=tp,instance=self.axis)

        ti = self.spinBox_ti.value()
        self.send_value("tmc","torqueI",val=ti,instance=self.axis)

        fp = self.spinBox_fp.value()
        self.send_value("tmc","fluxP",val=fp,instance=self.axis)

        fi = self.spinBox_fi.value()
        self.send_value("tmc","fluxI",val=fi,instance=self.axis)

        prec = self.checkBox_I_Precision.isChecked() | (self.checkBox_P_Precision.isChecked() << 1)
        self.send_value("tmc","pidPrec",val=prec,instance=self.axis)
        self.send_value("tmc","svpwm",val=1 if self.checkBox_svpwm.isChecked() else 0,instance=self.axis)
        
    def changePrecision(self,button,checked):
        rescale = (16 if checked else 1/16)
        if(button == self.checkBox_I_Precision):
            if(self.lastPrecI != checked):
                self.spinBox_ti.setValue(int(self.spinBox_ti.value() * rescale))
                self.spinBox_fi.setValue(int(self.spinBox_fi.value() * rescale))
        if(button == self.checkBox_P_Precision):
            if(self.lastPrecP != checked):
                self.spinBox_tp.setValue(int(self.spinBox_tp.value() * rescale))
                self.spinBox_fp.setValue(int(self.spinBox_fp.value() * rescale))

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
        selectorPopup = OptionsDialog(TMC_HW_Version_Selector(self.tr("TMC Version"),self,self.axis),self)
        selectorPopup.exec()
        self.send_command("tmc","tmcHwType",self.axis,'!')
        self.send_command("tmc","tmcHwType",self.axis,'?')
       
    def hwVersionsCb(self,v):
        entriesList = v.split("\n")
        entriesList = [m.split(":") for m in entriesList if m]
        self.hwversions = {int(entry[0]):entry[1] for entry in entriesList}

    def hwtcb(self,t):
        self.hwversion = int(t)
        
        self.label_hwversion.setText(self.hwversions[self.hwversion])
        if self.hwversion == 0 and self.versionWarningShow and len(self.hwversions) > 0:
            # no version set. ask user to select version
            self.versionWarningShow = False
            QTimer.singleShot(100,self.showVersionSelectorPopup) # return this function but show popup with a tiny delay
             
        else:
            self.versionWarningShow = False

    def init_ui(self):
        # clear graph
        self.startTime = QTime.currentTime()
        self.chartLastX = 0
        self.lines_Amps.clear()
        self.lines_Temps.clear()
        self.lines_Flux.clear()
        self.clearCoggingGraph()
        self.chartYaxis_Amps.setMin(0)
        self.chartYaxis_Temps.setMin(0)
        self.chartYaxis_Temps.setMax(90)
        try:
            # Fill encoder source types
            self.send_commands("tmc",["mtype","encsrc","tmcHwType","trqbq_mode"],self.axis,'!')
            self.send_commands("tmc",["tmctype","tmcHwType","iScale","calibrated","trqbq_f"],self.axis)
            self.send_command("tmc","cogging",self.axis,'?')
            self.getMotor()
            self.getPids()
            if not self.init_done:
                self.doubleSpinBox_fluxoffset.valueChanged.connect(lambda v : self.send_value("tmc","fluxoffset",v/self.adc_to_amps,instance=self.axis))
                self.pushButton_submitmotor.clicked.connect(self.submitMotor)
                self.pushButton_submitpid.clicked.connect(self.submitPid)
                self.comboBox_torqueFilter.currentIndexChanged.connect(self.torqueFilterChanged)
                self.spinBox_torqueFilterFreq.valueChanged.connect(lambda x : self.send_value("tmc","trqbq_f",x,instance=self.axis))
                self.init_done = True

            # Check if calibrated
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

    def calibrated(self,v):
        v = int(v)
        if not v and self.isEnabled():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle(self.tr("Calibration required"))
            msg.setText(self.tr("A calibration of ADC offsets and encoder settings is required."))
            msg.setInformativeText(self.tr("Please set up the encoder and motor parameters correctly, apply power and start the full calibration by clicking OK or Cancel and start the calibration manually later once everything is set up.\n\nCertain ADC and encoder settings are stored in flash to accelerate the startup.\nIf a new board is used a new calibration must be done."))
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            ret = msg.exec()
            # Warning displayed
            if ret == QMessageBox.StandardButton.Ok:
                self.send_command("tmc","calibrate",self.axis)


    def encsCb(self,encsrcs):
        updateListComboBox(combobox=self.comboBox_enc,reply=encsrcs,dataSep="=",lookup=self.encoder_type_to_index,dataconv=int)

    def filtersCb(self,filters):
        updateListComboBox(combobox=self.comboBox_torqueFilter,reply=filters,dataSep="=",lookup=self.filter_type_to_index,dataconv=int)
        self.send_command("tmc","trqbq_mode",self.axis)

    def motsCb(self,mots):
        updateListComboBox(combobox=self.comboBox_mtype,reply=mots,dataSep="=",lookup=self.motor_type_to_index,dataconv=int)

    def autotunePid(self):
        self.pushButton_autotunepid.setEnabled(False)
        def f(res):
            self.pushButton_autotunepid.setEnabled(True)
            if(res):
                msg = QMessageBox(QMessageBox.Icon.Information,"PID autotuning",res)
                msg.exec()
            self.getPids()

        self.get_value_async("tmc","pidautotune",f,self.axis,typechar='?')
        self.main.log("Started PID tuning")

    def alignEnc(self):
        self.pushButton_align.setEnabled(False)
        def f(res):
            self.pushButton_align.setEnabled(True)
            if(res):
                msg = QMessageBox(QMessageBox.Icon.Information,"Encoder align",res)
                msg.exec()

        self.get_value_async("tmc","encalign",f,self.axis,typechar='?')
        self.main.log("Started encoder alignment")
        
    def coggingDetection(self):
        self.pushButton_cogging.setEnabled(False)
        def f(res):
            self.pushButton_cogging.setEnabled(True)
            if(res):
                msg = QMessageBox(QMessageBox.Icon.Information,"Cogging map reading",res)
                msg.exec()

        self.get_value_async("tmc","calibrateCogging",f,self.axis,typechar='?')
        self.main.log("Started cogging detection")

    def tabChanged(self, index):
        # Assuming the tab is a QTabWidget and we can get the text
        if self.tabWidget.tabText(index) == "Cogging":
            # Load data only if it hasn't been loaded before
            if not any(self.cogging_data_received):
                self.reloadCoggingTable()

    def clearCoggingGraph(self):
        self.lines_cogging.clear()
        self.cogging_data = [0] * 2880
        self.cogging_data_received = [False] * 2880
        # Reset axes to default values
        self.chart_cogging_Yaxis.setMin(0)
        self.chart_cogging_Yaxis.setMax(20)

    def resetCoggingTable(self):
        self.send_value("tmc", "coggingTable", 0, instance=self.axis)
        self.clearCoggingGraph()

    def reloadCoggingTable(self):
        self.clearCoggingGraph()
        self.send_command("tmc", "coggingTable", self.axis, '?')
        

    def getMotor(self):
        commands=["mtype","poles","encsrc","cpr","abnindex","abnpol","combineEncoder","invertForce","fluxbrake"]
        self.send_commands("tmc",commands,self.axis)


    def getPids(self):
        commands = ["pidPrec","torqueP","torqueI","fluxP","fluxI","seqpi","svpwm"]
        self.send_commands("tmc",commands,self.axis)

        

    def setCurrentScaler(self,x):
        self.send_command("tmc","fluxoffset",self.axis)
        self.doubleSpinBox_fluxoffset.setEnabled(x > 0)
        self.doubleSpinBox_fluxoffset.setMaximum(round((0x7fff*x) / 3))
        if(x != self.adc_to_amps):
            self.adc_to_amps = x
            if(x > 0):
                self.chartYaxis_Amps.setMax(round((0x7fff*x) / 10))


class TMC_HW_Version_Selector(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,parent : TMC4671Ui,instance):
        self.parent = parent
        OptionsDialogGroupBox.__init__(self,name,parent)
        CommunicationHandler.__init__(self)
        self.typeBox = QGroupBox("Hardware Version")
        self.typeBoxLayout = QVBoxLayout()
        self.typeBox.setLayout(self.typeBoxLayout)
        self.axis = instance

    def initUI(self):
        vbox = QVBoxLayout()
        self.infolabel = QLabel(self.tr("Warning: Selecting the incorrect hardware version can lead to damage to the hardware or injury.\nSeveral calibration constants and safety features depend on the correct selection."))
        vbox.addWidget(self.infolabel)
        self.combobox = QComboBox()
        vbox.addWidget(self.combobox)
        self.setLayout(vbox)

    def onclose(self):
        self.remove_callbacks()


    def apply(self):
        self.send_value("tmc","tmcHwType",self.combobox.currentData(),instance=self.axis) # current data
        self.parent.init_ui() # Update TMC UI in case capabilities have changed
    
    def typeCb(self,entries):
        #print("Reply",entries)
        entriesList = entries.split("\n")
        entriesList = [m.split(":") for m in entriesList if m]
        for m in entriesList:
            self.combobox.addItem(m[1],m[0])
        self.get_value_async("tmc","tmcHwType",lambda val : self.combobox.setCurrentIndex(self.combobox.findData(val)),self.axis,int)

    def readValues(self):
        self.get_value_async("tmc","tmcHwType",self.typeCb,self.axis,str,typechar='!')
