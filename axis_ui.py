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
from encoderconf_ui import EncoderOptions

class AxisUI(WidgetUI):

    amp_gain = 60
    shunt_ohm = 0.0015
    
    drvClasses = {}
    drvIds = []

    encClasses = {}
    encIds = []

    drvId = 0
    encId = 0

    axis = 'X'
    encWidgets = {}

    def __init__(self, main=None, unique='X'):
        WidgetUI.__init__(self, main, 'axis_ui.ui')

        self.axis = unique

        self.timer = QTimer(self)

        self.horizontalSlider_power.valueChanged.connect(self.power_changed)
        self.horizontalSlider_degrees.valueChanged.connect(lambda val : self.serialWrite("degrees="+str(val)+"\n"))
        self.horizontalSlider_esgain.valueChanged.connect(lambda val : self.serialWrite("esgain="+str(val)+"\n"))
        self.horizontalSlider_fxratio.valueChanged.connect(self.fxratio_changed)
        self.horizontalSlider_idle.valueChanged.connect(lambda val : self.serialWrite("idlespring="+str(val)+"\n"))
        self.horizontalSlider_damper.valueChanged.connect(lambda val : self.serialWrite("axisdamper="+str(val)+"\n"))

        self.spinBox_range.editingFinished.connect(self.rangeChanged) # don't update while typing

        #self.comboBox_encoder.currentIndexChanged.connect(self.encoderIndexChanged)

        self.checkBox_invert.stateChanged.connect(lambda val : self.serialWrite("invert="+("0" if val == 0 else "1")+"\n"))

        self.pushButton_submit_hw.clicked.connect(self.submitHw)

        if(self.initUi()):
            tabId = self.main.addTab(self,"FFB Axis")
            self.main.selectTab(tabId)

        self.pushButton_center.clicked.connect(lambda : self.serialWrite("zeroenc\n"))


    def initUi(self):
        try:
            self.getMotorDriver()
            self.getEncoder()
            self.updateSliders()

            self.serialGetAsync("invert?",self.checkBox_invert.setChecked,int)
            
        except:
            self.main.log("Error initializing Axis tab")
            return False
        return True

    # Tab is currently shown
    def showEvent(self,event):
        self.timer.start(500)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()

    def rangeChanged(self):
        self.horizontalSlider_degrees.setValue(self.spinBox_range.value())
     
    def power_changed(self,val):
        self.serialWrite("power="+str(val)+"\n")
        text = str(val)
        # If tmc is used show a current estimate
        if(self.drvId == 1):
            v = (2.5/0x7fff) * val
            current = (v / self.amp_gain) / self.shunt_ohm
            text += " ("+str(round(current,1)) + "A)"
     
        self.label_power.setText(text)

    # Effect/Endstop ratio scaler
    def fxratio_changed(self,val):

        self.serialWrite("fxratio="+str(val)+"\n")
        ratio = val / 255
        text = str(round(100*ratio,1)) + "%"
        self.label_fxratio.setText(text)


    def submitHw(self):
        #val = self.spinBox_cpr.value()
        self.driverChanged(self.comboBox_driver.currentIndex())
        self.encoderChanged(self.comboBox_encoder.currentIndex())
        #self.serialWrite("cpr="+str(val)+"\n")


    def driverChanged(self,idx):
        if idx == -1:
            return
        id = self.drvClasses[idx][0]
        if(self.drvId != id):
            self.serialWrite("drvtype="+str(id)+"\n")
            self.getMotorDriver()
            self.getEncoder()
            self.main.updateTabs()
            
   
    def encoderChanged(self,idx):
        if idx == -1:
            return
        id = self.encClasses[idx][0]
        if(self.encId != id):
            self.serialWrite("enctype="+str(id)+"\n")
            self.getEncoder()
            self.main.updateTabs()
            self.encoderIndexChanged(id)
        
    
    def updateSliders(self):
        commands = ["power?","degrees?","fxratio?","esgain?","idlespring?","axisdamper?"]
  
        if(self.drvId == 1): # Reduce max range for TMC (ADC saturation margin. Recommended to keep <25000)
            self.horizontalSlider_power.setMaximum(28000)
        else:
            self.horizontalSlider_power.setMaximum(0x7fff)
        callbacks = [
        self.horizontalSlider_power.setValue,
        self.horizontalSlider_degrees.setValue,
        self.horizontalSlider_fxratio.setValue,
        self.horizontalSlider_esgain.setValue,
        self.horizontalSlider_idle.setValue,
        self.horizontalSlider_damper.setValue]

        self.serialGetAsync(commands,callbacks,convert=int)
        self.power_changed(self.horizontalSlider_power.value())


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
            self.updateSliders()
        self.serialGetAsync(["drvtype!","drvtype?"],drvtypecb)
       
    def encoderIndexChanged(self,idx):
        id = self.comboBox_encoder.currentData()
        if(id not in self.encWidgets):
            return
        self.stackedWidget_encoder.setCurrentWidget(self.encWidgets[id])

    def getEncoder(self):
        #self.comboBox_encoder.currentIndexChanged.disconnect()
        #self.spinBox_cpr.setEnabled(True)

        
        def f(dat):
            self.comboBox_encoder.clear()
            self.encWidgets.clear()

            self.encIds,self.encClasses = classlistToIds(dat)
            for c in self.encClasses:
                self.comboBox_encoder.addItem(c[1],c[0])
                id = c[0]
                if(id not in self.encWidgets or self.stackedWidget_encoder.indexOf(self.encWidgets[id]) == -1):
                    self.encWidgets[id] = EncoderOptions(self.main,id)
                    self.stackedWidget_encoder.addWidget(self.encWidgets[id])

        self.serialGetAsync("enctype!",f)
        
        def encid_f(id):
            if(id == None):
                self.main.log("Error getting encoder")
                return
            self.encId = int(id)
            
            idx = self.encIds[self.encId][0] if self.encId in self.encIds else 0
            self.comboBox_encoder.setCurrentIndex(idx)
            self.encoderIndexChanged(idx)
            
            # if(self.encId == 1):
            #     self.spinBox_cpr.setEnabled(False)
        self.serialGetAsync("enctype?",encid_f,int)
        # def f_cpr(v):
        #     self.spinBox_cpr.setValue(v)
        # self.serialGetAsync("cpr?",f_cpr,int)


    # Prepend the axis letter to the command before sending   
    def serialWrite(self,cmd):
        cmd = self.axis+"."+cmd
        self.main.comms.serialWrite(cmd)


    # Prepend the axis letter to the command(s) before sending   
    def serialGetAsync(self,cmds,callbacks,convert=None):
        if(type(cmds) == list):
            axis_cmds = list(map(lambda x: self.axis+"."+x, cmds)) # y.torqueP? etc
        else:
            axis_cmds = self.axis+"."+cmds
        self.main.comms.serialGetAsync(axis_cmds,callbacks,convert)


        