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

class OdriveUI(WidgetUI,CommunicationHandler):
    prefix = None
    odriveStates = ["AXIS_STATE_UNDEFINED","AXIS_STATE_IDLE","AXIS_STATE_STARTUP_SEQUENCE","AXIS_STATE_FULL_CALIBRATION_SEQUENCE","AXIS_STATE_MOTOR_CALIBRATION","-","AXIS_STATE_ENCODER_INDEX_SEARCH","AXIS_STATE_ENCODER_OFFSET_CALIBRATION","AXIS_STATE_CLOSED_LOOP_CONTROL","AXIS_STATE_LOCKIN_SPIN","AXIS_STATE_ENCODER_DIR_FIND","AXIS_STATE_HOMING","AXIS_STATE_ENCODER_HALL_POLARITY_CALIBRATION","AXIS_STATE_ENCODER_HALL_PHASE_CALIBRATION"]
    #odriveErrors = #["ODRIVE_ERROR_CONTROL_ITERATION_MISSED","ODRIVE_ERROR_DC_BUS_UNDER_VOLTAGE","ODRIVE_ERROR_DC_BUS_OVER_VOLTAGE","ODRIVE_ERROR_DC_BUS_OVER_REGEN_CURRENT","ODRIVE_ERROR_DC_BUS_OVER_CURRENT","ODRIVE_ERROR_BRAKE_DEADTIME_VIOLATION","ODRIVE_ERROR_BRAKE_DUTY_CYCLE_NAN","ODRIVE_ERROR_INVALID_BRAKE_RESISTANCE"]
    odriveErrors = {"AXIS_ERROR_NONE" : 0x00000000,"AXIS_ERROR_INVALID_STATE" : 0x00000001, "AXIS_ERROR_WATCHDOG_TIMER_EXPIRED" : 0x00000800,"AXIS_ERROR_MIN_ENDSTOP_PRESSED" : 0x00001000, "AXIS_ERROR_MAX_ENDSTOP_PRESSED" : 0x00002000,"AXIS_ERROR_ESTOP_REQUESTED" : 0x00004000,"AXIS_ERROR_HOMING_WITHOUT_ENDSTOP" : 0x00020000,"AXIS_ERROR_OVER_TEMP": 0x00040000,"AXIS_ERROR_UNKNOWN_POSITION" : 0x00080000}


    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'odrive.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
        
        self.pushButton_apply.clicked.connect(self.apply)
        #self.pushButton_anticogging.clicked.connect(self.antigoggingBtn) #TODO test first
        self.timer.timeout.connect(self.updateTimer)
        self.prefix = unique
        self.connected = False

        self.registerCallback("odrv","canid",self.spinBox_id.setValue,self.prefix,int)
        self.registerCallback("odrv","canspd",self.updateCanSpd,self.prefix,int)
        self.registerCallback("odrv","connected",self.connectedCb,self.prefix,int)
        self.registerCallback("odrv","maxtorque",self.updateTorque,self.prefix,int)
        self.registerCallback("odrv","vbus",self.voltageCb,self.prefix,int)
        self.registerCallback("odrv","errors",lambda v : self.showErrors(v),self.prefix,int)
        self.registerCallback("odrv","state",lambda v : self.stateCb(v),self.prefix,int)

        self.initUi()
        
    # Tab is currently shown
    def showEvent(self,event):
        self.initUi()
        self.timer.start(500)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    def initUi(self):
        commands = ["canid","canspd","maxtorque"]
        self.sendCommands("odrv",commands,self.prefix)

       
    def connectedCb(self,v):
        self.connected = False if v == 0 else True

    def updateCanSpd(self,preset):
        self.comboBox_baud.setCurrentIndex(preset-3) # 3 is lowest preset!

    def updateTorque(self,torque):
        self.doubleSpinBox_torque.setValue(torque/100)

    def voltageCb(self,v):
        if not self.connected:
            self.label_voltage.setText("Not connected")
            return
        self.label_voltage.setText("{}V".format(v/1000))

    def showErrors(self,codes):
        if not self.connected:
            self.label_errornames.setText("Not connected")
            return
        errs = []
        if(codes == 0):
            errs = ["None"]

        for name,i in (self.odriveErrors.items()):
            if(codes & i != 0):
                errs.append(name)
        if len(errs) == 0:
            errs = [str(codes)]
        errString = "\n".join(errs)

        self.label_errornames.setText(errString)

    def stateCb(self,dat):
        if not self.connected:
            self.label_state.setText("Not connected")
            return
        if(dat < len(self.odriveStates)):
            self.label_state.setText(self.odriveStates[dat])
        else:
            self.label_state.setText(str(dat))


    def updateTimer(self):
        self.sendCommands("odrv",["connected","vbus","errors","state"],self.prefix)
        #self.main.comms.serialGetAsync(["odriveVbus?","odriveErrors?","odriveState?"],self.statusUpdateCb,int,self.prefix)

        
    def apply(self):
        spdPreset = str(self.comboBox_baud.currentIndex()+3) # 3 is lowest preset!
        canId = str(self.spinBox_id.value())
        torqueScaler = str(int(self.doubleSpinBox_torque.value() * 100))
        self.sendValue("odrv","canspd",spdPreset,instance=self.prefix)
        self.sendValue("odrv","canid",canId,instance=self.prefix)
        self.sendValue("odrv","maxtorque",torqueScaler,instance=self.prefix)


        self.initUi() # Update UI

