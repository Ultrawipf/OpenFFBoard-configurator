"""Serial UI module.

Regroup all required classes to manage the Serial Connection UI
and the link with the communication module.

Module : serial_ui
Authors : yannick
"""
from concurrent.futures import process
import PyQt6.QtGui
import PyQt6.QtSerialPort
import PyQt6.QtCore
import PyQt6.QtWidgets
import base_ui
import main
import helper
import config


class Settings(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """This classe is the main Serial Chooser manager.

    *) Display the UI
    *) Manage the user interraction : connect/disconnect
    *) Manage the serial port status
    """

    OFFICIAL_VID_PID = [(0x1209, 0xFFB0)]  # Highlighted in serial selector

    def __init__(self,  main_ui, serialport : PyQt6.QtSerialPort.QSerialPort):
        """Initialize the manager with the QSerialPort for serial commmunication and the mainUi."""
        base_ui.WidgetUI.__init__(self, main_ui, "settings_serial.ui")
        base_ui.CommunicationHandler.__init__(self)

        self.main = main_ui
        self.main_id = None

        # prefer the serial port managed by the shared comms object if present
        self._serial = self.comms.serial

        self.pushButton_send.clicked.connect(self.send_line)
        self.lineEdit_cmd.returnPressed.connect(self.send_line)
        self.pushButton_mainclasschange.clicked.connect(self.main_btn)

        self.pushButton_reboot.clicked.connect(self.reboot)
        self.pushButton_save.clicked.connect(self.save_flashdump_to_file)
        self.pushButton_load.clicked.connect(self.load_flashdump_from_file)
        self.pushButton_resetFactory.clicked.connect(self.reset_factory_btn)
        
        # Update UI according to current connection state
        self.update_connected()

    def reboot(self):
        """Send the reboot message to the board."""
        self.send_command("sys", "reboot")
        self.main.reconnect()

    def save_flashdump_to_file(self):
        """Send a async message to get the flashdump from board."""
        self.get_value_async("sys", "flashdump", config.saveDump)

    def load_flashdump_from_file(self):
        """Load dumpfile and send config to board."""
        dump = config.loadDump()
        if not dump:
            return

        if self.main.connected:
            for sector in dump["flash"]:
                self.send_value("sys", "flashraw", sector["val"], sector["addr"], 0)
            # Message
            msg = PyQt6.QtWidgets.QMessageBox(
                PyQt6.QtWidgets.QMessageBox.Icon.Information,
                self.tr("Restore flash dump"),
                self.tr("Uploaded flash dump.\nPlease reboot."),
            )
        else:
            # Message
            msg = PyQt6.QtWidgets.QMessageBox(
                PyQt6.QtWidgets.QMessageBox.Icon.Warning,
                self.tr("Can't restore flash dump"),
                self.tr("Please connect board first."),
            )


        msg.exec()

    def reset_factory(self, btn):
        """Send a async message to reset factory settings."""
        cmd = btn.text()
        if cmd == "OK":
            self.send_value("sys", "format", 1)
            self.send_command("sys", "reboot")
            self.main.reset_port()

    def reset_factory_btn(self):
        """Prompt a confirmation to the user when he click on reset factory."""
        msg = PyQt6.QtWidgets.QMessageBox()
        msg.setIcon(PyQt6.QtWidgets.QMessageBox.Icon.Warning)
        msg.setText(self.tr("Format flash and reset?"))
        msg.setStandardButtons(
            PyQt6.QtWidgets.QMessageBox.StandardButton.Ok
            | PyQt6.QtWidgets.QMessageBox.StandardButton.Cancel
        )
        msg.buttonClicked.connect(self.reset_factory) # pylint: disable=no-value-for-parameter
        msg.exec()

    def showEvent(self, event): # pylint: disable=unused-argument, invalid-name
        """On show event, init the param.

        Connect the communication module with the history widget to load the board response.
        """
        self.get_raw_reply().connect(self.serial_log)

    # Tab is hidden
    def hideEvent(self, event): # pylint: disable=unused-argument, invalid-name
        """On hide event, disconnect the event.

        Disconnect the communication module with the history widget
        to stop to log the board response.
        """
        try:
            self.get_raw_reply().disconnect(self.serial_log)
        except TypeError:
            pass

    def serial_log(self, txt):
        """Add a new text in the history widget."""
        if isinstance(txt, list):
            txt = "\n".join(txt)
        else:
            txt = str(txt)
        self.serialLogBox.append(txt)

    def send_line(self):
        """Read the command input text, display it in history widget and send it to the board."""
        cmd = self.lineEdit_cmd.text() + "\n"
        self.serial_log(">" + cmd)
        self.serial_write_raw(cmd)

    def write(self, data):
        """Write data to the serial port."""
        self._serial.write(data)

    def update_connected(self, state=None):
        """Update the UI when a connection is successfull.

        Disable connection button, dropbox, etc.
        Emit for all the UI the [connected] event.
        """
        if state is None:
            state = self.main.connected

        self.pushButton_send.setEnabled(state)
        self.lineEdit_cmd.setEnabled(state)
        self.tabWidget.setEnabled(state)
        self.groupBox_system.setEnabled(state)


    def update_mains(self, dat):
        """Parse the list of main classes received from board, and update the combobox."""
        self.comboBox_main.clear()
        self._class_ids, self._classes = helper.classlistToIds(dat)

        if self.main_id is None:
            self.groupBox_system.setEnabled(False)
            return

        helper.updateClassComboBox(
            self.comboBox_main, self._class_ids, self._classes, self.main_id
        )

        self.main.log("Detected mode: " + self.comboBox_main.currentText())
        self.main.update_tabs()

    def get_main_classes(self):
        """Get the main classes available from the board in Async."""

        def fct(i):
            """Store the main currently selected to refresh the UI."""
            self.main_id = i

        self.get_value_async("main", "id", fct, conversion=int, delete=True)
        self.get_value_async("sys", "lsmain", self.update_mains, delete=True)

    def main_btn(self):
        """Read the select main class in the combobox.

        Push it to the board and display the reload warning.
        """
        index = self._classes[self.comboBox_main.currentIndex()][0]
        self.send_value("sys", "main", index)
        self.main.reconnect()
        msg = PyQt6.QtWidgets.QMessageBox(
            PyQt6.QtWidgets.QMessageBox.Icon.Information,
            "Main class changed",
            "Chip is rebooting. Please reconnect.",
        )
        msg.exec()
