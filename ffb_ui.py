from PyQt6.QtWidgets import QMainWindow, QSlider
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QWidget,QToolButton 
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QGridLayout,QSpinBox
from PyQt6 import uic
from helper import res_path,classlistToIds,splitListReply,throttle
from PyQt6.QtCore import QTimer,QEvent
import main
import buttonconf_ui
import analogconf_ui
from base_ui import WidgetUI,CommunicationHandler
from serial_comms import SerialComms

class FfbUI(WidgetUI,CommunicationHandler):

    btnClasses = {}
    btnIds = []

    axisClasses = {}
    axisIds = []

    
    buttonbtns = QButtonGroup()
    buttonconfbuttons = []

    axisbtns = QButtonGroup()
    axisconfbuttons = []


    #values
    active = 0
    rate = 0

    springgain = 4
    dampergain = 2
    inertiagain = 2
    frictiongain = 2

    def __init__(self, main=None,title = "FFB main"):
        WidgetUI.__init__(self, main,'ffbclass.ui')
        CommunicationHandler.__init__(main.comms)
        self.timer = QTimer(self)
        self.buttonbtns.setExclusive(False)
        self.axisbtns.setExclusive(False)

        self.horizontalSlider_cffilter.valueChanged.connect(self.cffilter_changed)

        self.horizontalSlider_CFq.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_CFq,0.01,"filterCfQ"))
        self.doubleSpinBox_CFq.valueChanged.connect(lambda val : self.horizontalSlider_CFq.setValue(val * 100))

        self.doubleSpinBox_spring.valueChanged.connect(lambda val : self.horizontalSlider_spring.setValue(round(val * 256/self.springgain)))
        self.horizontalSlider_spring.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_spring,self.springgain/256,"spring"))

        self.doubleSpinBox_damper.valueChanged.connect(lambda val : self.horizontalSlider_damper.setValue(val * 256/self.dampergain))
        self.horizontalSlider_damper.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_damper,self.dampergain/256,"damper"))

        self.doubleSpinBox_friction.valueChanged.connect(lambda val : self.horizontalSlider_friction.setValue(val * 256/self.frictiongain))
        self.horizontalSlider_friction.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_friction,self.frictiongain/256,"friction"))

        self.doubleSpinBox_inertia.valueChanged.connect(lambda val : self.horizontalSlider_inertia.setValue(val * 256/self.inertiagain))
        self.horizontalSlider_inertia.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_inertia,self.inertiagain/256,"inertia"))
        
        self.comboBox_reportrate.currentIndexChanged.connect(lambda val : self.sendValue("main","hidsendspd",str(val)))

        self.timer.timeout.connect(self.updateTimer)

        #self.registerCallback("main","axes",self.setAxisCheckBoxes,0,int)
        self.registerCallback("main","hidsendspd",self.hidreportrate_cb,0,typechar='!')
        self.registerCallback("main","hidsendspd",self.comboBox_reportrate.setCurrentIndex,0,int,typechar='?')
        self.registerCallback("main","hidrate",self.ffbRateCB,0,int)
        self.registerCallback("main","ffbactive",self.ffbActiveCB,0,int)

        self.registerCallback("main","lsbtn",self.updateButtonClassesCB,0)
        self.registerCallback("main","btntypes",self.updateButtonSources,0,int)
        self.registerCallback("main","lsain",self.updateAnalogClassesCB,0)
        self.registerCallback("main","aintypes",self.updateAnalogSources,0,int)

        self.registerCallback("fx","filterCfFreq",lambda val : self.cffilter_changed(val,send=False),0,int)

        self.registerCallback("fx","filterCfQ",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_CFq,self.horizontalSlider_CFq,0.01),0,int)
        
        self.registerCallback("fx","spring",self.setSpringScalerCb,0,str,typechar="!")
        self.registerCallback("fx","damper",self.setDamperScalerCb,0,str,typechar="!")
        self.registerCallback("fx","inertia",self.setInertiaScalerCb,0,str,typechar="!")
        self.registerCallback("fx","friction",self.setFrictionScalerCb,0,str,typechar="!")

        self.registerCallback("fx","spring",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_spring,self.horizontalSlider_spring,self.springgain/256),0,int)
        self.registerCallback("fx","damper",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_damper,self.horizontalSlider_damper,self.dampergain/256),0,int)
        self.registerCallback("fx","friction",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_friction,self.horizontalSlider_friction,self.frictiongain/256),0,int)
        self.registerCallback("fx","inertia",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_inertia,self.horizontalSlider_inertia,self.inertiagain/256),0,int)
        

        if(self.initUi()):
            tabId = self.main.addTab(self,title)
            self.main.selectTab(tabId)

        self.buttonbtns.buttonClicked.connect(self.buttonsChanged)
        self.axisbtns.buttonClicked.connect(self.axesChanged)
        

    
    def initUi(self):
        try:
            self.sendCommands("main",["hidrate","ffbactive"],0)

            self.sendCommand("main","lsbtn",0,'?') # get button types
            self.sendCommand("main","btntypes",0,'?') # get active buttons

            self.sendCommand("main","lsain",0,'?') # get analog types
            self.sendCommand("main","aintypes",0,'?') # get active analog

            self.updateSliders()
            self.sendCommand("main","hidsendspd",0,'!') # get speed
            
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

    def updateFfbRateLabel(self):
        if self.active == 1:
            act = "FFB ON"
        elif self.active == -1:
            act = "EMERGENCY STOP"
        else:
            act = "FFB OFF"
        self.label_HIDrate.setText(str(self.rate)+"Hz" + " (" + act + ")")

    def ffbActiveCB(self,active):
        self.active = active
        self.updateFfbRateLabel()
        
    def ffbRateCB(self,rate):
        self.rate = rate
        #self.updateFfbRateLabel()
 
    def updateTimer(self):
        try:
            self.sendCommands("main",["hidrate","ffbactive"],0)
        except:
            self.main.log("Update error")
    
    # Helper function to sync spinboxes and sliders
    # Should be called by the sliders update event while the spinbox should update the slider directly
    def sliderChangedUpdateSpinbox(self,val,spinbox,factor,command=None):
        newVal = val * factor
        if(spinbox.value != newVal):
            spinbox.blockSignals(True)
            spinbox.setValue(newVal)
            spinbox.blockSignals(False)
        if(command):
            self.sendValue("fx",command,val)

    def updateSpinboxAndSlider(self,val,spinbox : QSlider,slider,factor):
        slider.setValue(val)
        self.sliderChangedUpdateSpinbox(val,spinbox,factor)


    def hidreportrate_cb(self,modes):
        self.comboBox_reportrate.blockSignals(True)
        self.comboBox_reportrate.clear()
        modes = [m.split(":") for m in modes.split(",") if m]
        for m in modes:
            self.comboBox_reportrate.addItem(m[0],m[1])
        self.sendCommand("main","hidsendspd",0,'?') # get speed
        self.comboBox_reportrate.blockSignals(False)

    # Button selector
    def buttonsChanged(self,id):
        mask = 0
        for b in self.buttonbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.buttonbtns.id(b)

        self.sendValue("main","btntypes",str(mask))

    # Analog selector
    def axesChanged(self,id):
        mask = 0
        for b in self.axisbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.axisbtns.id(b)

        self.sendValue("main","aintypes",str(mask))
        
    def updateButtonClassesCB(self,reply):
        self.btnIds,self.btnClasses = classlistToIds(reply)

    def updateButtonSources(self,types):
        # btns = dat[0]
        # types = int(dat[1])
        if not self.btnClasses:
            self.sendCommand("main","lsbtn",0,'?')
            #print("Buttons missing")
            return
        
        # self.btnIds,self.btnClasses = classlistToIds(btns)
        if(types == None):
            self.main.log("Error getting buttons")
            return
        types = int(types)
        layout = QGridLayout()
        #clear
        for b in self.buttonconfbuttons:
            SerialComms.removeCallbacks(b[1])
            b[0].setParent(None)
            del b
        self.buttonconfbuttons.clear() # Clear buttons
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
            self.sendCommand("main","lsain",0,'?')
            #print("Analog missing")
            return
        
        if(types == None):
            self.main.log("Error getting analog")
            return

        types = int(types)
        layout = QGridLayout()
        #clear
        for b in self.axisconfbuttons:
            SerialComms.removeCallbacks(b[1])
            b[0].setParent(None)
            del b
        self.axisconfbuttons.clear()
        for b in self.axisbtns.buttons():
            self.axisbtns.removeButton(b)
            del b
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
        
    @throttle(50)
    def cffilter_changed(self,v,send=True):
        freq = max(min(v,500),0)
        if(send):
            self.sendValue("fx","filterCfFreq",(freq))
        else:
            self.horizontalSlider_cffilter.setValue(v)
        lbl = str(freq)+"Hz"
        
        qOn = True
        if(freq == 500):
            lbl = "Off"
            qOn = False
            
        self.horizontalSlider_CFq.setEnabled(qOn)
        self.doubleSpinBox_CFq.setEnabled(qOn)
        self.label_cffilter.setText(lbl)

    def setGainScaler(self,slider : QSlider,spinbox : QSpinBox, gain, repl):
        infos = {key:value for (key,value) in [entry.split(":") for entry in repl.split(",")]}
        if "scale" in infos:
            gain = float(infos["scale"]) if float(infos["scale"]) > 0 else gain
        spinbox.setMaximum(gain)
        self.sliderChangedUpdateSpinbox(slider.value(),spinbox,gain)
        return gain

    def setSpringScalerCb(self,repl):
        self.springgain = self.setGainScaler(self.horizontalSlider_spring,self.doubleSpinBox_spring,self.springgain,repl)
    def setDamperScalerCb(self,repl):
        self.dampergain = self.setGainScaler(self.horizontalSlider_damper,self.doubleSpinBox_damper,self.dampergain,repl)
    def setFrictionScalerCb(self,repl):
        self.frictiongain = self.setGainScaler(self.horizontalSlider_friction,self.doubleSpinBox_friction,self.frictiongain,repl)
    def setInertiaScalerCb(self,repl):
        self.inertiagain = self.setGainScaler(self.horizontalSlider_inertia,self.doubleSpinBox_inertia,self.inertiagain,repl)

    
    def updateSliders(self):
        self.sendCommands("fx",["spring","damper","friction","inertia"],0,typechar="!")
        self.sendCommands("fx",["filterCfQ","filterCfFreq","spring","damper","friction","inertia"],0)



        