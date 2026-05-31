from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QToolButton 
from PyQt6.QtWidgets import QMessageBox
from PyQt6 import uic
from helper import res_path,classlistToIds,updateClassComboBox,qtBlockAndCall,throttle
from PyQt6.QtCore import QTimer,QEvent
import main
from base_ui import WidgetUI,CommunicationHandler
from encoderconf_ui import EncoderOptions
import encoder_tuning_ui
import expo_ui

from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QScatterSeries, QValueAxis
from PyQt6.QtCore import Qt, QPointF, QMargins
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication
import math
from biquad import Biquad

def calc_freq_response(b, a, freqs, fs):
    resp = []
    for f in freqs:
        w = 2 * math.pi * f / fs
        cos_w = math.cos(w)
        sin_w = -math.sin(w)
        cos_2w = math.cos(2*w)
        sin_2w = -math.sin(2*w)
        
        num_real = b[0] + b[1]*cos_w + b[2]*cos_2w
        num_imag = b[1]*sin_w + b[2]*sin_2w
        
        den_real = 1 + a[1]*cos_w + a[2]*cos_2w
        den_imag = a[1]*sin_w + a[2]*sin_2w
        
        mag_num = math.sqrt(num_real**2 + num_imag**2)
        mag_den = math.sqrt(den_real**2 + den_imag**2)
        
        mag = mag_num / (mag_den + 1e-10)
        resp.append(20 * math.log10(mag + 1e-10))
    return resp

class EqChartView(QChartView):
    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.dragged_index = -1
        self.scatter_series = None
        self.frequencies = []
        self.on_gain_changed = None

    def set_data_series(self, scatter_series, frequencies):
        self.scatter_series = scatter_series
        self.frequencies = frequencies

    def mousePressEvent(self, event):
        if self.scatter_series:
            for i, p in enumerate(self.scatter_series.points()):
                p_pixel = self.chart().mapToPosition(p)
                dist = math.hypot(p_pixel.x() - event.position().x(), p_pixel.y() - event.position().y())
                if dist < 15:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.dragged_index = i
                        event.accept()
                        return
                    elif event.button() == Qt.MouseButton.RightButton:
                        self.scatter_series.replace(i, self.frequencies[i], 0.0)
                        if self.on_gain_changed:
                            self.on_gain_changed(i, 0)
                        event.accept()
                        return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragged_index >= 0 and self.scatter_series:
            val_point = self.chart().mapToValue(event.position())
            y = max(-120.0, min(120.0, val_point.y()))
            self.scatter_series.replace(self.dragged_index, self.frequencies[self.dragged_index], y)
            if self.on_gain_changed:
                self.on_gain_changed(self.dragged_index, int(y))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragged_index >= 0:
            val_point = self.chart().mapToValue(event.position())
            y = max(-120.0, min(120.0, val_point.y()))
            self.scatter_series.replace(self.dragged_index, self.frequencies[self.dragged_index], y)
            if self.on_gain_changed:
                self.on_gain_changed(self.dragged_index, int(y))
            self.dragged_index = -1
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class AxisUI(WidgetUI,CommunicationHandler):

    def __init__(self, main: 'main.MainUi'=None, unique=0):
        WidgetUI.__init__(self, main, 'axis_ui.ui')
        CommunicationHandler.__init__(self)

        self.main = main
        self.adc_to_amps = 0.0
        self.max_power = 0
        self.cpr = -1

        self.driver_classes = {}
        self.driver_ids = []

        self.encoder_classes = {}
        self.encoder_ids = []

        self.driver_id = 0
        self.encoder_id = 0

        self.encoder_widgets = {}
        self.axis = unique

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_cb)
        self.encoder_tuning_dlg = encoder_tuning_ui.AdvancedTuningDialog(self, self.axis)

        self.expo_dlg = expo_ui.ExpoTuneDialog(self,self.axis)

        self.horizontalSlider_power.valueChanged.connect(self.powerSiderMoved)

        self.spinBox_range.valueChanged.connect(self.send_range_value) # don't update while typing
        self.horizontalSlider_degrees.valueChanged.connect(self.update_range_slider)

        self.horizontalSlider_esgain.valueChanged.connect(lambda val : self.send_value("axis","esgain",(val),instance=self.axis))
        self.horizontalSlider_fxratio.valueChanged.connect(self.fxratio_changed)
        self.horizontalSlider_idle.valueChanged.connect(lambda val : self.send_value("axis","idlespring",(val),instance=self.axis))
        self.horizontalSlider_damper.valueChanged.connect(lambda val : self.send_value("axis","axisdamper",val,instance=self.axis))
        self.horizontalSlider_friction.valueChanged.connect(lambda val : self.send_value("axis","axisfriction",val,instance=self.axis))
        self.horizontalSlider_inertia.valueChanged.connect(lambda val : self.send_value("axis","axisinertia",val,instance=self.axis))
        self.pushButton_center.clicked.connect(lambda : self.send_command("axis","zeroenc",instance=self.axis))
        
        self.checkBox_speedlimit.stateChanged.connect(self.setSpeedLimitEnabled)
        self.spinBox_speedlimit.valueChanged.connect(lambda val : self.send_value("axis","maxspeed",val,instance=self.axis))

        self.pushButton_apply_options.clicked.connect(self.applyOptions)

        self.pushButton_submit_hw.clicked.connect(self.submitHw)
        self.pushButton_submit_enc.clicked.connect(self.submitEnc)

        # VMA Remove it is's also done in the tab processing tabId = self.main.add_tab(self,"FFB Axis")
        # Callbacks must prevent sending a value change command
        self.register_callback("axis","power",self.updatePowerSlider,self.axis,int)
        self.register_callback("axis","degrees",lambda val : self.updateRange(val),self.axis,int)

        self.register_callback("axis","maxspeed",self.speedLimitCb,self.axis,int)
        self.register_callback("axis","invert",lambda val : qtBlockAndCall(self.checkBox_invert,self.checkBox_invert.setChecked,val),self.axis,int)
        
        self.register_callback("axis","fxratio",lambda val : self.updateFxratio(val),self.axis,int)

        self.register_callback("axis","esgain",lambda val : self.updateEsgain(val),self.axis,int)
        self.register_callback("axis","idlespring",lambda val : self.updateIdlespring(val),self.axis,int)

        self.register_callback("axis","axisdamper",lambda val : self.updateDamper(val),self.axis,int)

        self.register_callback("axis","reduction",lambda val : self.updateReduction(val),self.axis,lambda x : tuple(map(int,x.split(":"))))

        # Check if reduction command is available
        self.register_callback("axis","cmdinfo",self.reductionAvailable,self.axis,int,adr = 19)


        self.register_callback("axis","pos",self.enc_pos_cb,self.axis,int)
        self.register_callback("axis","cpr",self.cpr_cb,self.axis,int)

        self.register_callback("axis","axisfriction",lambda val : self.updateFriction(val),self.axis,int)
        self.register_callback("axis","axisinertia",lambda val : self.updateInertia(val),self.axis,int)

        # Check if expo is available
        self.register_callback("axis","cmdinfo",self.expoAvailable,self.axis,int,adr = 24)
        
        # manage display
        self.pushButton_encoderTuning.clicked.connect(self.encoder_tuning_dlg.display)
        self.pushButton_expo.clicked.connect(self.expo_dlg.display)




        # --- Equalizer Controls ---
        
        self.eq_freqs = [10, 15, 25, 40, 60, 100]
        self.eq_gains = [0] * len(self.eq_freqs)
        self.eq_q = 2.14
        self.eq_fs = 1000.0
        
        self.chart_eq = QChart()
        self.chart_eq.legend().hide()
        self.chart_eq.setBackgroundRoundness(5)
        self.chart_eq.setBackgroundBrush(QApplication.instance().palette().window())
        
        self.axis_x_eq = QValueAxis(self.chart_eq)
        self.axis_x_eq.setRange(0, 120)
        self.axis_x_eq.setTitleText("Frequency (Hz)")
        grid_color = QColor(QApplication.instance().palette().text().color())
        grid_color.setAlpha(40)
        self.axis_x_eq.setGridLineColor(grid_color)
        self.chart_eq.addAxis(self.axis_x_eq, Qt.AlignmentFlag.AlignBottom)
        
        self.axis_y_eq = QValueAxis(self.chart_eq)
        self.axis_y_eq.setRange(-120, 120)
        self.axis_y_eq.setTitleText("Gain (%)")
        self.axis_y_eq.setTickCount(7)
        self.axis_y_eq.setGridLineColor(grid_color)
        self.chart_eq.addAxis(self.axis_y_eq, Qt.AlignmentFlag.AlignLeft)
        
        self.line_series_eq = QLineSeries()
        pen = QPen(QColor("cornflowerblue"))
        pen.setWidth(3)
        self.line_series_eq.setPen(pen)
        self.line_series_eq.setUseOpenGL(True)
        self.chart_eq.addSeries(self.line_series_eq)
        self.line_series_eq.attachAxis(self.axis_x_eq)
        self.line_series_eq.attachAxis(self.axis_y_eq)
        
        self.axis_y_eq_right = QValueAxis(self.chart_eq)
        self.axis_y_eq_right.setRange(-120, 120)
        self.axis_y_eq_right.setTickCount(7)
        self.axis_y_eq_right.setGridLineVisible(False)
        self.chart_eq.addAxis(self.axis_y_eq_right, Qt.AlignmentFlag.AlignRight)
        self.line_series_eq.attachAxis(self.axis_y_eq_right)
        
        self.zero_line_eq = QLineSeries()
        pen_zero = QPen(QApplication.instance().palette().text().color())
        pen_zero.setWidth(1)
        pen_zero.setDashPattern([4, 4])
        self.zero_line_eq.setPen(pen_zero)
        self.zero_line_eq.setUseOpenGL(True)
        self.zero_line_eq.append(0, 0)
        self.zero_line_eq.append(120, 0)
        self.chart_eq.addSeries(self.zero_line_eq)
        self.zero_line_eq.attachAxis(self.axis_x_eq)
        self.zero_line_eq.attachAxis(self.axis_y_eq)
        self.zero_line_eq.attachAxis(self.axis_y_eq_right)
        
        self.scatter_series_eq = QScatterSeries()
        self.scatter_series_eq.setMarkerShape(QScatterSeries.MarkerShape.MarkerShapeCircle)
        self.scatter_series_eq.setMarkerSize(12.0)
        self.scatter_series_eq.setColor(QColor("white"))
        self.scatter_series_eq.setBorderColor(QColor("cornflowerblue"))
        
        for f in self.eq_freqs:
            self.scatter_series_eq.append(f, 0)
            
        self.chart_eq.addSeries(self.scatter_series_eq)
        self.scatter_series_eq.attachAxis(self.axis_x_eq)
        self.scatter_series_eq.attachAxis(self.axis_y_eq)
        self.scatter_series_eq.attachAxis(self.axis_y_eq_right)
        
        idx = self.gridLayout_9.indexOf(self.graphWidget_eq)
        row, col, rowSpan, colSpan = self.gridLayout_9.getItemPosition(idx)
        self.graphWidget_eq.deleteLater()
        
        self.graphWidget_eq = EqChartView(self.chart_eq)
        self.graphWidget_eq.set_data_series(self.scatter_series_eq, self.eq_freqs)
        self.graphWidget_eq.on_gain_changed = self.on_eq_point_moved
        self.gridLayout_9.addWidget(self.graphWidget_eq, row, col, rowSpan, colSpan)
        
        for ax in self.chart_eq.axes():
            ax.setLabelsBrush(QApplication.instance().palette().text())
            ax.setTitleBrush(QApplication.instance().palette().text())
        
        self.update_eq_curve()

        self.checkBox_eq.stateChanged.connect(self.send_eq_enabled)
        
        self.pushButton_resetEq.clicked.connect(self.reset_eq)

        self.register_callback("axis","equalizer",self.update_eq_enabled,self.axis,int)
        for i in range(6):
            self.register_callback("axis",f"eqb{i+1}",lambda val, index=i: self.update_eq_band(val, index),self.axis,int)

    def setSpeedLimit(self,val):
        if self.checkBox_speedlimit.isChecked():
            self.send_value("axis","maxspeed",self.spinBox_speedlimit.value(),instance=self.axis)
        else:
            self.send_value("axis","maxspeed",0,instance=self.axis)
        

    def speedLimitCb(self,val):
        qtBlockAndCall(self.spinBox_speedlimit,self.spinBox_speedlimit.setValue,val)
        if not val:
            self.spinBox_speedlimit.setEnabled(False)
            self.checkBox_speedlimit.setChecked(False)
        else:
            self.checkBox_speedlimit.setChecked(True)
            self.spinBox_speedlimit.setEnabled(True)
        
    def updateReduction(self,val):
        numerator,denominator = val
        self.spinBox_reduction_numerator.setValue(numerator)
        self.spinBox_reduction_denominator.setValue(denominator)

    def reductionAvailable(self,available):
        self.groupBox_reduction.setVisible(available>0)
        if available > 0:
            self.send_command("axis","reduction",self.axis)

    def applyOptions(self):
        self.send_value("axis","invert",(0 if self.checkBox_invert.isChecked() == 0 else 1),instance=self.axis)
        self.send_value("axis","reduction",self.spinBox_reduction_numerator.value(),self.spinBox_reduction_denominator.value(),self.axis)
    
        # check if speed is required
        if self.checkBox_speedlimit.isChecked() :
            self.send_value("axis","maxspeed",self.spinBox_speedlimit.value(),instance=self.axis)
        else:
            self.send_value("axis","maxspeed",0,instance=self.axis)
            
    def setSpeedLimitEnabled(self,val):
        self.spinBox_speedlimit.setEnabled(val)

    def updateEsgain(self,val):
        qtBlockAndCall(self.spinBox_esgain,self.spinBox_esgain.setValue,val)
        qtBlockAndCall(self.horizontalSlider_esgain,self.horizontalSlider_esgain.setValue,val)

    def updateIdlespring(self,val):
        qtBlockAndCall(self.spinBox_idlespring,self.spinBox_idlespring.setValue,val)
        qtBlockAndCall(self.horizontalSlider_idle,self.horizontalSlider_idle.setValue,val)

    def updateDamper(self,val):
        qtBlockAndCall(self.spinBox_damper,self.spinBox_damper.setValue,val)
        qtBlockAndCall(self.horizontalSlider_damper,self.horizontalSlider_damper.setValue,val)

    def updateRange(self,val):
        qtBlockAndCall(self.spinBox_range,self.spinBox_range.setValue,val)
        qtBlockAndCall(self.horizontalSlider_degrees,self.horizontalSlider_degrees.setValue,val)

    def updateFriction(self,val):
        qtBlockAndCall(self.spinBox_friction,self.spinBox_friction.setValue,val)
        qtBlockAndCall(self.horizontalSlider_friction,self.horizontalSlider_friction.setValue,val)

    def updateInertia(self,val):
        qtBlockAndCall(self.spinBox_inertia,self.spinBox_inertia.setValue,val)
        qtBlockAndCall(self.horizontalSlider_inertia,self.horizontalSlider_inertia.setValue,val)

    def expoAvailable(self,available):
        self.pushButton_expo.setEnabled(available>0)
        self.expo_dlg.setEnabled(available>0)
        if available > 0:
            self.send_commands("axis",["expo","exposcale"],self.axis)




    # --- Equalizer Methods ---

    # Called when the 'Effect equalizer' checkbox is toggled
    def send_eq_enabled(self, state):
        """Sends the command to enable or disable the equalizer on the firmware."""
        self.send_value("axis", "equalizer", 1 if state else 0, instance=self.axis)

    def on_eq_point_moved(self, band_index, value):
        self.eq_gains[band_index] = value
        self.update_eq_curve()
        self.send_eq_band_value(value, band_index + 1)

    def send_eq_band_value(self, value, band):
        """Sends the gain value for a specific equalizer band to the firmware."""
        self.send_value("axis", f"eqb{band}", value, instance=self.axis)

    def reset_eq(self):
        """Asks for user confirmation and then resets all equalizer bands to 0."""
        reply = QMessageBox.question(self, 'Reset Equalizer', "Are you sure you want to reset all equalizer bands to 0?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for band in range(len(self.eq_freqs)):
                self.update_eq_band(0, band)
                self.send_eq_band_value(0, band + 1)

    def update_eq_enabled(self, value):
        """Updates the 'Effect equalizer' checkbox state based on data from the firmware."""
        qtBlockAndCall(self.checkBox_eq, self.checkBox_eq.setChecked, value)

    def update_eq_band(self, value, band):
        """Updates an equalizer gain value based on data from the firmware."""
        self.eq_gains[band] = value
        self.scatter_series_eq.replace(band, self.eq_freqs[band], value)
        self.update_eq_curve()

    def update_eq_curve(self):
        """Calculates and draws the frequency response curve of the equalizer."""
        freqs = [f for f in range(5, 121)]
        resp_total = [0] * len(freqs)
        
        for i, f0 in enumerate(self.eq_freqs):
            gain = self.eq_gains[i] / 10.0
            if abs(gain) > 0.01:
                if i == 0:
                    b_type = 5  # lowshelf
                elif i == len(self.eq_freqs) - 1:
                    b_type = 6  # highshelf
                else:
                    b_type = 4  # peak
                    
                bq = Biquad(b_type, f0 / self.eq_fs, self.eq_q, gain)
                b = [bq.a0, bq.a1, bq.a2]
                a = [1.0, bq.b1, bq.b2]
                
                resp = calc_freq_response(b, a, freqs, self.eq_fs)
                for j in range(len(freqs)):
                    resp_total[j] += resp[j]
        
        points = [QPointF(f, r * 10.0) for f, r in zip(freqs, resp_total)]
        self.line_series_eq.replace(points)

    def init_ui(self):
        try:
            self.getMotorDriver() # Call the motor driver and update the slicer when received message (updateSliders)
            self.getEncoder()
            self.send_commands("axis",["invert","cpr"],self.axis)
            self.send_command("axis","cmdinfo",self.axis,adr=19) # reduction
            self.send_command("axis","cmdinfo",self.axis,adr=24) # Expo
            # Request initial equalizer status and all band gains from the firmware
            self.send_commands("axis",["equalizer","eqb1","eqb2","eqb3","eqb4","eqb5","eqb6"],self.axis)
       
        except:
            self.main.log("Error initializing Axis tab")
            return False
        return True

    # Tab is currently shown
    def showEvent(self,event):
        self.init_ui() # update everything
        self.timer.start(100)

    # Tab is hidden
    def hideEvent(self,event):
        self.encoder_tuning_dlg.close()
        self.timer.stop()

    # Timer interval reached
    def timer_cb(self):

        if self.cpr > 0:
            self.send_command("axis","pos",self.axis)
        elif self.cpr == -1:
            # cpr invalid. Request cpr
            self.send_command("axis","cpr",typechar='?',instance=self.axis)
        
    
    def setCurrentScaler(self,x):
        if(x):
            self.adc_to_amps = x
            self.updatePowerLabel(self.horizontalSlider_power.value())

    def updatePowerLabel(self,val):
        text = str(val)
        # If tmc is used show a current estimate
        if((self.driver_id == 1 or self.driver_id == 2) and self.adc_to_amps != 0):
            current = (val * self.adc_to_amps)
            text += " ("+str(round(current,1)) + "A)"

        if(self.max_power > 0):
            text += "\n({:.0%})".format((val / self.max_power))

        self.label_power.setText(text)

    # Effect/Endstop ratio scaler
    def fxratio_changed(self,val):
        self.send_value("axis","fxratio",val,instance=self.axis)
        self.updateFxratioText(val)

    def updateFxratio(self,val):
        qtBlockAndCall(self.horizontalSlider_fxratio,self.horizontalSlider_fxratio.setValue,val)
        self.updateFxratioText(val)

    def updateFxratioText(self,val):
        ratio = val / 255
        text = str(round(100*ratio,1)) + "%"
        self.label_fxratio.setText(text)

    def updatePowerSlider(self,val):
        qtBlockAndCall(self.horizontalSlider_power,self.horizontalSlider_power.setValue,val)
        self.updatePowerLabel(val)

    def powerSiderMoved(self,val):
        self.powerSiderMovedUpdate(val)
        self.updatePowerLabel(val)

    # Power slider is very high resolution. throttle update calls to prevent flooding
    @throttle(50)
    def powerSiderMovedUpdate(self,val):
        self.send_value("axis","power",val,instance=self.axis)

    @throttle(50)
    def send_range_value(self,val):
        #self.horizontalSlider_degrees.setValue(val)
        qtBlockAndCall(self.horizontalSlider_degrees,self.horizontalSlider_degrees.setValue,val)
        self.send_value("axis","degrees",(val),instance=self.axis)

    def update_range_slider(self,val):
        if val :
            
            rounded_val = round(val, -1) #round to the nearest 10 step
            self.spinBox_range.setValue(rounded_val)
            self.horizontalSlider_degrees.setValue(rounded_val) # Snap slider
            #self.send_rangeslider_value(rounded_val)

    def submitEnc(self):
        self.encoderChanged(self.comboBox_encoder.currentIndex())

    def submitHw(self):
        self.driverChanged(self.comboBox_driver.currentIndex())

    def driverChanged(self,idx):
        if idx == -1:
            return
        id = self.driver_classes[idx][0]
        if(self.driver_id != id):
            self.send_value("axis","drvtype",id,instance=self.axis)
            self.getMotorDriver()
            self.getEncoder()
            self.main.update_tabs()
            self.cpr = -1 # Reset cpr
            
    def encoderChanged(self,idx):
        if idx == -1:
            return
        id = self.encoder_classes[idx][0]
        if(self.encoder_id != id):
            self.send_value("axis","enctype",id,instance=self.axis)
            self.getEncoder()
            self.main.update_tabs()
            #self.encoderIndexChanged(id)
            self.cpr = -1 # Reset cpr
    
    def updateSliders(self):
        if(self.driver_id == 1 or self.driver_id == 2): # Reduce max range for TMC (ADC saturation margin. Recommended to keep <25000)
            self.max_power = 28000
            self.horizontalSlider_power.setMaximum(self.max_power)
            self.get_value_async("tmc","iScale",self.setCurrentScaler,self.driver_id - 1,float)  
        else:
            self.max_power = 0x7fff
            self.horizontalSlider_power.setMaximum(self.max_power)

        commands = ["power","degrees","fxratio","esgain","idlespring","axisdamper","maxspeed","axisfriction","axisinertia"] # requests updates
        self.send_commands("axis",commands,self.axis)
        self.cpr = -1 # Reset cpr
        self.updatePowerLabel(self.horizontalSlider_power.value())

    def drvtypecb(self,i):
        self.driver_id = int(i)
        if i is None :
            self.main.log("Error getting driver")
            return
        updateClassComboBox(self.comboBox_driver,self.driver_ids,self.driver_classes,self.driver_id)
        self.updateSliders()

    def drvlistcb(self,l):
            self.driver_ids,self.driver_classes = classlistToIds(l)
            #print("drv",l)
            self.get_value_async("axis","drvtype",self.drvtypecb,self.axis,int,typechar='?',delete=False)

    def getMotorDriver(self):
        self.get_value_async("axis","drvtype",self.drvlistcb,self.axis,str,typechar='!')
        
       
    def encoderIndexChanged(self,idx):
        id = self.comboBox_encoder.currentData()
        if(id not in self.encoder_widgets):
            return
        self.stackedWidget_encoder.setCurrentWidget(self.encoder_widgets[id])

    def getEncoder(self):
       
        def f(dat):
            # for w in self.encWidgets:
            #     # cleanup if present
            #     CommunicationHandler.removeCallbacks(w)
            # self.comboBox_encoder.clear()
            # self.encWidgets.clear()

            self.encoder_ids,self.encoder_classes = classlistToIds(dat)
            for c in self.encoder_classes:
                id = c[0]
                creatable = c[2]
                if(id not in self.encoder_widgets or self.stackedWidget_encoder.indexOf(self.encoder_widgets[id]) == -1):
                    self.encoder_widgets[id] = EncoderOptions(self.main,id)
                    self.stackedWidget_encoder.addWidget(self.encoder_widgets[id])
                    self.comboBox_encoder.addItem(c[1],c[0])
                self.comboBox_encoder.model().item(self.encoder_ids[c[0]][0]).setEnabled(creatable)

        self.get_value_async("axis","enctype",f,self.axis,str,typechar='!')
        
        def encid_f(id):
            if(id == 255):
                #self.groupBox_encoder.setVisible(False)
                self.label_encoderSource.setVisible(False)
                self.comboBox_encoder.setVisible(False)
                self.pushButton_submit_enc.setVisible(False)
                self.stackedWidget_encoder.setVisible(False)
                return
            else:
                #self.groupBox_encoder.setVisible(True)
                self.label_encoderSource.setVisible(True)
                self.comboBox_encoder.setVisible(True)
                self.pushButton_submit_enc.setVisible(True)
                self.stackedWidget_encoder.setVisible(True)
            if(id == None):
                self.main.log("Error getting encoder")
                return
            self.encoder_id = int(id)
            
            idx = self.encoder_ids[self.encoder_id][0] if self.encoder_id in self.encoder_ids else 0
            self.comboBox_encoder.setCurrentIndex(idx)
            self.encoderIndexChanged(idx)
        self.get_value_async("axis","enctype",encid_f,self.axis,int,typechar='?')

    def cpr_cb(self,val : int):
        if val > 0:
            self.cpr = val

    def enc_pos_cb(self,val : int):
        if self.cpr > 0:
            rots = val / self.cpr
            degs = rots * 360
            self.doubleSpinBox_curdeg.setValue(degs)
            self.spinBox_curpos.setValue(int(val))
