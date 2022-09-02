from os import path
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

# Populates a combobox with entries formatted as "Entrylabel<datasep>data<entrysep>..."
def updateListComboBox(combobox,reply,entrySep=',',dataSep=':',lookup = None):
    combobox.clear()
    if lookup:
        lookup.clear()
    i = 0
    for s in reply.split(entrySep):
        e = s.split(dataSep)
        combobox.addItem(e[0],e[1])
        if lookup:
            lookup[e[1]] = i
        i += 1

def splitListReply(reply,itemdelim = ':', entrydelim = '\n'):
    #for line in reply.split(entrydelim):
    return [ line.split(itemdelim) for line in reply.split(entrydelim) ]


def qtBlockAndCall(object : QObject,function,value):
    object.blockSignals(True)
    function(value)
    object.blockSignals(False)


def throttle(ms):

    throttle.time_of_last_call = time.time()
    throttle.t = QTimer()
    throttle.t.setSingleShot(True)

    def decorator(fn):
        def wrapper(*args, **kwargs):
            def call():
                throttle.time_of_last_call = time.time()
                fn(*args, **kwargs)
            
            now = time.time()
            time_since_last_call = now - throttle.time_of_last_call

            # Call immediately if last call is older than timeout
            if time_since_last_call > ms/1000:
                if throttle.t.isActive():
                    throttle.t.stop()
                return call()

            else: # delay execution
                if throttle.t.isActive():
                    throttle.t.stop()

                # Disconnect previous call
                try: throttle.t.timeout.disconnect()
                except Exception: pass

                # Connect timer
                throttle.t.timeout.connect(call)
                throttle.t.setInterval(ms)
                throttle.t.start()     
        return wrapper
    return decorator

# Splits a reply in the format "name:value,name2:value2"... into a dict
def map_infostring(repl,type=float):
    return{key:type(value) for (key,value) in [entry.split(":") for entry in repl.split(",")]}