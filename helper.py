from os import path
from functools import wraps
import sys
import time

from PyQt6.QtCore import QObject,QTimer

RESPATH = "res"

def res_path(file):
    if getattr(sys, 'frozen',False) and hasattr(sys, '_MEIPASS'):
        return path.join(sys._MEIPASS,RESPATH,file)
    return path.join(RESPATH,file)

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

def updateClassComboBox(combobox,ids,classes,selected = None):
    """Populates a combobox with entries from a parsed classchooser reply"""
    combobox.clear()
    if(selected != None):
        selected = int(selected)
    for c in classes:
        creatable = c[2] or (selected == int(c[0]))
        combobox.addItem(c[1])
        combobox.model().item(ids[c[0]][0]).setEnabled(creatable)
    
    if(selected in ids and combobox.currentIndex() != ids[selected][0]):
        combobox.setCurrentIndex(ids[selected][0])

def updateListComboBox(combobox,reply,entrySep=',',dataSep=':',lookup = None,dataconv = None):
    """Populates a combobox with entries formatted as Entrylabel<datasep>data<entrysep>..."""
    combobox.clear()
    if lookup != None:
        lookup.clear()
    i = 0
    for s in reply.split(entrySep):
        e = s.split(dataSep)
        data = e[1]
        if dataconv != None:
            data = dataconv(data)
        combobox.addItem(e[0],data)
        if lookup != None:
            lookup[data] = i
        i += 1

def splitListReply(reply,itemdelim = ':', entrydelim = '\n'):
    #for line in reply.split(entrydelim):
    return [ line.split(itemdelim) for line in reply.split(entrydelim) ]


def qtBlockAndCall(object : QObject,function,value):
    object.blockSignals(True)
    function(value)
    object.blockSignals(False)

def throttle(ms):

    time_of_last_call = time.time()
    timer = QTimer()
    timer.setSingleShot(True)

    def decorator(fn):
        def wrapper(*args, **kwargs):
            def call():
                nonlocal time_of_last_call 
                time_of_last_call = time.time()
                fn(*args, **kwargs)
            
            now = time.time()
            time_since_last_call = now - time_of_last_call

            # Call immediately if last call is older than timeout
            if time_since_last_call > ms/1000:
                if timer.isActive():
                    timer.stop()
                return call()

            else: # delay execution
                if timer.isActive():
                    timer.stop()

                # Disconnect previous call
                try: timer.timeout.disconnect()
                except Exception: pass

                # Connect timer
                timer.timeout.connect(call)
                timer.setInterval(ms)
                timer.start()     
        return wrapper
    return decorator

# Splits a reply in the format "name:value,name2:value2"... into a dict
def map_infostring(repl,type=float):
    return{key:type(value) for (key,value) in [entry.split(":") for entry in repl.split(",")]}