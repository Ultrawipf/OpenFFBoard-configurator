from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
from base_ui import WidgetUI
import math

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
        self.pushButton_eraseOffset.clicked.connect(self.eraseOffset)
        self.pushButton_refresh.clicked.connect(self.initUi)
        self.timer.timeout.connect(self.updateTimer)
        self.prefix = unique

        self.checkBox_useEncoder.stateChanged.connect(lambda val : self.main.comms.serialWrite("vescUseEncoder="+("0" if val == 0 else "1")+"\n"))


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

    def updateEncoderUI(self, dat):
        self.checkBox_useEncoder.setChecked(dat)
        visible = dat==1
        self.label_6.setVisible(visible)
        self.label_encoder_rate.setVisible(visible)
        self.label_pos.setVisible(visible)
        self.label_7.setVisible(visible)
        self.horizontalSlider_pos.setVisible(visible)
        self.line.setVisible(visible)
        self.label_9.setVisible(visible)
        self.doubleSpinBox_encoderOffset.setVisible(visible)
        self.pushButton_manualRead.setVisible(visible)
        self.pushButton_eraseOffset.setVisible(visible)


    def initUi(self):
        self.main.comms.serialGetAsync("vescCanId?",self.spinBox_id.setValue,int,self.prefix)
        self.main.comms.serialGetAsync("vescCanSpd?",self.updateCanSpd,int,self.prefix)
        self.main.comms.serialGetAsync("vescUseEncoder?",self.updateEncoderUI,int)
        self.main.comms.serialGetAsync("vescOffset?",self.updateOffset,int)
    
    def updateOffset(self, preset):
        self.doubleSpinBox_encoderOffset.setValue(preset / 10000)

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

        vesc_encoder_rate = dat[2]
        vesc_encoder_position = ( 360 * dat[3] ) / 1000000000
        vesc_torque = math.ceil(dat[4] / 100)

        self.label_state.setText(vesc_state_label)
        self.label_errors.setText(remote_state)
        self.label_encoder_rate.setText(str(vesc_encoder_rate))
        self.label_pos.setText("{:.2f}".format(vesc_encoder_position))
        self.label_torque.setText(str(vesc_torque)) # not divide by 10000 but by 100 to display it in %

        self.horizontalSlider_pos.setValue(vesc_encoder_position)

        if vesc_torque >= 0:
            self.progressBar_torqueneg.setValue(0)
            self.progressBar_torquepos.setValue(vesc_torque)
        else:
            self.progressBar_torqueneg.setValue(-vesc_torque)
            self.progressBar_torquepos.setValue(0)

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

    def eraseOffset(self):
        self.main.comms.serialWrite(self.prefix+"."+"vescOffset=0;")
        self.initUi()
