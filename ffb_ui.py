from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup 
from PyQt5 import uic
from helper import res_path,classlistToIds
from PyQt5.QtCore import QTimer
import main
import tmc4671_ui

class FfbUI(QWidget):
    drvClasses = {}
    drvIds = []

    encClasses = {}
    encIds = []

    btnClasses = {}
    btnIds = []

    axes = 6

    analogbtns = QButtonGroup()
    buttonbtns = QButtonGroup()
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.main = parent #type: main.MainUi
        uic.loadUi(res_path('ffbclass.ui'), self)

        tabId = self.main.addTab(self,"FFB Wheel")
        self.main.selectTab(tabId)

        self.analogbtns.setExclusive(False)
        self.buttonbtns.setExclusive(False)

        self.horizontalSlider_power.valueChanged.connect(self.sliderPowerChanged)
        self.horizontalSlider_degrees.valueChanged.connect(self.sliderDegreesChanged)
        self.main.save.connect(self.save)

        self.initUi()

        self.analogbtns.buttonClicked.connect(self.axesChanged)
        self.buttonbtns.buttonClicked.connect(self.buttonsChanged)
        
        self.comboBox_driver.currentIndexChanged.connect(self.driverChanged)
        self.comboBox_encoder.currentIndexChanged.connect(self.encoderChanged)

        #self.spinBox_ppr.valueChanged.connect(lambda v : self.main.serialWrite("ppr="+str(v)+";"))



    def initUi(self):
        self.main.setSaveBtn(True)
        self.getMotorDriver()
        self.getEncoder()
        self.updateSliders()

        layout = QVBoxLayout()
        for i in range(self.axes):
            btn=QCheckBox(str(i+1),self.groupBox_analogaxes)
            self.analogbtns.addButton(btn,i)
            layout.addWidget(btn)

        self.groupBox_analogaxes.setLayout(layout)
        self.updateAxes()
        self.getButtonSources()

    def updateAxes(self):
        axismask = int(self.main.serialGet("axismask?\n"))
        for i in range(self.axes):
            self.analogbtns.button(i).setChecked(axismask & (1 << i))

    # Axis checkboxes
    def axesChanged(self,id):
        mask = 0
        for i in range(self.axes):
            if (self.analogbtns.button(i).isChecked()):
                mask |= 1 << i
        self.main.serialWrite("axismask="+str(mask)+"\n")

    # Button selector
    def buttonsChanged(self,id):
        mask = 0
        for b in self.buttonbtns.buttons():
            if(b.isChecked()):
                mask |= 1 << self.buttonbtns.id(b)

        self.main.serialWrite("btntypes="+str(mask)+"\n")


    def save(self):
        val = self.spinBox_ppr.value()
        self.main.serialWrite("ppr="+str(val)+"\n")

        self.main.serialWrite("save\n")


    def driverChanged(self):
        id = self.drvIds[self.comboBox_driver.currentIndex()][0]
        self.main.serialWrite("drvtype="+str(id)+"\n")
        self.getMotorDriver()
        self.getEncoder()
   
    def encoderChanged(self):
        id = self.encIds[self.comboBox_encoder.currentIndex()][0]
        self.main.serialWrite("enctype="+str(id)+"\n")
        
    
    def sliderPowerChanged(self,val):
        self.main.serialWrite("power="+str(val)+"\n")
        
    def sliderDegreesChanged(self,val):
        self.main.serialWrite("degrees="+str(val)+"\n")

    def updateSliders(self):
        power = self.main.serialGet("power?\n",150)
        degrees = self.main.serialGet("degrees?\n",150)

        if not(power and degrees):
            main.log("Error getting values")
            return
        power = int(power)
        degrees = int(degrees)
        self.horizontalSlider_power.setValue(power)
        self.horizontalSlider_degrees.setValue(degrees)
        self.label_power.setNum(power)
        self.label_range.setNum(degrees)


    def getMotorDriver(self):
        dat = self.main.serialGet("drvtype!\n")
        self.comboBox_driver.clear()
        self.drvIds,self.drvClasses = classlistToIds(dat)
        id = self.main.serialGet("drvtype?\n")
        if(id == None):
            main.log("Error getting driver")
            return
        id = int(id)
        for c in self.drvClasses:
            self.comboBox_driver.addItem(c[1])
        self.comboBox_driver.setCurrentIndex(self.drvIds[id][0])
        
        # TMC
        if(id == 1):
            if not self.main.hasTab("TMC4671"):
                tabId = self.main.addTab(tmc4671_ui.TMC4671Ui(self.main),"TMC4671")
                if(int(self.main.serialGet("mtype\n")) == 0):
                    self.main.selectTab(tabId)
                    msg = QMessageBox(QMessageBox.Information,"TMC4671","Please setup the motor driver first!")
                    msg.exec_()
        

    def getEncoder(self):
        self.spinBox_ppr.setEnabled(True)

        dat = self.main.serialGet("enctype!\n")
        self.comboBox_encoder.clear()
        self.encIds,self.encClasses = classlistToIds(dat)
        id = self.main.serialGet("enctype?\n")
        if(id == None):
            main.log("Error getting encoder")
            return
        id = int(id)
        for c in self.encClasses:
            self.comboBox_encoder.addItem(c[1])
        self.comboBox_encoder.setCurrentIndex(self.encIds[id][0])
        ppr = self.main.serialGet("ppr?\n")
        self.spinBox_ppr.setValue(int(ppr))

        if(id == 1):
            self.spinBox_ppr.setEnabled(False)

    def getButtonSources(self):
        dat = self.main.serialGet("lsbtn\n")
        
        self.btnIds,self.btnClasses = classlistToIds(dat)
        types = self.main.serialGet("btntypes?\n")
        if(types == None):
            main.log("Error getting buttons")
            return
        types = int(types)
        layout = QVBoxLayout()
        #clear
        for b in self.buttonbtns.buttons():
            self.buttonbtns.removeButton(b)
            del b
        #add buttons

        for c in self.btnClasses:
            btn=QCheckBox(str(c[1]),self.groupBox_buttons)
            self.buttonbtns.addButton(btn,c[0])
            layout.addWidget(btn)
            btn.setChecked(types & (1<<c[0]) != 0)

        self.groupBox_buttons.setLayout(layout)
        # TODO add UIs
        

        