from PyQt5.QtWidgets import QWidget
from helper import res_path
from PyQt5 import uic
import main
from base_ui import WidgetUI
class MidiUI(WidgetUI):
    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'midi.ui')
        
        self.initUi()
        self.horizontalSlider_power.valueChanged.connect(lambda val : self.main.comms.serialWrite("power="+str(val)))
        self.horizontalSlider_amp.valueChanged.connect(lambda val : self.main.comms.serialWrite("range="+str(val)))
        

    def initUi(self):
        self.main.comms.serialGetAsync("power?",self.horizontalSlider_power.setValue,int)
        self.main.comms.serialGetAsync("range?",self.horizontalSlider_amp.setValue,int)