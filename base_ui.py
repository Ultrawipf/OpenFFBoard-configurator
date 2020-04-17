from PyQt5.QtWidgets import QWidget
from helper import res_path
from PyQt5 import uic
import main

class WidgetUI(QWidget):
    
    def __init__(self, main=None, ui_form = ""):
        QWidget.__init__(self, main)
        self.main = main #type: main.MainUi
        if(ui_form):
            uic.loadUi(res_path(ui_form), self)

    def initUi(self):
        return True