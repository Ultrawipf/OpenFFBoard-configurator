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
import portconf_ui

class OdriveUI(WidgetUI,CommunicationHandler):
    ODRIVE_STATES = ["AXIS_STATE_UNDEFINED","AXIS_STATE_IDLE","AXIS_STATE_STARTUP_SEQUENCE","AXIS_STATE_FULL_CALIBRATION_SEQUENCE","AXIS_STATE_MOTOR_CALIBRATION","-","AXIS_STATE_ENCODER_INDEX_SEARCH","AXIS_STATE_ENCODER_OFFSET_CALIBRATION","AXIS_STATE_CLOSED_LOOP_CONTROL","AXIS_STATE_LOCKIN_SPIN","AXIS_STATE_ENCODER_DIR_FIND","AXIS_STATE_HOMING","AXIS_STATE_ENCODER_HALL_POLARITY_CALIBRATION","AXIS_STATE_ENCODER_HALL_PHASE_CALIBRATION"]
    #odriveErrors = #["ODRIVE_ERROR_CONTROL_ITERATION_MISSED","ODRIVE_ERROR_DC_BUS_UNDER_VOLTAGE","ODRIVE_ERROR_DC_BUS_OVER_VOLTAGE","ODRIVE_ERROR_DC_BUS_OVER_REGEN_CURRENT","ODRIVE_ERROR_DC_BUS_OVER_CURRENT","ODRIVE_ERROR_BRAKE_DEADTIME_VIOLATION","ODRIVE_ERROR_BRAKE_DUTY_CYCLE_NAN","ODRIVE_ERROR_INVALID_BRAKE_RESISTANCE"]
    # ODRIVE_ERRORS = {"AXIS_ERROR_NONE" : 0x00000000,"AXIS_ERROR_INVALID_STATE" : 0x00000001, "AXIS_ERROR_WATCHDOG_TIMER_EXPIRED" : 0x00000800,"AXIS_ERROR_MIN_ENDSTOP_PRESSED" : 0x00001000, "AXIS_ERROR_MAX_ENDSTOP_PRESSED" : 0x00002000,"AXIS_ERROR_ESTOP_REQUESTED" : 0x00004000,"AXIS_ERROR_HOMING_WITHOUT_ENDSTOP" : 0x00020000,"AXIS_ERROR_OVER_TEMP": 0x00040000,"AXIS_ERROR_UNKNOWN_POSITION" : 0x00080000}
    ODRIVE_ERRORS = {"AXIS_ERROR_NONE" : 0x00000000,"INITIALIZING" : 0x00000001, "SYSTEM_LEVEL" : 0x2,"TIMING_ERROR" : 0x4, "MISSING_ESTIMATE" : 0x8,"BAD_CONFIG" : 0x10,"DRV_FAULT" : 0x20,"MISSING_INPUT": 0x64,"DC_BUS_OVER_VOLTAGE" : 0x100,"DC_BUS_UNDER_VOLTAGE":0x200,"DC_BUS_OVER_CURRENT":0x400,"DC_BUS_OVER_REGEN_CURRENT":0x800,"CURRENT_LIMIT_VIOLATION":0x1000,"MOTOR_OVER_TEMP":0x2000,"INVERTER_OVER_TEMP":0x4000,"VELOCITY_LIMIT_VIOLATION":0x8000,"POSITION_LIMIT_VIOLATION":0x10000,"WATCHDOG_TIMER_EXPIRED" : 0x1000000, "ESTOP_REQUESTED" :0x2000000,"SPINOUT_DETECTED" : 0x4000000,"OTHER_DEVICE_FAILED" : 0x8000000,"CALIBRATION_ERROR" : 0x40000000 }
    

    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'odrive.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi

        self.timer = QTimer(self)
        self.canOptions = portconf_ui.CanOptionsDialog(0,"CAN",main)
        self.pushButton_apply.clicked.connect(self.apply)
        self.pushButton_cansettings.clicked.connect(self.canOptions.exec)
        #self.pushButton_anticogging.clicked.connect(self.antigoggingBtn) #TODO test first
        self.timer.timeout.connect(self.updateTimer)
        self.prefix = unique
        self.connected = False

        self.register_callback("odrv","canid",self.spinBox_id.setValue,self.prefix,int)
        #self.registerCallback("odrv","canspd",self.updateCanSpd,self.prefix,int)
        self.register_callback("odrv","connected",self.connectedCb,self.prefix,int)
        self.register_callback("odrv","maxtorque",self.updateTorque,self.prefix,int)
        self.register_callback("odrv","vbus",self.voltageCb,self.prefix,int)
        self.register_callback("odrv","errors",lambda v : self.showErrors(v),self.prefix,int)
        self.register_callback("odrv","state",lambda v : self.stateCb(v),self.prefix,int)

        self.init_ui()
        
    # Tab is currently shown
    def showEvent(self,event):
        self.init_ui()
        self.timer.start(500)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    def init_ui(self):
        commands = ["canid","canspd","maxtorque"]
        self.send_commands("odrv",commands,self.prefix)

       
    def connectedCb(self,v):
        self.connected = False if v == 0 else True

    # def updateCanSpd(self,preset):
    #     self.comboBox_baud.setCurrentIndex(preset-3) # 3 is lowest preset!

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

        for name,i in (self.ODRIVE_ERRORS.items()):
            if(codes & i != 0):
                errs.append(name)
        if len(errs) == 0:
            errs = [str(codes)]
        errString = "\n".join(errs)

        self.label_errornames.setText(f"{errString} ({codes})")

    def stateCb(self,dat):
        if not self.connected:
            self.label_state.setText("Not connected")
            return
        if(dat < len(self.ODRIVE_STATES)):
            self.label_state.setText(self.ODRIVE_STATES[dat])
        else:
            self.label_state.setText(str(dat))


    def updateTimer(self):
        self.send_commands("odrv",["connected","vbus","errors","state"],self.prefix)
        #self.serial_get_async(["odriveVbus?","odriveErrors?","odriveState?"],self.statusUpdateCb,int,self.prefix)

        
    def apply(self):
        #spdPreset = str(self.comboBox_baud.currentIndex()+3) # 3 is lowest preset!
        canId = str(self.spinBox_id.value())
        torqueScaler = str(int(self.doubleSpinBox_torque.value() * 100))
        #self.send_value("odrv","canspd",spdPreset,instance=self.prefix)
        self.send_value("odrv","canid",canId,instance=self.prefix)
        self.send_value("odrv","maxtorque",torqueScaler,instance=self.prefix)


        self.init_ui() # Update UI

