import json
from PyQt5.QtWidgets  import QFileDialog,QMessageBox

def saveDump(buf):
    dump = {"flash":[]} 
    for l in buf.split("\n"):
        if not l:
            break
        addr,val = l.split(":")
        dump["flash"].append({"addr":addr,"val":val})
    
    dlg = QFileDialog()
    dlg.setFileMode(QFileDialog.AnyFile)
    dlg.setNameFilters(["Json files (*.json)"])
    if dlg.exec_():
        filenames = dlg.selectedFiles()
        try:
            with open(filenames[0],"w") as f:
                json.dump(dump,f)
            msg = QMessageBox(QMessageBox.Information,"Save flash dump","Saved successfully.")
            msg.exec_()
        except Exception as e:
            msg = QMessageBox(QMessageBox.Warning,"Save flash dump","Error while saving flash dump:\n"+str(e))
            msg.exec_()
    else:
        return

def loadDump():
    dlg = QFileDialog()
    dlg.setFileMode(QFileDialog.ExistingFile)
    dlg.setNameFilters(["Json files (*.json)"])
    if dlg.exec_():
        dump = {}
        filenames = dlg.selectedFiles()
        with open(filenames[0],"r") as f:
            dump = json.load(f)
        return dump

    else:
        return None