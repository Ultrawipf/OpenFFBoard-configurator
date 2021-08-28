from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI

class VescUI(WidgetUI):
    prefix = None
    odriveStates = ["AXIS_STATE_UNDEFINED","AXIS_STATE_IDLE","AXIS_STATE_STARTUP_SEQUENCE","AXIS_STATE_FULL_CALIBRATION_SEQUENCE","AXIS_STATE_MOTOR_CALIBRATION","-","AXIS_STATE_ENCODER_INDEX_SEARCH","AXIS_STATE_ENCODER_OFFSET_CALIBRATION","AXIS_STATE_CLOSED_LOOP_CONTROL","AXIS_STATE_LOCKIN_SPIN","AXIS_STATE_ENCODER_DIR_FIND","AXIS_STATE_HOMING","AXIS_STATE_ENCODER_HALL_POLARITY_CALIBRATION","AXIS_STATE_ENCODER_HALL_PHASE_CALIBRATION"]
    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'vesc.ui')
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
        self.initUi()
        self.pushButton_apply.clicked.connect(self.apply)
        self.pushButton_manualRead.clicked.connect(self.manualEncPosRead)
        self.timer.timeout.connect(self.updateTimer)
        self.prefix = unique

    def vescstate(self,i):
        _result = "Invalid state"
        if i == 0 :
            _result = "No connection"
        elif i == 1 :
            _result = "Comm ok"
        elif i == 2 :
            _result = "ready"
        elif i == 3 :
            _result = "error"
        
        return _result
        
    # Tab is currently shown
    def showEvent(self,event):
        self.initUi()
        self.timer.start(500)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    def initUi(self):
        self.main.comms.serialGetAsync("vescCanId?",self.spinBox_id.setValue,int,self.prefix)
        self.main.comms.serialGetAsync("vescCanSpd?",self.updateCanSpd,int,self.prefix)
    
    def updateCanSpd(self,preset):
        self.comboBox_baud.setCurrentIndex(preset-3) # 3 is lowest preset!

    def statusUpdateCb(self,dat):
        
        vesc_state_label = self.vescstate(dat[0])

        if dat[0] == 0:
            remote_state = "-"
        elif dat[1] == 0:
            remote_state = "ok"
        else:
            remote_state = "Error code " + str(dat[1]) + ", (use vesctool)" 

        self.label_state.setText(vesc_state_label)
        self.label_errors.setText(remote_state)
        self.label_encoder_rate.setText(str(dat[2]))
        self.label_pos.setText(str((360*dat[3])/1000000000))
        self.label_torque.setText(str(dat[4]/100)) # not divide by 10000 but by 100 to display it in %

    def updateTimer(self):
        self.main.comms.serialGetAsync(["vescState?","vescErrorFlag?","vescEncRate?","vescPos?","vescTorque?"],self.statusUpdateCb,int,self.prefix)
 
    def apply(self):
        spdPreset = str(self.comboBox_baud.currentIndex()+3) # 3 is lowest preset!
        canId = str(self.spinBox_id.value())
        self.main.comms.serialWrite(self.prefix+"."+"vescCanSpd="+spdPreset+";")
        self.main.comms.serialWrite(self.prefix+"."+"vescCanId="+canId+";")
        self.initUi() # Update UI
    
    def manualEncPosRead(self):
        self.main.comms.serialWrite(self.prefix+"."+"vescPosReadForce=1;")

