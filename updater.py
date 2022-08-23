
""" Update notification and release parsers

Module : updater
Authors : yannick
"""
import PyQt6.QtGui
import PyQt6.QtCore
import PyQt6.QtWidgets
from PyQt6.QtWidgets import QListWidgetItem,QGroupBox,QHBoxLayout,QVBoxLayout,QLabel,QDialog,QTextBrowser,QPushButton
import base_ui
import pydfu
import requests
import json
import re
import helper
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
from datetime import datetime
from optionsdialog import OptionsDialogGroupBox

MAINREPO = "Ultrawipf/OpenFFBoard"
GUIREPO = "Ultrawipf/OpenFFBoard-Configurator"

class GithubRelease():

    @staticmethod
    def get_releases(repo : str, prerelease : bool = False, draft : bool = False):
        """Returns a list of releases or connection error or empty list if there was a connection error
        api: https://api.github.com/repos/Ultrawipf/OpenFFBoard/releases
        """
        url = f"https://api.github.com/repos/{repo}/releases"
        try:
            response = requests.get(url)
        except requests.ConnectionError:
            return []
        if not response:
            return []

        releases = json.loads(response.content)

        # Filter out prereleases and drafts if not allowed
        releases = filter(lambda r : (not bool(r["prerelease"]) or prerelease) and (not bool(r["draft"]) or draft), releases)

        return list(releases)

    @staticmethod
    def get_latest_release(repo : str):
        """Returns the latest release for repo or empty dict on error"""
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            response = requests.get(url)
        except requests.ConnectionError:
            return {}
        if not response:
            return {}

        release = json.loads(response.content)
        return(release)

    @staticmethod
    def get_time(release : dict):
        """Returns a datetime object of the creation time"""
        return datetime.strptime(release['created_at'],'%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def get_version(release : dict):
        """Returns None if invalid tag, otherwise (version,postfix) like ("1.2.3","dev")"""

        vermatch = re.match(r"v(\d+\.\d+\.\d+)(?:-?(.+))?",release.get("tag_name",""))
        if not vermatch or not release:
            return None,None
        version = vermatch.group(1)
        postfix = vermatch.group(2)

        return version,postfix
    @staticmethod
    def get_description(release : dict):
        """Returns the description text of a release"""
        return release.get("body",None)
    @staticmethod
    def get_title(release : dict):
        """Returns the title of the release"""
        return release.get("name",release.get("tag_name",""))

class UpdateChecker():

    @staticmethod
    def compare_versions(curver,comparever):
        """Returns False if current version newer or identical, True if comparever is newer"""
        if not curver or not comparever:
            return False
        comparever_i = [int(i) for i in comparever.split(".")]
        curver_i = [int(i) for i in curver.split(".")]
        outdated = (
            comparever_i[0] > curver_i[0] \
            or comparever_i[1] > curver_i[1] and comparever_i[0] == curver_i[0]  \
            or comparever_i[2] > curver_i[2] and comparever_i[1] ==  curver_i[1] and  comparever_i[0] == curver_i[0]
        )
        # return comparever_i[0] > curver_i[0] or comparever_i[1] > curver_i[1] or comparever_i[2] > curver_i[2] 
        return outdated


    @staticmethod
    def check_update(repo : str, version : str):
        """Returns (bool new version available, release object)"""
        release = GithubRelease.get_latest_release(repo)
        if not release:
            return False, {}
        releasever,_ = GithubRelease.get_version(release)
        
        return UpdateChecker.compare_versions(version,releasever), release

    
class UpdateBrowser(PyQt6.QtWidgets.QDialog):
    """Gets updates and displays them in a list"""
    def __init__(self,parentWidget):
        PyQt6.QtWidgets.QDialog.__init__(self, parentWidget)
        PyQt6.uic.loadUi(helper.res_path("updatebrowser.ui"), self)

        self.listWidget_release.currentItemChanged.connect(self.release_changed)
        self.listWidget_files.currentItemChanged.connect(self.file_changed)
        self.buttonGroup_repo.buttonClicked.connect(self.repo_changed)
        self.read_releases(MAINREPO)

    def fill_releases(self,releases : dict):
        self.listWidget_release.clear()
        for r in releases:
            if r.get("name",None):
                name = f"{r.get('tag_name','No tag')} ({r.get('name')})"
            else:
                name = f"{r.get('tag_name','No tag')}"
            item = QListWidgetItem(name)
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
            self.read_releases(GUIREPO)
        else:
            self.read_releases(MAINREPO)

    def read_releases(self,repo : str):
        releases = GithubRelease.get_releases(repo,True)
        if releases:
            self.fill_releases(releases)
            

    def fill_files(self,release : dict):
        self.listWidget_files.clear()
        for r in release.get("assets",[]):
            name = r['name']
            url = r['browser_download_url']
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, url)
            self.listWidget_files.addItem(item)
        self.listWidget_files.setCurrentRow(0)


    def release_changed(self,current : QListWidgetItem,old : QListWidgetItem):
        if not current:
            return
        release = current.data(Qt.ItemDataRole.UserRole)
        self.textBrowser_releasenotes.setMarkdown(GithubRelease.get_description(release))
        self.label_releaseUrl.setText(f"<a href=\"{release['html_url']}\">{release['html_url']}</a>")
        self.fill_files(release)
        publishtime = GithubRelease.get_time(release)
        infotext = f"Date: {publishtime}"
        self.label_releaseInfo.setText(infotext)

    def file_changed(self,current : QListWidgetItem,old : QListWidgetItem):
        if not current:
            return
        url = current.data(Qt.ItemDataRole.UserRole)
        self.label_fileUrl.setText(f"<a href=\"{url}\">Download</a>")



class UpdateNotification(QDialog):
    """Shows a dialog with release information"""
    def __init__(self,release,main,desc,curver):
        self.main = main
        QDialog.__init__(self, main)
        self.setWindowTitle("Update available")
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        self.infolabel = QLabel(desc)
        self.infolabel.setOpenExternalLinks(True)
        self.infolabel.setTextFormat(Qt.TextFormat.RichText)
        self.vbox.addWidget(self.infolabel)
        if not release:
            self.vbox.addWidget(QLabel("Error displaying release"))
            return
        self.releaseversion = release["tag_name"]
        url = release['html_url']
        self.versionlabel = QLabel(f"New version: <a href=\"{url}\"> {self.releaseversion}</a>, Current version: {curver}")
        self.versionlabel.setOpenExternalLinks(True)
        self.versionlabel.setTextFormat(Qt.TextFormat.RichText)
        self.vbox.addWidget(self.versionlabel)

        self.titlelabel = QLabel(f"<a href=\"{url}\"> {GithubRelease.get_title(release)}</a>")
        self.titlelabel.setOpenExternalLinks(True)
        self.vbox.addWidget(self.titlelabel)

        self.updatebrowserbutton = QPushButton("Open update browser",self)
        self.updatebrowserbutton.clicked.connect(self.open_updater)
        
        self.releasenotes = QTextBrowser(self)
        self.releasenotes.setMarkdown(GithubRelease.get_description(release))
        self.vbox.addWidget(self.releasenotes)
        self.vbox.addWidget(self.updatebrowserbutton)

        

    def open_updater(self):
        """Opens the updatebrowser"""
        self.close()
        UpdateBrowser(self).exec()
