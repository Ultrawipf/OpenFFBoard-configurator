from PyQt6.QtCore import QTimer
import main
from base_ui import WidgetUI
from base_ui import CommunicationHandler

class SimplemotionUI(WidgetUI,CommunicationHandler):
    SM_STATES = ["RESERVED","TARGET_REACHED","FERROR_RECOVERY","RUNNING","ENABLED","<font color='red'>FAULTSTOP</font>","<font color='orange'>FERROR_WARNING</font>","<font color='red'>STO_ACTIVE</font>","SERVO_READY","BRAKING","HOMING","AXIS_STATE_HOMING","INITIALIZED","VOLTAGES_OK","<font color='red'>PERMANENT_STOP</font>"]
    
    def __init__(self, main=None, unique=None):
        WidgetUI.__init__(self, main,'simplemotion.ui')
        CommunicationHandler.__init__(self)
        self.main = main #type: main.MainUi
        self.prefix = unique
        self.crcerr = 0
        self.uarterr = 0
        self.register_callback("sm2","state",self.stateCb,self.prefix,int)
        self.register_callback("sm2","voltage",lambda v: self.doubleSpinBox_voltage.setValue(v/1000),self.prefix,int)
        self.register_callback("sm2","torque",lambda v: self.doubleSpinBox_torque.setValue(v/1000),self.prefix,int)
        self.register_callback("sm2","crcerr",self.crcErrCb,self.prefix,int)
        self.register_callback("sm2","uarterr",self.uartErrCb,self.prefix,int)
        self.pushButton_restart.clicked.connect(self.restart)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)
        self.init_ui()
        
    # Tab is currently shown
    def showEvent(self,event):
        self.init_ui()
        self.timer.start(1000)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    def init_ui(self):
        commands = ["state","voltage","torque"]
        self.send_commands("sm2",commands,self.prefix)

    def stateCb(self,codes):
        if not codes:
            self.label_state.setText("Not connected")
            return
        states = []

        for i,name in enumerate(self.SM_STATES):
            if(codes & 1<<i != 0):
                states.append(name)
        if len(states) == 0:
            states = [str(states)]
        statstr = "<br>".join(states)

        self.label_state.setText(statstr)
    
    def crcErrCb(self,v):
        self.crcerr = v

    def uartErrCb(self,v):
        self.uarterr = v
        self.updateErrText()

    def restart(self):
        self.send_command("sm2","restart",self.prefix)
        

    def updateErrText(self):
        if self.crcerr == 0 and self.uarterr == 0:
            self.label_comm_errors.setText("No communication errors")
            return
        text = "Errors: "
        if self.crcerr:
            text+=f"CRC: {self.crcerr} "
        if self.uarterr:
            text+=f"UART: {self.uarterr} "
        self.label_comm_errors.setText(text)


    def updateTimer(self):
        commands = ["state","crcerr","voltage","uarterr","torque"]
        self.send_commands("sm2",commands,self.prefix)