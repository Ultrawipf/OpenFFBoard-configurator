import queue,time
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication
from collections import deque
import re
from PyQt6.QtCore import pyqtSignal

# Regex group indices:
GRP_CLS         = 0
GRP_INSTANCE    = 1
GRP_CMD         = 2
GRP_TYPE        = 3
GRP_CMDVAL1     = 4
GRP_CMDVAL2     = 5
GRP_REPLY       = 6

class SerialComms(QObject):
    replytext = ""
    cmdRegex = re.compile(r"\[(\w+)\.(?:(\d+)\.)?(\w+)([?!=]?)(?:(\d+))?(?:\?(\d+))?\|(.+)\]",re.DOTALL)
    callbackDict = {}
    rawReply = pyqtSignal(str)

    def __init__(self,main,serialport):
        QObject.__init__(self)
        self.serial = serialport
        self.main=main
        self.serial.readyRead.connect(self.serialReceive)
        self.serial.aboutToClose.connect(self.reset)


    def registerCallback(handler,cls,cmd,callback,instance=0,conversion=None,adr=None,delete=False,typechar='?'):
        if cls not in SerialComms.callbackDict:
            SerialComms.callbackDict[cls] = []

        callbackObj = {"handler":handler,"callback":callback,"convert":conversion,"instance":instance,"class":cls,"cmd":cmd,"address":adr,"delete":delete,"typechar":typechar}
        if callbackObj not in SerialComms.callbackDict[cls]:
            SerialComms.callbackDict[cls].append(callbackObj)
            #print("New callback",cls,cmd)

    def removeCallbacks(handler):
        for cls,item in (SerialComms.callbackDict.items()):
            SerialComms.callbackDict[cls] = [ entry for entry in item if entry["handler"] != handler]

    def removeAllCallbacks(self):
        SerialComms.callbackDict.clear()

    def getValueAsync(self,handler,cls,cmd,callback,instance=0,conversion=None,adr=None,typechar='?',delete=True):
        if typechar == None:
            typechar = ''
        SerialComms.registerCallback(handler=handler,cls=cls,cmd=cmd,callback=callback,instance=instance,conversion=conversion,adr=adr,delete=delete,typechar=typechar)
        if not adr:
            self.serialWriteRaw(f"{cls}.{instance}.{cmd}{typechar};")
        else:
            self.serialWriteRaw(f"{cls}.{instance}.{cmd}{typechar}{adr};")

    def sendCommand(self,cls,cmd,instance=0,typechar='?'):
        cmdstring = f"{cls}.{instance}.{cmd}{typechar};"
        self.serialWriteRaw(cmdstring)

    def sendValue(self,handler,cls,cmd,val,adr=None,instance=0):
        cmdstring  = f"{cls}.{instance}.{cmd}={val}"
        if adr:
            cmdstring+="?"+str(adr)
        cmdstring += ";"
        SerialComms.registerCallback(handler=handler,cls=cls,cmd=cmd,callback=self.checkOk,instance=instance,adr=adr,delete=True,typechar='=')
        self.serialWriteRaw(cmdstring)

    def reset(self):
        self.replytext = ""

    def checkOk(self,reply):
        if(reply == "OK" or reply.find("Err") == -1):
            return
        else:
            self.main.log(reply)

    def serialWriteRaw(self,cmdraw):
        if(self.serial.isOpen()):
            #print(f"{cmdraw}")
            self.serial.write(bytes(cmdraw,"utf-8"))

    def serialReceive(self):
        data = self.serial.readAll()
        try:
            newReply = data.data().decode("utf-8")
            self.replytext += newReply # Buffer replies until newline found at end of buffer
        except Exception as e:
            print(f"Can not decode:\n{data}. Exception: {e}")
        try:
        
            while self.replytext:
                firstEndmarker = self.replytext.find("]")
                firstStartmarker = self.replytext.find("[")
                if(firstStartmarker >= 0 and firstEndmarker > 1 and firstStartmarker < firstEndmarker):
                    match = self.cmdRegex.search(self.replytext,firstStartmarker,firstEndmarker+1)
                    if (match):
                        curRepl = self.replytext[firstStartmarker+1:firstEndmarker]
                        self.replytext = self.replytext[match.end()::] # cut out everything before the end of the match
                        if self.processMatchedReply(match):
                            pass
                        else:
                            self.rawReply.emit(curRepl)
                        
                    else:
                        self.rawReply.emit(self.replytext[firstStartmarker+1:firstEndmarker])
                        self.replytext = self.replytext[firstEndmarker+1::]
                else:
                    break
        except Exception as e:
            print("Can not process:",e)
        


    def processMatchedReply(self,match):
        groups = match.groups()
        #print(groups)
        cls = groups[GRP_CLS]
        instance = int(groups[GRP_INSTANCE]) if groups[GRP_INSTANCE] else 0
        reply = str(groups[GRP_REPLY])
        typechar = groups[GRP_TYPE] if groups[GRP_TYPE] else ''
        cmd = groups[GRP_CMD]
        deleted = False
        adr = groups[GRP_CMDVAL2] if groups[GRP_CMDVAL2] else None
        val = groups[GRP_CMDVAL1] if groups[GRP_CMDVAL1] else None
        
        if cls in SerialComms.callbackDict:
            for callbackObject in SerialComms.callbackDict[cls]:
                if callbackObject["cmd"] != cmd:
                    continue
                if (instance != callbackObject["instance"]) and (callbackObject["instance"] != 0xff):
                    #print("ignoring",callbackObject,instance)
                    continue
                if typechar != callbackObject["typechar"] and callbackObject["typechar"] != None:
                    #print("Ignoring",typechar,callbackObject["typechar"])
                    continue

                if adr != None and adr != callbackObject["address"]:
                    #print("Ignoring address",callbackObject,groups)
                    continue

                if reply == "NOT_FOUND":
                    #print(f"Cmd {cmd} not found. check syntax")
                    continue
                if(callbackObject["convert"]):
                    reply = callbackObject["convert"](reply)
                callbackObject["callback"](reply) 
                if callbackObject["delete"]: # delete if flag is set
                    #print("Deleting",callbackObject)
                    SerialComms.callbackDict[cls].remove(callbackObject)
                    deleted = True
          
        return deleted
