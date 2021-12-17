from PyQt5.QtWidgets import QMainWindow, QSlider
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QToolButton 
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QGridLayout,QSpinBox
from PyQt5 import uic
from helper import res_path,classlistToIds,splitListReply
from PyQt5.QtCore import QTimer,QEvent
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

    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'ffbclass.ui')
        CommunicationHandler.__init__(main.comms)
        self.timer = QTimer(self)
        self.buttonbtns.setExclusive(False)
        self.axisbtns.setExclusive(False)

        self.horizontalSlider_cffilter.valueChanged.connect(self.cffilter_changed)

        self.horizontalSlider_CFq.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_CFq,0.01,"filterCfQ"))
        self.doubleSpinBox_CFq.valueChanged.connect(lambda val : self.horizontalSlider_CFq.setValue(val * 100))

        self.doubleSpinBox_spring.valueChanged.connect(lambda val : self.horizontalSlider_spring.setValue(val * 64))
        self.horizontalSlider_spring.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_spring,4/255,"spring"))

        self.doubleSpinBox_damper.valueChanged.connect(lambda val : self.horizontalSlider_damper.setValue(val * 128))
        self.horizontalSlider_damper.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_damper,2/255,"damper"))

        self.doubleSpinBox_friction.valueChanged.connect(lambda val : self.horizontalSlider_friction.setValue(val * 128))
        self.horizontalSlider_friction.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_friction,2/255,"friction"))

        self.doubleSpinBox_inertia.valueChanged.connect(lambda val : self.horizontalSlider_inertia.setValue(val * 128))
        self.horizontalSlider_inertia.valueChanged.connect(lambda val : self.sliderChangedUpdateSpinbox(val,self.doubleSpinBox_inertia,2/255,"inertia"))
        
        self.comboBox_reportrate.currentIndexChanged.connect(lambda val : self.sendValue("main","hidsendspd",str(val)))

        self.timer.timeout.connect(self.updateTimer)

        self.registerCallback("main","axes",self.setAxisCheckBoxes,0,int)
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
        
        self.registerCallback("fx","spring",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_spring,self.horizontalSlider_spring,4/255),0,int)
        self.registerCallback("fx","damper",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_damper,self.horizontalSlider_damper,2/255),0,int)
        self.registerCallback("fx","friction",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_friction,self.horizontalSlider_friction,2/255),0,int)
        self.registerCallback("fx","inertia",lambda val : self.updateSpinboxAndSlider(val,self.doubleSpinBox_inertia,self.horizontalSlider_inertia,2/255),0,int)
        

        if(self.initUi()):
            tabId = self.main.addTab(self,"FFB Wheel")
            self.main.selectTab(tabId)

        self.pushButton_changeAxes.clicked.connect(self.changeFFBAxesCount)
        self.checkBox_axisY.stateChanged.connect(self.axisCheckBoxClicked)
#        self.checkBox_axisZ.stateChanged.connect(self.axisCheckBoxClicked)

        self.buttonbtns.buttonClicked.connect(self.buttonsChanged)
        self.axisbtns.buttonClicked.connect(self.axesChanged)
        


    def initUi(self):
        try:
            self.sendCommand("main","axes",0,'?') # get axes
            self.sendCommands("main",["hidrate","ffbactive"],0)

            self.sendCommand("main","lsbtn",0,'?') # get button types
            self.sendCommand("main","btntypes",0,'?') # get active buttons

            self.sendCommand("main","lsain",0,'?') # get analog types
            self.sendCommand("main","aintypes",0,'?') # get active analog

            #self.getAxisSources()
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

    def setAxisCheckBoxes(self,count):
        self.checkBox_axisX.setChecked(True if (count>0) else False)
        self.checkBox_axisY.setChecked(True if (count>1) else False)
        self.checkBox_axisZ.setChecked(True if (count>2) else False)
        self.pushButton_changeAxes.setEnabled(False)


    def axisCheckBoxClicked(self, val):
        self.pushButton_changeAxes.setEnabled(True)


    def changeFFBAxesCount(self):
        def f():
            axisCount = 1
            if self.checkBox_axisY.isChecked():
                axisCount +=1
            if self.checkBox_axisZ.isChecked():
                axisCount +=1
            self.sendValue("main","axes",axisCount)
            self.main.updateTabs()

        self.pushButton_changeAxes.setEnabled(False)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Changing the number of axis may cause or require a reboot!")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.buttonClicked.connect(f)
        msg.exec_()

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

    # Axis selector
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
            print("Analog missing")
            return
        
        if(types == None):
            self.main.log("Error getting analog")
            return

        types = int(types)
        layout = QGridLayout()
        #clear
        for b in self.axisconfbuttons:
            SerialComms.removeCallbacks(b[1])
            del b
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

    
    def updateSliders(self):
        self.sendCommands("fx",["filterCfQ","filterCfFreq","spring","damper","friction","inertia"],0)



        