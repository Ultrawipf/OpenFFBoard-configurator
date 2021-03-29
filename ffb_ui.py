from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget,QToolButton 
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QGridLayout,QSpinBox
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer,QEvent
import main
import buttonconf_ui
import analogconf_ui
from base_ui import WidgetUI

class FfbUI(WidgetUI):

    btnClasses = {}
    btnIds = []

    axisClasses = {}
    axisIds = []

    

    buttonbtns = QButtonGroup()
    buttonconfbuttons = []

    axisbtns = QButtonGroup()
    axisconfbuttons = []


    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'ffbclass.ui')
    
        self.timer = QTimer(self)
        self.buttonbtns.setExclusive(False)
        self.axisbtns.setExclusive(False)

        self.horizontalSlider_cffilter.valueChanged.connect(self.cffilter_changed)
        self.horizontalSlider_spring.valueChanged.connect(lambda val : self.main.comms.serialWrite("spring="+str(val)+"\n"))
        self.horizontalSlider_damper.valueChanged.connect(lambda val : self.main.comms.serialWrite("damper="+str(val)+"\n"))
        self.horizontalSlider_friction.valueChanged.connect(lambda val : self.main.comms.serialWrite("friction="+str(val)+"\n"))
        self.horizontalSlider_inertia.valueChanged.connect(lambda val : self.main.comms.serialWrite("inertia="+str(val)+"\n"))

        self.timer.timeout.connect(self.updateTimer)
        

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
            self.main.comms.serialGetAsync("axis?",self.setAxisCheckBoxes,int)
            self.getButtonSources()
            self.getAxisSources()
            self.updateSliders()
            
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
            self.main.comms.serialWrite("axis="+str(axisCount)+"\n")
            self.main.updateTabs()

        self.pushButton_changeAxes.setEnabled(False)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("Changing the number of axis may cause or require a reboot!")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.buttonClicked.connect(f)
        msg.exec_()


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
        

    def cffilter_changed(self,v):
        freq = max(min(v,500),0)
        self.main.comms.serialWrite("ffbfiltercf="+str(freq)+"\n")
        lbl = str(freq)+"Hz"
        if(freq == 500):
            lbl = "Off"
        self.label_cffilter.setText(lbl)


    def updateSliders(self):
        commands = ["ffbfiltercf?","spring?","damper?","friction?","inertia?"]
  
        callbacks = [
        self.horizontalSlider_cffilter.setValue,
        self.horizontalSlider_spring.setValue,
        self.horizontalSlider_damper.setValue,
        self.horizontalSlider_friction.setValue,
        self.horizontalSlider_inertia.setValue]

        self.main.comms.serialGetAsync(commands,callbacks,convert=int)


        