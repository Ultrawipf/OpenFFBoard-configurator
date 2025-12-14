"""Profile module.

Regroup all required classes to manage Profiles in UI.

Module : profile_ui
Authors : vincent
"""

import os
import json
import copy
import sys
import shutil

import PyQt6.QtCore
import PyQt6.QtWidgets
import PyQt6.QtGui
import base_ui
import helper



class ProfileUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Manage the Profile selector and the board communication about them."""

    __RELEASE = 3

    __PROFILES_FILENAME = "profiles.json"
    __APP_NAME = "openffboard"
    __PROFILES_FILEPATH = None
    __PROFILESSETUP_FILENAME = helper.res_path("profile.cfg")
    __PROFILES_TEMPLATE = {
        "release": __RELEASE,
        "global":{},
        "profiles": [{"name": "None", "data": []}],
    }
    FLASH_PROFILE_NAME = "Flash profile"
    NONE_PROFILE_NAME = "None"

    profiles_updated_event = PyQt6.QtCore.pyqtSignal(list)
    profile_selected_event = PyQt6.QtCore.pyqtSignal(str)

    def __init__(self, main=None):
        """Initialize profile without UI."""
        self.main = main
        self.profiles_dlg = None  # ProfilesDialog is not initialized yet
        self.profile_setup = {}
        self.profiles = {}

        self._current_class = -1
        self._current_command = -1
        self._current_instance = -1
        self._map_class_running = []
        self._running_profile = []
        self._profilename_tosave: str = None

        self.ui_initialized = False
        
        self.__PROFILES_FILEPATH = self.setup_and_migrate_config(self.__PROFILES_FILENAME, self.__APP_NAME)

        self.load_profile_settings()
        self.load_profiles()

    def initialize_ui(self):
        """Init the UI and link the event."""
        base_ui.WidgetUI.__init__(self, self.main, "profile.ui")
        base_ui.CommunicationHandler.__init__(self)
        
        self.profiles_dlg = ProfilesDialog(self)
        self.profiles_dlg.closeSignal.connect(self.close_profile_manager)

        self.pushButton_save.clicked.connect(self.save_clicked)
        icon_save = PyQt6.QtGui.QIcon(
            self.style().standardIcon(PyQt6.QtWidgets.QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.toolButton_save.setIcon(icon_save)
        self.toolButton_save.clicked.connect(self.save_config_in_profile)

        self.comboBox_profiles.currentIndexChanged.connect(self.apply_config)
        icon_manage = PyQt6.QtGui.QIcon(
            self.style().standardIcon(
                PyQt6.QtWidgets.QStyle.StandardPixmap.SP_FileDialogDetailedView
            )
        )
        self.toolButton_manage.setIcon(icon_manage)
        self.toolButton_manage.clicked.connect(self.open_profile_manager)

        self.profiles_updated_event.connect(self.main.systray.refresh_profile_list)
        self.profile_selected_event.connect(
            self.main.systray.refresh_profile_action_status
        )

        self.setEnabled(False)
        
    def get_system_config_dir(self, app_name):
        """
        Returns the system-specific configuration directory.
        """
        home = os.path.expanduser("~")
        
        if sys.platform == "win32":
            # Windows: User requested specific path: C:\Users\Name\.appname
            # We add a dot prefix for Windows to match the request
            return os.path.join(home, f".{app_name}")
            
        elif sys.platform == "darwin":
            # macOS Standard: ~/Library/Application Support/appname
            return os.path.join(home, "Library", "Application Support", app_name)
            
        else:
            # Linux Standard: ~/.config/appname (XDG standard)
            base = os.getenv("XDG_CONFIG_HOME", os.path.join(home, ".config"))
            return os.path.join(base, app_name)

    def setup_and_migrate_config(self, filename, app_name):
        """
        Prepares the configuration directory and migrates the old file if it exists locally.
        Returns the final path of the file to use.
        """
        system_dir = self.get_system_config_dir(app_name)
        system_file_path = os.path.join(system_dir, filename)
        
        # Old location (current working directory)
        local_file_path = os.path.join(os.getcwd(), filename) 

        # Create system directory if it doesn't exist
        if not os.path.exists(system_dir):
            try:
                os.makedirs(system_dir)
                self.log(f"[Info] Config directory created: {system_dir}")
            except OSError as e:
                self.log(f"[Error] Could not create directory: {e}")
                return local_file_path

        # Migration Logic, ff a file exists in the current directory (old method)...
        if os.path.exists(local_file_path):
            
            # and NO file exists in the new system folder yet:
            if not os.path.exists(system_file_path):
                self.log("[Info] Migration in progress: Moving local config to system folder...")
                try:
                    shutil.move(local_file_path, system_file_path)
                    self.log("[Success] Migration complete.")
                except OSError as e:
                    self.log(f"[Error] Migration failed: {e}")
                    return local_file_path # Fallback to local on failure
            
            # if a file exists in BOTH locations (Conflict):
            else:
                self.log("[Warning] Config file exists in both locations.")
                self.log("[Info] Renaming the local (old) file to .bak to avoid confusion.")
                try:
                    shutil.move(local_file_path, local_file_path + ".bak")
                except Exception as e:
                    self.log(f"[Error] Could not rename local file: {e}")

        # 4. Return the final path (System path)
        return system_file_path

    def save_clicked(self):
        """Save current seeting in Flash and replace the 'Flash profile' settings by the new one."""

        def log_save_cb(res):
            """Display the confirmation in log."""
            self.log("Save in flash: " + str(res))
            self.save_config_in_profile(self.FLASH_PROFILE_NAME)
            self.set_save_btn(True)
        
        self.set_save_btn(False)
        self.get_value_async("sys", "save", callback=log_save_cb)

    def onclose(self):
        """Remove the serial call backs on close."""
        self.remove_callbacks()

    def setEnabled(self, a0: bool) -> None:  # pylint: disable=invalid-name
        """Refresh the combo box content with profile when connection is up."""
        if a0 and self.comboBox_profiles.count() == 0:
            self.refresh_combox_list()
        return super().setEnabled(a0)

    def set_save_btn(self, status):
        """Enable the save button based on status."""
        self.pushButton_save.setEnabled(status)

    def open_profile_manager(self):
        """Open the profile list manager."""
        self.profiles_dlg.set_profiles(self.profiles)
        self.profiles_dlg.show()

    def close_profile_manager(self, profile_name:str = ''):
        """Close the profile list manager."""
        self.comboBox_profiles.currentIndexChanged.disconnect(self.apply_config)
        self.refresh_combox_list()
        self.comboBox_profiles.currentIndexChanged.connect(self.apply_config)
        if (profile_name):
            self.select_profile(profile_name)
        self.create_or_update_profile_file()
        self.log('Profile: profiles list updated')

    def load_profile_settings(self):
        """Load the settings for the profile manager in profile.cfg file."""
        check = os.path.exists(self.__PROFILESSETUP_FILENAME)
        if check:
            with open(self.__PROFILESSETUP_FILENAME, "r", encoding="utf_8") as file:
                self.profile_setup = json.load(file)

    def load_profiles(self):
        """Load profiles data in memory : from file if exits, or create a new file."""
        check = os.path.exists(self.__PROFILES_FILEPATH)
        if check:
            self.load_profiles_from_file()
        else:
            self.create_or_update_profile_file(create=True)

    def load_profiles_from_file(self):
        """Load profiles from file profiles.json ."""
        with open(self.__PROFILES_FILEPATH, "r", encoding="utf_8") as profile_file:
            self.profiles = json.load(profile_file)
        if self.profiles['release'] < self.__RELEASE :
            os.rename(self.__PROFILES_FILEPATH, self.__PROFILES_FILEPATH + '.' + str(self.profiles['release']) + '.old')
            self.create_or_update_profile_file(create=True)
            self.log("Profile: profiles are not compatible, need to redo them")
        else:
            self.log("Profile: profiles loaded")
        
        if self.ui_initialized:
            self.refresh_combox_list()

    def create_or_update_profile_file(self, create: bool = False) -> bool:
        """Create a new profile file or update existing one
        
        Args:
            create: Whether to create a new file
            
        Returns:
            bool: Whether operation succeeded
        """
        if create:
            self.profiles = self.__PROFILES_TEMPLATE
            os_lang = PyQt6.QtCore.QLocale.system().name() # get system language, such as zh_CN
            lang_file = os.path.join("translations", f"{os_lang}.qm")
            
            # Use system language if translation exists, otherwise use English
            if os.path.exists(lang_file):
                default_lang = os_lang
            else:
                default_lang = "en_US"
                
            self.profiles['global']['language'] = default_lang
            self.log(f"Profile: use {default_lang} as default language")
            self.log("Profile: profile file created")

            # Ensure the parent directory exists
            os.makedirs(self.get_system_config_dir(self.__APP_NAME), exist_ok=True)

        try:
            with open(self.__PROFILES_FILEPATH, "w", encoding="utf_8") as f:
                json.dump(self.profiles, f)
            return True
        except OSError:
            return False

    def get_global_setting(self,key : str, default = None):
        """Returns an entry of the global section or saves a default if set and not found"""
        if "global" in self.profiles:
            if (key not in self.profiles['global']) and default != None:
                self.set_global_setting(key,default)
            return self.profiles['global'].get(key,None)
        return None

    def set_global_setting(self,key : str, entry, save : bool = True):
        """Adds an item to the global section of the profile file. Set save true to write file immediately"""
        self.profiles['global'][key] = entry
        if save:
            self.create_or_update_profile_file()


    def refresh_combox_list(self):
        """Refresh the combo list of profile when init UI or when list change."""
        self.comboBox_profiles.clear()
        listprofile = []
        data = self.profiles["profiles"]
        for profilename in data:
            listprofile.append(profilename["name"])

        try:
            listprofile.index(ProfileUI.FLASH_PROFILE_NAME)
            listprofile.remove(ProfileUI.NONE_PROFILE_NAME)
        except ValueError:
            pass

        self.comboBox_profiles.addItems(listprofile)
        self.profiles_updated_event.emit(listprofile)

        current_name_selected = self.comboBox_profiles.currentText()
        if current_name_selected is not None:
            self.profile_selected_event.emit(current_name_selected)

    def select_profile(self, profilename: str):
        """Change the current selection with the specified profile name."""
        if profilename == "":
            return
        if profilename != str(self.comboBox_profiles.currentText()):
            index = self.comboBox_profiles.findText(
                profilename, PyQt6.QtCore.Qt.MatchFlag.MatchFixedString
            )
            if index >= 0 and index != self.comboBox_profiles.currentIndex():
                self.comboBox_profiles.setCurrentIndex(index)

    def apply_config(self):
        """Apply the config of the current profile to the board.

        Read active class in board
        Send the paramter for active class to the board.
        """
        # if not enabled, don't select profile
        if not self.isEnabled():
            return

        # read the selected profile name, if profile is None, remove the last message
        profilename = str(self.comboBox_profiles.currentText())
        if profilename == "" or profilename == ProfileUI.NONE_PROFILE_NAME:
            return

        # get the Running Active class and process result with the write config profile
        try:
            self._read_running_class_and_go_cb(self._write_profile_cb)
            self.profile_selected_event.emit(profilename)
        except OSError:
            self.log(F"Profile: can't apply profile '{profilename}', connection is closed.")

    def save_config_in_profile(self, profile_name: str = ""):
        """Save the current config in the selected profile.

        If the  method is called without parameter, save order come from Save-Icon click :
            1- read the profile name in the dropbox.
            2- if the name is 'None' or 'Profile flash', store in flash before all
        When the profile_name is pass, we don't check if "None or Flash Profile", else we have recursivity with method
        'save_clicked'.
        """
        if not(profile_name) or profile_name == "":
            self._profilename_tosave = str(self.comboBox_profiles.currentText())
            
            if self._profilename_tosave == self.NONE_PROFILE_NAME or \
            self._profilename_tosave == self.FLASH_PROFILE_NAME:  
                # if profile to save is "None" or "Profile Flash", we first save in flash and save in profile after
                self.save_clicked()
        else:
            self._profilename_tosave = profile_name

        # get the Running Active class and process result with the read config profile
        try:
            self._read_running_class_and_go_cb(self._read_profile_cb)
        except OSError:
            self.log(F"Profile: can't save the profile '{self._profilename_tosave}'" +
                    ", connection is closed.")


    def _read_running_class_and_go_cb(self, call_back):
        """Get the running class from board, and process the call_back when board respond."""
        # refresh the global var when starting to read value from board
        self._current_class = -1
        self._current_command = -1
        self._current_instance = -1
        self._map_class_running = []
        self._running_profile = []
        # get the list active class from board, after that the the callBack call recursively
        self.get_value_async("sys", "lsactive", call_back)

    ###############  method helper to construct and go through struct definition ###############

    def _build_running_map(self, buffer: str):
        self._map_class_running = []
        # Split the string buffer into array
        splitted_running_class = [x.split(":") for x in buffer.split("\n")]
        # Format the arrray in array of object {classname, fullname, instance}
        formated_iterator = list(
            map(
                lambda tab: {
                    "classname": tab[1],
                    "fullname": tab[0],
                    "instance": int(tab[2]),
                },
                splitted_running_class,
            )
        )
        # For each class to saved declared in the cfg file,
        # we filter the running instance to keep only those
        for call_order in self.profile_setup["callOrder"]:
            filtered_iterator = filter(
                lambda x, call=call_order: x["classname"] == call["classname"]
                and x["fullname"] == call["fullname"],
                formated_iterator,
            )
            self._map_class_running.extend(list(filtered_iterator))

    def _get_instance_running(self, indexclass: int, indexinstance: int):
        if indexclass > len(self.profile_setup["callOrder"]):
            return None

        classname = self.profile_setup["callOrder"][indexclass]["classname"]
        fullname = self.profile_setup["callOrder"][indexclass]["fullname"]
        classes_running = list(
            filter(
                lambda x: x["classname"] == classname and x["fullname"] == fullname,
                self._map_class_running,
            )
        )

        # To test
        # the request instance is not on a running classes
        if len(classes_running) == 0 or indexinstance >= len(classes_running):
            return None
        else:  # else return the instance number
            return int(classes_running[indexinstance]["instance"])

    def _get_next_element_to_request(self):
        is_another_element = False

        # if it's the start
        if (
            self._current_class == -1
            and self._current_command == -1
            and self._current_instance == -1
        ):
            self._current_class = 0
            self._current_command = 0
            self._current_instance = 0
            is_another_element = True
        # if there is another command for this class, go to next command
        elif (self._current_command + 1) < len(
            self.profile_setup["callOrder"][self._current_class]["key"]
        ):
            self._current_command += 1
            is_another_element = True
        else:
            # if there is not next command,
            # we check if there is another instance of this class to request
            next_instance = self._get_instance_running(
                self._current_class, self._current_instance + 1
            )
            if (
                next_instance is not None
            ):  # a next instance exist, we move index to this and restart on 1st dmd
                self._current_instance += 1
                self._current_command = 0
                is_another_element = True
            elif (self._current_class + 1) < len(
                self.profile_setup["callOrder"]
            ):  # there isn't next instance, we move too next class if exist
                self._current_class += 1
                self._current_command = 0
                self._current_instance = 0
                is_another_element = True
            else:
                is_another_element = False

        # if the next computed class/instance is not running, we go to the next
        if (
            is_another_element
            and self._get_instance_running(self._current_class, self._current_instance)
            is None
        ):
            return self._get_next_element_to_request()

        return is_another_element

    def _read_value(self, indexclass: int, indexcmd: int, indexinstance: int):
        if indexclass < len(self.profile_setup["callOrder"]) and indexcmd < len(
            self.profile_setup["callOrder"][indexclass]["key"]
        ):
            classname = self.profile_setup["callOrder"][self._current_class][
                "classname"
            ]
            cmd = self.profile_setup["callOrder"][self._current_class]["key"][
                self._current_command
            ]
            instance = self._get_instance_running(indexclass, indexinstance)
            self.get_value_async(classname, cmd, self._read_profile_cb, instance)

    def _save_profile_in_file(self, profile_data: str, profilename: str):
        # search the profile in the json profiles and replace is content
        profile_json_entry = next(
            filter(lambda x: x["name"] == profilename, self.profiles["profiles"]), None
        )

        # if profile is not exist, we copy a new one from "None" profile and
        # return the profile_json_entry which reference the new profile entry
        if profile_json_entry is None:
            profile_json_entry = next(
                filter(
                    lambda x: x["name"] == 'None',
                    self.profiles["profiles"],
                ),
                None,
            )
            new_profile = copy.deepcopy(profile_json_entry)
            if new_profile is not None:
                new_profile["name"] = profilename
                self.profiles["profiles"].append(new_profile)

            profile_json_entry =  new_profile

        if profile_json_entry is not None:
            profile_json_entry["data"] = profile_data
        else:
            self.log(F"Profile: can't save profile '{profilename}', it doesn't exist")

        # store new config in file
        self.create_or_update_profile_file()
        self.log("Profile: '" + profilename + "' is successfully updated")
        self.select_profile(profilename)

    ####################### Call Back for Async Serial Communication #######################

    def _read_profile_cb(self, buffer: str):
        # process the incoming buffer
        if self._current_class == -1:
            # first call is sys.lsactive to get all active class
            # that running and we extract a map of class/instances
            self._build_running_map(buffer)
        else:
            # each time we received a value, we store the value
            # and awe asked the next one in the config file,
            # for each instance read in the firt call
            fullname = self.profile_setup["callOrder"][self._current_class]["fullname"]
            classname = self.profile_setup["callOrder"][self._current_class][
                "classname"
            ]
            cmd = self.profile_setup["callOrder"][self._current_class]["key"][
                self._current_command
            ]
            instance = self._get_instance_running(
                self._current_class, self._current_instance
            )
            self._running_profile.append(
                {
                    "fullname": fullname,
                    "cls": classname,
                    "instance": instance,
                    "cmd": cmd,
                    "value": buffer,
                }
            )

        # if there is another command for this class, go to next command
        if self._get_next_element_to_request():
            self._read_value(
                self._current_class, self._current_command, self._current_instance
            )
        elif self._profilename_tosave is not False:
            self._save_profile_in_file(self._running_profile, self._profilename_tosave)
        else:
            self.log("Profiles: profile read from board")

    def _write_profile_cb(self, buffer: str):
        # process the incoming buffer
        if self._current_class == -1:
            # first call is sys.lsactive to get all active class
            # that running and we extract a map of class/instances
            self._build_running_map(buffer)
        else:
            return

        # read the selected profile name
        profilename = str(self.comboBox_profiles.currentText())
        if profilename == "":
            return

        # From the profile, filter parameters that are running
        parameters_running = []
        profile_json_entry = next(
            filter(lambda x: x["name"] == profilename, self.profiles["profiles"]), None
        )
        for running_class in self._map_class_running:
            parameters_running.extend(
                list(
                    filter(
                        lambda x, running=running_class: x["fullname"]
                        == running["fullname"]
                        and x["cls"] == running["classname"]
                        and x["instance"] == running["instance"],
                        profile_json_entry["data"],
                    )
                )
            )

        # sent the filter running parameter to the board
        # and after, read a new time values to refresh UI
        if len(parameters_running) > 0:
            for pararmeter in parameters_running:
                self.send_value(
                    cls=pararmeter["cls"],
                    cmd=pararmeter["cmd"],
                    val=pararmeter["value"],
                    instance=pararmeter["instance"],
                )

                # axis.0.degrees?|900
                replytext = (
                    "["
                    + pararmeter["cls"]
                    + "."
                    + str(pararmeter["instance"])
                    + "."
                    + pararmeter["cmd"]
                    + "?|"
                    + str(pararmeter["value"])
                    + "]"
                )
                self.process_virtual_comms_buffer(replytext)

            # self.sendCommand(cls=pararmeter["cls"],
            # cmd=pararmeter["cmd"], instance=pararmeter["instance"])

        # send message that announce new profile is selected
        self.profile_selected_event.emit(profilename)
        self.log("Profile: '" + profilename + "' is active")


class ProfilesDialog(PyQt6.QtWidgets.QDialog):
    """This class manage the dialog box which contain the list profile manager."""

    closeSignal = PyQt6.QtCore.pyqtSignal(str)

    def __init__(self, profile_ui=None):
        """Create and attach the DLG to the profile_ui and store locally the profiles list."""
        PyQt6.QtWidgets.QDialog.__init__(self, profile_ui)
        self.profiles = None
        self.profile_manager_ui = ProfilesManagerUI(self)
        self.layout = PyQt6.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.profile_manager_ui)
        self.setLayout(self.layout)
        self.setWindowTitle(self.tr("Profiles manager"))
        self.setModal(True)

    def set_profiles(self, profiles):
        """Update the profiles stored in the DLG."""
        self.profiles = profiles

    def closeEvent(self, a0: PyQt6.QtGui.QCloseEvent) -> None:  # pylint: disable=invalid-name
        """Emit the close signal before to close, this help parent to resfresh combobox."""

        # get the current selection item to push it to the main UI on closing action
        name = None

        if self.profile_manager_ui.selection_model.selection() and \
            len(self.profile_manager_ui.selection_model.selection().indexes()) != 0:
            name = self.profile_manager_ui.selection_model.selection().indexes()[0].data()

        self.closeSignal.emit(name)
        return super().closeEvent(a0)


class ProfilesManagerUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """Init the UI in the dialog box to manage profile from a list box."""

    def __init__(self, parent: ProfilesDialog = None):
        """Attach the UI to the dialog box and keep a reference to get profiles."""
        base_ui.WidgetUI.__init__(self, parent, "profile_list.ui")
        base_ui.CommunicationHandler.__init__(self)
        self.profile_dlg = parent
        self.model = PyQt6.QtGui.QStandardItemModel(self.listView)
        self.listView.setModel(self.model)
        self.selection_model = self.listView.selectionModel()
        self.selection_model.selectionChanged.connect(self.onClicked)

        self.pushButton_refresh.clicked.connect(self.read_profiles)
        self.pushButton_close.clicked.connect(self.profile_dlg.close)
        self.pushButton_delete.clicked.connect(self.delete)
        self.pushButton_copyas.clicked.connect(self.copy_as)
        self.pushButton_rename.clicked.connect(self.rename)

    def showEvent(self, a0):  # pylint: disable=invalid-name, unused-argument
        """Init the profile list on the show event."""
        self.read_profiles()

    def onClicked(self, index):  # pylint: disable=invalid-name, unused-argument
        """Activate all button if it's not the "None" or "Flash profile" one."""
        if len(self.selection_model.selection().indexes()) <= 0:
            self.pushButton_delete.setEnabled(False)
            self.pushButton_rename.setEnabled(False)
            self.pushButton_copyas.setEnabled(False)
            return

        item = self.selection_model.selection().indexes()[0]
        if item.data() == ProfileUI.NONE_PROFILE_NAME:
            self.pushButton_delete.setEnabled(False)
            self.pushButton_rename.setEnabled(False)
            self.pushButton_copyas.setEnabled(False)
        elif item.data() == ProfileUI.FLASH_PROFILE_NAME:
            self.pushButton_delete.setEnabled(False)
            self.pushButton_rename.setEnabled(False)
            self.pushButton_copyas.setEnabled(True)
        else:
            self.pushButton_delete.setEnabled(True)
            self.pushButton_rename.setEnabled(True)
            self.pushButton_copyas.setEnabled(True)

    def delete(self):
        """Remove the selected item when click on remove, and refresh profiles list."""
        if len(self.selection_model.selection().indexes()) <= 0:
            return
        item_name = self.selection_model.selection().indexes()[0].data()
        for i in range(len(self.profile_dlg.profiles["profiles"])):
            if self.profile_dlg.profiles["profiles"][i]["name"] == item_name:
                self.profile_dlg.profiles["profiles"].pop(i)
                break
        self.read_profiles()

    def copy_as(self):
        """Prompt the new name, copy the selected item and refresh profiles list."""
        if len(self.selection_model.selection().indexes()) <= 0:
            return
        item_name = self.selection_model.selection().indexes()[0].data()
        name, status = PyQt6.QtWidgets.QInputDialog.getText(self, "Copy as", "new name")
        if status and (name != "") and (name not in self.get_profiles_name()):
            profile_json_entry = next(
                filter(
                    lambda x: x["name"] == item_name,
                    self.profile_dlg.profiles["profiles"],
                ),
                None,
            )
            new_profile = copy.deepcopy(profile_json_entry)
            if profile_json_entry is not None:
                new_profile["name"] = name
                self.profile_dlg.profiles["profiles"].append(new_profile)
        self.read_profiles()

    def rename(self):
        """Prompt the new name, rename the selected item and refresh profiles list."""
        if len(self.selection_model.selection().indexes()) <= 0:
            return
        item_name = self.selection_model.selection().indexes()[0].data()
        name, status = PyQt6.QtWidgets.QInputDialog.getText(
            self, "Copy as", "new name", text=item_name
        )
        if status and (name != "") and (name not in self.get_profiles_name()):
            profile_json_entry = next(
                filter(
                    lambda x: x["name"] == item_name,
                    self.profile_dlg.profiles["profiles"],
                ),
                None,
            )
            if profile_json_entry is not None:
                profile_json_entry["name"] = name
        self.read_profiles()

    def read_profiles(self):
        """Update the list box with element read in the profiles list store in the dialog box."""
        self.model.clear()

        for profile in self.get_profiles_name():
            item = PyQt6.QtGui.QStandardItem(profile)
            item.setEditable(False)
            self.model.appendRow(item)

        item = self.model.item(0, 0)
        index = self.model.indexFromItem(item)
        self.selection_model.select(
            index, PyQt6.QtCore.QItemSelectionModel.SelectionFlag.Select
        )

    def get_profiles_name(self):
        """Create the list of profiles name from the profiles list store in the dialog box."""
        list_name = []
        data = self.profile_dlg.profiles['profiles']
        nb_profile = len(data)
        # return the list of name profile without the None one if there is more than one profile.
        for profile in data:
            list_name.append(profile["name"])

        if nb_profile > 1:
            list_name.remove(ProfileUI.NONE_PROFILE_NAME)

        return list_name
