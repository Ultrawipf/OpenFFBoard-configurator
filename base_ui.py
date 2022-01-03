from PyQt6.QtWidgets import QWidget
from helper import res_path
from PyQt6 import uic
import main
from serial_comms import SerialComms

class WidgetUI(QWidget):
    
    def __init__(self, main=None, ui_form = ""):
        QWidget.__init__(self, main)
        self.main = main #type: main.MainUi
        if(ui_form):
            uic.loadUi(res_path(ui_form), self)

    def initUi(self):
        return True
        


class CommunicationHandler():
    comms: SerialComms = None
    def __init__(self):
        #self.comms = comms
        #print("Newclass")
        pass

    def __del__(self):
        # remove callbacks
        #print("Delclass")
        self.removeCallbacks()
        
    # deletes all callbacks to this class
    def removeCallbacks(self):
        SerialComms.removeCallbacks(self)

    # Helper function to register a callback that can be deleted automatically later
    # Callbacks normally must prevent sending a value change command in this callback to prevent the same value from being sent back again
    def registerCallback(self,cls,cmd,callback,instance=0,conversion=None,adr=None,delete=False,typechar='?'):
        SerialComms.registerCallback(self,cls=cls,cmd=cmd,callback=callback,instance=instance,conversion=conversion,adr=adr,delete=delete,typechar=typechar)

    def getValueAsync(self,cls,cmd,callback,instance : int=0,conversion=None,adr=None,typechar='?',delete=True):
        self.comms.getValueAsync(self,cls=cls,cmd=cmd,callback=callback,instance=instance,conversion=conversion,adr=adr,typechar=typechar,delete=delete)

    def serialWriteRaw(self,cmd):
        self.comms.serialWriteRaw(cmd)
    
    def sendValue(self,cls,cmd,val,adr=None,instance=0):
        self.comms.sendValue(self,cls=cls,cmd=cmd,val=val,adr=adr,instance=instance)

    def sendCommand(self,cls,cmd,instance=0,typechar = '?'):
        self.comms.sendCommand(cls,cmd,instance=instance,typechar=typechar)

    def sendCommands(self,cls,cmds,instance=0,typechar = '?'):
        cmdstring = ""
        for cmd in cmds:
            cmdstring += f"{cls}.{instance}.{cmd}{typechar};"
        self.comms.serialWriteRaw(cmdstring)
        
