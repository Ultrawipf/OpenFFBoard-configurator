from PyQt6.QtWidgets import QMainWindow, QSlider
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QToolButton 
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QGridLayout,QSpinBox
from PyQt6 import uic
from helper import res_path,classlistToIds,splitListReply,throttle
from PyQt6.QtCore import QTimer,QEvent, pyqtSignal
import main
import buttonconf_ui
import analogconf_ui
from base_ui import WidgetUI,CommunicationHandler
from serial_comms import SerialComms
import portconf_ui
from helper import map_infostring

class CanRemoteUi(WidgetUI,CommunicationHandler):

    ffb_rate_event = pyqtSignal(list)

    def __init__(self, main : 'main.MainUi'=None,  title = "CAN remote source"):
        WidgetUI.__init__(self, main,'remotecanclass.ui')
        CommunicationHandler.__init__(self)


        self.main = main 
        self.btnClasses = []
        self.btnIds = []
        self.axisClasses = {}
        self.axisIds = []
        self.buttonbtns = QButtonGroup()
        self.buttonconfbuttons = []
        self.axisbtns = QButtonGroup()
        self.axisconfbuttons = []
        self.active = 0
        self.rate = 0
        self.dvals = [0]
        self.avals = [0]

        self.canOptions = portconf_ui.CanOptionsDialog(0,"CAN",main)

        self.timer = QTimer(self)
        self.buttonbtns.setExclusive(False)
        self.axisbtns.setExclusive(False)

        self.timer.timeout.connect(self.updateTimer)

        self.register_callback("main","lsbtn",self.updateButtonClassesCB,0)
        self.register_callback("main","btntypes",self.updateButtonSources,0,int)
        self.register_callback("main","lsain",self.updateAnalogClassesCB,0)
        self.register_callback("main","aintypes",self.updateAnalogSources,0,int)
        self.register_callback("main","canidbtn",self.spinBox_digital_id.setValue,0,int)
        self.register_callback("main","canidain",self.spinBox_analog_id.setValue,0,int)
        self.register_callback("main","rate",self.reportrate_cb,0,typechar='!')
        self.register_callback("main","rate",self.comboBox_reportrate.setCurrentIndex,0,int,typechar='?')
        self.register_callback("main","dvals",self.dvalsCb,0)
        self.register_callback("main","avals",self.avalsCb,0)

        self.comboBox_reportrate.currentIndexChanged.connect(lambda val : self.send_value("main","rate",str(val)))


        if(self.init_ui()):
            tabId = self.main.add_tab(self,title)
            self.main.select_tab(tabId)
            self.timer.start(500) # timer always updates

        self.buttonbtns.buttonClicked.connect(self.buttonsChanged)
        self.axisbtns.buttonClicked.connect(self.axesChanged)
        self.pushButton_ids.clicked.connect(self.submit_ids)
        self.pushButton_cansettings.clicked.connect(self.canOptions.exec)

        self.timer.timeout.connect(self.updateTimer)
        
    def submit_ids(self):
        self.send_value("main","canidbtn",self.spinBox_digital_id.value())
        self.send_value("main","canidain",self.spinBox_analog_id.value())
    
    def init_ui(self):
        try:
            self.send_commands("main",["lsbtn","btntypes","lsain","aintypes","canidbtn","canidain"],0,'?')
            self.send_command("main","rate",0,'!') # get speed
        except:
            self.main.log("Error initializing CAN remote tab")
            return False
        return True

    # Tab is currently shown
    def showEvent(self,event):
        self.timer.start(500)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

 
    def updateTimer(self):
        try:
           self.send_commands("main",["avals","dvals"],0,'?')
        except:
            self.main.log("Update error")

    def avalsCb(self,vals):
        if not ":" in vals:
            self.label_analogvals.setText("No analog values")
            return
    
        values = [[int(v) for v in line.split(":")] for line in vals.split("\n")]
        if len(values) > 1:
            text = "\n".join([f"{i}:{value}" for value,i in values])
        else:
            text = f"{values[0][0]}"
        
        self.label_analogvals.setText("Analog values:\n"+text)


    def dvalsCb(self,vals):
        if not ":" in vals:
            self.label_analogvals.setText("No digital values")
            return

        values = [[int(v) for v in line.split(":")] for line in vals.split("\n")]
        if len(values) > 1:
            text = "\n".join([f"{i}:{value:b}" for value,i in values])
        else:
            text = f"{values[0][0]:b}"
        self.label_digitalvals.setText("Digital values:\n"+text)


  
    def reportrate_cb(self,modes):
        self.comboBox_reportrate.blockSignals(True)
        self.comboBox_reportrate.clear()
        modes = [m.split(":") for m in modes.split(",") if m]
        for m in modes:
            self.comboBox_reportrate.addItem(m[0],m[1])
        self.send_command("main","rate",0,'?') # get speed
        self.comboBox_reportrate.blockSignals(False)

    # Button selector
    def buttonsChanged(self,id):
        mask = 0
        for b in self.buttonbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.buttonbtns.id(b)

        self.send_value("main","btntypes",str(mask))

    # Analog selector
    def axesChanged(self,id):
        mask = 0
        for b in self.axisbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.axisbtns.id(b)

        self.send_value("main","aintypes",str(mask))
        self.avals = [0]
        
    def updateButtonClassesCB(self,reply):
        self.btnIds,self.btnClasses = classlistToIds(reply)

    def updateButtonSources(self,types):
        if not self.btnClasses:
            self.send_command("main","lsbtn",0,'?')
            return
        if(types == None):
            self.main.log("Error getting buttons")
            return
        types = int(types)
        
        layout = QGridLayout() if not self.groupBox_buttons.layout() else self.groupBox_buttons.layout()
        layout.setVerticalSpacing(0)
        layout.setContentsMargins(12,5,12,5)
        #clear
        for b in self.buttonconfbuttons:
            self.remove_callbacks(b[1])
            b[0].setParent(None)
            for c in b :
                c.deleteLater()
            #del b
        self.buttonconfbuttons.clear() # Clear buttons
        for b in self.buttonbtns.buttons():
            self.buttonbtns.removeButton(b)
            # del b
            b.deleteLater()
        #add buttons
        row = 0
        for c in self.btnClasses:
            btn=QCheckBox(str(c[1]),self.groupBox_buttons)
            self.buttonbtns.addButton(btn,c[0])
            layout.addWidget(btn,row,0)
            enabled = types & (1<<c[0]) != 0
            btn.setChecked(enabled)

            creatable = c[2]
            btn.setEnabled(creatable or enabled)

            confbutton = QToolButton(self)
            confbutton.setText(">")
            layout.addWidget(confbutton,row,1)
            self.buttonconfbuttons.append((confbutton,buttonconf_ui.ButtonOptionsDialog(str(c[1]),c[0],self.main)))
            confbutton.clicked.connect(self.buttonconfbuttons[row][1].exec)
            confbutton.setEnabled(enabled)
            self.buttonbtns.button(c[0]).stateChanged.connect(confbutton.setEnabled)
            row+=1
        self.groupBox_buttons.setLayout(layout)

    def updateAnalogClassesCB(self,reply):
        self.axisIds,self.axisClasses = classlistToIds(reply)

    def updateAnalogSources(self,types):
 
        if not self.axisClasses:
            self.send_command("main","lsain",0,'?')
            #print("Analog missing")
            return
        
        if(types == None):
            self.main.log("Error getting analog")
            return

        types = int(types)
        layout = QGridLayout() if not self.groupBox_analogaxes.layout() else self.groupBox_analogaxes.layout()
        #clear
        for b in self.axisconfbuttons:
            self.remove_callbacks(b[1])
            b[0].setParent(None)
            # del b
            for c in b :
                c.deleteLater()
        self.axisconfbuttons.clear()
        for b in self.axisbtns.buttons():
            self.axisbtns.removeButton(b)
            #del b
            b.deleteLater()
        #add buttons
        row = 0
        for c in self.axisClasses:
            creatable = c[2]
            btn=QCheckBox(str(c[1]),self.groupBox_analogaxes)
            self.axisbtns.addButton(btn,c[0])
            layout.addWidget(btn,row,0)
            enabled = types & (1<<c[0]) != 0
            btn.setChecked(enabled)

            confbutton = QToolButton(self)
            confbutton.setText(">")
            layout.addWidget(confbutton,row,1)
            self.axisconfbuttons.append((confbutton,analogconf_ui.AnalogOptionsDialog(str(c[1]),c[0],self.main)))
            confbutton.clicked.connect(self.axisconfbuttons[row][1].exec)
            confbutton.setEnabled(enabled)
            self.axisbtns.button(c[0]).stateChanged.connect(confbutton.setEnabled)
            row+=1
    
            #confbutton.setEnabled(creatable or enabled)
            btn.setEnabled(creatable or enabled)

        self.groupBox_analogaxes.setLayout(layout)
        
  