from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QDialog,QSizePolicy
from PyQt6.QtWidgets import QWidget,QGroupBox,QProgressBar,QSpacerItem 
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QHBoxLayout,QGridLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox,QFormLayout
from PyQt6 import uic
from PyQt6.QtCore import QTimer,Qt
import main
from helper import res_path,classlistToIds,updateListComboBox
from optionsdialog import OptionsDialog,OptionsDialogGroupBox
from base_ui import CommunicationHandler
import portconf_ui
from qrangeslider import QtRangeSlider


# Helper widget implementing common commands for analog axes
class AnalogProcessingOptions(QWidget,CommunicationHandler):
    def __init__(self, parent,classname : str, instance : int = 0, autoscale : bool = False, filter : bool = False,values : bool = True, manual_tune : bool = False, channels : int = 0):
        QWidget.__init__(self,parent=parent)
        CommunicationHandler.__init__(self)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,2,0,2)
        self.setLayout(self.layout)

        self.channels = channels
        self.classname = classname
        self.instance = instance
        self.filter = filter
        self.autoscale = autoscale
        self.manual_tune = manual_tune
        self.values = values
        self.timer = QTimer(self)
        self.pgb_list = []

        if self.manual_tune:
            self.tune_list = []
            self.tuneBox = QGroupBox("Manual limits")
            self.tuneBoxLayout = QGridLayout()
            self.tuneBox.setLayout(self.tuneBoxLayout)
            self.layout.addWidget(self.tuneBox)

        if self.values:
            self.pgbBox = QGroupBox("Output values")
            self.pgbBoxLayout = QVBoxLayout()
            self.pgbBox.setLayout(self.pgbBoxLayout)
            self.layout.addWidget(self.pgbBox)

        if filter:
            self.filterBox = QCheckBox("Lowpass filter")
            self.layout.addWidget(self.filterBox)
            #self.get_value_async("apin","filter",self.filterBox.setChecked,0,conversion=int)

        if autoscale:
            self.autorangeBox = QCheckBox("Autorange")
            self.layout.addWidget(self.autorangeBox)
            if self.manual_tune:
                self.autorangeBox.stateChanged.connect(lambda v: self.tuneBox.setEnabled(not v))
           # self.get_value_async("apin","autocal",self.autorangeBox.setChecked,0,conversion=int)

        if channels > 0:
            self.setChannels(channels)
           
        self.readValues()
        self.register_callback(self.classname,"values",self.valueCb,self.instance,str)
        self.register_callback(self.classname,"rawval",self.rawValueCb,self.instance,str)
        self.timer.timeout.connect(self.tim)
        

    def showEvent(self,event):
        self.timer.start(300)


    def hideEvent(self,event):
        self.timer.stop()

    def tim(self): # Timer timeout
        if self.values:
            self.send_command(self.classname,"values",self.instance)
        if self.manual_tune:
            self.send_command(self.classname,"rawval",self.instance)

        if self.manual_tune and self.autorangeBox.isChecked():
            for i in range(self.channels):
                self.send_commands(self.classname,["min","max"],instance = self.instance,adr=i)


    def valueCb(self, str):
        val_list = str.split("\n")
        j=0
        for i in range(len(self.pgb_list)):
            pgb = self.pgb_list[i]
            if j < len(val_list):
                pgb.setValue(int(val_list[j]))
                pgb.setVisible(True)
                j=j+1
            else:
                pgb.setValue(-32768)
                pgb.setVisible(False)

    def rawValueCb(self, str):
        val_list = str.split("\n")
        if "OK" in str: # no reply
            return
        j=0
        for i in range(len(self.tune_list)):
            pgb = self.tune_list[i][1]
            if j < len(val_list):
                pgb.setValue(int(val_list[j]))
                j=j+1
            else:
                pgb.setValue(0)
        
     # create min/max boxes or sliders
    def setChannels(self,channels : int):
        if channels == self.channels and len(self.pgb_list) >= channels:
            return
        self.channels = channels
        self.remove_callback(self.classname,"min",adr=None)
        self.remove_callback(self.classname,"max",adr=None)

        if self.manual_tune:
            self.tuneBox.setVisible(channels > 0)
            start_row = len(self.tune_list) # Start index row
            sliders = []
            for i in range(channels):
                if len(self.tune_list) >= channels:
                    continue # Do not add more
                rangeSlider = QtRangeSlider(self,0xfffe) # TODO fix slider to allow non 0 start values
                sliders.append(rangeSlider)
                rawProgressBar = QProgressBar(self)
                rawProgressBar.setRange(-32768, 32767)
                rawProgressBar.setFixedHeight(QtRangeSlider.HEIGHT-4)
                rawProgressBar.setTextVisible(False)
                
                self.tune_list.append([rangeSlider,rawProgressBar])
                self.tuneBoxLayout.addItem(QSpacerItem(QtRangeSlider.TRACK_PADDING,1,QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Minimum) ,i+start_row,0)
                self.tuneBoxLayout.addWidget(rawProgressBar,i+start_row,1)
                self.tuneBoxLayout.addItem(QSpacerItem(QtRangeSlider.TRACK_PADDING,1,QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Minimum) ,i+start_row,2)
                self.tuneBoxLayout.addWidget(rangeSlider,i+start_row,0,1,2)
                #rangeSlider.setValue(0x7fff)                
                # for col,widget in enumerate(newWidgets):
                #     self.tuneBoxLayout.addWidget(widget,i,col)
                #     widget.setVisible(True)
            for ch,row in enumerate(self.tune_list):
                self.register_callback(self.classname,"min",lambda v,slider=row[0] : slider.set_left_thumb_value(v+0x7fff) ,self.instance,adr=ch,conversion=int)
                self.register_callback(self.classname,"max",lambda v,slider=row[0] : slider.set_right_thumb_value(v+0x7fff),self.instance,adr=ch,conversion=int)
                for widget in row:
                    widget.setVisible(ch < channels)

        if self.values:
            for i in range(channels):
                if len(self.pgb_list) >= channels:
                    continue # Do not add more

                pgb = QProgressBar(self)
                pgb.setVisible(False)
                # pgb.setFixedHeight(16)
                pgb.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pgb.setRange(-32768, 32767)
                pgb.setValue(-32768)
                pgb.setFormat(f"%p% (%v) Ch{i+1}")
                self.pgbBoxLayout.addWidget(pgb)
                self.pgb_list.append(pgb)

        self.readValues()

    def readValues(self):
        if self.autoscale:
            self.get_value_async(self.classname,"autocal",self.autorangeBox.setChecked,self.instance,conversion=int)
        if self.filter:
            self.get_value_async(self.classname,"filter",self.filterBox.setChecked,self.instance,conversion=int)
        if self.manual_tune:
            for i in range(self.channels):
                self.send_commands(self.classname,["min","max"],instance = self.instance,adr=i)

    def apply(self):
        manual_allowed = True
        if self.autoscale:
            manual_allowed = not self.autorangeBox.isChecked()
            self.send_value(self.classname,"autocal",1 if self.autorangeBox.isChecked() else 0,instance = self.instance)

        if self.filter:
            self.send_value(self.classname,"filter",1 if self.filterBox.isChecked() else 0,instance = self.instance)

        if self.manual_tune and manual_allowed: # Do not send if autorange is checked
            for i in range(self.channels):
                min = self.tune_list[i][0].get_left_thumb_value() - 0x7fff
                max = self.tune_list[i][0].get_right_thumb_value() - 0x7fff
                self.send_value(self.classname,"min",min,instance = self.instance,adr=i)
                self.send_value(self.classname,"max",max,instance = self.instance,adr=i)
            #self.readValues()
                

        

class AnalogOptionsDialog(OptionsDialog):
    def __init__(self,name,id, main):
        self.main = main
        self.dialog = OptionsDialogGroupBox(name,main)

        if(id == 0): # local analog
            self.dialog = (AnalogInputConf(name,self.main))
        if(id == 1): # can analog
            self.dialog = (CANAnalogConf(name,self.main))
        if(id == 2): # ADS111X
            self.dialog = (ADS111XAnalogConf(name,self.main))

        OptionsDialog.__init__(self, self.dialog,main)


class AnalogInputConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)
        self.analogbtns = QButtonGroup()
        self.analogbtns.setExclusive(False)
        self.buttonBox = QGroupBox("Output channels")
        self.buttonBoxLayout = QFormLayout()
        self.buttonBox.setLayout(self.buttonBoxLayout)

        self.axes = 0

        self.pgb_list=[]
        self.axismask=0
        self.prefix=0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)

    def initUI(self):
        layout = QHBoxLayout()
        self.processingOptions = AnalogProcessingOptions(self,"apin",0,filter=True,autoscale=True,values=False,manual_tune=True)
        layout.addWidget(self.processingOptions)
        # self.autorangeBox = QCheckBox("Autorange")
        # layout.addWidget(self.autorangeBox)
        # self.filterBox = QCheckBox("Lowpass filters")
        # layout.addWidget(self.filterBox)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    # Tab is currently shown
    def showEvent(self,event):
        self.timer.start(300)

    # Tab is hidden
    def hideEvent(self,event):
        self.timer.stop()
        
    def updateTimer(self):
        self.send_commands("apin",["values"],self.prefix)

    def readValues(self):
        
        self.get_value_async("apin","pins",self.createAinButtons,0,conversion=int)
        self.processingOptions.readValues()
        # self.get_value_async("apin","autocal",self.autorangeBox.setChecked,0,conversion=int)
        # self.get_value_async("apin","filter",self.filterBox.setChecked,0,conversion=int)

    def createAinButtons(self,axes):
        self.axes = axes
        # remove buttons
        for i in range(self.buttonBoxLayout.count()):
            b = self.buttonBoxLayout.takeAt(0)
            self.buttonBoxLayout.removeItem(b)
            b.widget().setParent(None)
            #b.widget().deleteLater()
        for b in self.analogbtns.buttons():
            self.analogbtns.removeButton(b)

        self.pgb_list.clear()
        # add buttons
        for i in range(axes):
            btn=QCheckBox(str(i+1),self)
            pgb = QProgressBar(self)
            pgb.setFixedHeight(20)
            pgb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pgb.setRange(-32768, 32767)
            pgb.setValue(-32768)
            self.analogbtns.addButton(btn,i)
            self.buttonBoxLayout.addRow(btn,pgb)
            #self.buttonBoxLayout.addWidget(pgb)
            self.pgb_list.append(pgb)

        def f(axismask):
            self.axismask = axismask
            channels = 0
            for i in range(self.axes):
                on = axismask & (1 << i)
                self.analogbtns.button(i).setChecked(on)
                if on:
                    channels+=1
            self.processingOptions.setChannels(channels)

        self.get_value_async("apin","mask",f,0,conversion=int)

    def valueCb(self, str):
        val_list = str.split("\n")
        j=0
        for i in range(self.axes):
            pgb = self.pgb_list[i]
            if self.axismask & (1<<i):
                pgb.setValue(int(val_list[j]))
                j=j+1
                pgb.setEnabled(True)
            else:
                pgb.setValue(-32768)
                pgb.setEnabled(False)

    def apply(self):
        self.processingOptions.apply()
        mask = 0
        channels = 0
        for i in range(self.axes):
            if (self.analogbtns.button(i).isChecked()):
                channels += 1
                mask |= 1 << i
        self.axismask = mask
        self.send_value("apin","mask",mask)
        self.processingOptions.setChannels(channels)
        # self.send_value("apin","autocal",1 if self.autorangeBox.isChecked() else 0)
        # self.send_value("apin","filter",1 if self.filterBox.isChecked() else 0)

    def onshown(self):
        self.register_callback("apin","values",self.valueCb,self.prefix,str)

    def onclose(self):
        self.remove_callbacks()


class CANAnalogConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)


    def initUI(self):
        vbox = QVBoxLayout()

        self.numAinBox = QSpinBox()
        self.numAinBox.setMinimum(1)
        self.numAinBox.setMaximum(8)
        vbox.addWidget(QLabel("Number of axes"))
        vbox.addWidget(self.numAinBox)
        self.numAinBox.valueChanged.connect(self.amountChanged)

        self.canIdBox = QSpinBox()
        self.canIdBox.setMinimum(1)
        self.canIdBox.setMaximum(0x7ff)
        vbox.addWidget(QLabel("CAN frame ID"))
        vbox.addWidget(self.canIdBox)
        self.canIdBox.valueChanged.connect(self.amountChanged)

        self.infoLabel = QLabel("")
        vbox.addWidget(self.infoLabel)

        self.cansettingsbutton = QPushButton("CAN settings")
        self.canOptions = portconf_ui.CanOptionsDialog(0,"CAN",self.main)
        self.cansettingsbutton.clicked.connect(self.canOptions.exec)
        vbox.addWidget(self.cansettingsbutton)
        
        self.setLayout(vbox)

    def onclose(self):
        self.remove_callbacks()

    def amountChanged(self,_):
        amount = self.numAinBox.value()
        text = ""
        for packet in range(int((amount-1)/4)+1):
            text += f"ID {self.canIdBox.value()+packet}:\n("
            for value in range(4):
                if(value < int(amount - int(packet*4))):
                    text += f"| v{value+1+packet*4}[0:7], v{value+1+packet*4}[8:15] |"
                else:
                    text += "|xx||xx|"
            text += ")\n"

        self.infoLabel.setText(text)

    def apply(self):
        self.send_value("cananalog","canid",self.canIdBox.value())
        self.send_value("cananalog","amount",self.numAinBox.value())

    def maximumCb(self,val):
        self.numAinBox.setMaximum(val)
        self.canIdBox.setMaximum(0x7ff - int((val-1)/4))
    
    def readValues(self):
        self.get_value_async("cananalog","amount",self.numAinBox.setValue,0,conversion=int)
        self.get_value_async("cananalog","maxamount",self.maximumCb,0,conversion=int)
        self.get_value_async("cananalog","canid",self.canIdBox.setValue,0,conversion=int)

        
 
class ADS111XAnalogConf(OptionsDialogGroupBox,CommunicationHandler):

    def __init__(self,name,main):
        self.main = main
        OptionsDialogGroupBox.__init__(self,name,main)
        CommunicationHandler.__init__(self)


    def initUI(self):
        layout = QFormLayout()

        self.processingOptions = AnalogProcessingOptions(self,"adsAnalog",0,filter=True,autoscale=True,values=True,manual_tune=True,channels = 4)
        layout.addRow(self.processingOptions)

        self.numAinBox = QSpinBox()
        self.numAinBox.setMinimum(1)
        self.numAinBox.setMaximum(4)
        
        layout.addRow("Number of inputs",self.numAinBox)
 
        self.diffCb = QCheckBox("Differential mode")
        self.diffCb.stateChanged.connect(lambda c : self.numAinBox.setMaximum(2 if c else 4))

        self.gainCombobox = QComboBox()
        #self.gainCombobox.addItems(["2/3x (+/- 6.144V)","1x (+/- 4.096V)","2x (+/- 2.048V)","4x (+/- 1.024V)","8x (+/- 0.512V)","16x (+/- 0.256V)"])
        layout.addRow("Scale:",self.gainCombobox)

        self.samplerateCombobox = QComboBox()
        #self.samplerateCombobox.addItems(["8 SPS","16 SPS","32 SPS","64 SPS","128 SPS","250 SPS","475 SPS","860 SPS"])
        layout.addRow("Samplerate:",self.samplerateCombobox)

        self.portsettingsbutton = QPushButton("I2C settings")
        self.i2cOptions = portconf_ui.I2COptionsDialog(0,"I2C",self.main)
        self.portsettingsbutton.clicked.connect(self.i2cOptions.exec)
        layout.addRow(self.diffCb,self.portsettingsbutton)

        layout.addRow(QLabel("Mapping in differential mode:\nChannel 1: IN0 = p IN1 = n\nChannel 2: IN2 = p IN3 = n"))
        layout.addRow(QLabel("I²C address is fixed to primary address\n(ADDR pin to GND)"))
        
        self.setLayout(layout)

    def onclose(self):
        self.remove_callbacks()

    def numChannelChanged(self,channels):
        self.processingOptions.setChannels(channels)
        self.numAinBox.setValue(channels)

    def apply(self):
        self.send_value("adsAnalog","diff",1 if self.diffCb.isChecked() else 0)
        self.send_value("adsAnalog","inputs",self.numAinBox.value())
        self.send_value("adsAnalog","gain",int(self.gainCombobox.currentData()))
        self.send_value("adsAnalog","rate",int(self.samplerateCombobox.currentData()))
        self.processingOptions.setChannels(self.numAinBox.value())
        self.processingOptions.apply()
        
    
    def readValues(self):
        self.processingOptions.readValues()
        self.get_value_async("adsAnalog","gain",lambda d : updateListComboBox(self.gainCombobox,d),0,typechar='!')
        self.get_value_async("adsAnalog","rate",lambda d : updateListComboBox(self.samplerateCombobox,d),0,typechar='!')

        self.get_value_async("adsAnalog","gain",self.gainCombobox.setCurrentIndex,0,conversion=int)
        self.get_value_async("adsAnalog","rate",self.samplerateCombobox.setCurrentIndex,0,conversion=int)
        self.get_value_async("adsAnalog","diff",self.diffCb.setChecked,0,conversion=int)
        self.get_value_async("adsAnalog","inputs",self.numChannelChanged,0,conversion=int)