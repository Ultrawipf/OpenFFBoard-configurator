import os
import json

import PyQt6.QtCore

import profile_manager
import base_ui

class SystemUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    profilesUpdated = PyQt6.QtCore.pyqtSignal(list)
    profileSelected = PyQt6.QtCore.pyqtSignal(str)
    
    profile_setup = {}
    profiles = {}

    _current_class = -1
    _current_command = -1
    _current_instance = -1
    _map_class_running = []
    _running_profile = []
    _profilename_tosave : str = None

    __RELEASE = 1
    __PROFILES_FILENAME = 'profiles.json'
    __PROFILESSETUP_FILENAME = 'profile.cfg'
    __PROFILES_TEMPLATE = {'release':__RELEASE, 'profiles': [ {"name":"Default", "data":{}} ] }

    def __init__(self, main=None):
        base_ui.WidgetUI.__init__(self, main,'baseclass.ui')
        base_ui.CommunicationHandler.__init__(self)
        self.profilesDialog = profile_manager.ProfilesDialog(self)
        self.profilesDialog.closeSignal.connect(self.closeProfileManager)

        self.pushButton_save.clicked.connect(self.saveClicked)
        self.toolButton_save.clicked.connect(self.saveCurrentSettingsInProfile)
        self.comboBox_profiles.currentIndexChanged.connect(self.changeSelectedProfile)
        self.toolButton_manage.clicked.connect(self.openProfileManager)

        self.profilesUpdated.connect(self.main.systray.refreshProfiles)
        self.profileSelected.connect(self.main.systray.selectProfiles)
        
        self.setEnabled(False)
        self.initSetup()
        self.initProfiles()

    # Save current seeting in Flash and replace the default settings by the new one
    def saveClicked(self):
        def logSave_Cb(res):
            self.main.log("Save in flash: "+ str(res))

        self.getValueAsync("sys","save",callback=logSave_Cb)
        self.saveCurrentSettingsInProfile("Default")
    
    def log(self,s):
        self.logBox_1.append(s)
        
    def setSaveBtn(self,on):
        self.pushButton_save.setEnabled(on)

    def openProfileManager(self):
        self.profilesDialog.setProfiles(self.profiles)
        self.profilesDialog.show()

    def closeProfileManager(self):
        self.createOrUpdateProfileFile()
        self.refreshComboxList()

    def initSetup(self):
        check = os.path.exists(self.__PROFILESSETUP_FILENAME)
        if check:
            with open(self.__PROFILESSETUP_FILENAME, "r") as f:
                self.profile_setup = json.load(f)
    
    def initProfiles(self):
        check = os.path.exists(self.__PROFILES_FILENAME)
        if check:
            self.loadFileProfiles()
        else:
            self.createOrUpdateProfileFile(create=True)

    def refreshComboxList(self):
        self.comboBox_profiles.clear()
        #for profilename in self.profiles["profiles"]:
            #self.comboBox_profiles.addItem(profilename["name"])
        listprofile = []
        for profilename in self.profiles["profiles"]:
            listprofile.append(profilename["name"])

        self.profilesUpdated.emit(listprofile)
        self.comboBox_profiles.addItems(listprofile)

    def loadFileProfiles(self):
        with open(self.__PROFILES_FILENAME,"r") as profileFile:
            self.profiles = json.load(profileFile)
        self.log("Profile: profiles loaded")
        self.refreshComboxList()

    def createOrUpdateProfileFile(self, create: bool=False):
        if (create):
            self.profiles = self.__PROFILES_TEMPLATE
            self.log("Profile: init default profile")
        
        try:
            f = open(self.__PROFILES_FILENAME,"w") 
        except OSError:
            return False
            
        with f as profileFile:
            json.dump(self.profiles, profileFile)

        self.log("Profile: profiles saved")

        return True

    def selectProfile(self, profilename:str):
        if profilename == '':
            return
        if profilename != str(self.comboBox_profiles.currentText()):
            index = self.comboBox_profiles.findText(profilename, PyQt6.QtCore.Qt.MatchFlag.MatchFixedString)
            if index >= 0:
                self.comboBox_profiles.setCurrentIndex(index)

    def changeSelectedProfile(self):
        # read the selected profile name
        profilename = str(self.comboBox_profiles.currentText())
        if profilename == '':
            return

        # read the setting and push all settings to 
        profile_json_entry = next(filter(lambda x:x["name"]==profilename,self.profiles["profiles"]), None)
        if profile_json_entry is not None:
            for data in profile_json_entry["data"]:
                self.sendValue(cls=data["cls"], cmd=data["cmd"], val=data["value"], instance=data["instance"])
 
            for data in profile_json_entry["data"]:
                self.sendCommand(cls=data["cls"], cmd=data["cmd"], instance=data["instance"])

        # send message that announce new profile is selected
        self.profileSelected.emit(profilename)
        self.log("Profile: '" + profilename + "' is active")

    def saveCurrentSettingsInProfile(self, profile_name:str = ''):
        if (profile_name is False):
            self._profilename_tosave = str(self.comboBox_profiles.currentText())
            # if we save the profile "default" we start to save it in FlashFirst
            if self._profilename_tosave == "Default":
                self.saveClicked()
        else:
            self._profilename_tosave = profile_name

        # refresh the global var when starting to read value from board
        self._current_class = -1
        self._current_command = -1
        self._current_instance = -1
        self._map_class_running = []
        self._running_profile = []
        # to start process get the list active class from board, after that the the callBack call recursively
        self.getValueAsync("sys", "lsactive", self._readProfileCallBack)

    def _buildRunningMap(self, buffer:str):
        all_class_running = []
        splitted_running_class = [x.split(":") for x in buffer.split("\n")]
        for running_class in splitted_running_class:
            fullname = running_class[0]
            classname = running_class[1]
            instance = running_class[2]
            # search if this class is already register, if not we add the class and instance number
            # else add the instance number 
            config_class = next(filter(lambda x:x["classname"]==classname, all_class_running), None)
            if (config_class is None) :
                all_class_running.append({"classname":classname, "fullname":fullname ,"instance":[instance]})
            else:
                config_class["instance"].append(instance)

        # filter on active class the classes in the setup file to export
        self._map_class_running = []
        for classes in all_class_running:
            # search in setup list for this classes if not present or for another Class, remove it
            profileJSonEntry = next(filter(lambda x:x["classname"]==classes["classname"],self.profile_setup["callOrder"]), None)
            if (profileJSonEntry is not None) and profileJSonEntry["fullname"]==classes["fullname"]:
                self._map_class_running.append(classes)


    def _getInstanceRunning(self, indexclass:int, indexinstance:int):
        if indexclass > len(self.profile_setup['callOrder']) :
            return None
        
        classname = self.profile_setup['callOrder'][indexclass]['classname']
        fullname = self.profile_setup['callOrder'][indexclass]['fullname']
        class_running = \
            next(filter(lambda x:
                            x["classname"]==classname and x["fullname"]==fullname,
                            self._map_class_running), None)
        if (class_running is None):                                # the request instance is not on a running classes
            return None 
        elif (indexinstance >= len(class_running["instance"])):    # the next instance not exist
            return None
        else:                                                              # else return the instance number
            return int(class_running["instance"][indexinstance])

    def _getNextElementToRequest(self):
        is_another_element = False

        # if it's the start 
        if self._current_class == -1 and self._current_command == -1 and self._current_instance == -1:
            self._current_class = 0
            self._current_command = 0
            self._current_instance = 0
            is_another_element = True
        # if there is another command for this class, go to next command
        elif (self._current_command + 1) < len(self.profile_setup['callOrder'][self._current_class]['key']):
            self._current_command += 1
            is_another_element = True
        else:
            # if there is not next command, we check if there is another instance of this class to request
            nextInstance = self._getInstanceRunning(self._current_class, self._current_instance + 1)
            if (nextInstance is not None):  # a next instance exist, we move index to this and restart on 1st dmd
                self._current_instance +=1
                self._current_command = 0
                is_another_element = True
            elif (self._current_class + 1) < len(self.profile_setup['callOrder']): # there isn't next instance, we move too next class if exist
                self._current_class += 1
                self._current_command = 0
                self._current_instance = 0
                is_another_element = True
            else:
                is_another_element = False
        
        # if the next computed class/instance is not running, we go to the next
        if is_another_element and self._getInstanceRunning(self._current_class, self._current_instance) is None:
            return self._getNextElementToRequest()

        return is_another_element

    def _readValue(self, indexclass:int, indexcmd:int, indexinstance:int):
        if indexclass < len(self.profile_setup['callOrder']) and indexcmd < len(self.profile_setup['callOrder'][indexclass]['key']) :
            classname = self.profile_setup['callOrder'][self._current_class]['classname']
            cmd = self.profile_setup['callOrder'][self._current_class]['key'][self._current_command]
            instance = self._getInstanceRunning(indexclass, indexinstance)
            self.getValueAsync(classname, cmd, self._readProfileCallBack, instance)

    def _readProfileCallBack(self, buffer:str):
        # process the incoming buffer
        if (self._current_class == -1):
            # first call is sys.lsactive to get all active class that running and we extract a map of class/instances
            self._buildRunningMap(buffer)
        else :
            # each time we received a value, we store the value and awe asked the next one in the config file, 
            # for each instance read in the firt call
            fullname = self.profile_setup['callOrder'][self._current_class]['fullname']
            classname = self.profile_setup['callOrder'][self._current_class]['classname']
            cmd = self.profile_setup['callOrder'][self._current_class]['key'][self._current_command]
            instance = self._getInstanceRunning(self._current_class, self._current_instance)
            self._running_profile.append({"fullname":fullname ,"cls":classname, "instance":instance, "cmd":cmd, "value":buffer})

        # if there is another command for this class, go to next command
        if self._getNextElementToRequest():
            self._readValue(self._current_class, self._current_command, self._current_instance)
        elif self._profilename_tosave is not False:
            self._saveProfileInFile(self._running_profile, self._profilename_tosave)

    def _saveProfileInFile(self, profile_data:str, profilename:str):
        # search the profile in the json profiles and replace is content
        profileJSonEntry = next(filter(lambda x:x["name"]==profilename,self.profiles["profiles"]), None)
        if profileJSonEntry is not None:
            profileJSonEntry["data"] = profile_data

        #store new config in file
        self.createOrUpdateProfileFile()
        self.log("Profile: '" + profilename + "' is successfully updated")
        self.selectProfile(profilename)