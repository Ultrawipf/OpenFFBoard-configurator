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
        self._port = None
        self._ports = []

        self.pushButton_refresh.clicked.connect(self.get_ports)
        self.pushButton_connect.clicked.connect(self.serial_connect_button)
        
        self.update()

    def showEvent(self, event): # pylint: disable=unused-argument, invalid-name
        """On show event, init the param.

        Connect the communication module with the history widget to load the board response.
        """
        self.shown.emit()

    # Tab is hidden
    def hideEvent(self, event): # pylint: disable=unused-argument, invalid-name
        """On hide event, disconnect the event.

        Disconnect the communication module with the history widget
        to stop to log the board response.
        """
        self.hidden.emit()

    # def serial_log(self, txt):
    #     """Add a new text in the history widget."""
    #     if isinstance(txt, list):
    #         txt = "\n".join(txt)
    #     else:
    #         txt = str(txt)

    # def send_line(self):
    #     """Read the command input text, display it in history widget and send it to the board."""
    #     cmd = self.lineEdit_cmd.text() + "\n"
    #     self.serial_log(">" + cmd)
    #     self.serial_write_raw(cmd)

    # def write(self, data):
    #     """Write data to the serial port."""
    #     self._serial.write(data)

    def update(self):
        """Update the UI when a connection is successfull.

        Disable connection button, dropbox, etc.
        Emit for all the UI the [connected] event.
        """
        if self._serial.isOpen():
            self.pushButton_connect.setText(self.tr("Disconnect"))
            self.comboBox_port.setEnabled(False)
            self.pushButton_refresh.setVisible(False)
            self.connected.emit(True)
        else:
            self.pushButton_connect.setText(self.tr("Connect"))
            self.comboBox_port.setEnabled(True)
            self.pushButton_refresh.setVisible(True)
            self.connected.emit(False)

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

    def select_port(self, port_id):
        """Change the selected port."""
        if port_id != -1 and len(self._ports) != 0:
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
        nb_compatible_device = 0
        for i, port in enumerate(self._ports):
            supported_vid_pid = (
                port.vendorIdentifier(),
                port.productIdentifier(),
            ) in self.OFFICIAL_VID_PID
            

            if supported_vid_pid and not name.startswith("cu."):
                name = F"FFBoard device ({port.portName()})"
            else:
                name = F"{port.description()} ({port.portName()})"
                
            self.comboBox_port.addItem(name)

            if supported_vid_pid and not name.startswith("cu."):
                sel_idx = i
                nb_compatible_device = nb_compatible_device + 1
                self.comboBox_port.setItemData(
                    i,
                    PyQt6.QtGui.QColor(0x00FF00),
                    PyQt6.QtCore.Qt.ItemDataRole.ForegroundRole,
                )
            else:
                self.comboBox_port.setItemData(
                    i,
                    PyQt6.QtGui.QColor(0x990000),
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

        return nb_compatible_device
    
    def auto_connect(self, nb_compatible_device):
        if (nb_compatible_device == 1) :
            self.serial_connect_button()
