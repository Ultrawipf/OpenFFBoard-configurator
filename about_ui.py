import PyQt6.QtWidgets
import base_ui
import helper

class AboutUI(base_ui.WidgetUI):
    """
    About page widget
    """

    def __init__(self, main_ui, version_str, fw_version_str):
        super().__init__(main_ui, "about_page.ui")

        verstr = "Version: " + version_str
        if fw_version_str:
            verstr += " / Firmware: " + fw_version_str
        self.version.setText(verstr)

        try:
            with open("LICENSE", "r") as f:
                self.textBrowser_license.setText(f.read())
        except FileNotFoundError:
            self.textBrowser_license.setText("LICENSE file not found.")
