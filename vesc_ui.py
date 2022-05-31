from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt6 import uic
from helper import res_path,classlistToIds
from PyQt6.QtCore import QTimer
import main
from base_ui import WidgetUI
import math
from base_ui import CommunicationHandler
import portconf_ui

class VescUI(WidgetUI,CommunicationHandler):
    prefix = None
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
        self.canOptions = portconf_ui.CanOptionsDialog(0,"CAN",main)
        self.pushButton_cansettings.clicked.connect(self.canOptions.exec)

        #self.checkBox_useEncoder.stateChanged.connect(lambda val : self.sendValue("vesc","useencoder",(0 if val == 0 else 1),instance=self.prefix))
        self.registerCallback("vesc","offbcanid",self.spinBox_OFFB_can_id.setValue,self.prefix,int)
        self.registerCallback("vesc","vesccanid",self.spinBox_VESC_can_Id.setValue,self.prefix,int)
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
        self.pushButton_eraseOffset.setVisible(visible)


    def initUi(self):
        self.sendCommands("vesc",["offbcanid", "vesccanid",  "useencoder", "offset"],self.prefix)
    
    def updateOffset(self, preset):
        self.doubleSpinBox_encoderOffset.setValue(preset / 10000)

    # def updateCanSpd(self,preset):
    #     self.comboBox_baud.setCurrentIndex(preset-3) # 3 is lowest preset!

    def stateCb(self,state):
        self.label_state.setText(self.vescstate(state))
        if (state == 0) and (self.label_errors.isEnabled()):
            self.label_errors.setEnabled(0)
            self.label_voltage.setEnabled(0)
            self.label_encoder_rate.setEnabled(0)
        elif (state != 0) and (not self.label_errors.isEnabled()):
            self.label_errors.setEnabled(1)
            self.label_voltage.setEnabled(1)
            self.label_encoder_rate.setEnabled(1)

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
        OpenFFBoardCANId = str(self.spinBox_OFFB_can_id.value())
        VESCCANId = str(self.spinBox_VESC_can_Id.value())
        self.sendValue("vesc","offbcanid",OpenFFBoardCANId,instance=self.prefix)
        self.sendValue("vesc","vesccanid",VESCCANId,instance=self.prefix)
        self.sendValue("vesc","useencoder",(1 if self.checkBox_useEncoder.isChecked() else 0),instance=self.prefix)
        self.initUi() # Update UI
    
    def manualEncPosRead(self):
        self.sendCommand("vesc","forceposread",instance=self.prefix)

    def eraseOffset(self):
        self.sendValue("vesc","offset",0,instance=self.prefix)
        self.initUi()
