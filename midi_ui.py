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
        
        self.init_ui()
        self.horizontalSlider_power.valueChanged.connect(lambda val : self.send_value("main","power",val))
        self.horizontalSlider_amp.valueChanged.connect(lambda val : self.send_value("main","range",val))


    def init_ui(self):
        self.register_callback("main","power",self.horizontalSlider_power.setValue,0,int)
        self.register_callback("main","range",self.horizontalSlider_amp.setValue,0,int)
    
    def showEvent(self, a0) -> None:
        self.send_commands("main",["power","range"])
        return super().showEvent(a0)