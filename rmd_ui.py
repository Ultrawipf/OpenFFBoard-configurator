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

class RmdUI(WidgetUI,CommunicationHandler):
    ERRORS = {"Stall" : 0x02,"Undervoltage" : 0x04, "Overvoltage" : 0x08,"Overcurrent" : 0x10, "Overpower" : 0x40,"Write err" : 0x80,"Overspeed" : 0x100,"Overtemperature": 0x10000,"Calibration error" : 0x2000}
    

    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'rmdmotor.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi

        self.timer = QTimer(self)
        self.canOptions = portconf_ui.CanOptionsDialog(0,"CAN",main)
        self.pushButton_apply.clicked.connect(self.apply)
        self.pushButton_cansettings.clicked.connect(self.canOptions.exec)
        self.timer.timeout.connect(self.updateTimer)
        self.prefix = unique
        self.connected = False
        self.activepos = True

        self.register_callback("rmd","canid",self.spinBox_id.setValue,self.prefix,int)
        self.register_callback("rmd","maxtorque",self.updateTorque,self.prefix,int)
        self.register_callback("rmd","vbus",self.voltageCb,self.prefix,int)
        self.register_callback("rmd","errors",lambda v : self.showErrors(v),self.prefix,int)
        self.register_callback("rmd","model",self.modelcb,self.prefix,str)
        self.register_callback("rmd","requestpos",self.requestposcb,self.prefix,int)

        self.init_ui()
        
    # Tab is currently shown
    def showEvent(self,event):
        self.init_ui()
        self.timer.start(1000)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    def init_ui(self):
        commands = ["canid","maxtorque","requestpos","model"]
        self.send_commands("rmd",commands,self.prefix)

       
    def modelcb(self,v):
        self.label_model.setText(v)

    def requestposcb(self,v):
        self.checkBox_activerequests.setChecked(v != 0)
        self.activepos = v != 0

    def updateTorque(self,torque):
        self.doubleSpinBox_torque.setValue(torque/100)

    def voltageCb(self,v):
        if not self.activepos:
            self.label_voltage.setText("Not available")
            return
        self.label_voltage.setText("{}V".format(v/10))

    def showErrors(self,codes):
        errs = []
        if(codes == 0):
            errs = ["None"]

        for name,i in (self.ERRORS.items()):
            if(codes & i != 0):
                errs.append(name)
        if len(errs) == 0:
            errs = [str(codes)]
        errString = "\n".join(errs)

        self.label_errornames.setText(f"{errString} ({codes})")

    def updateTimer(self):
        if self.activepos:
            self.send_commands("rmd",["vbus","errors"],self.prefix)
        else:
            self.send_commands("rmd",["errors"],self.prefix)
        
        
    def apply(self):
        canId = str(self.spinBox_id.value())
        torqueScaler = str(int(self.doubleSpinBox_torque.value() * 100))
        self.send_value("rmd","canid",canId,instance=self.prefix)
        self.send_value("rmd","maxtorque",torqueScaler,instance=self.prefix)
        self.send_value("rmd","requestpos",1 if self.checkBox_activerequests.isChecked() else 0,instance=self.prefix)
        self.activepos = self.checkBox_activerequests.isChecked()
        if not self.activepos:
            self.voltageCb(0)

        self.init_ui() # Update UI

