from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QToolButton 
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QGridLayout
from PyQt6 import uic
from helper import res_path,classlistToIds,updateClassComboBox,qtBlockAndCall,throttle
from PyQt6.QtCore import QTimer,QEvent
import main
from base_ui import WidgetUI,CommunicationHandler
from encoderconf_ui import EncoderOptions
import encoder_tuning_ui
import expo_ui


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

        tabId = self.main.add_tab(self,"FFB Axis")
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
        self.groupBox_enableAxisBlock.toggled.connect(self.toggleAxisBlock)

        self.pushButton_encoderTuning.clicked.connect(self.encoder_tuning_dlg.display)
        self.pushButton_expo.clicked.connect(self.expo_dlg.display)

        
        # The slew rate slider is named horizontalSlider in the UI file
        self.horizontalSlider.setMinimum(0)
        # self.horizontalSlider.setMaximum(5000) # Max value is now set dynamically
        self.horizontalSlider.valueChanged.connect(self.send_slewrate)
        self.register_callback("axis", "slewrate", self.update_slewrate_ui, self.axis, int)
        self.register_callback("axis", "maxdrvslewrate", self.update_slewrate_slider_max, self.axis, int)


        # --- Equalizer Controls ---
        # Store all equalizer sliders in a list for easy access
        self.eq_sliders = [self.verticalSlider_eq1, self.verticalSlider_eq2, self.verticalSlider_eq3, self.verticalSlider_eq4, self.verticalSlider_eq5, self.verticalSlider_eq6]
        # Connect the checkbox stateChanged signal to send the enable/disable command
        self.checkBox_eq.stateChanged.connect(self.send_eq_enabled)
        # Iterate through each slider to connect its valueChanged signal
        for i, slider in enumerate(self.eq_sliders):
            # When a slider value changes, call send_eq_band_value with the slider's value and band number (index + 1)
            slider.valueChanged.connect(lambda val, index=i: self.send_eq_band_value(val, index + 1))
        
        # Connect the reset button's clicked signal to the reset function
        self.pushButton_resetEq.clicked.connect(self.reset_eq)

        # Register callbacks to receive equalizer status updates from the firmware
        self.register_callback("axis","equalizer",self.update_eq_enabled,self.axis,int)
        for i in range(6):
            # Register a callback for each equalizer band (eqb1, eqb2, etc.)
            self.register_callback("axis",f"eqb{i+1}",lambda val, index=i: self.update_eq_band(val, index),self.axis,int)

        # Set initial state of the collapsible groupbox
        self.toggleAxisBlock(self.groupBox_enableAxisBlock.isChecked())
    
    def toggleAxisBlock(self, checked):
        # This function hides/shows the content of the groupbox and adjusts its height
        # to create a collapsible effect.
        self.groupBox_hardware.setVisible(checked)
        self.groupBox_axisOption.setVisible(checked)
        self.groupBox_encoder.setVisible(checked)

        if checked:
            # When checked (expanded), remove the maximum height constraint.
            self.groupBox_enableAxisBlock.setMaximumHeight(16777215) # QWIDGETSIZE_MAX
        else:
            # When unchecked (collapsed), set a fixed height for the title bar.
            # You might need to adjust this value (e.g., 30) to fit your UI style.
            self.groupBox_enableAxisBlock.setMaximumHeight(40)
            self.groupBox_enableAxisBlock.setMaximumWidth(800)
        
        # Notify this widget (the tab page) that its size hint has changed.
        self.updateGeometry()
        # Also notify the parent tab widget, forcing it to recalculate its own size hint.
        self.main.tabWidget_main.updateGeometry()
        
        # Use a single shot timer to allow the event to process, then update the main window layout.
        # This will now get the correct, updated size hint from the tab widget.
        QTimer.singleShot(0, self.main.adjustSize)

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

    # --- Smoothing Methods ---

    # Called when the slew rate limit slider is moved
    @throttle(50) # Throttle to prevent flooding the connection
    def send_slewrate(self, value):
        """Sends the slew rate limit value to the firmware."""
        self.send_value("axis", "slewrate", value, instance=self.axis)
        
        # display the slew rate in A/ms if it's a tmc driver, else display a lot
        if((self.driver_id == 1 or self.driver_id == 2) and self.adc_to_amps != 0):
            current = (value * self.adc_to_amps)
            value = str(round(current,1)) + "A/ms"
            
        self.label_14.setText(f"{value}")

    # Callback to update the slew rate limit UI from firmware data
    def update_slewrate_ui(self, value):
        """Updates the slew rate limit slider and label."""
        qtBlockAndCall(self.horizontalSlider, self.horizontalSlider.setValue, value)
        if((self.driver_id == 1 or self.driver_id == 2) and self.adc_to_amps != 0):
            current = (value * self.adc_to_amps)
            value = str(round(current,1)) + "A/ms"
        self.label_14.setText(f"{value}")

    def update_slewrate_slider_max(self, max_val):
        """Sets the maximum value of the slew rate slider and then requests the current value. """
        if((self.driver_id == 1 or self.driver_id == 2) and self.adc_to_amps != 0):
            current = (max_val * self.adc_to_amps)
            value = str(round(current,1)) + "A/ms"
        else:
            value = max_val
        self.label_maxDrvSlewRate.setText(value)
        
        self.horizontalSlider.setMaximum(max_val)
        # Now that the maximum is set, request the current value to position the slider correctly.
        self.send_command("axis", "slewrate", self.axis)


    # --- Equalizer Methods ---

    # Called when the 'Effect equalizer' checkbox is toggled
    def send_eq_enabled(self, state):
        """Sends the command to enable or disable the equalizer on the firmware."""
        self.send_value("axis", "equalizer", 1 if state else 0, instance=self.axis)

    # Called when any equalizer slider's value is changed
    def send_eq_band_value(self, value, band):
        """Sends the gain value for a specific equalizer band to the firmware."""
        self.send_value("axis", f"eqb{band}", value, instance=self.axis)

    # Called when the 'Reset gain' button is clicked
    def reset_eq(self):
        """Asks for user confirmation and then resets all equalizer sliders to 0."""
        # Display a confirmation dialog
        reply = QMessageBox.question(self, 'Reset Equalizer', "Are you sure you want to reset all equalizer bands to 0?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        # If the user clicks 'Yes'
        if reply == QMessageBox.StandardButton.Yes:
            # Set each slider's value to 0, which will also trigger the send_eq_band_value signal
            for slider in self.eq_sliders:
                slider.setValue(0)

    # Callback function to update the checkbox when a value is received from the firmware
    def update_eq_enabled(self, value):
        """Updates the 'Effect equalizer' checkbox state based on data from the firmware."""
        # qtBlockAndCall temporarily blocks signals from the checkbox, sets its state,
        # and then unblocks them. This prevents the checkbox from re-sending the same value
        # back to the firmware, avoiding a potential infinite loop.
        qtBlockAndCall(self.checkBox_eq, self.checkBox_eq.setChecked, value)

    # Callback function to update a slider when a value is received from the firmware
    def update_eq_band(self, value, band):
        """Updates an equalizer slider's value based on data from the firmware."""
        # qtBlockAndCall is used here for the same reason as in update_eq_enabled:
        # to prevent the slider's valueChanged signal from firing and re-sending the value.
        qtBlockAndCall(self.eq_sliders[band], self.eq_sliders[band].setValue, value)

    def init_ui(self):
        try:
            self.getMotorDriver()
            self.getEncoder()
            #self.updateSliders()
            self.send_commands("axis",["invert","cpr"],self.axis)
            self.send_command("axis","cmdinfo",self.axis,adr=19) # reduction
            self.send_command("axis","cmdinfo",self.axis,adr=24) # Expo
            # Request initial equalizer status and all band gains from the firmware
            self.send_commands("axis",["equalizer","eqb1","eqb2","eqb3","eqb4","eqb5","eqb6"],self.axis)
            # Request initial smoothing values. Slewrate is requested by the maxdrvslewrate callback chain.
       
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
        self.send_command("axis", "maxdrvslewrate", self.axis) # Get max slew rate for slider
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
