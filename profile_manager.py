from PyQt6 import QtGui
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from base_ui import WidgetUI
from PyQt6.QtWidgets import QApplication, QDialog, QInputDialog,QTableWidgetItem ,QHeaderView
from PyQt6.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt6.QtCore import QAbstractTableModel, QItemSelectionModel,Qt,QModelIndex
from base_ui import CommunicationHandler
import sys
import copy

class ProfilesDialog(QDialog):
    profiles = None
    def __init__(self,main=None):
        QDialog.__init__(self, main)
        self.main = main
        self.ui = ProfilesManagerUI(main,self)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Profiles manager")
        self.setModal(True)

    def setProfiles(self, profiles):
        self.profiles = profiles

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.main.closeProfileManagerEventLike()
        return super().closeEvent(a0)

class ProfilesManagerUI(WidgetUI,CommunicationHandler):
    parent : ProfilesDialog = None

    def __init__(self, main=None,parent:ProfilesDialog = None):
        WidgetUI.__init__(self, parent,'profiles.ui')
        CommunicationHandler.__init__(self)
        self.main = main
        self.parent = parent
        self.model = QStandardItemModel(self.listView)
        self.listView.setModel(self.model)
        self.selModel = self.listView.selectionModel()
        self.selModel.selectionChanged.connect(self.onClicked)

        self.pushButton_refresh.clicked.connect(self.readProfiles)
        self.pushButton_close.clicked.connect(self.parent.close)
        self.pushButton_delete.clicked.connect(self.delete)
        self.pushButton_copyas.clicked.connect(self.copyAs)
        self.pushButton_rename.clicked.connect(self.rename)
        
    def showEvent(self, a0):
        self.readProfiles()
    
    def onClicked(self, index):
        item = self.selModel.selection().indexes()[0]
        if item.data()=="Default":
            self.pushButton_delete.setEnabled(False)
            self.pushButton_rename.setEnabled(False)
        else:
            self.pushButton_delete.setEnabled(True)
            self.pushButton_rename.setEnabled(True)

    def delete(self):
        itemName = self.selModel.selection().indexes()[0].data()
        for i in range(len(self.parent.profiles["profiles"])):
            if self.parent.profiles["profiles"][i]["name"] == itemName:
                self.parent.profiles["profiles"].pop(i)
                break
        self.readProfiles()
    
    def copyAs(self):
        itemName = self.selModel.selection().indexes()[0].data()
        name, ok = QInputDialog.getText(self, "Copy as", "new name")
        if ok and (name != "") and (name not in self.getProfilesName()):
            profileJSonEntry = next(filter(lambda x:x["name"]==itemName,self.parent.profiles["profiles"]), None)
            new_profile = copy.deepcopy(profileJSonEntry)
            if profileJSonEntry is not None:
                new_profile["name"]=name
                self.parent.profiles["profiles"].append(new_profile)
        self.readProfiles()
    
    def rename(self):
        itemName = self.selModel.selection().indexes()[0].data()
        name, ok = QInputDialog.getText(self, "Copy as", "new name", text=itemName)
        if ok and (name != "") and (name not in self.getProfilesName()):
            profileJSonEntry = next(filter(lambda x:x["name"]==itemName,self.parent.profiles["profiles"]), None)
            if profileJSonEntry is not None:
                profileJSonEntry["name"]=name
        self.readProfiles()

    def readProfiles(self):
        self.model.clear()

        for profile in self.getProfilesName():
            item = QStandardItem(profile)
            item.setEditable(False)
            self.model.appendRow(item)

        item = self.model.item(0,0)
        index = self.model.indexFromItem(item)
        self.selModel.select( index, QItemSelectionModel.SelectionFlag.Select )

    def getProfilesName(self):
        list = []
        data = self.parent.profiles
        for profile in data["profiles"]:
            list.append(profile["name"])
        return list

