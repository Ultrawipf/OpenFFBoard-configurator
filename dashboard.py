import PyQt6.QtWidgets
from PyQt6 import uic
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex
import base_ui
import hid_comms
import effects_monitor


class DashboardUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """
    Dashboard page widget
    """

    def __init__(self, main_ui):
        base_ui.WidgetUI.__init__(self, main_ui, "dashboard.ui")
        base_ui.CommunicationHandler.__init__(self)
        self.main = main_ui

        self.ffbeffect_ui = effects_monitor.EffectStatsUI(main=self.main, parent=self)
        self.ffbeffect_ui.setEnabled(False)

        # Push content in groupBox_features
        layout = self.groupBox_ffbeffect.layout()
        for i in reversed(range(layout.count())):
            widgetToRemove = layout.itemAt(i).widget()
            if widgetToRemove:
                layout.removeWidget(widgetToRemove)
                widgetToRemove.setParent(None)
        layout.addWidget(self.ffbeffect_ui)
        
        # start Thread HID
        self.worker = hid_comms.HIDWorker()
        self.worker.data_received.connect(self.update_dashboard)
        self.worker.connection_status.connect(self.handle_connection_status)

        self.serial_connected = False
        
        
    def showEvent(self, a0):
        # Start the worker when the dashboard is shown
        self.worker.start_thread()
        return super().showEvent(a0)
    
    def hideEvent(self, a0):
        self.worker.stop()
        return super().hideEvent(a0)

    def set_connected(self, connected):
        self.serial_connected = connected
        self.groupBox_ffbeffect.setEnabled(connected)
        self.ffbeffect_ui.setEnabled(connected)
        if connected:
            self.registerCallbacks()
        else:
            # remove the handler on disconnect
            self.remove_callbacks()

    def setEffectAvailable(self, a0: bool) -> None:
        self.ffbeffect_ui.setEffectAvailable(a0)
        
    def registerCallbacks(self):
        pass

    def handle_connection_status(self, connected, message):
        """Handle connection status updates from HID worker"""
        if connected:
            # Hide status label when connected successfully
            self.lbl_status.setVisible(False)
            self.groupBox_FFBAxes.setVisible(True)
            self.groupBox_ffbeffect.setVisible(True)
            self.groupBox_secAxis.setVisible(True)
            self.groupBox_matrixButton.setVisible(True)
            self.worker.sendCommand(1,0x000,0,0x7) # ask the main class without CDC connexion

        else:
            # Show error message in status label
            self.lbl_status.setVisible(True)
            self.lbl_status.setText(f"{message}")
            self.groupBox_FFBAxes.setVisible(False)
            self.groupBox_ffbeffect.setVisible(False)
            self.groupBox_secAxis.setVisible(False)
            self.groupBox_matrixButton.setVisible(False)

    def update_dashboard(self, report):

        if isinstance(report, hid_comms.CMDReport):
            rep: hid_comms.CMDReport = report
            if (rep.cls == 0 and rep.command == 0x7): # sys.0.main response
                if rep.value==1 :
                    self.progressBar_Y_pos.setEnabled(False)
                    self.progressBar_Y_neg.setEnabled(False)
            return

        """Update dashboard with HID report data"""
        # Hide status label when data is received
        self.lbl_status.setVisible(False)
        
        # Update axis values
        if (report.axis_x > 0) :
            self.progressBar_X_pos.setValue(report.axis_x)
            self.progressBar_X_neg.setValue(0)
        else :
            self.progressBar_X_pos.setValue(0)
            self.progressBar_X_neg.setValue(-report.axis_x)

        if (report.axis_y > 0) :
            self.progressBar_Y_pos.setValue(report.axis_y)
            self.progressBar_Y_neg.setValue(0)
        else :
            self.progressBar_Y_pos.setValue(0)
            self.progressBar_Y_neg.setValue(-report.axis_y)


        self.progressBar_Z.setValue(report.axis_z)
        self.progressBar_RX.setValue(report.axis_rx)
        self.progressBar_RY.setValue(report.axis_ry)
        self.progressBar_RZ.setValue(report.axis_rz)
        self.progressBar_dial.setValue(report.dial)
        self.progressBar_slider.setValue(report.slider)
        
        # Update buttons
        self.lbl_buttons.setText(f"{bin(report.buttons)}")
        # Update individual button checkboxes
        for i in range(64):
            radiobox_name = f"radioButton_{i}"
            if hasattr(self, radiobox_name):
                radiobox = getattr(self, radiobox_name)
                radiobox.setChecked(report.is_button_pressed(i))
