from base_ui import WidgetUI
from PyQt6.QtWidgets import QDialog, QTableWidgetItem, QHeaderView
from PyQt6.QtWidgets import (
    QMessageBox,
    QVBoxLayout,
    QCheckBox,
    QButtonGroup,
    QPushButton,
    QLabel,
    QSpinBox,
    QComboBox,
)
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex
from base_ui import CommunicationHandler


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


class ErrorsDialog(QDialog):
    def __init__(self, main=None):
        QDialog.__init__(self, main)
        self.main = main
        self.ui = ErrorsUI(main, self)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Errors")

    def registerCallbacks(self):
        self.ui.registerCallbacks()

    def connected_cb(self,connected):
        if connected:
            self.ui.clear_stored_errors()

class ErrorsUI(WidgetUI, CommunicationHandler):
    def __init__(self, main=None, parent=None):
        WidgetUI.__init__(self, parent, "errors.ui")
        CommunicationHandler.__init__(self)
        self.main = main
        self.parent = parent
        self.pushButton_refresh.clicked.connect(self.readErrors)
        self.pushButton_clearErrors.clicked.connect(self.clear_errors)
        self.pushButton_clearLogs.clicked.connect(self.clear_logs)
        self.errors = ErrorsModel(self.tableView)
        self.tableView.setModel(self.errors)
        header = self.tableView.horizontalHeader()
        header.setStretchLastSection(True)
        self.registerCallbacks()
        self.logger.register_to_logger(self.append_log)

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
        # self.readErrors()

    def readErrors(self):
        if self.isEnabled:
            self.send_command("sys", "errors", 0)

    def errorCallback(self, errorstring):
        if errorstring != "None":
            self.parent.show()
        errors = []
        for errorline in errorstring.split("\n"):
            e = errorline.split(":", 2)
            if len(e) < 3:
                continue
            error = {"code": e[0], "level": e[1], "info": e[2]}
            errors.append(error)
        self.errors.setErrors(errors)
        self.tableView.resizeColumnsToContents()
