"""DFU module for UI and upgrade process.

Regroup all required classes to manage the DFU UI.

Module : dfu_ui
Authors : yannick
"""
import PyQt6.QtGui
import PyQt6.QtCore
import PyQt6.QtWidgets
import base_ui
import pydfu


class DFUModeUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Manage the UI : show the ui and manage button event.

    Init the class with :
    parentWidget : DialogBox that display this UI
    mainUI : the main class with the serial init.
    """

    def __init__(self, parentWidget, mainUI):
        """Init the UI element and super class with parent."""
        base_ui.WidgetUI.__init__(self, parentWidget, "dfu.ui")
        base_ui.CommunicationHandler.__init__(self)
        self.groupbox_controls.setEnabled(False)
        self.main = mainUI

        self.selected_file = None
        self.dfu_device = None
        self.first_fail = True
        self.elements = None
        self.uploading = False

        self.pushButton_DFU.clicked.connect(self.dfu)
        self.pushButton_filechooser.clicked.connect(self.file_clicked)
        self.pushButton_fullerase.clicked.connect(self.full_erase_clicked)
        self.pushButton_upload.clicked.connect(self.upload_clicked)

        self.device_found = False
        self.timer = PyQt6.QtCore.QTimer(self)
        self.timer.timeout.connect(self.init_ui)  # pylint: disable=no-value-for-parameter
        self.timer.start(1000)

        self.checkBox_massErase.setEnabled(False)  # TODO disable checkbox for now

    def hideEvent(self, a0) -> None:  # pylint: disable=invalid-name
        """Close the dfu mode in pydfu lib and call the UI close event."""
        if self.dfu_device and not self.uploading:
            pydfu.exit_dfu()
        return super().hideEvent(a0)

    def init_ui(self):
        """Set the component status and display log message."""
        dfu_devices = pydfu.get_dfu_devices(idVendor=0x0483, idProduct=0xDF11)
        if not dfu_devices:
            # No devices found
            if self.first_fail:
                self.log("Searching devices...\n")
                self.log(
                    "Make sure the bootloader is detected and drivers installed. Short boot0 to "
                    "force the bootloader when connecting\n"
                )
                self.log("No DFU device found.\nRetrying..")
                self.first_fail = False
            else:
                self.log(".")
            # Enable the DFU button if the serial is connected
            if self.main.connected:
                self.pushButton_DFU.setEnabled(True)
            else:
                self.pushButton_DFU.setEnabled(False)
        elif len(dfu_devices) > 1:
            self.log("Found multiple DFU devices:" + str(dfu_devices) + "\n")
            self.log("Please disconnect other DFU devices to avoid mistakes\n")

        else:
            self.timer.stop()
            try:
                pydfu.init()
            except ValueError as e:
                self.log("Found DFU device but could not connect: " + str(e.args[1]) + "\n")
                self.timer.start()
                return
            self.log("Found DFU device. Please select an option\n")
            self.dfu_device = dfu_devices[0]
            self.groupbox_controls.setEnabled(True)
            self.pushButton_filechooser.setEnabled(True)
            self.pushButton_fullerase.setEnabled(True)
            self.pushButton_DFU.setEnabled(False)

    def dfu(self):
        """Send the dfu command to the board, log message, and close serial."""
        self.send_command("sys", "dfu")
        self.log("\nEntering DFU...\n")
        self.main.reset_port()

    def file_clicked(self):
        """Open the dialog box to select the file to Upload."""
        dlg = PyQt6.QtWidgets.QFileDialog()
        dlg.setFileMode(PyQt6.QtWidgets.QFileDialog.FileMode.ExistingFile)
        dlg.setNameFilters(
            [
                "Firmware files (*.hex *.dfu)",
                "DFU files (*.dfu)",
                "Intel hex files (*.hex)",
            ]
        )
        if dlg.exec():
            filenames = dlg.selectedFiles()
            self.select_file(filenames[0])
            self.pushButton_upload.setEnabled(True)
        else:
            self.pushButton_upload.setEnabled(False)

    def select_file(self, filename):
        """Use the appropriate dfu reader depends on file extension : dfu, hex."""
        self.selected_file = filename
        self.label_filename.setText(self.selected_file)
        if self.selected_file.endswith("dfu"):
            elements = pydfu.read_dfu_file(self.selected_file)
        elif self.selected_file.endswith("hex"):
            elements = pydfu.read_hex_file(self.selected_file)
        else:
            self.log("Not a known firmware file\n")
            return

        if not elements:
            self.log("Error parsing file\n")
            return
        size = sum([e["size"] for e in elements])
        self.log(F"Loaded {len(elements)} segments with {size} bytes\n")
        self.elements = elements

    def upload_clicked(self):
        """Start the upload after the button click event."""
        self.uploading = True
        elements = self.elements
        mass_erase = self.checkBox_massErase.isChecked()
        self.groupbox_controls.setEnabled(False)
        if mass_erase:
            self.full_erase()

        self.log(
            F"Uploading {len(elements)} segments... Do NOT "
            "close this window or disconnect until done!\n"
        )
        try:
            pydfu.write_elements(elements, mass_erase, progress=self.progress)
            self.log("Uploaded!\n")
        except pydfu.DFUException as exception:
            self.log(str(exception))
            self.log("\nUSB Exception during flashing... Please reflash firmware!\n")
        self.uploading = False
        pydfu.exit_dfu()
        self.log("Done. Please reset\n")
        self.groupbox_controls.setEnabled(True)
        self.dfu_device = None

    def full_erase_clicked(self):
        """Ask an confirmation on erase click button event."""
        msg = PyQt6.QtWidgets.QMessageBox()
        msg.setIcon(PyQt6.QtWidgets.QMessageBox.Icon.Warning)
        msg.setWindowTitle("Full chip erase")
        msg.setText("Fully erase the chip?")
        msg.setInformativeText(
            "This erases EVERYTHING.\nFirmware and settings.\nYou may need a programmer "
            "or short the boot0 pins to reflash it!"
        )
        msg.setStandardButtons(
            PyQt6.QtWidgets.QMessageBox.StandardButton.Ok
            | PyQt6.QtWidgets.QMessageBox.StandardButton.Cancel
        )
        ret = msg.exec()
        # Warning displayed. Erase!
        if ret == PyQt6.QtWidgets.QMessageBox.StandardButton.Ok:
            self.full_erase()

    def full_erase(self):
        """Erase the chip using pydfu."""
        if self.dfu_device:
            self.log("Full chip erase started...\n")
            try:
                self.progress(0, 25, 100)
                pydfu.mass_erase()
                self.progress(0, 100, 100)
                self.log("Chip erased\n")
            except pydfu.DFUException as exception:
                self.progress(0, 100, 100)
                self.log(str(exception))
                self.log("\nUSB Exception during erasing... Please reflash firmware!\n")

    def log(self, txt):
        """Append a message in the displayed log."""
        self.textBrowser_dfu.moveCursor(PyQt6.QtGui.QTextCursor.MoveOperation.End)
        self.textBrowser_dfu.insertPlainText(txt)
        self.textBrowser_dfu.moveCursor(PyQt6.QtGui.QTextCursor.MoveOperation.End)
        self.update()
        PyQt6.QtWidgets.QApplication.processEvents()

    def progress(self, addr, offset, size):
        """Update the UI progress bar with the current value."""
        if addr:
            pass  # ignore the addr parameter for the moment
        self.progressBar.setValue(int(offset * 100 / size))
        self.update()
        PyQt6.QtWidgets.QApplication.processEvents()
