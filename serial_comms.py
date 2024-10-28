import queue,time, traceback, sys
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication
from collections import deque
import re
import PyQt6.QtSerialPort
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import QTimer
import logging

from helper import throttle

# Regex group indices:
GRP_CLS         = 0
GRP_INSTANCE    = 1
GRP_CMD         = 2
GRP_TYPE        = 3
GRP_CMDVAL1     = 4
GRP_CMDVAL2     = 5
GRP_REPLY       = 6

class SerialComms(QObject):
    MAX_REQUEST_SIZE = 1024
    MAX_DELAY_SEND_CMD = 30

    cmdRegex = re.compile(r"\[(\w+)\.(?:(\d+)\.)?(\w+)([?!=]?)(?:(\d+))?(?:\?(\d+))?\|(.+)\]",re.DOTALL)
    callbackDict = {}
    rawReply = pyqtSignal(str)
    send_buffer = []

    def __init__(self,main,serialport : PyQt6.QtSerialPort.QSerialPort):
        QObject.__init__(self)
        self.serial : PyQt6.QtSerialPort.QSerialPort = serialport 
        self.main=main
        self.serial.readyRead.connect(self.serialReceive)
        self.serial.aboutToClose.connect(self.reset)
        self.replytext = ""
        self.logger = logging.getLogger("serial_comms")

    @staticmethod
    def registerCallback(handler,cls,cmd,callback,instance=0,conversion=None,adr=None,delete=False,typechar='?'):
        if cls not in SerialComms.callbackDict:
            SerialComms.callbackDict[cls] = []

        callbackObj = {"handler":handler,"callback":callback,"convert":conversion,"instance":instance,"class":cls,"cmd":cmd,"address":adr,"delete":delete,"typechar":typechar}
        if callbackObj not in SerialComms.callbackDict[cls]:
            SerialComms.callbackDict[cls].append(callbackObj)
    @staticmethod
    def removeCallbacks(handler):
        for cls,item in (SerialComms.callbackDict.items()):
            SerialComms.callbackDict[cls] = [ entry for entry in item if entry["handler"] != handler]

    def removeAllCallbacks(self):
        SerialComms.callbackDict.clear()

    def getValueAsync(self,handler,cls,cmd,callback,instance=0,conversion=None,adr=None,typechar='?',delete=True):
        if typechar == None:
            typechar = ''
        SerialComms.registerCallback(handler=handler,cls=cls,cmd=cmd,callback=callback,instance=instance,conversion=conversion,adr=adr,delete=delete,typechar=typechar)
        if adr == None:
            self.serialWriteRaw(f"{cls}.{instance}.{cmd}{typechar};")
        else:
            self.serialWriteRaw(f"{cls}.{instance}.{cmd}{typechar}{adr};")

    def sendCommand(self,cls,cmd,instance=0,typechar='?',adr=None):
        if(adr):
            cmdstring = f"{cls}.{instance}.{cmd}{typechar}{adr};"
        else:
            cmdstring = f"{cls}.{instance}.{cmd}{typechar};"
        self.serialWriteRaw(cmdstring)

    def sendValue(self,handler,cls,cmd,val,adr=None,instance=0):
        cmdstring  = f"{cls}.{instance}.{cmd}={val}"
        if adr != None:
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

    def pack_cmd(self,cmd):
        # if buffer is empty, add the line
        if len(self.send_buffer) == 0 :
            self.send_buffer.append(cmd)
            self.logger.debug("First command added")
        else :
        # if buffer is not empty, take the last line, append the new line
            last_line = self.send_buffer.pop()
            last_line += cmd
            if len(last_line) < SerialComms.MAX_REQUEST_SIZE :
                self.send_buffer.append(last_line)
                self.logger.debug("New command packed (size %d)", len(last_line))
            else:
                # if the last buffer + cmd is over 1024, we split all the commands and make 1024 max size new_line
                # and append it to be sent
                new_line = ""
                for line in last_line.split(";"):
                    if (len(new_line) + len(line) +1) < SerialComms.MAX_REQUEST_SIZE :
                        new_line += line + ";"
                    else:
                        self.send_buffer.append(new_line)
                        new_line = line
                self.send_buffer.append(new_line)
                self.logger.debug("New command packed with new line (size %d/line %d)", len(self.send_buffer) ,len(new_line))

    def serialWriteRaw(self,cmdraw):
        self.pack_cmd(cmdraw)
        self._send_over_uart()
    
    @throttle(MAX_DELAY_SEND_CMD)
    def _send_over_uart(self):
        # exit if serial is not opened
        if not self.serial.isOpen() : return

        ## send buffer commands to the board if the port is opened
        cmd_not_sent = []
        self.logger.debug(F"Send %d lines to uart, commm is %d %s", len(self.send_buffer), self.serial.isOpen(),self.send_buffer)
        for cmdraw in self.send_buffer:
            if self.serial.isOpen():
                # if command can't be send, we reput them in the buffer for a retry
                if self.serial.write(bytes(cmdraw,"utf-8")) == -1:
                    cmd_not_sent.append(cmdraw)
            else:
                cmd_not_sent.append(cmdraw)
        self.send_buffer = cmd_not_sent


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
            traceback.print_exception(*sys.exc_info())
        


    def processMatchedReply(self,match):
        groups = match.groups()
        #print(groups)
        cls = groups[GRP_CLS]
        instance = int(groups[GRP_INSTANCE]) if groups[GRP_INSTANCE] else 0
        reply = str(groups[GRP_REPLY])
        typechar = groups[GRP_TYPE] if groups[GRP_TYPE] else ''
        cmd = groups[GRP_CMD]
        deleted = False
        adr = int(groups[GRP_CMDVAL2]) if groups[GRP_CMDVAL2] != None else int(groups[GRP_CMDVAL1]) if groups[GRP_CMDVAL1] != None and typechar == '?' else None  
        val = int(groups[GRP_CMDVAL1]) if groups[GRP_CMDVAL1] != None  else None
    
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
                    #print("Ignoring address",callbackObject,adr)
                    continue

                if reply == "NOT_FOUND":
                    self.logger.error(f"Unknown command {cmd}")
                    #print(f"Cmd {cmd} not found. check syntax")
                    continue
                if reply == "ERR":
                    self.logger.error(f"Error executing command {cmd}")
                    continue
                if(callbackObject["convert"]):
                    try:
                        reply = callbackObject["convert"](reply)
                    except ValueError as e:
                        self.logger.error("Error converting object: " + str(e))
                try:
                    callbackObject["callback"](reply)
                    
                except RuntimeError as e:
                    self.logger.error("Error calling object: " + str(e))
                    callbackObject["delete"] = True # force delete

                if callbackObject["delete"]: # delete if flag is set
                    #print("Deleting",callbackObject)
                    if (SerialComms.callbackDict[cls] is not None) \
                        and (callbackObject in SerialComms.callbackDict[cls]) :
                        SerialComms.callbackDict[cls].remove(callbackObject)
                    else :
                        #self.logger.error(f"Not found callback {callbackObject} for {cls}")
                        pass
                    deleted = True
          
        return deleted
