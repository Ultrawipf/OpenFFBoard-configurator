from base_ui import WidgetUI
from PyQt5.QtWidgets import QDialog,QTableWidgetItem ,QHeaderView
from PyQt5.QtWidgets import QMessageBox,QVBoxLayout,QCheckBox,QButtonGroup,QPushButton,QLabel,QSpinBox,QComboBox
from PyQt5.QtCore import QAbstractTableModel,Qt,QModelIndex


class ActiveClassModel(QAbstractTableModel):
    def __init__(self,parent):
        super(ActiveClassModel, self).__init__()
        self.parent = parent
        self.items = []
        self.header = ["Name", "CMD addr","Instance","Classchooser ID"]
 
    def data(self, index, role):
        if role == Qt.DisplayRole:
            idx = index.row()

            d = self.items[idx]
                
            if(index.column() == 0):
                return d["name"]
            elif(index.column() == 1):
                return d["cmdaddr"]
            elif(index.column() == 2):
                return d["unique"]
            elif(index.column() == 3):
                return d["id"]
   
            else:
                return None

    def headerData(self,section,orientation,role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.header[section]


    def getHeader(self):
        return self.header

    def rowCount(self, index):
        return len(self.items)

    def columnCount(self, index):
        return len(self.header)

    def clearItems(self):
        self.beginResetModel()
        self.items.clear()
        self.endResetModel()

    def count(self):
        return len(self.items)
    
    def addItem(self,item):
        cnt = len(self.items)
        self.beginInsertRows(QModelIndex(),cnt,cnt)
        self.items.append(item)
        self.endInsertRows()

    def setItems(self,items):
        self.beginResetModel()
        self.items = items
        self.endResetModel()

class ActiveClassDialog(QDialog):
    def __init__(self,main=None):
        QDialog.__init__(self, main)
        self.main = main
        self.ui = ActiveClassUI(main,self)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Active features")

class ActiveClassUI(WidgetUI):
    
    def __init__(self, main=None,parent = None):
        WidgetUI.__init__(self, parent,'activelist.ui')
        self.main = main
        self.parent = parent
        #main.comms.serialRegisterCallback("lsactive",self.updateCb)
        self.pushButton_refresh.clicked.connect(self.read)
        self.items = ActiveClassModel(self.tableView)
        self.tableView.setModel(self.items)
        header = self.tableView.horizontalHeader()
        header.setStretchLastSection(True)


    def showEvent(self, a0):
        self.tableView.resizeColumnsToContents()
        self.read()

    def read(self):
        self.main.comms.serialGetAsync("lsactive",self.updateCb)

    def updateCb(self,string):
        self.parent.show()
        items = []
        for line in string.split("\n"):
            e = line.split(":")
            if(len(e) < 4):
                continue
            item = {"name":e[0], "id":e[1], "unique":e[2],"cmdaddr":e[3]}
            items.append(item)
        self.items.setItems(items)
        self.tableView.resizeColumnsToContents()
        

            

    