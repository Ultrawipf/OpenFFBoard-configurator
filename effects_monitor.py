import json
from base_ui import WidgetUI,CommunicationHandler
from PyQt6 import QtGui,QtWidgets
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
            icon_ok = QtGui.QIcon(
            self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogYesButton)
            )
            icon_ko = QtGui.QIcon(
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DialogNoButton)
            )
            self.icon_ok = icon_ok.pixmap(18, 18)
            self.icon_ko = icon_ko.pixmap(18, 18)
            self.setActiveState_cb(0)

    def setEnabled(self, a0: bool) -> None:
        self.pushButton_ResetData.setEnabled(a0)
        return super().setEnabled(a0)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.timer.start(1000)
        return super().showEvent(a0)

    def hideEvent(self, a0) -> None:
        self.timer.stop()
        return super().hideEvent(a0)
    
    def resetData(self):
        self.send_value("fx","effectsDetails",0)

    def refreshUi(self):
        self.get_value_async("fx","effectsDetails",self.decodeData_cb)
        self.get_value_async("fx","effects",self.setActiveState_cb,conversion=int)
    
    def setLabelPixmapState(self,label,state):
        label.setPixmap(self.icon_ok if state else self.icon_ko)

    def setActiveState_cb(self,state):
        self.setLabelPixmapState(self.label_used_1,state & 0x1 != 0)
        self.setLabelPixmapState(self.label_used_2,state & 0x2 != 0)
        self.setLabelPixmapState(self.label_used_3,state & 0x4 != 0)
        self.setLabelPixmapState(self.label_used_4,state & 0x8 != 0)
        self.setLabelPixmapState(self.label_used_5,state & 0x10 != 0)
        self.setLabelPixmapState(self.label_used_6,state & 0x20 != 0)
        self.setLabelPixmapState(self.label_used_7,state & 0x40 != 0)
        self.setLabelPixmapState(self.label_used_8,state & 0x80 != 0)
        self.setLabelPixmapState(self.label_used_9,state & 0x100 != 0)
        self.setLabelPixmapState(self.label_used_10,state & 0x200 != 0)
        self.setLabelPixmapState(self.label_used_11,state & 0x400 != 0)
        self.setLabelPixmapState(self.label_used_11,state & 0x800 != 0)
        self.setLabelPixmapState(self.label_used_12,state & 0x1000 != 0)

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
