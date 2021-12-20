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
from base_ui import CommunicationHandler

class VescUI(WidgetUI,CommunicationHandler):
    prefix = None
    odriveStates = ["AXIS_STATE_UNDEFINED","AXIS_STATE_IDLE","AXIS_STATE_STARTUP_SEQUENCE","AXIS_STATE_FULL_CALIBRATION_SEQUENCE","AXIS_STATE_MOTOR_CALIBRATION","-","AXIS_STATE_ENCODER_INDEX_SEARCH","AXIS_STATE_ENCODER_OFFSET_CALIBRATION","AXIS_STATE_CLOSED_LOOP_CONTROL","AXIS_STATE_LOCKIN_SPIN","AXIS_STATE_ENCODER_DIR_FIND","AXIS_STATE_HOMING","AXIS_STATE_ENCODER_HALL_POLARITY_CALIBRATION","AXIS_STATE_ENCODER_HALL_PHASE_CALIBRATION"]
    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'vesc.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
        
        self.pushButton_apply.clicked.connect(self.apply)
        self.pushButton_manualRead.clicked.connect(self.manualEncPosRead)
        self.pushButton_eraseOffset.clicked.connect(self.eraseOffset)
        self.pushButton_refresh.clicked.connect(self.initUi)
        self.timer.timeout.connect(self.updateTimer)
        self.prefix = unique

        self.checkBox_useEncoder.stateChanged.connect(lambda val : self.sendValue("vesc","useencoder",(0 if val == 0 else 1),instance=self.prefix))
        self.registerCallback("vesc","canid",self.spinBox_id.setValue,self.prefix,int)
        self.registerCallback("vesc","canspd",self.updateCanSpd,self.prefix,int)
        self.registerCallback("vesc","useencoder",self.updateEncoderUI,self.prefix,int)
        self.registerCallback("vesc","offset",self.updateOffset,self.prefix,int)

        self.registerCallback("vesc","errorflags",self.errorCb,self.prefix,int)
        self.registerCallback("vesc","encrate",self.label_encoder_rate.setText,self.prefix,str)
        self.registerCallback("vesc","voltage",lambda mv : self.label_voltage.setText(f"{mv/1000}V"),self.prefix,int)
        self.registerCallback("vesc","pos",self.posCb,self.prefix,int)
        self.registerCallback("vesc","vescstate",self.stateCb,self.prefix,int)
        self.registerCallback("vesc","torque",self.torqueCb,self.prefix,int)
        
        self.initUi()

    def vescstate(self,i):
        _result = "Invalid state"
        if i == 0 :
            _result = "No connection"
        elif i == 1 :
            _result = "vesc FW incompatible"
        elif i == 2 :
            _result = "Comm ok"
        elif i == 3 :
            _result = "vesc compatible"
        elif i == 4 :
            _result = "ready"
        elif i == 5 :
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
        self.sendCommands("vesc",["canid","canspd","useencoder","offset"],self.prefix)
    
    def updateOffset(self, preset):
        self.doubleSpinBox_encoderOffset.setValue(preset / 10000)

    def updateCanSpd(self,preset):
        self.comboBox_baud.setCurrentIndex(preset-3) # 3 is lowest preset!

    def stateCb(self,state):
        self.label_state.setText(self.vescstate(state))

    def torqueCb(self,v):
        vesc_torque = math.ceil(v / 100)
        self.label_torque.setText(str(vesc_torque)) # not divide by 10000 but by 100 to display it in %
        if vesc_torque >= 0:
            self.progressBar_torqueneg.setValue(0)
            self.progressBar_torquepos.setValue(vesc_torque)
        else:
            self.progressBar_torqueneg.setValue(-vesc_torque)
            self.progressBar_torquepos.setValue(0)

    def posCb(self,v):
        vesc_encoder_position = ( 360 * v ) / 1000000000
        self.label_pos.setText("{:.2f}".format(vesc_encoder_position))
        self.horizontalSlider_pos.setValue(vesc_encoder_position)

    def errorCb(self,dat):
        txt = "Ok"
        if dat != 0:
            txt = "Error code " + str(dat)
        self.label_errors.setText(txt)


    def updateTimer(self):
        self.sendCommands("vesc",["vescstate","errorflags","voltage","pos","encrate","torque"],self.prefix)
 
    def apply(self):
        spdPreset = str(self.comboBox_baud.currentIndex()+3) # 3 is lowest preset!
        canId = str(self.spinBox_id.value())
        self.sendValue("vesc","canspd",spdPreset,instance=self.prefix)
        self.sendValue("vesc","canid",canId,instance=self.prefix)

        self.initUi() # Update UI
    
    def manualEncPosRead(self):
        self.sendCommand("vesc","forceposread",instance=self.prefix)

    def eraseOffset(self):
        self.sendValue("vesc","offset",0,instance=self.prefix)
        self.initUi()
