from PyQt6.QtGui import QHideEvent
from base_ui import WidgetUI,CommunicationHandler
import PyQt6.QtWidgets
from PyQt6.QtCore import QAbstractTableModel,Qt,QModelIndex,QTimer
import re


class ActiveTaskModel(QAbstractTableModel):
    def __init__(self):
        super(ActiveTaskModel, self).__init__()
        self.items = []
        self.header = ["Name","CPU %","State","Prio","Stack","Num"]
 
    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            idx = index.row()

            d = self.items[idx]
                
            if(index.column() == 0):
                return d.get("name")
            elif(index.column() == 1):
                return f"{d['cpu']}%" if "cpu" in d else None
            elif(index.column() == 2):
                return d.get("state")
            elif(index.column() == 3):
                return d.get("prio")
            elif(index.column() == 4):
                return  d.get("stack")
            elif(index.column() == 5):
                return  d.get("num")
            else:
                return None

    def headerData(self,section,orientation,role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
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

class ActiveTaskDialog(PyQt6.QtWidgets.QDialog):
    def __init__(self, parent = None):
        PyQt6.QtWidgets.QDialog.__init__(self, parent)
        self.active_class_ui = ActiveTaskUI(parent)
        self.layout = PyQt6.QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.active_class_ui)
        self.setLayout(self.layout)
        self.setWindowTitle("Active threads")

    def set_taskstats_enabled(self,enabled):
        self.active_class_ui.taskstats_enabled = enabled
        
    def set_tasklist_enabled(self,enabled):
        self.active_class_ui.tasklist_enabled = enabled

class ActiveTaskUI(WidgetUI, CommunicationHandler):
    def __init__(self, parent = None):
        WidgetUI.__init__(self, parent, 'activelist.ui')
        CommunicationHandler.__init__(self)
        self.parent = parent
        self.pushButton_refresh.clicked.connect(self.read)
        self.items = ActiveTaskModel()
        self.tableView.setModel(self.items)
        header = self.tableView.horizontalHeader()
        header.setSectionResizeMode(0,PyQt6.QtWidgets.QHeaderView.ResizeMode.Stretch) # Stretch first section
        self.tableView.setSortingEnabled(True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read)

        self.items_list = []
        self.items_stats = []

        self.taskstats_enabled = False
        self.tasklist_enabled = False
    

    def showEvent(self, a0):
        self.tableView.resizeColumnsToContents()
        self.read()
        self.timer.start(1000)
        return super().showEvent(a0)

    def hideEvent(self, a0: QHideEvent) -> None:
        self.timer.stop()
        return super().hideEvent(a0)
    
    def read(self):
        self.items_stats.clear()
        self.items_list.clear()
        if self.taskstats_enabled:
            self.get_value_async("sys","taskstats",self.updateStatsCb)
                
        if self.tasklist_enabled:
            self.get_value_async("sys","tasklist",self.updateListCb)
        

    def updateItems(self):
        
        items = {}
        
        if (not self.taskstats_enabled or self.items_stats) and (not self.tasklist_enabled or self.items_list):
            for item in self.items_stats:
                items.setdefault(item["name"], {})
                items[item["name"]].update(item)
            for item in self.items_list:
                items.setdefault(item["name"], {})
                items[item["name"]].update(item)
            self.items.setItems(list(items.values()))
            self.parent.show()


    def updateStatsCb(self,string):
        for line in string.split("\n"):
            e = re.split("\t+",line)
            if(len(e) < 3):
                continue
            item = {"name":e[0].strip(),"cpu":int(e[1])}
            self.items_stats.append(item)
        totalcnt = sum([int(c["cpu"]) for c in self.items_stats])
        for item in self.items_stats:
            item["cpu"] = round(100*item["cpu"] / totalcnt,2)

        self.updateItems()

    def updateListCb(self,string):
        for line in string.split("\n"):
            e = re.split("\t+",line)
            if(len(e) < 5):
                continue
            item = {"name":e[0].strip(),"state":(e[1]),"prio":int(e[2]),"stack":int(e[3]),"num":int(e[4])}
            self.items_list.append(item)

        self.updateItems()
        
