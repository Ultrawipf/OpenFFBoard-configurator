"""Base module helper for UI.

Regroup helper for UI class : the widget_ui, communication_handler and the
inner EventLogger.

Module : base_ui
Authors : yannick, vincet
"""
import PyQt6.QtCore
import PyQt6.QtWidgets
import helper
import serial_comms


class EventLogger(PyQt6.QtCore.QObject):
    """Manage all operation on log_event signal and receiver registration."""

    __log_event = PyQt6.QtCore.pyqtSignal(str)

    def __init__(self):
        """Init the mandatory QObject to manage Signal."""
        PyQt6.QtCore.QObject.__init__(self)

    def log_message(self, msg: str):
        """Send the log message to all receiver."""
        self.__log_event.emit(msg)

    def register_to_logger(self, logger):
        """Register a receiver on the log signal."""
        self.__log_event.connect(logger)

    def unregister_to_logger(self, logger):
        """Unregister a receiver on the log signal."""
        self.__log_event.disconnect(logger)


class WidgetUI(PyQt6.QtWidgets.QWidget):
    """Load the .ui file and set item to the current class. Provide a quick access to logger."""

    logger = EventLogger()

    def __init__(self, parent: PyQt6.QtWidgets.QWidget = None, ui_form: str = ""):
        """Load the .ui file and map it."""
        PyQt6.QtWidgets.QWidget.__init__(self, parent)
        if ui_form:
            PyQt6.uic.loadUi(helper.res_path(ui_form), self)

    def init_ui(self):
        """Prototype of init_ui to manage this status in subclass."""
        return True

    def log(self, message):
        """Access to the internal logger and offer a log message to all subclass."""
        self.logger.log_message(message)


class CommunicationHandler:
    """Store the serial communication to share it to subclass and offer register operation."""

    comms: serial_comms.SerialComms = None

    def __init__(self):
        """Do nothing on the constructor."""

    def __del__(self):
        """Unregister all callback on class destruction."""
        self.remove_callbacks()

    # deletes all callbacks to this class
    def remove_callbacks(self):
        """Remove all callback in SerialComms object (static)."""
        serial_comms.SerialComms.removeCallbacks(self)

    def register_callback(
        self,
        cls,
        cmd,
        callback,
        instance=0,
        conversion=None,
        adr=None,
        delete=False,
        typechar="?",
    ):
        """Register a callback that can be deleted automatically later."""
        # Callbacks normally must prevent sending a value change command in this callback
        # to prevent the same value from being sent back again
        serial_comms.SerialComms.registerCallback(
            self,
            cls=cls,
            cmd=cmd,
            callback=callback,
            instance=instance,
            conversion=conversion,
            adr=adr,
            delete=delete,
            typechar=typechar,
        )

    def get_value_async(
        self,
        cls,
        cmd,
        callback,
        instance: int = 0,
        conversion=None,
        adr=None,
        typechar="?",
        delete=True,
    ):
        """Ask a value to the board from in async way."""
        self.comms.getValueAsync(
            self,
            cls=cls,
            cmd=cmd,
            callback=callback,
            instance=instance,
            conversion=conversion,
            adr=adr,
            typechar=typechar,
            delete=delete,
        )

    def serial_write_raw(self, cmd):
        """Write a command in direct mode througt serial."""
        self.comms.serialWriteRaw(cmd)

    def send_value(self, cls, cmd, val, adr=None, instance=0):
        """Send a value for a specific paramter to the board."""
        self.comms.sendValue(
            self, cls=cls, cmd=cmd, val=val, adr=adr, instance=instance
        )

    def send_command(self, cls, cmd, instance=0, typechar="?"):
        """Send one command to the board."""
        self.comms.sendCommand(cls, cmd, instance=instance, typechar=typechar)

    def send_commands(self, cls, cmds, instance=0, typechar="?"):
        """Send colection of command to the board."""
        cmdstring = ""
        for cmd in cmds:
            cmdstring += f"{cls}.{instance}.{cmd}{typechar};"
        self.comms.serialWriteRaw(cmdstring)
