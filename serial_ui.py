"""Serial UI module.

Regroup all required classes to manage the Serial Connection UI
and the link with the communication module.

Module : serial_ui
Authors : yannick
"""
import PyQt6.QtGui
import PyQt6.QtSerialPort
import PyQt6.QtCore
import PyQt6.QtWidgets
import base_ui
import main
import helper


class SerialChooser(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """This classe is the main Serial Chooser manager.

    *) Display the UI
    *) Manage the user interraction : connect/disconnect
    *) Manage the serial port status
    """

    OFFICIAL_VID_PID = [(0x1209, 0xFFB0)]  # Highlighted in serial selector
    connected = PyQt6.QtCore.pyqtSignal(bool)
    shown = PyQt6.QtCore.pyqtSignal()
    hidden = PyQt6.QtCore.pyqtSignal()
    visible = PyQt6.QtCore.pyqtSignal(bool)

    def __init__(self, serial: PyQt6.QtSerialPort.QSerialPort, main_ui: main.MainUi):
        """Initialize the manager with the QSerialPort for serial commmunication and the mainUi."""
        base_ui.WidgetUI.__init__(self, main_ui, "serialchooser.ui")
        base_ui.CommunicationHandler.__init__(self)
        self._serial = serial
        self.main = main_ui
        #VMA self.connected = PyQt6.QtCore.pyqtSignal(bool)
        self.main_id = None
        self._classes = []
        self._class_ids = {}
        self._port = None
        self._ports = []

        self.pushButton_refresh.clicked.connect(self.get_ports)
        self.pushButton_connect.clicked.connect(self.serial_connect_button)
        self.pushButton_send.clicked.connect(self.send_line)
        self.lineEdit_cmd.returnPressed.connect(self.send_line)
        self.pushButton_ok.clicked.connect(self.main_btn)

        self.get_ports()
        self.update()

    def showEvent(self, event): # pylint: disable=unused-argument, invalid-name
        """On show event, init the param.

        Connect the communication module with the history widget to load the board response.
        """
        self.main.comms.rawReply.connect(self.serial_log)
        self.shown.emit()

    # Tab is hidden
    def hideEvent(self, event): # pylint: disable=unused-argument, invalid-name
        """On hide event, disconnect the event.

        Disconnect the communication module with the history widget
        to stop to log the board response.
        """
        self.main.comms.rawReply.disconnect(self.serial_log)
        self.hidden.emit()

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
        self.main.comms.serialWriteRaw(cmd)

    def write(self, data):
        """Write data to the serial port."""
        self._serial.write(data)

    def update(self):
        """Update the UI when a connection is successfull.

        Disable connection button, dropbox, etc.
        Emit for all the UI the [connected] event.
        """
        if self._serial.isOpen():
            self.pushButton_connect.setText("Disconnect")
            self.comboBox_port.setEnabled(False)
            self.pushButton_refresh.setEnabled(False)
            self.pushButton_send.setEnabled(True)
            self.lineEdit_cmd.setEnabled(True)
            self.connected.emit(True)
            self.get_main_classes()
        else:
            self.pushButton_connect.setText("Connect")
            self.comboBox_port.setEnabled(True)
            self.pushButton_refresh.setEnabled(True)
            self.pushButton_send.setEnabled(False)
            self.lineEdit_cmd.setEnabled(False)
            self.connected.emit(False)
            self.groupBox_system.setEnabled(False)

    def serial_connect_button(self):
        """Check if it's not connected, and call start the serial connection."""
        if not self._serial.isOpen() and self._port is not None:
            self.serial_connect()
        else:
            self._serial.close()
            self.update()

    def serial_connect(self):
        """Check if port is not open and open it with right settings."""
        self.select_port(self.comboBox_port.currentIndex())

        if not self._serial.isOpen() and self._port is not None:
            self.main.log("Connecting...")
            self._serial.setPort(self._port)
            self._serial.setBaudRate(115200)
            self._serial.open(PyQt6.QtCore.QIODevice.OpenModeFlag.ReadWrite)
            if not self._serial.isOpen():
                self.main.log("Can not open port")
            else:
                self._serial.setDataTerminalReady(True)

        self.update()

    def select_port(self, port_id):
        """Change the selected port."""
        if port_id != -1:
            self._port = self._ports[port_id]
        else:
            self._port = None

    def get_ports(self):
        """Get all the serial port available on the computer.

        If the VID.VIP is compatible with openFFBoard color the text in green,
        else put it in red.
        """
        oldport = self._port if self._port else None

        self._ports = PyQt6.QtSerialPort.QSerialPortInfo().availablePorts()
        self.comboBox_port.clear()
        sel_idx = 0
        for i, port in enumerate(self._ports):
            supported_vid_pid = (
                port.vendorIdentifier(),
                port.productIdentifier(),
            ) in self.OFFICIAL_VID_PID
            name = port.portName() + " : " + port.description()
            if supported_vid_pid:
                name += " (FFBoard device)"
            else:
                name += " (Unsupported device)"
            self.comboBox_port.addItem(name)
            if supported_vid_pid:
                sel_idx = i
                self.comboBox_port.setItemData(
                    i,
                    PyQt6.QtGui.QColor("green"),
                    PyQt6.QtCore.Qt.ItemDataRole.ForegroundRole,
                )
            else:
                self.comboBox_port.setItemData(
                    i,
                    PyQt6.QtGui.QColor("red"),
                    PyQt6.QtCore.Qt.ItemDataRole.ForegroundRole,
                )

        plist = [p.portName() for p in self._ports]
        if (
            (oldport is not None)
            and (
                (oldport.vendorIdentifier(), oldport.productIdentifier())
                in self.OFFICIAL_VID_PID
            )
            and (oldport.portName() in plist)
        ):
            self.comboBox_port.setCurrentIndex(plist.index(oldport.portName()))
        else:
            self.comboBox_port.setCurrentIndex(sel_idx)  # preselect found entry
        self.select_port(self.comboBox_port.currentIndex())
        self.update()

    def update_mains(self, dat):
        """Parse the list of main classes received from board, and update the combobox."""
        self.comboBox_main.clear()
        self._class_ids, self._classes = helper.classlistToIds(dat)

        if self.main_id is None:
            # self.main.resetPort()
            self.groupBox_system.setEnabled(False)
            return
        self.groupBox_system.setEnabled(True)

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
