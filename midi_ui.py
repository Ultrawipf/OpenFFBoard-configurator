from PyQt6.QtWidgets import QWidget
from helper import res_path
from PyQt6 import uic
import main
from base_ui import WidgetUI
from base_ui import CommunicationHandler

class MidiUI(WidgetUI,CommunicationHandler):
    def __init__(self, main=None):
        WidgetUI.__init__(self, main,'midi.ui')
        CommunicationHandler.__init__(self)
        
        self.initUi()
        self.horizontalSlider_power.valueChanged.connect(lambda val : self.sendValue("main","power",val))
        self.horizontalSlider_amp.valueChanged.connect(lambda val : self.sendValue("main","range",val))


    def initUi(self):
        self.registerCallback("main","power",self.horizontalSlider_power.setValue,0,int)
        self.registerCallback("main","range",self.horizontalSlider_amp.setValue,0,int)
    
    def showEvent(self, a0) -> None:
        self.sendCommands("main",["power","range"])
        return super().showEvent(a0)