from os import path
import sys

from PyQt5.QtCore import QObject

respath = "res"
def res_path(file):
    if getattr(sys, 'frozen',False) and hasattr(sys, '_MEIPASS'):
        return path.join(sys._MEIPASS,respath,file)
    return path.join(respath,file)

# Parses a classchooser reply into a list of classes and a dict to translate the class ID to (list index,name)
def classlistToIds(dat):
    classes = []
    idToIdx = {}
    if(dat):
        n=0
        for c in dat.split("\n"):
            if(c):
                id,creatable,name = c.split(":",2)
                idToIdx[int(id)] = (n,name)
                classes.append([int(id),name,bool(creatable != "0")])
                n+=1
    return (idToIdx,classes)

# Populates a combobox with entries from a parsed classchooser reply
def updateClassComboBox(combobox,ids,classes,selected = None):
    combobox.clear()
    if(selected != None):
        selected = int(selected)
    for c in classes:
        creatable = c[2] or (selected == int(c[0]))
        combobox.addItem(c[1])
        combobox.model().item(ids[c[0]][0]).setEnabled(creatable)
    
    if(selected in ids and combobox.currentIndex() != ids[selected][0]):
        combobox.setCurrentIndex(ids[selected][0])

def splitListReply(reply,itemdelim = ':', entrydelim = '\n'):
    #for line in reply.split(entrydelim):
    return [ line.split(itemdelim) for line in reply.split(entrydelim) ]


def qtBlockAndCall(object : QObject,function,value):
    object.blockSignals(True)
    function(value)
    object.blockSignals(False)