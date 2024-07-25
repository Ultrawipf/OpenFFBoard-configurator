from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt6 import uic
from helper import res_path,classlistToIds
from PyQt6.QtCore import QTimer
import main
from base_ui import WidgetUI
from base_ui import CommunicationHandler

class TMCDebugUI(WidgetUI,CommunicationHandler):
    
    def __init__(self, main=None, unique=1):
        WidgetUI.__init__(self, main,'tmcdebug.ui')
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
        self.timer_slow = QTimer(self)

        self.pwm = 0
        self.speed = 0
        self.axis = 0
        self.openloopenabled = False
        self.adc_to_amps = 0

        self.timer.timeout.connect(self.updateTimer)
        self.timer_slow.timeout.connect(self.updateTimerSlow)

        self.register_callback("tmc","acttrq",self.updateCurrent,self.axis,str)
        self.register_callback("tmc","state",self.stateCb,self.axis,str,typechar='?')
        self.register_callback("tmc","iScale",self.setCurrentScaler,self.axis,float)

        self.horizontalSlider_speed.valueChanged.connect(self.speedchanged)
        self.horizontalSlider_pwm.valueChanged.connect(self.pwmchanged)
        self.pushButton_openloop.clicked.connect(lambda : self.set_openloop(True))
        self.checkBox_reverse.stateChanged.connect(lambda : self.speedchanged(self.speed))
        self.init_ui()


    def init_ui(self):
        self.send_commands("tmc",["state","iScale"],self.axis)

    def updateTimer(self):
        self.send_command("tmc","acttrq",self.axis)

    def updateTimerSlow(self):
        self.send_command("tmc","state",self.axis)

    def stateCb(self,state):
        intstate = int(state)
        if(intstate == 3 or intstate == 2):
            self.set_ready(True)
    
    def hideEvent(self,event):
        self.timer.stop()
        self.timer_slow.stop()

    def showEvent(self,event):
        self.init_ui()
        self.timer.start(100)
        self.timer_slow.start(1000)

    def set_ready(self,ready):
        self.pushButton_openloop.setEnabled(ready)
    
    def set_openloop(self,enable):
        self.openloopenabled = enable
        self.groupBox_openlooptest.setEnabled(enable)
        self.send_value("main","openloopspeed",instance=self.axis,val=0,adr=0)
        self.horizontalSlider_speed.setValue(0)
        self.horizontalSlider_pwm.setValue(0)
    
    def setCurrentScaler(self,x):
        if x != self.adc_to_amps:
            self.adc_to_amps = x
            if x != 0:
                self.spinBox_current.setSuffix("mA")
            else:
                self.spinBox_current.setSuffix("/32787")
            
    
    def updateCurrent(self,torqueflux):
        tflist = [(int(v)) for v in torqueflux.split(":")]
        torque = abs(tflist[0])
        flux = tflist[1]
        currents = complex(torque,flux)
        self.progressBar_power.setValue(int(abs(currents)))
        if self.adc_to_amps != 0:
            self.spinBox_current.setValue(int(abs(currents*self.adc_to_amps*1000)))
        else:
            self.spinBox_current.setValue(int(abs(currents)))

    def speedchanged(self,speed):
        self.speed = speed
        newspeed = -self.speed if self.checkBox_reverse.isChecked() else self.speed
        self.send_value("main","openloopspeed",instance=self.axis,val=newspeed,adr=self.pwm)

    def pwmchanged(self,pwm):
        self.pwm = pwm
        self.spinBox_pwm.setValue(int(pwm/200))
        self.send_value("main","openloopspeed",instance=self.axis,val=self.speed,adr=self.pwm)