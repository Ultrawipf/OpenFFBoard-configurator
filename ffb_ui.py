from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QToolButton 
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QGridLayout
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer,QEvent
import main
import buttonconf_ui
import analogconf_ui
from base_ui import WidgetUI

class FfbUI(WidgetUI):

    amp_gain = 60
    shunt_ohm = 0.0015
    
    drvClasses = {}
    drvIds = []

    encClasses = {}
    encIds = []

    btnClasses = {}
    btnIds = []

    axisClasses = {}
    axisIds = []

    drvId = 0
    encId = 0

    buttonbtns = QButtonGroup()
    buttonconfbuttons = []

    axisbtns = QButtonGroup()
    axisconfbuttons = []
    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'ffbclass.ui')
    
        self.timer = QTimer(self)

        self.buttonbtns.setExclusive(False)
        self.axisbtns.setExclusive(False)
        self.horizontalSlider_power.valueChanged.connect(self.power_changed)
        self.horizontalSlider_degrees.valueChanged.connect(lambda val : self.main.comms.serialWrite("degrees="+str(val)+"\n"))
        self.horizontalSlider_friction.valueChanged.connect(lambda val : self.main.comms.serialWrite("friction="+str(val)+"\n"))
        self.horizontalSlider_idle.valueChanged.connect(lambda val : self.main.comms.serialWrite("idlespring="+str(val)+"\n"))
        self.horizontalSlider_esgain.valueChanged.connect(lambda val : self.main.comms.serialWrite("esgain="+str(val)+"\n"))
        self.horizontalSlider_fxratio.valueChanged.connect(self.fxratio_changed)
        self.horizontalSlider_cffilter.valueChanged.connect(self.cffilter_changed)


        self.checkBox_invertX.stateChanged.connect(lambda val : self.main.comms.serialWrite("invertx="+("0" if val == 0 else "1")+"\n"))

        self.timer.timeout.connect(self.updateTimer)
        
        #self.comboBox_driver.currentIndexChanged.connect(self.driverChanged)
        #self.comboBox_encoder.currentIndexChanged.connect(self.encoderChanged)
        self.pushButton_submit_hw.clicked.connect(self.submitHw)

        if(self.initUi()):
            tabId = self.main.addTab(self,"FFB Wheel")
            self.main.selectTab(tabId)

        self.buttonbtns.buttonClicked.connect(self.buttonsChanged)
        self.axisbtns.buttonClicked.connect(self.axesChanged)
        self.pushButton_center.clicked.connect(lambda : self.main.comms.serialWrite("zeroenc\n"))
        
        #self.spinBox_cpr.valueChanged.connect(lambda v : self.main.comms.serialWrite("cpr="+str(v)+";"))



    def initUi(self):
        try:
            self.getMotorDriver()
            self.getEncoder()
            self.updateSliders()

            self.main.comms.serialGetAsync("invertx?",self.checkBox_invertX.setChecked,int)
            self.getButtonSources()
            self.getAxisSources()
            
        except:
            self.main.log("Error initializing FFB tab")
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
            def f(d):
                rate,active = d
                if active == 1:
                    act = "FFB ON"
                elif active == -1:
                    act = "EMERGENCY STOP"
                else:
                    act = "FFB OFF"
                self.label_HIDrate.setText(str(rate)+"Hz" + " (" + act + ")")
            self.main.comms.serialGetAsync(["hidrate","ffbactive"],f,int)
        except:
            self.main.log("Update error")
    
    def cffilter_changed(self,v):
        freq = max(min(v,500),0)
        self.main.comms.serialWrite("ffbfiltercf="+str(freq)+"\n")
        lbl = str(freq)+"Hz"
        if(freq == 500):
            lbl = "Off"
        self.label_cffilter.setText(lbl)

    def power_changed(self,val):
        self.main.comms.serialWrite("power="+str(val)+"\n")
        text = str(val)     

        # If tmc is used show a current estimate
        if(self.drvId == 1):
            v = (2.5/0x7fff) * val
            current = (v / self.amp_gain) / self.shunt_ohm
            text += " ("+str(round(current,1)) + "A)"
     
        self.label_power.setText(text)

    # Effect/Endstop ratio scaler
    def fxratio_changed(self,val):

        self.main.comms.serialWrite("fxratio="+str(val)+"\n")
        ratio = val / 255
        text = str(round(100*ratio,1)) + "%"
        self.label_fxratio.setText(text)

    # Button selector
    def buttonsChanged(self,id):
        mask = 0
        for b in self.buttonbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.buttonbtns.id(b)

        self.main.comms.serialWrite("btntypes="+str(mask)+"\n")

    # Axis selector
    def axesChanged(self,id):
        mask = 0
        for b in self.axisbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.axisbtns.id(b)

        self.main.comms.serialWrite("aintypes="+str(mask)+"\n")

    def submitHw(self):
        val = self.spinBox_cpr.value()
        self.driverChanged(self.comboBox_driver.currentIndex())
        self.encoderChanged(self.comboBox_encoder.currentIndex())
        self.main.comms.serialWrite("cpr="+str(val)+"\n")


    def driverChanged(self,idx):
        if idx == -1:
            return
        id = self.drvClasses[idx][0]
        if(self.drvId != id):
            self.main.comms.serialWrite("drvtype="+str(id)+"\n")
            self.getMotorDriver()
            self.getEncoder()
            self.main.updateTabs()
            self.updateSliders()
            
   
    def encoderChanged(self,idx):
        if idx == -1:
            return
        id = self.encClasses[idx][0]
        if(self.encId != id):
            self.main.comms.serialWrite("enctype="+str(id)+"\n")
            self.getEncoder()
            self.main.updateTabs()
            self.updateSliders()
        
    
    def updateSliders(self):
        commands = ["power?","degrees?","friction?","idlespring?","fxratio?","esgain?","ffbfiltercf?"]
  
        if(self.drvId == 1): # Reduce max range for TMC (ADC saturation margin. Recommended to keep <25000)
            self.horizontalSlider_power.setMaximum(28000)
        else:
            self.horizontalSlider_power.setMaximum(0x7fff)

        callbacks = [
        self.horizontalSlider_power.setValue,
        self.horizontalSlider_degrees.setValue,
        self.horizontalSlider_friction.setValue,
        self.horizontalSlider_idle.setValue,
        self.horizontalSlider_fxratio.setValue,
        self.horizontalSlider_esgain.setValue,
        self.horizontalSlider_cffilter.setValue]

        self.main.comms.serialGetAsync(commands,callbacks,convert=int)


    def getMotorDriver(self):
        def drvtypecb(dat):
            l,i = dat
            self.comboBox_driver.clear()
            self.drvIds,self.drvClasses = classlistToIds(l)
            if(i == None):
                self.main.log("Error getting driver")
                return
            self.drvId = int(i)
            for c in self.drvClasses:
                self.comboBox_driver.addItem(c[1])

            if(self.drvId in self.drvIds and self.comboBox_driver.currentIndex() != self.drvIds[self.drvId][0]):
                self.comboBox_driver.setCurrentIndex(self.drvIds[self.drvId][0])
        self.main.comms.serialGetAsync(["drvtype!","drvtype?"],drvtypecb)
       

    def getEncoder(self):
        #self.comboBox_encoder.currentIndexChanged.disconnect()
        self.spinBox_cpr.setEnabled(True)

        
        def f(dat):
            self.comboBox_encoder.clear()
            self.encIds,self.encClasses = classlistToIds(dat)
            for c in self.encClasses:
                self.comboBox_encoder.addItem(c[1])
        self.main.comms.serialGetAsync("enctype!",f)

        
        def encid_f(id):
            if(id == None):
                self.main.log("Error getting encoder")
                return
            self.encId = int(id)
            
            idx = self.encIds[self.encId][0] if self.encId in self.encIds else 0
            self.comboBox_encoder.setCurrentIndex(idx)
                        

            if(self.encId == 1):
                self.spinBox_cpr.setEnabled(False)
        self.main.comms.serialGetAsync("enctype?",encid_f,int)
        def f_cpr(v):
            self.spinBox_cpr.setValue(v)
        self.main.comms.serialGetAsync("cpr?",f_cpr,int)
        

    def getButtonSources(self):
        
        def cb_buttonSources(dat):
            btns = dat[0]
            types = int(dat[1])
            
            self.btnIds,self.btnClasses = classlistToIds(btns)
            if(types == None):
                self.main.log("Error getting buttons")
                return
            types = int(types)
            layout = QGridLayout()
            #clear
            for b in self.buttonconfbuttons:
                del b
            for b in self.buttonbtns.buttons():
                self.buttonbtns.removeButton(b)
                del b
            #add buttons
            row = 0
            for c in self.btnClasses:
                btn=QCheckBox(str(c[1]),self.groupBox_buttons)
                self.buttonbtns.addButton(btn,c[0])
                layout.addWidget(btn,row,0)
                enabled = types & (1<<c[0]) != 0
                btn.setChecked(enabled)

                confbutton = QToolButton(self)
                confbutton.setText(">")
                layout.addWidget(confbutton,row,1)
                self.buttonconfbuttons.append((confbutton,buttonconf_ui.ButtonOptionsDialog(str(c[1]),c[0],self.main)))
                confbutton.clicked.connect(self.buttonconfbuttons[row][1].exec)
                confbutton.setEnabled(enabled)
                self.buttonbtns.button(c[0]).stateChanged.connect(confbutton.setEnabled)
                row+=1

            self.groupBox_buttons.setLayout(layout)
        self.main.comms.serialGetAsync(["lsbtn","btntypes?"],cb_buttonSources)


    def getAxisSources(self):
        
        def cb_axisSources(dat):
            btns = dat[0]
            types = int(dat[1])
            
            self.axisIds,self.axisClasses = classlistToIds(btns)
            if(types == None):
                self.main.log("Error getting buttons")
                return
            types = int(types)
            layout = QGridLayout()
            #clear
            for b in self.axisconfbuttons:
                del b
            for b in self.axisbtns.buttons():
                self.axisbtns.removeButton(b)
                del b
            #add buttons
            row = 0
            for c in self.axisClasses:
                btn=QCheckBox(str(c[1]),self.groupBox_buttons)
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

            self.groupBox_analogaxes.setLayout(layout)
        self.main.comms.serialGetAsync(["lsain","aintypes?"],cb_axisSources)
        

        