from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI

class OdriveUI(WidgetUI):
    prefix = None
    odriveStates = ["AXIS_STATE_UNDEFINED","AXIS_STATE_IDLE","AXIS_STATE_STARTUP_SEQUENCE","AXIS_STATE_FULL_CALIBRATION_SEQUENCE","AXIS_STATE_MOTOR_CALIBRATION","-","AXIS_STATE_ENCODER_INDEX_SEARCH","AXIS_STATE_ENCODER_OFFSET_CALIBRATION","AXIS_STATE_CLOSED_LOOP_CONTROL","AXIS_STATE_LOCKIN_SPIN","AXIS_STATE_ENCODER_DIR_FIND","AXIS_STATE_HOMING","AXIS_STATE_ENCODER_HALL_POLARITY_CALIBRATION","AXIS_STATE_ENCODER_HALL_PHASE_CALIBRATION"]
    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'odrive.ui')
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
        self.initUi()
        self.pushButton_apply.clicked.connect(self.apply)
        self.timer.timeout.connect(self.updateTimer)
        self.prefix = unique
        
    # Tab is currently shown
    def showEvent(self,event):
        self.initUi()
        self.timer.start(500)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    def initUi(self):
        self.main.comms.serialGetAsync("odriveCanId?",self.spinBox_id.setValue,int,self.prefix)
        self.main.comms.serialGetAsync("odriveCanSpd?",self.updateCanSpd,int,self.prefix)
        self.main.comms.serialGetAsync("odriveMaxTorque?",self.updateTorque,int,self.prefix)
    
    def updateCanSpd(self,preset):
        self.comboBox_baud.setCurrentIndex(preset-3) # 3 is lowest preset!

    def updateTorque(self,torque):
        self.doubleSpinBox_torque.setValue(torque/100)

    def statusUpdateCb(self,dat):
        self.label_voltage.setText("{}V".format(dat[0]/1000))
        self.label_errors.setText("{:02x}".format(dat[1]))
        self.label_state.setText(self.odriveStates[dat[2]])


    def updateTimer(self):
        self.main.comms.serialGetAsync(["odriveVbus?","odriveErrors?","odriveState?"],self.statusUpdateCb,int,self.prefix)

 
    def apply(self):
        spdPreset = str(self.comboBox_baud.currentIndex()+3) # 3 is lowest preset!
        canId = str(self.spinBox_id.value())
        torqueScaler = str(int(self.doubleSpinBox_torque.value() * 100))
        self.main.comms.serialWrite(self.prefix+"."+"odriveCanSpd="+spdPreset+";")
        self.main.comms.serialWrite(self.prefix+"."+"odriveCanId="+canId+";")
        self.main.comms.serialWrite(self.prefix+"."+"odriveMaxTorque="+torqueScaler+";")
        self.initUi() # Update UI

