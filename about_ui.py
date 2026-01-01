import PyQt6.QtWidgets
from PyQt6 import uic
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex
import base_ui
import helper
import activelist
import activetasks

class ErrorsModel(QAbstractTableModel):
    def __init__(self, parent):
        super(ErrorsModel, self).__init__()
        self.parent = parent
        self.errors = []
        self.header = ["Code", "Level", "Info"]

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            idx = index.row()

            d = self.errors[idx]

            if index.column() == 0:
                return d["code"]
            elif index.column() == 1:
                return d["level"]
            elif index.column() == 2:
                return d["info"]
            else:
                return None

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.header[section]

    def getHeader(self):
        return self.header

    def rowCount(self, index):
        return len(self.errors)

    def columnCount(self, index):
        return len(self.header)

    def clearErrors(self):
        self.beginResetModel()
        self.errors.clear()
        self.endResetModel()

    def errorCount(self):
        return len(self.errors)

    def addError(self, error):
        errcnt = len(self.errors)
        self.beginInsertRows(QModelIndex(), errcnt, errcnt)
        self.errors.append(error)
        self.endInsertRows()

    def setErrors(self, errors):
        self.beginResetModel()
        self.errors = errors
        self.endResetModel()

class AboutUI(base_ui.WidgetUI, base_ui.CommunicationHandler):
    """
    About page widget
    """

    def __init__(self, main_ui, version_str, fw_version_str):
        base_ui.WidgetUI.__init__(self, main_ui, "about_page.ui")
        base_ui.CommunicationHandler.__init__(self)
        self.main = main_ui

        verstr = "Version: " + version_str
        if fw_version_str:
            verstr += " / Firmware: " + fw_version_str
        self.version.setText(verstr)

        try:
            with open("LICENSE", "r") as f:
                self.textBrowser_license.setText(f.read())
        except FileNotFoundError:
            self.textBrowser_license.setText("LICENSE file not found.")
            
        # Setup logging for all apps to get event here
        self.logger.register_to_logger(self.append_log)

    
        # Setup logic for Errors tab
        self.pushButton_refresh.clicked.connect(self.readErrors)
        self.pushButton_clearErrors.clicked.connect(self.clear_errors)
        self.pushButton_clearLogs.clicked.connect(self.clear_logs)
        self.errors = ErrorsModel(self.tableView)
        self.tableView.setModel(self.errors)
        header = self.tableView.horizontalHeader()
        header.setStretchLastSection(True)
                
        # Setup Modules tab
        self.active_class_ui = activelist.ActiveClassUI(self)
        self.active_task_ui = activetasks.ActiveTaskUI(self)

        # Push content in groupBox_features
        layout = self.groupBox_features.layout()
        for i in reversed(range(layout.count())):
            widgetToRemove = layout.itemAt(i).widget()
            layout.removeWidget(widgetToRemove)
            widgetToRemove.setParent(None)
        layout.addWidget(self.active_class_ui)

        # Replace content in groupBox_thread
        layout = self.groupBox_thread.layout()
        for i in reversed(range(layout.count())):
            widgetToRemove = layout.itemAt(i).widget()
            layout.removeWidget(widgetToRemove)
            widgetToRemove.setParent(None)
        layout.addWidget(self.active_task_ui)

    def set_connected(self, connected):
        self.setEnabled(connected)
        if connected:
            self.registerCallbacks()
            # Refresh modules
            self.active_class_ui.read()
            self.active_task_ui.read()
        else:
            # remove the handler on disconnect
            self.remove_callbacks()

    def set_taskstats_enabled(self, enabled):
        self.active_task_ui.taskstats_enabled = enabled

    def set_tasklist_enabled(self, enabled):
        self.active_task_ui.tasklist_enabled = enabled
    
    def append_log(self, message):
        """Display the log message."""
        self.logBox_1.append(message)

    def clear_stored_errors(self):
        """Clears stored errors but does not clear them on the device"""
        self.errors.clearErrors()
        self.readErrors()

    def clear_errors(self):
        """Remove errors in the board by serial command and clear UI."""
        self.send_command("sys", "errorsclr")
        self.readErrors()

    def clear_logs(self):
        """Remove all item in the log box to clear it."""
        self.logBox_1.clear()

    def registerCallbacks(self):
        self.register_callback("sys", "errors", self.errorCallback, 0, typechar="?")

    def showEvent(self, a0):
        self.tableView.resizeColumnsToContents()
        # Vérifier l'état des fonctionnalités taskstats et tasklist
        self.check_taskstats()

    def readErrors(self):
        if self.isEnabled():
            self.send_command("sys", "errors", 0)

    def errorCallback(self, errorstring):
        if errorstring != "None" and not self.main.isVisible():
            self.main.show()
        errors = []
        for errorline in errorstring.split("\n"):
            e = errorline.split(":", 2)
            if len(e) < 3:
                continue
            error = {"code": e[0], "level": e[1], "info": e[2]}
            errors.append(error)
        self.errors.setErrors(errors)
        self.tableView.resizeColumnsToContents()

    def check_taskstats(self):
        """Vérifie l'état des fonctionnalités taskstats et tasklist lorsque l'onglet est affiché."""
        if self.isEnabled():
            # Vérifier taskstats
            self.get_value_async("sys", "cmdinfo", adr=18, conversion=int, callback=lambda x: self.set_taskstats_enabled(x==1))
            # Vérifier tasklist
            self.get_value_async("sys", "cmdinfo", adr=23, conversion=int, callback=lambda x: self.set_tasklist_enabled(x==1))
