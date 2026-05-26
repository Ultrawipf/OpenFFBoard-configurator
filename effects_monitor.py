import json
from base_ui import WidgetUI,CommunicationHandler
from PyQt6 import QtGui,QtWidgets
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout
import effects_graph_ui

class EffectStatsUI(WidgetUI, CommunicationHandler):
    def __init__(self, main=None, parent = None):
            WidgetUI.__init__(self, main, 'effects_stats.ui')
            CommunicationHandler.__init__(self)
            self.main = main #type: main.MainUi
            self.parent = parent
            self.pending_updates = 0

            self.effects_graph_dlg = effects_graph_ui.EffectsGraphDialog(self)
            
            self.main.maxaxischanged.connect(self.spinBox_axis.setMaximum)
            self.main.maxaxischanged.connect(self.effects_graph_dlg.set_max_axes)

            self.pushButton_ResetData.clicked.connect(self.resetData)
            self.pushButton_graph.clicked.connect(self.openGraph)
            self.spinBox_axis.valueChanged.connect(self.setAxis)
            self.pushButton_reload.clicked.connect(self.reloadUi)

            self.monitoring_available = False

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
            self.axis = None


    def cmdflags(self,flags):
        if flags & CommunicationHandler.CMDFLAG_GETADR:
            # enable axis selection
            self.spinBox_axis.setEnabled(True)

    def setEnabled(self, enable: bool) -> None:
        if not self.monitoring_available :
            enable = False
        self.pushButton_ResetData.setEnabled(enable)
        
        # Stop or start the timer based on connection/enabled state
        if enable:
            if not self.timer.isActive():
                self.timer.start(10000)
        else:
            if self.timer.isActive():
                self.timer.stop()

        return super().setEnabled(enable)
    
    def setEffectAvailable(self, available: bool) -> None:
        self.monitoring_available = available
        if available:
            self.setEnabled(available)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        if self.isEnabled():
            self.timer.start(10000)
        if self.axis == None:
            self.get_value_async("fx", "cmdinfo", self.cmdflags,adr=16,conversion=int) # TODO remove in later version
        return super().showEvent(a0)

    def hideEvent(self, a0) -> None:
        if self.timer.isActive : self.timer.stop()
        self.parent.hide()
        return super().hideEvent(a0)
    
    def resetData(self):
        self.send_value("fx","effectsDetails",0)

    def setAxis(self,axis):
        self.axis = axis

    def refreshUi(self):
        self.pushButton_reload.setEnabled(False)
        self.pending_updates = 2
        self.get_value_async("fx","effectsDetails",self.decodeData_cb,adr=self.axis)
        self.get_value_async("fx","effects",self.setActiveState_cb,conversion=int)
    
    def setLabelPixmapState(self,label,state):
        label.setPixmap(self.icon_ok if state else self.icon_ko)

    def setActiveState_cb(self,state):
        try:
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
            self.setLabelPixmapState(self.label_used_12,state & 0x800 != 0)
        finally:
            self.check_update_finished()

    def decodeData_cb(self, data):
        try:
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
        finally:
            self.check_update_finished()

    def openGraph(self):
        self.effects_graph_dlg.display()
        self.effects_graph_dlg.set_total_output_display(False) # come from the main

    def check_update_finished(self):
        self.pending_updates -= 1
        if self.pending_updates <= 0:
            self.pushButton_reload.setEnabled(True)

    def reloadUi(self):
        self.timer.stop()
        self.refreshUi()
        self.timer.start(10000)