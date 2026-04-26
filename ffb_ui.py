from PyQt6.QtWidgets import QMainWindow, QSlider
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QToolButton 
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QGridLayout,QSpinBox
from PyQt6 import uic
from helper import res_path,classlistToIds,splitListReply,throttle,qtBlockAndCall
from PyQt6.QtCore import QTimer,QEvent, pyqtSignal
import main
import buttonconf_ui
import analogconf_ui
from base_ui import WidgetUI,CommunicationHandler
from serial_comms import SerialComms
import effects_tuning_ui
from helper import map_infostring

class FfbUI(WidgetUI,CommunicationHandler):

    ffb_rate_event = pyqtSignal(list)

    def __init__(self, main : 'main.MainUi'=None,  title = "FFB main"):
        WidgetUI.__init__(self, main,'ffbclass.ui')
        CommunicationHandler.__init__(self)

        ##### TODO hides friction clipping label until the formula is fixed
        self.label_friction_rpm.setVisible(False)
        self.label_4.setVisible(False)
        #####

        self.main = main 
        self.btnClasses = []
        self.btnIds = []
        self.axisClasses = {}
        self.axisIds = []
        self.buttonbtns = QButtonGroup()
        self.buttonconfbuttons = []
        self.axisbtns = QButtonGroup()
        self.axisconfbuttons = []
        self.active = 0
        self.rate = 0
        self.cfrate = 0
        self.springgain = 4
        self.dampergain = 2
        self.inertiagain = 2
        self.frictiongain = 2
        self.damper_internal_scale = 1
        self.inertia_internal_scale = 1
        self.friction_internal_scale = 1
        self.damper_internal_factor = 1
        self.inertia_internal_factor = 1
        self.friction_internal_factor = 1
        self.friction_pct_speed_rampup = 25

        self.timer = QTimer(self)
        self.buttonbtns.setExclusive(False)
        self.axisbtns.setExclusive(False)

        self.effect_tuning_dlg = effects_tuning_ui.AdvancedFFBTuneDialog(self)
        self.main.maxaxischanged.connect(self.effect_tuning_dlg.set_max_axes)

        self.horizontalSlider_cffilter.valueChanged.connect(self.cffilter_changed)

        self.horizontalSlider_CFq.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_CFq,0.01,"filterCfQ"))
        self.doubleSpinBox_CFq.valueChanged.connect(lambda val : self.horizontalSlider_CFq.setValue(int(round(val * 100))))

        self.doubleSpinBox_spring.valueChanged.connect(lambda val : self.horizontalSlider_spring.setValue(int(round(val * 256/self.springgain))))
        self.horizontalSlider_spring.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_spring,self.springgain/256,"spring"))

        self.doubleSpinBox_damper.valueChanged.connect(lambda val : self.horizontalSlider_damper.setValue(int(round(val * 256/self.dampergain))))
        self.horizontalSlider_damper.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_damper,self.dampergain/256,"damper"))
        self.horizontalSlider_damper.valueChanged.connect(self.display_speed_cutoff_damper)

        self.doubleSpinBox_friction.valueChanged.connect(lambda val : self.horizontalSlider_friction.setValue(int(round(val * 256/self.frictiongain))))
        self.horizontalSlider_friction.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_friction,self.frictiongain/256,"friction"))
        self.horizontalSlider_friction.valueChanged.connect(self.display_speed_cutoff_friction)

        self.doubleSpinBox_inertia.valueChanged.connect(lambda val : self.horizontalSlider_inertia.setValue(int(round(val * 256/self.inertiagain))))
        self.horizontalSlider_inertia.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_inertia,self.inertiagain/256,"inertia"))
        self.horizontalSlider_inertia.valueChanged.connect(self.display_accel_cutoff_inertia)
        
        self.comboBox_reportrate.currentIndexChanged.connect(lambda val : self.send_value("main","hidsendspd",str(val)))

        self.pushButton_advanced_tuning.clicked.connect(self.effect_tuning_dlg.display)

        self.timer.timeout.connect(self.updateTimer)

        #self.registerCallback("main","axes",self.setAxisCheckBoxes,0,int)
        self.register_callback("main","hidsendspd",self.hidreportrate_cb,0,typechar='!')
        self.register_callback("main","hidsendspd",self.comboBox_reportrate.setCurrentIndex,0,int,typechar='?')
        self.register_callback("main","hidrate",self.ffbRateCB,0,int)
        self.register_callback("main","cfrate",self.ffbCfRateCB,0,int)
        self.register_callback("main","ffbactive",self.ffbActiveCB,0,int)

        self.register_callback("main","lsbtn",self.updateButtonClassesCB,0)
        self.register_callback("main","btntypes",self.updateButtonSources,0,int)
        self.register_callback("main","lsain",self.updateAnalogClassesCB,0)
        self.register_callback("main","aintypes",self.updateAnalogSources,0,int)

        self.register_callback("fx","filterCfFreq",lambda val : self.cffilter_changed(val,send=False),0,int)

        self.register_callback("fx","filterCfQ",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_CFq,self.horizontalSlider_CFq,0.01),0,int)
        
        self.register_callback("fx","spring",self.setSpringScalerCb,0,str,typechar="!")
        self.register_callback("fx","damper",self.setDamperScalerCb,0,str,typechar="!")
        self.register_callback("fx","inertia",self.setInertiaScalerCb,0,str,typechar="!")
        self.register_callback("fx","friction",self.setFrictionScalerCb,0,str,typechar="!")

        self.register_callback("fx","spring",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_spring,self.horizontalSlider_spring,self.springgain/256),0,int)
        self.register_callback("fx","damper",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_damper,self.horizontalSlider_damper,self.dampergain/256),0,int)
        self.register_callback("fx","friction",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_friction,self.horizontalSlider_friction,self.frictiongain/256),0,int)
        self.register_callback("fx","inertia",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_inertia,self.horizontalSlider_inertia,self.inertiagain/256),0,int)
        
        self.register_callback("fx", "frictionPctSpeedToRampup", self.set_friction_pct_speed_rampup,0,int)

        # --- Smoothing Controls ---
        self.radioButton_reconfilter_0.toggled.connect(lambda checked: self.send_recon_filter(0) if checked else None)
        self.radioButton_reconfilter_1.toggled.connect(lambda checked: self.send_recon_filter(1) if checked else None)
        self.radioButton_reconfilter_2.toggled.connect(lambda checked: self.send_recon_filter(2) if checked else None)
        self.radioButton_reconfilter_3.toggled.connect(lambda checked: self.send_recon_filter(3) if checked else None)
        self.register_callback("fx", "reconFilterMode", self.update_recon_filter_ui, 0, int)

        self.init_ui()

        self.buttonbtns.buttonClicked.connect(self.buttonsChanged)
        self.axisbtns.buttonClicked.connect(self.axesChanged)
        

    
    def init_ui(self):
        try:
            self.send_commands("main",["hidrate","ffbactive"],0)

            self.send_command("main","lsbtn",0,'?') # get button types
            self.send_command("main","btntypes",0,'?') # get active buttons

            self.send_command("main","lsain",0,'?') # get analog types
            self.send_command("main","aintypes",0,'?') # get active analog

            self.send_commands("fx", ["reconFilterMode"])

            self.updateSliders()
            self.send_command("main","hidsendspd",0,'!') # get speed
            
        except:
            self.main.log("Error initializing FFB tab")
            return False
        return True

    # Tab is currently shown
    def showEvent(self,event):
        self.init_ui()
        self.startTimer()

    # # Tab is hidden
    def hideEvent(self,event):
        self.stopTimer()

    def startTimer(self):
        self.timer.start(500)

    # Tab is hidden
    def stopTimer(self):
        self.timer.stop()
        self.ffb_rate_event.emit((0,0,0))

    def ffbActiveCB(self,active):
        self.active = active
        self.ffb_rate_event.emit((self.active,self.rate,self.cfrate))
        
    def ffbRateCB(self,rate):
        self.rate = rate

    def ffbCfRateCB(self,rate):
        self.cfrate = rate
 
    def updateTimer(self):
        try:
            self.send_commands("main",["hidrate","ffbactive","cfrate"],0)
        except:
            self.main.log("Update error")
    
    # Helper function to sync spinboxes and sliders
    # Should be called by the sliders update event while the spinbox should update the slider directly
    def sliderChangedUpdateSpinbox(self,val,spinbox,factor,command=None):
        newVal = val * factor
        if(spinbox.value != newVal):
            spinbox.blockSignals(True)
            spinbox.setValue(newVal)
            spinbox.blockSignals(False)
        if(command):
            self.send_value("fx",command,val)

    def display_speed_cutoff_damper(self, gain):
        """Update the max rpm speed cutoff"""
        damper_fw_internal_scaler = self.damper_internal_factor * self.damper_internal_scale
        damper_speed = self.dampergain * damper_fw_internal_scaler * ((gain + 1) / 256)
        max_speed = (32767 * 60 / 360) / damper_speed
        self.label_damper_rpm.setText(f"{max_speed:.1f}")

    # TODO actually use the gain
    def display_speed_cutoff_friction(self, gain):
        """Update the max rpm speed cutoff"""
        friction_fw_internal_scaler = self.friction_internal_factor * self.friction_internal_scale
        max_speed = (32767 * self.friction_pct_speed_rampup / 100.0) * (60 / 360) / friction_fw_internal_scaler
        self.label_friction_rpm.setText(f"{max_speed:.1f}")
        
    def display_accel_cutoff_inertia(self, gain):
        """Update the max accel cutoff for inertia"""
        inertia_fw_internal_scaler = self.inertia_internal_factor * self.inertia_internal_scale
        inertia_accel = self.inertiagain * inertia_fw_internal_scaler * ((gain + 1) / 256)
        max_accel = 32767 / inertia_accel
        self.label_accel.setText(f"{max_accel:.0f}")

    def updateSpinboxAndSlider(self,val,spinbox : QSlider,slider,factor):
        slider.setValue(val)
        self.sliderChangedUpdateSpinbox(val,spinbox,factor)


    def hidreportrate_cb(self,modes):
        self.comboBox_reportrate.blockSignals(True)
        self.comboBox_reportrate.clear()
        modes = [m.split(":") for m in modes.split(",") if m]
        for m in modes:
            self.comboBox_reportrate.addItem(m[0],m[1])
        self.send_command("main","hidsendspd",0,'?') # get speed
        self.comboBox_reportrate.blockSignals(False)

    # Button selector
    def buttonsChanged(self,id):
        mask = 0
        for b in self.buttonbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.buttonbtns.id(b)

        self.send_value("main","btntypes",str(mask))

    # Analog selector
    def axesChanged(self,id):
        mask = 0
        for b in self.axisbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.axisbtns.id(b)

        self.send_value("main","aintypes",str(mask))
        
    def updateButtonClassesCB(self,reply):
        self.btnIds,self.btnClasses = classlistToIds(reply)

    def updateButtonSources(self,types):
        if not self.btnClasses:
            self.send_command("main","lsbtn",0,'?')
            return
        if(types == None):
            self.main.log("Error getting buttons")
            return
        types = int(types)
        
        layout = QGridLayout() if not self.groupBox_buttons.layout() else self.groupBox_buttons.layout()
        layout.setVerticalSpacing(0)
        layout.setContentsMargins(12,5,12,5)
        #clear
        for b in self.buttonconfbuttons:
            self.remove_callbacks(b[1])
            b[0].setParent(None)
            for c in b :
                c.deleteLater()
            #del b
        self.buttonconfbuttons.clear() # Clear buttons
        for b in self.buttonbtns.buttons():
            self.buttonbtns.removeButton(b)
            # del b
            b.deleteLater()
        #add buttons
        row = 0
        for c in self.btnClasses:
            btn=QCheckBox(str(c[1]),self.groupBox_buttons)
            self.buttonbtns.addButton(btn,c[0])
            layout.addWidget(btn,row,0)
            enabled = types & (1<<c[0]) != 0
            btn.setChecked(enabled)

            creatable = c[2]
            btn.setEnabled(creatable or enabled)

            confbutton = QToolButton(self)
            confbutton.setText(">")
            layout.addWidget(confbutton,row,1)
            self.buttonconfbuttons.append((confbutton,buttonconf_ui.ButtonOptionsDialog(str(c[1]),c[0],self.main)))
            confbutton.clicked.connect(self.buttonconfbuttons[row][1].exec)
            confbutton.setEnabled(enabled)
            self.buttonbtns.button(c[0]).stateChanged.connect(confbutton.setEnabled)
            row+=1
        self.groupBox_buttons.setLayout(layout)

    def updateAnalogClassesCB(self,reply):
        self.axisIds,self.axisClasses = classlistToIds(reply)

    def updateAnalogSources(self,types):
 
        if not self.axisClasses:
            self.send_command("main","lsain",0,'?')
            #print("Analog missing")
            return
        
        if(types == None):
            self.main.log("Error getting analog")
            return

        types = int(types)
        layout = QGridLayout() if not self.groupBox_analogaxes.layout() else self.groupBox_analogaxes.layout()
        #clear
        for b in self.axisconfbuttons:
            self.remove_callbacks(b[1])
            b[0].setParent(None)
            # del b
            for c in b :
                c.deleteLater()
        self.axisconfbuttons.clear()
        for b in self.axisbtns.buttons():
            self.axisbtns.removeButton(b)
            #del b
            b.deleteLater()
        #add buttons
        row = 0
        for c in self.axisClasses:
            creatable = c[2]
            btn=QCheckBox(str(c[1]),self.groupBox_analogaxes)
            self.axisbtns.addButton(btn,c[0])
            layout.addWidget(btn,row,0)
            enabled = types & (1<<c[0]) != 0
            btn.setChecked(enabled)

            confbutton = QToolButton(self)
            confbutton.setText(">")
            layout.addWidget(confbutton,row,1)
            self.axisconfbuttons.append((confbutton,analogconf_ui.AnalogOptionsDialog(str(c[1]),c[0],self.main)))
            confbutton.clicked.connect(self.axisconfbuttons[row][1].exec)
            confbutton.setEnabled(enabled)
            self.axisbtns.button(c[0]).stateChanged.connect(confbutton.setEnabled)
            row+=1
    
            #confbutton.setEnabled(creatable or enabled)
            btn.setEnabled(creatable or enabled)

        self.groupBox_analogaxes.setLayout(layout)

    # Called when the reconstruction filter slider is moved
    def send_recon_filter(self, value):
        """Sends the selected reconstruction filter mode to the firmware."""
        self.send_value("fx", "reconFilterMode", value)

    # Callback to update the reconstruction filter UI from firmware data
    def update_recon_filter_ui(self, value):
        """Updates the reconstruction filter slider and label."""
        button_radio = None 
        if (value < 0 or value >= 4):
            self.main.log(f"Warning: Received unknown reconstruction filter mode value: {value}")
        elif value == 0:
            button_radio = self.radioButton_reconfilter_0
        elif value == 1:
            button_radio = self.radioButton_reconfilter_1
        elif value == 2:
            button_radio = self.radioButton_reconfilter_2
        elif value == 3:
            button_radio = self.radioButton_reconfilter_3
        qtBlockAndCall(button_radio, button_radio.setChecked, True)
        button_radio.setChecked(True)

    @throttle(50)
    def cffilter_changed(self,v,send=True):
        self.tech_log.debug("Freq %s send %d", v, send)
        freq = max(min(v,500),0)
        if(send):
            self.send_value("fx","filterCfFreq",(freq))
        else:
            self.horizontalSlider_cffilter.setValue(v)
        lbl = str(freq)+"Hz"
        
        qOn = True
        if(freq == 500):
            lbl = "Off"
            qOn = False
            
        self.horizontalSlider_CFq.setEnabled(qOn)
        self.doubleSpinBox_CFq.setEnabled(qOn)
        self.label_cffilter.setText(lbl)

    def extract_scaler(self, gain_default, repl) :
        infos = {key:value for (key,value) in [entry.split(":") for entry in repl.split(",")]}
        if "scale" in infos:
            gain_default = float(infos["scale"]) if float(infos["scale"]) > 0 else gain_default
        return gain_default

    def updateGainScaler(self,slider : QSlider,spinbox : QSpinBox, gain):
        spinbox.setMaximum(gain)
        self.sliderChangedUpdateSpinbox(slider.value(),spinbox,gain)

    def setSpringScalerCb(self,repl):
        dat = map_infostring(repl)
        self.springgain = dat.get("scale",self.springgain)
        self.updateGainScaler(self.horizontalSlider_spring,self.doubleSpinBox_spring,self.springgain)
    def setDamperScalerCb(self,repl):
        dat = map_infostring(repl)
        self.dampergain = dat.get("scale",self.dampergain)
        self.damper_internal_factor = dat.get("factor",self.damper_internal_factor)
        self.updateGainScaler(self.horizontalSlider_damper,self.doubleSpinBox_damper,self.dampergain)
    def setFrictionScalerCb(self,repl):
        dat = map_infostring(repl)
        self.frictiongain = dat.get("scale",self.frictiongain)
        self.friction_internal_factor = dat.get("factor",self.friction_internal_factor)
        self.updateGainScaler(self.horizontalSlider_friction,self.doubleSpinBox_friction,self.frictiongain)
    def setInertiaScalerCb(self,repl):
        dat = map_infostring(repl)
        self.inertiagain = dat.get("scale",self.inertiagain)
        self.inertia_internal_factor = dat.get("factor",self.inertia_internal_factor)
        self.updateGainScaler(self.horizontalSlider_inertia,self.doubleSpinBox_inertia,self.inertiagain)


    def set_friction_pct_speed_rampup(self,value):
        self.friction_pct_speed_rampup = value
    
    def updateSliders(self):
        self.send_commands("fx",["spring","damper","friction","inertia"],0,typechar="!")
        self.send_commands("fx",["filterCfQ","filterCfFreq","spring","damper","friction","inertia"],0)



        