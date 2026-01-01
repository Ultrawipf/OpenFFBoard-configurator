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
import pydfu
import updater
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt


class Settings(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """This classe is the main Serial Chooser manager.

    *) Display the UI
    *) Manage the user interraction : connect/disconnect
    *) Manage the serial port status
    """

    OFFICIAL_VID_PID = [(0x1209, 0xFFB0)]  # Highlighted in serial selector
    STM_DEVID_ADR_F4 = 0x40024000

    def __init__(self,  main_ui, serialport : PyQt6.QtSerialPort.QSerialPort):
        """Initialize the manager with the QSerialPort for serial commmunication and the mainUi."""
        base_ui.WidgetUI.__init__(self, main_ui, "settings_serial.ui")
        base_ui.CommunicationHandler.__init__(self)

        self.main = main_ui
        self.main_id = None

        # prefer the serial port managed by the shared comms object if present
        self._serial = self.comms.serial

        # OpenFFBoard Tab
        self.pushButton_send.clicked.connect(self.send_line)
        self.lineEdit_cmd.returnPressed.connect(self.send_line)
        self.pushButton_mainclasschange.clicked.connect(self.main_btn)

        self.pushButton_reboot.clicked.connect(self.reboot)
        self.pushButton_save.clicked.connect(self.save_flashdump_to_file)
        self.pushButton_load.clicked.connect(self.load_flashdump_from_file)
        self.pushButton_resetFactory.clicked.connect(self.reset_factory_btn)
        
        # Update Tab - DFU
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
        self.timer.timeout.connect(self.init_dfu_ui)

        if self.main.connected:
            self.getInfoSerial()

        self.checkBox_massErase.setEnabled(False)  # TODO disable checkbox for now

        self.devinfo = {"devid":0,"revid":0,"uid":0,"signature":0,"CUR_HW_TYPE":None}
        
        # Update Tab - Update Browser
        self.listWidget_release.currentItemChanged.connect(self.release_changed)
        self.listWidget_files.currentItemChanged.connect(self.file_changed)
        self.buttonGroup_repo.buttonClicked.connect(self.repo_changed)
        self.read_releases(updater.MAINREPO)
        
        if self.main.profile_ui:
            self.checkBox_notify.setChecked(not self.main.profile_ui.get_global_setting("donotnotify_updates",False))
            self.checkBox_notify.toggled.connect(self.notify_checkbox_toggled)
        else:
            self.checkBox_notify.setVisible(False)

        # Update UI according to current connection state
        self.update_connected()
        
        # Connect the debug checkbox from UI
        self.checkBox_debug.stateChanged.connect(self.toggle_debug_mode)

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
        self.timer.start(1000)
        return super().showEvent(event)


    # Tab is hidden
    def hideEvent(self, event): # pylint: disable=unused-argument, invalid-name
        """On hide event, disconnect the event.

        Disconnect the communication module with the history widget
        to stop to log the board response.
        """
        # disconnect the serial logging
        try:
            self.get_raw_reply().disconnect(self.serial_log)
        except TypeError:
            pass
        
        # stop DFU timer
        if (self.timer.isActive()):
            self.timer.stop()
        if self.dfu_device and not self.uploading:
            pydfu.exit_dfu()
        
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

        Emit for all the UI the [connected] event.
        This is also called with state=False when disconnected.
        Event come from main_ui when connection state change.
        """
        if state is None:
            state = self.main.connected
            
        # Hardware Tab
        self.groupBox_system.setEnabled(state)
        self.groupBox_terminal.setEnabled(state)

        # Update Tab
        #self.groupBox_dfu.setEnabled(state)
        self.pushButton_DFU.setEnabled(state)
        
        if state:
            self.get_main_classes()

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
        
    # DFU Methods
    def getInfoDfu(self):
        #self.devinfo["devid"] = pydfu.read_memory(self.STM_DEVID_ADR_F4,32)
        #print(self.devinfo)
        pass

    def getInfoSerial(self):
        pass

    def init_dfu_ui(self):
        """Set the component status and display log message."""
        dfu_devices = pydfu.get_dfu_devices(idVendor=0x0483, idProduct=0xDF11)
        if not dfu_devices:
            # No devices found
            self.groupbox_controls_update.setEnabled(False)
            if self.first_fail:
                self.log_dfu(self.tr("Searching devices...\n"))
                self.log_dfu(self.tr(
                    "Make sure the bootloader is detected and drivers installed. Short boot0 to "
                    "force the bootloader when connecting.\n"
                ))
                self.log_dfu(self.tr("No DFU device found.\nRetrying.."))
                self.first_fail = False
            else:
                self.log_dfu(".")
            # Enable the DFU button if the serial is connected
            if self.main.connected:
                self.pushButton_DFU.setEnabled(True)
            else:
                self.pushButton_DFU.setEnabled(False)
        elif len(dfu_devices) > 1:
            self.log_dfu(self.tr("Found multiple DFU devices:" + str(dfu_devices) + "\n"))
            self.log_dfu(self.tr("Please disconnect other DFU devices to avoid mistakes\n"))

        else:
            self.timer.stop()
            try:
                pydfu.init()
            except ValueError as e:
                self.log_dfu(self.tr("\nFound DFU device but could not connect: " + str(e.args[1]) + "\n"))
                self.timer.start()
                return
            self.log_dfu(self.tr("\nFound DFU device. Please select an option\n"))
            self.dfu_device = dfu_devices[0]
            self.getInfoDfu()
            self.groupbox_controls_update.setEnabled(True)
            self.pushButton_filechooser.setEnabled(True)
            self.pushButton_fullerase.setEnabled(True)
            self.pushButton_DFU.setEnabled(False)

    def dfu(self):
        """Send the dfu command to the board, log message, and close serial."""
        #
        self.send_command("sys", "dfu")
        self.log_dfu("\nEntering DFU...\n")
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
            elements,metadata = pydfu.read_hex_file(self.selected_file,"#")
            if(metadata):
                self.check_metadata(metadata)
        else:
            self.log_dfu("Not a known firmware file\n")
            return

        if not elements:
            self.log_dfu("Error parsing file\n")
            return
        size = sum([e["size"] for e in elements])
        self.log_dfu(F"Loaded {len(elements)} segments with {round(size/1024,2)}kB\n")
        self.elements = elements

    def upload_clicked(self):
        """Start the upload after the button click event."""
        self.uploading = True
        elements = self.elements
        mass_erase = self.checkBox_massErase.isChecked()
        self.groupbox_controls_update.setEnabled(False)
        if mass_erase:
            self.full_erase()

        self.log_dfu(
            F"Uploading {len(elements)} segments... Do NOT "
            "close this window or disconnect until done!\n"
        )
        try:
            pydfu.write_elements(elements, mass_erase, progress=self.progress,logfunc=self.log_dfu)
            self.log_dfu("Uploaded!\n")
        except pydfu.DFUException as exception:
            self.log_dfu(str(exception))
            self.log_dfu("\nUSB Exception during flashing... Please reflash firmware!\n")
        self.uploading = False
        pydfu.exit_dfu()
        self.log_dfu("Done. Please reset\n")
        self.groupbox_controls_update.setEnabled(True)
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
            self.log_dfu("Full chip erase started...\n")
            try:
                self.progress(0, 25, 100)
                pydfu.mass_erase()
                self.progress(0, 100, 100)
                self.log_dfu("Chip erased\n")
            except pydfu.DFUException as exception:
                self.progress(0, 100, 100)
                self.log_dfu(str(exception))
                self.log_dfu("\nUSB Exception during erasing... Please reflash firmware!\n")

    def log_dfu(self, txt):
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

    def check_metadata(self,metadata):
        # Split all comment lines into a dict of definename:value or None
        metadatadict = {line[0]:line[1] if len(line)>1 else None for line in [l.split(" ",1) for l in metadata]} 
        # print(metadatadict)
        warnmsg = ""
        if "HW_TYPE" in metadatadict and self.devinfo["CUR_HW_TYPE"]: # hw name definition of new firmware should match current one
            if self.devinfo["CUR_HW_TYPE"] != metadatadict["HW_TYPE"]:
                # Warn hwtype
                warnmsg += self.tr(f"Warning: Current firmware type {self.devinfo['CUR_HW_TYPE']} does not match new firmware type {metadatadict['HW_TYPE']}\n")
        if warnmsg:
            self.log_dfu(warnmsg + "\n")
            msg = PyQt6.QtWidgets.QMessageBox()
            msg.setIcon(PyQt6.QtWidgets.QMessageBox.Icon.Warning)
            msg.setWindowTitle("WARNING")
            msg.setText(self.tr("Firmware mismatch detected!"))
            msg.setInformativeText(warnmsg)
            ret = msg.exec()

    # Update Browser Methods
    def notify_checkbox_toggled(self,status):
        self.main.profile_ui.set_global_setting("donotnotify_updates",not status)

    def fill_releases(self,releases : dict):
        self.listWidget_release.clear()
        for r in releases:
            if r.get("name",None):
                name = f"{r.get('tag_name','No tag')} ({r.get('name')})"
            else:
                name = f"{r.get('tag_name','No tag')}"
            item = PyQt6.QtWidgets.QListWidgetItem(name)
            if r.get("prerelease",False):
                item.setBackground(QColor('#ffb810'))
            else:
                item.setBackground(QColor('#70ea5d'))
            item.setData(Qt.ItemDataRole.UserRole, r)
            self.listWidget_release.addItem(item)

        self.listWidget_release.setCurrentRow(0)

    
    def get_selected_release(self):
        r = self.listWidget_release.currentItem().data(Qt.ItemDataRole.UserRole)
        return r
    
    def repo_changed(self,button):
        if button == self.radioButton_configurator:
            self.read_releases(updater.GUIREPO)
        else:
            self.read_releases(updater.MAINREPO)

    def read_releases(self,repo : str):
        releases = updater.GithubRelease.get_releases(repo,True)
        if releases:
            self.fill_releases(releases)
            

    def fill_files(self,release : dict):
        self.listWidget_files.clear()
        for r in release.get("assets",[]):
            name = r['name']
            url = r['browser_download_url']
            item = PyQt6.QtWidgets.QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, url)
            self.listWidget_files.addItem(item)
        self.listWidget_files.setCurrentRow(0)


    def release_changed(self,current : PyQt6.QtWidgets.QListWidgetItem,old : PyQt6.QtWidgets.QListWidgetItem):
        if not current:
            return
        release = current.data(Qt.ItemDataRole.UserRole)
        self.textBrowser_releasenotes.setMarkdown(updater.GithubRelease.get_description(release))
        self.label_releaseUrl.setText(f"<a href=\"{release['html_url']}\">{release['html_url']}</a>")
        self.fill_files(release)
        publishtime = updater.GithubRelease.get_time(release)
        infotext = f"Date: {publishtime}"
        self.label_releaseInfo.setText(infotext)

    def file_changed(self,current : PyQt6.QtWidgets.QListWidgetItem,old : PyQt6.QtWidgets.QListWidgetItem):
        if not current:
            return
        url = current.data(Qt.ItemDataRole.UserRole)
        self.label_fileUrl.setText(f"<a href=\"{url}\">Download</a>")

    def init_language_selector(self):
        """Initialize the language selector in the settings tab."""
        # Get available languages
        import glob
        import os
        languages = ["en_US"]  # Default language
        languages.extend([os.path.splitext(os.path.basename(f))[0] for f in glob.glob(helper.res_path("*.qm","translations"))])
        
        # Clear existing items
        self.comboBox_language.clear()
        
        # Add languages to combo box
        for langid in languages:
            self.comboBox_language.addItem(langid)
        
        # Set current language
        current_lang = self.main.profile_ui.get_global_setting("language", "en_US")
        current_index = self.comboBox_language.findText(current_lang)
        if current_index >= 0:
            self.comboBox_language.setCurrentIndex(current_index)
        
        # Connect signal
        self.comboBox_language.currentTextChanged.connect(self.change_language)

    def change_language(self, language_id):
        """Change the application language."""
        # Check if language is different from current
        if language_id == self.main.profile_ui.get_global_setting("language", "en_US"):
            return
            
        # Remove current translator
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and hasattr(self.main, 'translator'):
            app.removeTranslator(self.main.translator)
        
        # Load new language
        if language_id != "en_US":
            langfile = helper.res_path(f"{language_id}.qm", "translations")
            if hasattr(self.main, 'translator') and self.main.translator.load(langfile):
                if app:
                    app.installTranslator(self.main.translator)
        
        # Store language setting
        self.main.profile_ui.set_global_setting("language", language_id)
        
        # Emit signal to restart application (as in original code)
        self.main.languagechanged.emit()
        
    def toggle_debug_mode(self, state):
        """Toggle debug mode on the board."""
        # Send debug mode command to board
        self.send_value("sys", "debug", 1 if state else 0)
        # Reload main classes to apply debug mode
        self.get_main_classes()
