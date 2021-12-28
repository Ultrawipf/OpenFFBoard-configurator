import json
from base_ui import WidgetUI,CommunicationHandler
from PyQt6 import QtGui
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout

class EffectStatsUI(WidgetUI, CommunicationHandler):
    def __init__(self, main=None, parent = None):
            WidgetUI.__init__(self, main, 'effects_stats.ui')
            CommunicationHandler.__init__(self)
            self.main = main #type: main.MainUi
            self.parent = parent

            self.pushButton_ResetData.clicked.connect(self.resetData)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.refreshUi)

    def setEnabled(self, a0: bool) -> None:
        self.pushButton_ResetData.setEnabled(a0)
        return super().setEnabled(a0)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.timer.start(1000)
        return super().showEvent(a0)

    def hideEvent(self, a0) -> None:
        print("close")
        self.timer.stop()
        return super().hideEvent(a0)
    
    def resetData(self):
        self.send_value("fx","effectsDetails",0)

    def refreshUi(self):
        self.get_value_async("fx","effectsDetails",self.decodeData_cb)
    
    def decodeData_cb(self, data):
        json_data = json.loads( '[' + data + ']' )
        if len(json_data) == 12:
            self.label.setEnabled(json_data[0]["nb"] != 0)
            self.label_2.setEnabled(json_data[1]["nb"] != 0)
            self.label_3.setEnabled(json_data[2]["nb"] != 0)
            self.label_4.setEnabled(json_data[3]["nb"] != 0)
            self.label_5.setEnabled(json_data[4]["nb"] != 0)
            self.label_6.setEnabled(json_data[5]["nb"] != 0)
            self.label_7.setEnabled(json_data[6]["nb"] != 0)
            self.label_8.setEnabled(json_data[7]["nb"] != 0)
            self.label_9.setEnabled(json_data[8]["nb"] != 0)
            self.label_10.setEnabled(json_data[9]["nb"] != 0)
            self.label_11.setEnabled(json_data[10]["nb"] != 0)
            self.label_12.setEnabled(json_data[11]["nb"] != 0)
            self.progressBar.setValue(json_data[0]["max"])
            self.progressBar_2.setValue(json_data[1]["max"])
            self.progressBar_3.setValue(json_data[2]["max"])
            self.progressBar_4.setValue(json_data[3]["max"])
            self.progressBar_5.setValue(json_data[4]["max"])
            self.progressBar_6.setValue(json_data[5]["max"])
            self.progressBar_7.setValue(json_data[6]["max"])
            self.progressBar_8.setValue(json_data[7]["max"])
            self.progressBar_9.setValue(json_data[8]["max"])
            self.progressBar_10.setValue(json_data[9]["max"])
            self.progressBar_11.setValue(json_data[10]["max"])
            self.progressBar_12.setValue(json_data[11]["max"])
            self.spinBox.setValue(json_data[0]["nb"])
            self.spinBox_2.setValue(json_data[1]["nb"])
            self.spinBox_3.setValue(json_data[2]["nb"])
            self.spinBox_4.setValue(json_data[3]["nb"])
            self.spinBox_5.setValue(json_data[4]["nb"])
            self.spinBox_6.setValue(json_data[5]["nb"])
            self.spinBox_7.setValue(json_data[6]["nb"])
            self.spinBox_8.setValue(json_data[7]["nb"])
            self.spinBox_9.setValue(json_data[8]["nb"])
            self.spinBox_10.setValue(json_data[9]["nb"])
            self.spinBox_11.setValue(json_data[10]["nb"])
            self.spinBox_12.setValue(json_data[11]["nb"])

class EffectsMonitorDialog(QDialog):
    def __init__(self,main=None):
        QDialog.__init__(self, main)
        self.ui = EffectStatsUI(main,self)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Effects statistics")
    
    def setEnabled(self, a0: bool) -> None:
        self.ui.setEnabled(a0)
        return super().setEnabled(a0)

    def display(self):
        self.show()
        self.raise_()
        self.activateWindow()
