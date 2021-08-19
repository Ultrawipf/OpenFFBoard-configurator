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
    odriveErrors = ["ODRIVE_ERROR_CONTROL_ITERATION_MISSED","ODRIVE_ERROR_DC_BUS_UNDER_VOLTAGE","ODRIVE_ERROR_DC_BUS_OVER_VOLTAGE","ODRIVE_ERROR_DC_BUS_OVER_REGEN_CURRENT","ODRIVE_ERROR_DC_BUS_OVER_CURRENT","ODRIVE_ERROR_BRAKE_DEADTIME_VIOLATION","ODRIVE_ERROR_BRAKE_DUTY_CYCLE_NAN","ODRIVE_ERROR_INVALID_BRAKE_RESISTANCE"]
    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'odrive.ui')
        self.main = main #type: main.MainUi
        self.timer = QTimer(self)
        self.initUi()
        self.pushButton_apply.clicked.connect(self.apply)
        #self.pushButton_anticogging.clicked.connect(self.antigoggingBtn) #TODO test first
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
    
    # def antigoggingBtn(self):
    #     def anticogging( btn):
    #         cmd = btn.text()
    #         if(cmd=="OK"):
    #             self.main.comms.serialWrite("odriveAnticogging=1\n")

    #     msg = QMessageBox()
    #     msg.setIcon(QMessageBox.Warning)
    #     msg.setText("Start Anticogging calibration?\nThis can take a very long time or may not work if the position controller is not tuned!")
    #     msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    #     msg.buttonClicked.connect(anticogging)
    #     msg.exec_()

    def updateCanSpd(self,preset):
        self.comboBox_baud.setCurrentIndex(preset-3) # 3 is lowest preset!

    def updateTorque(self,torque):
        self.doubleSpinBox_torque.setValue(torque/100)

    def shorErrors(self,codes):
        errs = []
        if(codes == 0):
            errs = ["None"]

        for i,name in enumerate(self.odriveErrors):
            if(codes & 1 << i) != 0:
                errs.append(name)
        errString = "\n".join(errs)

        self.label_errornames.setText(errString)

    def statusUpdateCb(self,dat):
        self.label_voltage.setText("{}V".format(dat[0]/1000))
        #self.label_errors.setText("{:02x}".format(dat[1]))
        self.shorErrors(dat[1])
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

