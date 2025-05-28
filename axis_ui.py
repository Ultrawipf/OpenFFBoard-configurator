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
        
        #self.checkBox_invert.stateChanged.connect(lambda val : self.send_value("axis","invert",(0 if val == 0 else 1),instance=self.axis))
        self.checkBox_speedlimit.stateChanged.connect(self.setSpeedLimitEnabled)
        self.spinBox_speedlimit.valueChanged.connect(lambda val : self.send_value("axis","maxspeed",val,instance=self.axis))

        self.spinBox_reduction_numerator.valueChanged.connect(self.updateReductionText)
        self.spinBox_reduction_denominator.valueChanged.connect(self.updateReductionText)
        self.pushButton_apply_options.clicked.connect(self.applyOptions)

        self.pushButton_submit_hw.clicked.connect(self.submitHw)
        self.pushButton_submit_enc.clicked.connect(self.submitEnc)

        tabId = self.main.add_tab(self,"FFB Axis")
        # Callbacks must prevent sending a value change command
        self.register_callback("axis","power",self.updatePowerSlider,self.axis,int)
        self.register_callback("axis","degrees",lambda val : self.updateRange(val),self.axis,int)

        self.register_callback("axis","invert",lambda val : qtBlockAndCall(self.checkBox_invert,self.checkBox_invert.setChecked,val),self.axis,int)
        
        self.register_callback("axis","fxratio",lambda val : self.updateFxratio(val),self.axis,int)

        self.register_callback("axis","esgain",lambda val : self.updateEsgain(val),self.axis,int)
        self.register_callback("axis","idlespring",lambda val : self.updateIdlespring(val),self.axis,int)

        self.register_callback("axis","axisdamper",lambda val : self.updateDamper(val),self.axis,int)

        self.register_callback("axis","reduction",lambda val : self.updateReduction(val),self.axis,lambda x : tuple(map(int,x.split(":"))))

        self.register_callback("axis","cmdinfo",self.reductionAvailable,self.axis,int,adr = 17)

        self.register_callback("axis","maxspeed",self.speedLimitCb,self.axis,int)

        self.register_callback("axis","pos",self.enc_pos_cb,self.axis,int)
        self.register_callback("axis","cpr",self.cpr_cb,self.axis,int)

        self.register_callback("axis","axisfriction",lambda val : self.updateFriction(val),self.axis,int)
        self.register_callback("axis","axisinertia",lambda val : self.updateInertia(val),self.axis,int)

        # Check if expo is available
        self.register_callback("axis","cmdinfo",self.expoAvailable,self.axis,int,adr = 24)

        self.pushButton_encoderTuning.clicked.connect(self.encoder_tuning_dlg.display)
        self.pushButton_expo.clicked.connect(self.expo_dlg.display)
    
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
        

    def setSpeedLimitEnabled(self,val):
        self.spinBox_speedlimit.setEnabled(val)
        if self.checkBox_speedlimit.isChecked():
            self.send_value("axis","maxspeed",self.spinBox_speedlimit.value(),instance=self.axis)
        else:
            self.send_value("axis","maxspeed",0,instance=self.axis)
        

    def updateReduction(self,val):
        numerator,denominator = val
        self.spinBox_reduction_numerator.setValue(numerator)
        self.spinBox_reduction_denominator.setValue(denominator)
        self.updateReductionText()

    def reductionAvailable(self,available):
        self.frame_reduction.setVisible(available>0)
        if available > 0:
            self.send_command("axis","reduction",self.axis)

    def updateReductionText(self):
        self.label_gear_reduction_value.setText(f"Prescaler: {round(self.spinBox_reduction_numerator.value()/self.spinBox_reduction_denominator.value(),5)}")

    def applyOptions(self):
        self.send_value("axis","invert",(0 if self.checkBox_invert.isChecked() == 0 else 1),instance=self.axis)
        if(self.frame_reduction.isVisible()):
            self.send_value("axis","reduction",self.spinBox_reduction_numerator.value(),self.spinBox_reduction_denominator.value(),self.axis)

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
        # if available > 0:
            # self.send_commands("axis",["expo","exposcale"],self.axis)

    def init_ui(self):
        try:
            self.getMotorDriver()
            self.getEncoder()
            #self.updateSliders()
            self.send_commands("axis",["invert","cpr"],self.axis)
            self.send_command("axis","cmdinfo",self.axis,adr=17)
            self.send_command("axis","cmdinfo",self.axis,adr=24) # Expo
       
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
                self.groupBox_encoder.setVisible(False)
                return
            else:
                self.groupBox_encoder.setVisible(True)
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
