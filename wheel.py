from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QToolButton 
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout
from PyQt6.QtWidgets import QCheckBox,QButtonGroup,QGridLayout, QSpinBox, QSlider, QLabel
from PyQt6 import uic
from helper import res_path,classlistToIds,updateClassComboBox,qtBlockAndCall,throttle, map_infostring
from PyQt6.QtCore import QTimer,QEvent
from base_ui import WidgetUI,CommunicationHandler
import main
import effects_tuning_ui

class WheelUI(WidgetUI,CommunicationHandler):

    def __init__(self, main: 'main.MainUi'=None):
        WidgetUI.__init__(self, main, 'wheel.ui')
        CommunicationHandler.__init__(self)

        self.main = main 

        self.cpr = -1
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
        self.timer.timeout.connect(self.timer_cb)
        
        self.effect_tuning_dlg = effects_tuning_ui.AdvancedFFBTuneDialog(self)
        self.main.maxaxischanged.connect(self.effect_tuning_dlg.set_max_axes)
        
        ### Event management with board message
        # General FFB Section
        self.horizontalSlider_fxratio.valueChanged.connect(lambda val : self.sliderChanged_UpdateLabel(val,self.label_fxratio,"{:2.2f}%",1/255,"axis","fxratio"))
        
        self.horizontalSlider_degrees.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val,self.spinBox_range,1,"axis","degrees"))
        self.spinBox_range.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val,self.spinBox_range,1))
        
        # Mechanical section
        self.horizontalSlider_idle.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val, self.spinBox_idlespring,1,"axis","idlespring"))
        self.spinBox_idlespring.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val,self.horizontalSlider_idle,1,))
        
        self.horizontalSlider_perma_damper.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val, self.spinBox_perma_damper,1,"axis","axisdamper"))
        self.spinBox_perma_damper.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val,self.horizontalSlider_perma_damper,1))
        
        self.horizontalSlider_perma_inertia.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val, self.spinBox_perma_inertia,1,"axis","axisinertia"))
        self.spinBox_perma_inertia.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val,self.horizontalSlider_perma_inertia,1))
        
        self.horizontalSlider_perma_friction.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val, self.spinBox_perma_friction,1,"axis","axisfriction"))
        self.spinBox_perma_friction.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val,self.horizontalSlider_perma_friction,1))
        
        # FFB Settings
        self.horizontalSlider_cffilter.valueChanged.connect(lambda val : self.cffilter_changed(val, send=True))
        
        self.horizontalSlider_spring.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val,self.doubleSpinBox_spring,self.springgain/256,"fx", "spring"))
        self.doubleSpinBox_spring.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val,self.horizontalSlider_spring, 256/self.springgain))

        self.horizontalSlider_damper.valueChanged.connect(self.display_speed_cutoff_damper)
        self.horizontalSlider_damper.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val,self.doubleSpinBox_damper,self.dampergain/256,"fx", "damper"))
        self.doubleSpinBox_damper.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val, self.horizontalSlider_damper, 256/self.dampergain))

        self.horizontalSlider_friction.valueChanged.connect(self.display_speed_cutoff_friction)
        self.horizontalSlider_friction.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val,self.doubleSpinBox_friction,self.frictiongain/256,"fx", "friction"))
        self.doubleSpinBox_friction.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val, self.horizontalSlider_friction, 256/self.frictiongain))

        self.horizontalSlider_inertia.valueChanged.connect(self.display_accel_cutoff_inertia)
        self.horizontalSlider_inertia.valueChanged.connect(lambda val : self.sliderChanged_UpdateSpinbox(val,self.doubleSpinBox_inertia,self.inertiagain/256,"fx", "inertia"))
        self.doubleSpinBox_inertia.valueChanged.connect(lambda val : self.spinboxChanged_UpdateSlider(val, self.horizontalSlider_inertia, 256/self.inertiagain))
        
        ### Event manager for UI button
        self.pushButton_advanced_tuning.clicked.connect(self.effect_tuning_dlg.display)
        self.pushButton_pushcenter.clicked.connect(lambda : self.send_command("axis","zeroenc",0))
        
        
        
        ### Register event to received data from board
        # Callback used for axis incoming data
        self.register_callback("axis","fxratio",lambda val : self.dataChanged_UpdateSliderAndLabel(val,self.horizontalSlider_fxratio, self.label_fxratio, "{:2.2%}", 1/255),0,int)
        self.register_callback("axis","degrees",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val,self.horizontalSlider_degrees,self.spinBox_range,1), 0, int)
        
        self.register_callback("axis","idlespring",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_idle, self.spinBox_idlespring, 1), 0, int)
        self.register_callback("axis","axisdamper",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_perma_damper, self.spinBox_perma_damper, 1), 0, int)
        self.register_callback("axis","axisinertia",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_perma_inertia, self.spinBox_perma_inertia, 1), 0, int)
        self.register_callback("axis","axisfriction",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_perma_friction, self.spinBox_perma_friction, 1), 0, int)
        
        # Callback used for FFB incoming data
        # This callback are used to adapt the min/max/scale value for the UI (depending on firmware internal setup)
        self.register_callback("fx","frictionPctSpeedToRampup", self.set_friction_pct_speed_rampup_cb,0,int)
        self.register_callback("fx","spring", self.set_spring_scaler_cb, 0, str, typechar="!")
        self.register_callback("fx","damper", self.set_damper_scaler_cb, 0, str, typechar="!")
        self.register_callback("fx","inertia", self.set_inertia_scaler_cb, 0, str, typechar="!")
        self.register_callback("fx","friction", self.set_friction_scaler_cb, 0, str, typechar="!")

        # This callback are used to get the current setting
        self.register_callback("fx","filterCfFreq",lambda val : self.cffilter_changed(val),0,int)
        self.register_callback("fx","spring",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_spring, self.doubleSpinBox_spring, self.springgain/256), 0, int)
        self.register_callback("fx","damper",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_damper, self.doubleSpinBox_damper, self.dampergain/256), 0, int)
        self.register_callback("fx","friction",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_friction, self.doubleSpinBox_friction, self.frictiongain/256), 0, int)
        self.register_callback("fx","inertia",lambda val : self.dataChanged_UpdateSliderAndSpinbox(val, self.horizontalSlider_inertia, self.doubleSpinBox_inertia, self.inertiagain/256), 0, int)

        # This callback are used to display the wheel position
        self.register_callback("axis","pos",self.enc_pos_cb,0,int)
        self.register_callback("axis","cpr",self.cpr_cb,0,int)

    def init_ui(self):
        try:
            self.send_commands("fx",["spring","damper","friction","inertia"],0,typechar="!")          
            self.send_commands("axis",["cpr","pos","degrees", "fxratio", "idlespring", "axisdamper", "axisinertia", "axisfriction"])
            self.send_commands("fx",["filterCfFreq","spring","damper","friction","inertia"],0)
        except:
            self.main.log("Error initializing Wheel tab")
            return False
        return True
    
    # Tab is currently shown
    def showEvent(self,event):
        self.init_ui() # Refresh data in UI
        self.timer.start(500)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    # Timer interval reached
    def timer_cb(self):
        if self.cpr > 0:
            self.send_command("axis","pos",0, typechar='?')
        elif self.cpr == -1:
            # cpr invalid. Request cpr
            self.send_command("axis","cpr",0, typechar='?')
    
    #######################################################################################################
    #                                            Windows Event
    #######################################################################################################
       
    @throttle(50)
    def sliderChanged_UpdateSpinbox(self, val : int, spinbox : QSpinBox, factor :float, cls : str=None, command : str=None):
        """when a slider move, and it provide a command, the slider update de spinbox
        and send to the board the Value
        """
        newVal = val * factor
        if(spinbox.value() != newVal):
            qtBlockAndCall(spinbox, spinbox.setValue,newVal)
        if(command):
            self.send_value(cls,command,val)
    
    def spinboxChanged_UpdateSlider(self, val : float, slider : QSlider, factor : float):
        newVal = int(round(val * factor))
        if (slider.value() != newVal) :
            slider.setValue(newVal)
            
        
    @throttle(50)
    def sliderChanged_UpdateLabel(self, val : int, label : QLabel, pattern :str, factor: float, cls : str=None, command : str=None):
        """when a slider move, and it provide a command, the slider update de label using the pattern
        and send to the board the Value
        """
        newVal = val * factor
        chaine = pattern.format(newVal)
        if(label.text != chaine):
            qtBlockAndCall(label, label.setText,chaine)
        if(command):
            self.send_value(cls,command,val)
            
    @throttle(50)
    def cffilter_changed(self,v,send=False):
        self.tech_log.debug("Freq %s send %d", v, send)
        freq = max(min(v,500),0)
        
        if self.horizontalSlider_cffilter.value != freq :
            self.horizontalSlider_cffilter.setValue(freq)
        
        if send:
            self.send_value("fx","filterCfFreq",(freq))
        
        lbl = str(freq)+"Hz"
        if(freq == 500):
            lbl = "Off"
            qOn = False
        
        self.label_cffilter.setText(lbl)
        
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
        
    def refresh_limit_ui(self, slider : QSlider) :
        if slider == self.horizontalSlider_damper :
            self.display_speed_cutoff_damper(slider.value())
        elif slider == self.horizontalSlider_friction :
            self.display_speed_cutoff_friction(slider.value())
        elif slider == self.horizontalSlider_inertia :
            self.display_accel_cutoff_inertia(slider.value())
            
    #######################################################################################################
    #                                            Board CallBack
    #######################################################################################################
    
    def cpr_cb(self,val : int):
        if val > 0:
            self.cpr = val
        
    def enc_pos_cb(self,val : int):
        if self.cpr > 0:
            rots = val / self.cpr
            degs = rots * 360
            self.doubleSpinBox_curdeg.setValue(degs)

    def dataChanged_UpdateSliderAndSpinbox(self,val : float,slider : QSlider,spinbox : QSpinBox,factor : float):
        newval = int(round(val,1))
        qtBlockAndCall(slider, slider.setValue, newval)
        qtBlockAndCall(spinbox, spinbox.setValue,newval * factor)
        self.refresh_limit_ui(slider)
        
    def dataChanged_UpdateSliderAndLabel(self,val : float,slider : QSlider, label : QLabel, pattern : str, factor : float):
        newval = int(round(val))
        qtBlockAndCall(slider, slider.setValue, newval)
        self.sliderChanged_UpdateLabel(newval,label,pattern, factor)
        
    def update_gain_scaler(self,slider : QSlider,spinbox : QSpinBox, gain):
        spinbox.setMaximum(gain)
        self.sliderChanged_UpdateSpinbox(slider.value(), spinbox, gain)

    def set_spring_scaler_cb(self,repl):
        dat = map_infostring(repl)
        self.springgain = dat.get("scale",self.springgain)
        self.update_gain_scaler(self.horizontalSlider_spring, self.doubleSpinBox_spring, self.springgain)
    
    def set_damper_scaler_cb(self,repl):
        dat = map_infostring(repl)
        self.dampergain = dat.get("scale",self.dampergain)
        self.damper_internal_factor = dat.get("factor",self.damper_internal_factor)
        self.update_gain_scaler(self.horizontalSlider_damper, self.doubleSpinBox_damper, self.dampergain)
    
    def set_friction_scaler_cb(self,repl):
        dat = map_infostring(repl)
        self.frictiongain = dat.get("scale",self.frictiongain)
        self.friction_internal_factor = dat.get("factor",self.friction_internal_factor)
        self.update_gain_scaler(self.horizontalSlider_friction, self.doubleSpinBox_friction, self.frictiongain)
    
    def set_inertia_scaler_cb(self,repl):
        dat = map_infostring(repl)
        self.inertiagain = dat.get("scale",self.inertiagain)
        self.inertia_internal_factor = dat.get("factor",self.inertia_internal_factor)
        self.update_gain_scaler(self.horizontalSlider_inertia, self.doubleSpinBox_inertia, self.inertiagain)
    
    def set_friction_pct_speed_rampup_cb(self,value):
        self.friction_pct_speed_rampup = value
    