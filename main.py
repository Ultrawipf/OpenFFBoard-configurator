"""Main module for UI.
Regroup all required classes to manage the main UI, the systray and
the menu.

Module : main_ui
Authors : yannick

# This GUIs version

# Minimal supported firmware version. 
# Major version of firmware must match firmware. Minor versions must be higher or equal
min_fw = "1.9.1"
version = "1.8.7"
"""
import sys
import functools
import logging
import logging.config
from typing import List
import glob
import os

import PyQt6.QtWidgets
import PyQt6.QtCore
import PyQt6.QtGui
import PyQt6.QtSerialPort
import PyQt6
from PyQt6.QtCore import QEventLoop
from PyQt6.QtGui import QAction,QActionGroup

import config
import helper


# UIs
import base_ui
import serial_ui
import dfu_ui
import dark_palette
import profile_ui
import ffb_ui
import axis_ui
import tmc4671_ui
import pwmdriver_ui
import serial_comms
import midi_ui
import errors
import activelist
import tmcdebug_ui
import odrive_ui
import vesc_ui
import effects_monitor
import effects_graph_ui
import updater
import simplemotion_ui
import activetasks
import rmd_ui
import canremote_ui

# This GUIs version
VERSION = "1.16.9"

# Minimal supported firmware version.
# Major version of firmware must match firmware. Minor versions must be higher or equal
MIN_FW = "1.16.6"

DEFAULTLANG = "en_US"

class MainUi(PyQt6.QtWidgets.QMainWindow, base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Display and manage the main UI."""
    tabsinitialized = PyQt6.QtCore.pyqtSignal(bool)
    maxaxischanged = PyQt6.QtCore.pyqtSignal(int)
    languagechanged = PyQt6.QtCore.pyqtSignal()
    def __init__(self):
        """Init the mainUI : init the UI, all the dlg element, and the main timer."""
        PyQt6.QtWidgets.QMainWindow.__init__(self)
        base_ui.CommunicationHandler.__init__(self)
        
        self.profile_ui = profile_ui.ProfileUI(main=self) # load profile without UI
        self.load_language_id(self.profile_ui.get_global_setting("language",DEFAULTLANG)) # load language file

        base_ui.WidgetUI.__init__(self, None, "MainWindow.ui")

        self.restart_app_flag = False

        self.serial = PyQt6.QtSerialPort.QSerialPort()
        base_ui.CommunicationHandler.comms = serial_comms.SerialComms(self, self.serial)
        self.main_class_ui = None
        self.timeouting = False
        self.connected = False
        self.not_minimize_and_close = True
        self.serial_timer = None

        self.systray : SystrayWrapper = None

        self.lang_actions = {}
        self.language_action_group = QActionGroup(self)
        self.language_action_group.setExclusive(True)

        self.tab_connections = [] # Signals to disconnect on reset

        # Systray
        self.systray = SystrayWrapper(self)
        # Profile
        self.profile_ui.initialize_ui() # Profile UI
        self.make_lang_selector()

        self.timer = PyQt6.QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer) # pylint: disable=no-value-for-parameter
        self.tabWidget_main.currentChanged.connect(self.tab_changed)
        self.errors_dlg = errors.ErrorsDialog(self)
        self.effects_monitor_dlg = effects_monitor.EffectsMonitorDialog(self)
        self.maxaxischanged.connect(self.effects_monitor_dlg.set_max_axes)
        self.effects_graph_dlg = effects_graph_ui.EffectsGraphDialog(self)
        self.maxaxischanged.connect(self.effects_graph_dlg.set_max_axes)
        self.active_class_dlg = activelist.ActiveClassDialog(self)
        self.active_threads_dlg = activetasks.ActiveTaskDialog(self)
        self.active_classes = {}
        self.fw_version_str = None


        self.process_events_timer = PyQt6.QtCore.QTimer()
        self.process_events_timer.timeout.connect(process_events) # Kick eventloop when timeouting
        self.axes = 0

        self.setup()
        self.languagechanged.connect(self.restart_app)
        
        # start the auto disconnect timer (call the board)
        self.timer.start(5000)

    def setup(self):
        """Init the systray, the serial, the toolbar, the status bar and the connection status."""
                # Error dialog clear TODO possibly call after the tab has changed so that it does not appear in the serial log
        self.tabsinitialized.connect(self.errors_dlg.connected_cb)

        self.systray.open_main_ui_signal.connect(self.display_ui)
        self.systray.change_profile_signal.connect(self.change_profile)
        
        self.serialchooser = serial_ui.SerialChooser(serial=self.serial, main_ui=self)
        self.tabWidget_main.addTab(self.serialchooser, self.tr("Serial"))
        self.serialchooser.connected.connect(self.systray.set_connected)
        self.serialchooser.connected.connect(self.profile_ui.setEnabled)

        # Status Bar
        self.wrapper_status_bar = WrapperStatusBar(self.statusBar())
        self.serialchooser.connected.connect(self.wrapper_status_bar.serial_connected)

        # self.serial.readyRead.connect(self.serialReceive)
        self.actionAbout.triggered.connect(self.open_about)
        self.serialchooser.connected.connect(self.serial_connected)

        self.actionUpdates.triggered.connect(self.open_updater)

        self.actionDebug_mode.triggered.connect(self.toggle_debug)

        #self.serialchooser.connected.connect(self.effects_monitor_dlg.setEnabled) # Gets enabled in class management
        self.effects_monitor_dlg.setEnabled(False)

        #self.serialchooser.connected.connect(self.effects_graph_dlg.setEnabled)
        self.effects_graph_dlg.setEnabled(False)

        # Toolbar menu items
        self.actionDFU_Uploader.triggered.connect(self.open_dfu_dialog)

        self.actionErrors.triggered.connect(self.open_logs_errors_dialog)  # Open error list

        self.actionActive_features.triggered.connect(
            self.active_class_dlg.show
        )  # Open active classes list
        self.serialchooser.connected.connect(self.actionActive_features.setEnabled)
        self.serialchooser.connected.connect(self.actionDebug_mode.setEnabled)

        self.actionActive_threads.triggered.connect(self.active_threads_dlg.show)

        self.actionRestore_chip_config.triggered.connect(self.load_flashdump_from_file)
        self.serialchooser.connected.connect(self.actionRestore_chip_config.setEnabled)

        self.actionSave_chip_config.triggered.connect(self.save_flashdump_to_file)
        self.serialchooser.connected.connect(self.actionSave_chip_config.setEnabled)

        self.actionReboot.triggered.connect(self.reboot)
        self.serialchooser.connected.connect(self.actionReboot.setEnabled)

        self.actionReset_Factory_Config.triggered.connect(self.reset_factory_btn)
        self.serialchooser.connected.connect(self.actionReset_Factory_Config.setEnabled)

        self.actionEffectsMonitor.triggered.connect(self.effects_monitor_dlg.display)
        #self.serialchooser.connected.connect(self.actionEffectsMonitor.setEnabled)

        self.actionEffects_forces.triggered.connect(self.effects_graph_dlg.display)
        #self.serialchooser.connected.connect(self.actionEffects_forces.setEnabled)

        # Main Panel
        layout = PyQt6.QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.profile_ui)
        self.groupBox_main.setLayout(layout)
        
        
    def autoconnect(self) :
        # after UI load get serial port and if only one : autoconnect
        nb_device_compat = self.serialchooser.get_ports()
        self.serialchooser.auto_connect(nb_device_compat)

    def load_language_id(self, langid:str):
        """load language file"""
        if langid != DEFAULTLANG:
            langfile = helper.res_path(f"{langid}.qm","translations")
            if translator.load(langfile):
                app.installTranslator(translator)

    def change_lang_callback(self, enabled:bool):
        """Change language of the UI, this will run too when initializing the UI"""
        if(not enabled):  # Language not selected
            return
        
        user_lang_id = self.language_action_group.checkedAction().data()

        if user_lang_id == self.profile_ui.get_global_setting("language",DEFAULTLANG): # If user selected language same as current language
            return 
        
        app.removeTranslator(translator)
        self.profile_ui.set_global_setting("language",user_lang_id) # store language setting
        self.languagechanged.emit() # loading in next start

    def restart_app(self):
        self.restart_app_flag = True
        self.reset_port()
        base_ui.CommunicationHandler.comms.removeAllCallbacks()
        app.quit()
 
    def make_lang_selector(self):
        '''Create the language selector menu, and connect the callback to change language.'''
        languages = [DEFAULTLANG]
        languages.extend([os.path.splitext(os.path.basename(f))[0] for f in glob.glob(helper.res_path("*.qm","translations"))])
        
        for langid in languages:
            action = QAction(langid)
            action.setData(langid)
            action.setCheckable(True)
            self.language_action_group.addAction(action)
            self.lang_actions[langid] = action
            self.menuLanguage.addAction(action)
            action.toggled.connect(self.change_lang_callback)


    def reboot(self):
        """Send the reboot message to the board."""
        self.send_command("sys", "reboot")
        self.reconnect()

    def check_configurator_update(self):
        """Checks if there is an update for the configurator only"""
        donotnotify = self.profile_ui.get_global_setting("donotnotify_updates",False)
        if donotnotify:
            return

        release = updater.GithubRelease.get_latest_release(updater.GUIREPO)
        if not release:
            return
        releaseversion,_ = updater.GithubRelease.get_version(release)
        if updater.UpdateChecker.compare_versions(VERSION,releaseversion):
            # New release available for firmware
            msg =  "New configurator update available.<br>Warning: Check if compatible with firmware.<br>Install firmware from <a href=\"https://github.com/Ultrawipf/OpenFFBoard/releases\"> main repo</a>"
            notification = updater.UpdateNotification(release,self,msg,VERSION,donotnotifysetting="donotnotify_updates")
            notification.exec()

    def open_dfu_dialog(self):
        """Open the dfu dialog and start managing."""
        msg = PyQt6.QtWidgets.QDialog()
        msg.setWindowTitle(self.tr("Firmware"))
        dfu = dfu_ui.DFUModeUI(parentWidget=msg, mainUI=self)
        layout = PyQt6.QtWidgets.QVBoxLayout()
        layout.addWidget(dfu)
        msg.setLayout(layout)
        msg.exec()
        dfu.deleteLater()
        

    def moveEvent(self, event: PyQt6.QtGui.QMoveEvent): #pylint: disable=invalid-name
        """Move all modal dialog when moving main ui."""
        super().moveEvent(event)
        diff = event.pos() - event.oldPos()

        list_dialog:List[PyQt6.QtWidgets.QDialog] = [self.errors_dlg, self.effects_monitor_dlg,
            self.effects_graph_dlg, self.active_class_dlg]
        for dialog in list_dialog:
            if dialog and dialog.isVisible():
                dialog.move(dialog.pos() + diff)
                dialog.update()

    def open_logs_errors_dialog(self):
        """Display the log file on the right if it fill in the screen."""
        # Move the dialog to the widget that called it
        self.errors_dlg.show()

        point = self.window().frameGeometry().topRight()
        height = self.size().height()
        width = self.errors_dlg.size().width()

        if (point.x() + width) < self.screen().size().width() :
            self.errors_dlg.move(point)
            self.errors_dlg.resize(width,height)


    def open_about(self):
        """Open the about dialog box."""
        AboutDialog(self).exec()

    def open_updater(self):
        """Opens updater window"""
        updater.UpdateBrowser(self,self.profile_ui).exec()

    def toggle_debug(self,enabled):
        self.send_value("sys","debug",1 if enabled else 0)
        # Reload mainclasses
        self.serialchooser.get_main_classes() # TODO better move somewhere else


    def save_flashdump_to_file(self):
        """Send a async message to get the flashdump from board."""
        self.get_value_async("sys", "flashdump", config.saveDump)

    def load_flashdump_from_file(self):
        """Load dumpfile and send config to board."""
        dump = config.loadDump()
        if not dump:
            return

        if self.connected:
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

    def timeout_check_cb(self, port_checked):
        """Close the serial connection if the port is not open after a timeout."""
        self.process_events_timer.stop()
        if port_checked != self.serialchooser.main_id:
            self.reset_port()
            self.log("Communication error. Please reconnect")
        else:
            self.timeouting = False

    def update_timer(self):
        """Check on timer if the port is always opened."""
        if self.serial.isOpen():
            if self.timeouting:
                self.timeouting = False
                self.reset_port()
                self.log("Timeout. Please reconnect")
                return
            else:
                self.timeouting = True
                self.process_events_timer.start(100)
                self.get_value_async("main", "id", self.timeout_check_cb, conversion=int)
                self.get_value_async("sys", "heapfree", self.wrapper_status_bar.update_ram_used)
                self.get_value_async("sys", "temp", self.wrapper_status_bar.update_temp)

    def tab_changed(self, id_tab):
        """Add an handler on tab changed : do nothing for the moment."""

    def add_tab(self, widget, name):
        """Add a new tab in the tabWidget with a specific name."""
        return self.tabWidget_main.addTab(widget, name)

    def del_tab(self, widget : PyQt6.QtWidgets.QWidget):
        """Remove a tab in the widget and unregister the serial callback."""
        self.tabWidget_main.removeTab(self.tabWidget_main.indexOf(widget))
        base_ui.CommunicationHandler.remove_callbacks(widget)
        widget.deleteLater()
        del widget

    def select_tab(self, idx):
        """Select a specific tab from the idx parameter."""
        self.tabWidget_main.setCurrentIndex(idx)

    def has_tab(self, name) -> bool:
        """Check if the tab "name" exist in the tab list."""
        names = [
            self.tabWidget_main.tabText(i) for i in range(self.tabWidget_main.count())
        ]
        return name in names

    def reset_tabs(self):
        """Remove all the tab and unregister the callBack."""
        self.active_classes = {}
        self.profile_ui.set_save_btn(False)
        for i in range(self.tabWidget_main.count() - 1, 0, -1):
            self.del_tab(self.tabWidget_main.widget(i))
        self.remove_callbacks()
        self.tabsinitialized.emit(False)

        self.effects_monitor_dlg.setEnabled(False)
        self.effects_graph_dlg.setEnabled(False)
        self.effects_graph_dlg.set_total_output_display(False)
        self.actionActive_threads.setEnabled(False)
        self.actionEffectsMonitor.setEnabled(False)
        self.actionEffects_forces.setEnabled(False)
        self.axes = 0
        self.maxaxischanged.emit(self.axes)

        # Delete signals
        for connection in self.tab_connections:
            try:
                PyQt6.QtCore.QObject.disconnect(connection)
            except Exception as e:
                print("Error disconnecting", e)

    def update_tabs(self):
        """Get the active classes from the board, and add tab when not exist."""
        def update_tabs_cb(active):
            """Process the name received by callback : split string and add tabs."""
            lines = [l.split(":") for l in active.split("\n") if l]
            new_active_classes = {
                i[1]
                + ":"
                + i[2]: {
                    "name": i[0],
                    "clsname": i[1],
                    "id": int(i[3]),
                    "unique": int(i[2]),
                    "ui": None,
                    "cmdaddr": [4],
                }
                for i in lines
            }
            delete_classes = [
                (classe, name)
                for name, classe in self.active_classes.items()
                if name not in new_active_classes
            ]
            #print(new_active_classes)

            for classe, name in delete_classes:
                self.del_tab(classe)
                del self.active_classes[name]
            for name, classe_active in new_active_classes.items():
                if name in self.active_classes:
                    continue
                classname = classe_active["name"]
                if classe_active["id"] == 1 or classe_active["id"] == 2 or classe_active["id"] == 3:
                    self.main_class_ui = ffb_ui.FfbUI(main=self, title=classname)
                    self.active_classes[name] = self.main_class_ui
                    self.profile_ui.set_save_btn(True)
                    self.tab_connections.append(self.main_class_ui.ffb_rate_event.connect(self.wrapper_status_bar.update_ffb_rate))
                    # Start ffb timer
                    
                    self.tab_connections.append(self.serialchooser.hidden.connect(self.main_class_ui.startTimer))
                    self.tab_connections.append(self.serialchooser.shown.connect(self.main_class_ui.stopTimer))
                    self.tab_connections.append(self.serialchooser.shown.connect(lambda : self.wrapper_status_bar.update_ffb_block_display(False)))
                    self.tab_connections.append(self.serialchooser.hidden.connect(lambda : self.wrapper_status_bar.update_ffb_block_display(True)))
                    self.wrapper_status_bar.update_ffb_block_display(True)
                    
                elif classe_active["id"] == 0xA01:
                    classe = axis_ui.AxisUI(main=self, unique=classe_active["unique"])
                    name_axis = classe_active["name"] + ":" + chr(classe.axis + ord("0"))
                    self.active_classes[name] = classe
                    self.add_tab(classe, name_axis)
                    self.profile_ui.set_save_btn(True)
                    self.axes = max(self.axes,classe.axis)
                    self.maxaxischanged.emit(self.axes)
                    self.effects_graph_dlg.set_total_output_display(True)
                elif classe_active["id"] == 0x81 or classe_active["id"] == 0x82 or \
                    classe_active["id"] == 0x83:
                    classe = tmc4671_ui.TMC4671Ui(main=self, unique=classe_active["unique"])
                    name_axis = classe_active["name"] + ":" + chr(classe.axis + ord("0"))
                    self.active_classes[name] = classe
                    self.add_tab(classe, name_axis)
                    self.profile_ui.set_save_btn(True)
                elif classe_active["id"] == 0x84:
                    classe = pwmdriver_ui.PwmDriverUI(main=self)
                    self.active_classes[name] = classe
                    self.add_tab(classe, classe_active["name"])
                    self.profile_ui.set_save_btn(True)
                elif classe_active["id"] == 0xD:
                    classe = midi_ui.MidiUI(main=self)
                    self.active_classes[name] = classe
                    self.add_tab(classe, classe_active["name"])
                elif classe_active["id"] == 0xB:
                    classe = tmcdebug_ui.TMCDebugUI(main=self)
                    self.active_classes[name] = classe
                    self.add_tab(classe, classe_active["name"])
                elif classe_active["id"] == 0x85 or classe_active["id"] == 0x86:
                    classe = odrive_ui.OdriveUI(main=self, unique=classe_active["unique"])
                    name_axis = classe_active["name"]
                    self.active_classes[name] = classe
                    self.add_tab(classe, name_axis)
                    self.profile_ui.set_save_btn(True)
                elif classe_active["id"] == 0x87 or classe_active["id"] == 0x88:
                    classe = vesc_ui.VescUI(main=self, unique=classe_active["unique"])
                    name_axis = classe_active["name"]
                    self.active_classes[name] = classe
                    self.add_tab(classe, name_axis)
                    self.profile_ui.set_save_btn(True)
                elif classe_active["id"] == 0x89 or classe_active["id"] == 0x8A:
                    classe = simplemotion_ui.SimplemotionUI(main=self, unique=classe_active["unique"])
                    name_axis = classe_active["name"]
                    self.active_classes[name] = classe
                    self.add_tab(classe, name_axis)
                    self.profile_ui.set_save_btn(True)
                elif classe_active["id"] == 0xA02: # Effects manager
                    self.effects_monitor_dlg.setEnabled(True)
                    self.effects_graph_dlg.setEnabled(True)
                    self.actionEffectsMonitor.setEnabled(True)
                    self.actionEffects_forces.setEnabled(True)
                elif classe_active["id"] == 0x8B or classe_active["id"] == 0x8C:
                    classe = rmd_ui.RmdUI(main=self, unique=classe_active["unique"])
                    name_axis = classe_active["name"]
                    self.active_classes[name] = classe
                    self.add_tab(classe, name_axis)
                    self.profile_ui.set_save_btn(True)
                elif classe_active["id"] == 0x5:
                    classe = canremote_ui.CanRemoteUi(main=self)
                    name_axis = classe_active["name"]
                    self.active_classes[name] = classe
                    self.add_tab(classe, name_axis)
                    self.profile_ui.set_save_btn(True)



            self.tabsinitialized.emit(True)

        self.get_value_async("sys", "lsactive", update_tabs_cb, delete=True)
        self.get_value_async(
            "sys", "heapfree", self.wrapper_status_bar.update_ram_used, delete=True
        )
        def cmdinfo18_cb(x):
            self.actionActive_threads.setEnabled(x==1)
            self.active_threads_dlg.set_taskstats_enabled(x==1) 
        self.get_value_async("sys","cmdinfo",adr=18,conversion=int,callback=cmdinfo18_cb) # Check taskstats
        self.get_value_async("sys","cmdinfo",adr=23,conversion=int,callback=lambda x:self.active_threads_dlg.set_tasklist_enabled(x==1) ) # Check taskstats

    def reconnect(self):
        """Reconnect the board : re-open the serial link, and check it."""
        self.reset_port()
        PyQt6.QtCore.QTimer.singleShot(1500, self.serialchooser.serial_connect_button)

    def reset_port(self):
        """Close serial port and remove tabs."""
        self.log("Reset port")
        self.profile_ui.setEnabled(False)
        #self.serial.waitForBytesWritten(250) # Broken on pyqt6.3

        # Workaround until waitForBytesWritten works again or a better solution has been found
        def close():
            self.serial.close()
            self.comms_reset()
            self.timeouting = False
            self.serialchooser.update()
            self.reset_tabs()

        if self.serial.bytesToWrite() > 0:
            # Not everything has been sent
            self.serial.flush() # Immediately send
            PyQt6.QtCore.QTimer.singleShot(250, close) # Close port after 250ms because no signal is currently working. Should ensure data has been sent.

        else:
            close() # Close port
        
    def version_check(self, ver):
        """Check if the UI is compatible with this board firmware."""
        self.fw_version_str = ver.replace("\n", "")
        if not self.fw_version_str:
            self.log("Communication error")
            self.reset_port()

        fw_ver_split = [int(i) for i in self.fw_version_str.split(".")]
        min_fw_split = [int(i) for i in MIN_FW.split(".")]
        #guiVersion = [int(i) for i in VERSION.split(".")]

        self.log("FW v" + self.fw_version_str)
        fw_outdated = False
        gui_outdated = False

        fw_outdated = (
            min_fw_split[0] > fw_ver_split[0] \
            or min_fw_split[1] > fw_ver_split[1] and min_fw_split[0] == fw_ver_split[0]  \
            or min_fw_split[2] > fw_ver_split[2] and min_fw_split[1] ==  fw_ver_split[1] and  min_fw_split[0] == fw_ver_split[0]
        )
        gui_outdated = min_fw_split[0] < fw_ver_split[0] or min_fw_split[1] < fw_ver_split[1] and min_fw_split[0] == fw_ver_split[0]

        if gui_outdated:
            msg = PyQt6.QtWidgets.QMessageBox(
                PyQt6.QtWidgets.QMessageBox.Icon.Information,
                self.tr("Incompatible GUI"),
                self.tr("The GUI you are using (")
                + VERSION
                + self.tr(") may be too old for this firmware.\nPlease make sure both "
                "firmware and GUI are up to date if you encounter errors.")
            )
            msg.exec()
        elif fw_outdated:
            msg = PyQt6.QtWidgets.QMessageBox(
                PyQt6.QtWidgets.QMessageBox.Icon.Information,
                self.tr("Incompatible firmware"),
                self.tr("The firmware you are using (")
                + self.fw_version_str
                + self.tr(") is too old for this GUI.\n(")
                + MIN_FW
                + self.tr(" required)\nPlease make sure both firmware "
                "and GUI are up to date if you encounter errors.")
            )
            msg.exec()
        # Check github
        mainreporelease = updater.GithubRelease.get_latest_release(updater.MAINREPO)
        releaseversion,_ = updater.GithubRelease.get_version(mainreporelease)
        if updater.UpdateChecker.compare_versions(self.fw_version_str,releaseversion):
            donotnotify = self.profile_ui.get_global_setting("donotnotify_updates",False)
            if not donotnotify:
                # New release available for firmware
                msg = self.tr( "New firmware available")
                notification = updater.UpdateNotification(mainreporelease,self,msg,self.fw_version_str)
                notification.exec()
   


    def serial_connected(self, connected):
        """Check the release when a board is connected."""
        
        def timer_cb():
            if not self.connected:
                self.log("Can't detect board")
                self.reset_port()

        def id_cb(identifier):
            if identifier:
                self.serial_timer.stop()
                self.connected = True

        if connected:
            self.get_value_async("main", "id", id_cb, 0)
            self.errors_dlg.registerCallbacks()
            self.get_value_async("sys", "swver", self.version_check)
            self.get_value_async("sys", "hwtype", self.wrapper_status_bar.set_board_text)
            self.get_value_async("sys", "debug", self.actionDebug_mode.setChecked,0,int)
            
            if (self.serial_timer is None) :
                self.serial_timer = PyQt6.QtCore.QTimer(singleShot=True, timeout=timer_cb)
            self.serial_timer.start(500)

        else:
            self.connected = False
            self.log("Disconnected")
            self.reset_tabs()
            self.comms.removeAllCallbacks() # Ensure everything is cleared

    def reset_factory(self, btn):
        """Send a async message to reset factory settings."""
        cmd = btn.text()
        if cmd == "OK":
            self.send_value("sys", "format", 1)
            self.send_command("sys", "reboot")
            self.reset_port()

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

    def change_profile(self, profilename: str):
        """Change the current profile by this one selected."""
        if self.connected:
            self.profile_ui.select_profile(profilename)

    def display_ui(self):
        """Show the UI, and restore it to normal state."""
        self.show()
        self.showNormal()


class SystrayWrapper(PyQt6.QtCore.QObject):
    """Manage the actions and the content of the systray menu."""

    open_main_ui_signal = PyQt6.QtCore.pyqtSignal()
    change_profile_signal = PyQt6.QtCore.pyqtSignal(str)

    def __init__(self, main: MainUi):
        """Build the content menu, and link the action on the main action."""
        PyQt6.QtCore.QObject.__init__(self)
        self._submenu_profiles: PyQt6.QtWidgets.QMenu = None

        # Adding an icon
        icon = PyQt6.QtGui.QIcon("app.png")

        # Adding item on the menu bar
        tray = PyQt6.QtWidgets.QSystemTrayIcon(main)
        tray.setIcon(icon)
        tray.setVisible(True)
        tray.activated.connect(self.on_tray_icon_activated) # pylint: disable=no-value-for-parameter
        tray.setToolTip(self.tr("Open FFBoard Configurator"))

        # Creating the options
        menu = PyQt6.QtWidgets.QMenu(main)
        option1 = PyQt6.QtGui.QAction(self.tr("Open console"), menu)
        option1.triggered.connect(self.open_main_ui_signal) # pylint: disable=no-value-for-parameter
        menu.addAction(option1)
        menu.addSeparator()

        # profiles selection
        submenu = PyQt6.QtWidgets.QMenu(self.tr("Profiles"), main)
        menu.addMenu(submenu)
        self._submenu_profiles = submenu

        menu.addSeparator()

        # To quit the app
        quit_action = menu.addAction(self.tr("Quit"))
        quit_action.triggered.connect(app.quit)

        # Adding options to the System Tray
        tray.setContextMenu(menu)

    def on_tray_icon_activated(self, reason):
        """Show the main UI if double click on icon in systray."""
        if reason == PyQt6.QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_main_ui_signal.emit()

    def refresh_profile_list(self, listprofile):
        """Refresh the menu list with the actions profiles name."""
        self._submenu_profiles.clear()
        actions = []
        for profilename in listprofile:
            action = PyQt6.QtGui.QAction(profilename, self._submenu_profiles)
            action.triggered.connect(   # pylint: disable=no-value-for-parameter
                functools.partial(self.select_profile, profilename)
            )
            action.setEnabled(False)
            actions.append(action)
        self._submenu_profiles.addActions(actions)

    def select_profile(self, profile_name):
        """Propagate the signal change_profile to notify all listener about change."""
        self.change_profile_signal.emit(profile_name)

    def set_connected(self, val):
        """Enable the submenu profile if the board is connected."""
        self._submenu_profiles.setEnabled(val)

    def refresh_profile_action_status(self, profilename):
        """Enable menu action for the profile not currently loaded."""
        for action in self._submenu_profiles.actions():
            action.setEnabled(action.text() != profilename)


class WrapperStatusBar(base_ui.WidgetUI):
    """Manage the status bar and display status."""

    def __init__(self, status_bar=None):
        """Init the status bar UI in the Qt status bar object."""
        base_ui.WidgetUI.__init__(self, None, "statusbar.ui")

        status_bar.addPermanentWidget(self,1)

        icon_ok = PyQt6.QtGui.QIcon(
            self.style().standardIcon(PyQt6.QtWidgets.QStyle.StandardPixmap.SP_DialogYesButton)
        )
        icon_ko = PyQt6.QtGui.QIcon(
            self.style().standardIcon(PyQt6.QtWidgets.QStyle.StandardPixmap.SP_DialogNoButton)
        )
        icon_err = PyQt6.QtGui.QIcon(
            self.style().standardIcon(PyQt6.QtWidgets.QStyle.StandardPixmap.SP_BrowserStop)
        )
        
        self.icon_ok = icon_ok.pixmap(18, 18)
        self.icon_ko = icon_ko.pixmap(18, 18)
        self.icon_err = icon_err.pixmap(18, 18)
        self.label_cnx.setPixmap(self.icon_ko)

        self.label_ffbcnx.setPixmap(self.icon_ko)
        self.label_ffbfreq.setText("")
        self.update_ffb_block_display(False)
        self.line_temp.hide()

        self.serial_connected(False)

        self.logger.register_to_logger(self.append_log)

    def update_ram_used(self, reply):
        """Display in the status bar the new ram used."""
        usage = reply.split(":")
        use = int(usage[0])
        minuse = None
        if len(usage) == 2:
            minuse = int(usage[1])
        if use:
            use = round(int(use) / 1000.0, 2)
            if minuse:
                minuse = round(int(minuse) / 1000.0, 2)
                self.label_memfree.setText(F"{use}k ({minuse}k min)")
            else:
                self.label_memfree.setText(F"{use}k")

    def update_ffb_block_display(self, visibility:bool):
        """Show the ffb block in the status block."""
        if visibility:
            self.line_ffb.show()
            self.label_ffbcnx.show()
            self.label_ffb.show()
            self.label_ffbfreq.show()
        else:
            self.line_ffb.hide()
            self.label_ffbcnx.hide()
            self.label_ffb.hide()
            self.label_ffbfreq.hide()

    def set_board_text(self,text):
        self.label_board.setText(text)

    def update_ffb_rate(self, event):
        status, rate, cfrate = event
        if status == 1:
            self.label_ffbcnx.setPixmap(self.icon_ok)
            self.label_ffbfreq.setText(F"{rate} hz (CF {cfrate} hz)")
        elif status == -1:
            # Emergency stop
            self.label_ffbcnx.setPixmap(self.icon_err)
            self.label_ffbfreq.setText(F"{rate} hz (EMERGENCY STOP)")
        else :
            self.label_ffbcnx.setPixmap(self.icon_ko)
            self.label_ffbfreq.setText(F"{rate} hz")
        

    def update_status(self, msg):
        """Change the status message in the bottom right."""
        self.label_status.setText(msg)

    def update_temp(self,msg):
        """Update temperature display"""
        self.line_temp.show()
        self.label_temp.setText(f"{msg} °C")


    def serial_connected(self, connected):
        """Enable or disable the label in the button, when connection status change."""
        if connected:
            self.label_cnx.setPixmap(self.icon_ok)
        else:
            self.label_cnx.setPixmap(self.icon_ko)
            self.update_ffb_block_display(False)
            self.label_board.setText(self.tr("disconnected"))

    def append_log(self, message):
        """Display the last log message in the status bar."""
        self.label_log.setText(message)


class AboutDialog(PyQt6.QtWidgets.QDialog):
    """Display the about dialog box."""

    def __init__(self, parent : MainUi = None ):
        """Display the about box with the release number updated."""
        PyQt6.QtWidgets.QDialog.__init__(self, parent)
        PyQt6.uic.loadUi(helper.res_path("about.ui"), self)
        verstr = "Version: " + VERSION
        if parent.fw_version_str:
            verstr += " / Firmware: " + parent.fw_version_str
        self.version.setText(verstr)


def windows_theme_is_light():
    """Detect if the user is using Dark Mode in Windows.

    Registry will return 0 if Windows is in Dark Mode and 1
    if Windows is in Light Mode. This dictionary converts that
    output into the text that the program is expecting.
    0 = Dark, 1 = Light
    In HKEY_CURRENT_USER, get the Personalisation Key.
    """
    try:
        key = getKey( hkey, "Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize" )
        # In the Personalisation Key, get the AppsUseLightTheme subkey. This returns a tuple.
        # The first item in the tuple is the result we want
        # (0 or 1 indicating Dark Mode or Light Mode); the other value
        # is the type of subkey e.g. DWORD, QWORD, String, etc.
        subkey = getSubkeyValue(key, "AppsUseLightTheme")[0]
    except FileNotFoundError:
        # some headless Windows instances (e.g. GitHub Actions or Docker images)
        # do not have this key
        return None
    return subkey


def process_events():
    """Function to force processing background events. Do NOT call from any slots in the main thread without blocking as that may lead to recursion"""
    app.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents,50)



    

if __name__ == "__main__":
    logging.config.fileConfig(helper.res_path('logger.conf'))
    restart = True
    exit_code = -1
    app = PyQt6.QtWidgets.QApplication(sys.argv)
    translator = PyQt6.QtCore.QTranslator(app) # Translator must be created before UI loaded
    while(restart):
        restart = False
        window = MainUi()
        if (sys.platform == "win32" or "Windows" in sys.platform):
            # only on windows, for macOS and linux use system palette.
            # windows server is not called win32
            # pylint: disable=import-error
            from winreg import (
                HKEY_CURRENT_USER as hkey,
                QueryValueEx as getSubkeyValue,
                OpenKey as getKey,
            )
            # Check if is not using windows 11 style(windows 11 style is dark mode compatible)
            if windows_theme_is_light() == 0 and app.style().objectName() != "windows11":
                app.setStyle("Fusion")
                app.setPalette(dark_palette.PALETTE_DARK)
                window.menubar.setStyleSheet("QMenu::item {color: white; }") # Menu item text ignores palette setting and stays black. Force to white.

        window.setWindowTitle(PyQt6.QtCore.QCoreApplication.translate("MainUi", "Open FFBoard Configurator"))
        window.setWindowIcon(PyQt6.QtGui.QIcon(helper.res_path('app.ico')))
        window.show()
        window.check_configurator_update() # Check for updates after window is shown
        window.autoconnect()

        exit_code = app.exec()
        # Check if we need to restart
        restart = window.restart_app_flag
        window.deleteLater()
        #del app

    sys.exit(exit_code)
