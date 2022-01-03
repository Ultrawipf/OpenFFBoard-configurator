import json
from PyQt6.QtWidgets  import QFileDialog,QMessageBox

def saveDump(buf):
    dump = {"flash":[]} 
    for l in buf.split("\n"):
        if not l:
            break
        val,addr = l.split(":")
        dump["flash"].append({"addr":addr,"val":val})
    fname,_ = QFileDialog.getSaveFileName( directory = 'dump.json' ,filter  = "Json files (*.json)")
    try:
        with open(fname,"w") as f:
            json.dump(dump,f)
        msg = QMessageBox(QMessageBox.Icon.Information,"Save flash dump","Saved successfully.")
        msg.exec()
    except Exception as e:
        msg = QMessageBox(QMessageBox.Icon.Warning,"Save flash dump","Error while saving flash dump:\n"+str(e))
        msg.exec()


def loadDump():
    fname,_ = QFileDialog.getOpenFileName(directory = 'dump.json' ,filter  = "Json files (*.json)")
    if fname:
        dump = {}
        with open(fname,"r") as f:
            dump = json.load(f)
        return dump
    else:
        return None