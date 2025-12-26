
""" Update notification and release parsers

Module : updater
Authors : yannick
"""

import requests
import json
import re
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QVBoxLayout, QLabel, QDialog, QTextBrowser
from datetime import datetime

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
            response = requests.get(url,timeout=3) # timeout to avoid blocking when board connecting
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

 
class UpdateNotification(QDialog):
    """Shows a dialog with release information"""
    def __init__(self,release,main,desc,curver,donotnotifysetting = None):
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
             
        self.releasenotes = QTextBrowser(self)
        self.releasenotes.setMarkdown(GithubRelease.get_description(release))
        self.vbox.addWidget(self.releasenotes)
        self.vbox.addWidget(self.updatebrowserbutton)

        if donotnotifysetting:
            self.donotnotify = QCheckBox("Notify about releases at startup",self)
            self.donotnotify.setChecked(not self.main.profile_ui.get_global_setting(donotnotifysetting,False))
            self.vbox.addWidget(self.donotnotify)

            def donotnotify_save(status):
                self.main.profile_ui.set_global_setting(donotnotifysetting,not status)

            self.donotnotify.toggled.connect(donotnotify_save)
