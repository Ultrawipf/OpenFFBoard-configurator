import queue,time
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication
from collections import deque
import re
from PyQt5.QtCore import pyqtSignal

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
    cmdRegex = re.compile(r"\[(\w+)\.(?:(\d+)\.)?(\w+)([?!=])(?:(\d+))?(?:\?(\d))?\|(.+)\]",re.DOTALL)
    callbackDict = {}
    rawReply = pyqtSignal(str)

    def __init__(self,main,serialport):
        QObject.__init__(self)
        self.serial = serialport
        self.main=main
        #self.serialQueue = []
        self.serial.readyRead.connect(self.serialReceive)
        #self.waitForRead = False
        self.serial.aboutToClose.connect(self.reset)
        #self.cmdbuf = []
        #self.persistentCallbacks = []


    def registerCallback(self,handler,cls,cmd,callback,instance=0,conversion=None,adr=None,delete=False,typechar='?'):
        if cls not in self.callbackDict:
            self.callbackDict[cls] = []

        callbackObj = {"handler":handler,"callback":callback,"convert":conversion,"instance":instance,"class":cls,"cmd":cmd,"address":adr,"delete":delete,"typechar":typechar}
        if callbackObj not in self.callbackDict[cls]:
            self.callbackDict[cls].append(callbackObj)
            print("New callback",cls,cmd)

    def removeCallbacks(self,handler):
        for cls,item in (self.callbackDict.items()):
            for cb in (item):
                if cb["handler"] == handler:
                    del cb
        #print("CB",self.callbackDict)


    def getValueAsync(self,handler,cls,cmd,callback,instance=0,conversion=None,adr=None,typechar='?',delete=True):
        if typechar == None:
            typechar = ''
        self.registerCallback(handler=handler,cls=cls,cmd=cmd,callback=callback,instance=instance,conversion=conversion,adr=adr,delete=delete,typechar=typechar)
        self.serialWriteRaw(f"{cls}.{instance}.{cmd}{typechar};")

    def sendCommand(self,cls,cmd,instance=0,typechar='?'):
        cmdstring = f"{cls}.{instance}.{cmd}{typechar};"
        self.serialWriteRaw(cmdstring)

    def sendValue(self,handler,cls,cmd,val,adr=None,instance=0):
        cmdstring  = f"{cls}.{instance}.{cmd}={val}"
        if adr:
            cmdstring+=str(adr)
        cmdstring += ";"
        self.registerCallback(handler=handler,cls=cls,cmd=cmd,callback=self.checkOk,instance=instance,adr=adr,delete=True,typechar='=')
        self.serialWriteRaw(cmdstring)

    

    def reset(self):
        self.replytext = ""
        # self.serialQueue.clear()
        # self.waitForRead = False
        # self.cmdbuf = []
        
    def checkOk(self,reply):
        if(reply == "OK" or reply.find("Err") == -1):
            return
        else:
            self.main.log(reply)

    def serialWriteRaw(self,cmdraw):
        if(self.serial.isOpen()):
            print(f"{cmdraw}")
            self.serial.write(bytes(cmdraw,"utf-8"))

    # def serialWrite(self,cmd,prefix=None):
        
    #     if(prefix != None):
    #         cmd=prefix+"."+cmd
    #     if(self.serial.isOpen()):
    #         self.serialGetAsync(cmd,self.checkOk)

    def serialReceive(self):
        # if(self.waitForRead):
        #     self.waitForRead=False
        #     return
        data = self.serial.readAll()
        newReply = data.data().decode("utf-8")
        self.replytext += newReply # Buffer replies until newline found at end of buffer
        # if(self.replytext.endswith("\n")):
        #     self.processReplies()
        print(newReply)
        while self.replytext:
            firstEndmarker = self.replytext.find("]")
            firstStartmarker = self.replytext.find("[")
            if(firstStartmarker >= 0 and firstEndmarker > 1 and firstStartmarker < firstEndmarker):
                self.rawReply.emit(self.replytext[firstStartmarker+1:firstEndmarker])
                match = self.cmdRegex.search(self.replytext,firstStartmarker,firstEndmarker+1)
                if (match):
                    self.replytext = self.replytext[match.end()::] # cut out everything before the end of the match
                    if self.processMatchedReply(match):
                        pass
                    else:
                        pass
                else:
                    self.replytext = self.replytext[firstEndmarker+1::]
            else:
                break


    def processMatchedReply(self,match):
        groups = match.groups()
        #print(groups)
        cls = groups[GRP_CLS]
        instance = int(groups[GRP_INSTANCE]) if groups[GRP_INSTANCE] else 0
        reply = groups[GRP_REPLY]
        typechar = groups[GRP_TYPE] if groups[GRP_TYPE] else ''
        cmd = groups[GRP_CMD]
        found = False
        #if(typechar == '?'): # read command with value. return the value to the callback
        if cls in self.callbackDict:
            for i,callbackObject in enumerate(self.callbackDict[cls]):
                if callbackObject["cmd"] != cmd:
                    continue
                if (instance != callbackObject["instance"]) and (callbackObject["instance"] != 0xff):
                    print("ignoring",callbackObject,instance)
                    continue
                if typechar != callbackObject["typechar"] and callbackObject["typechar"] != None:
                    continue
                if(callbackObject["convert"]):
                    reply = callbackObject["convert"](reply)
                callbackObject["callback"](reply) # send reply to callback
                #print("Got reply",reply)
                if callbackObject["delete"]: # delete if flag is set
                    del self.callbackDict[cls][i]
                found = True
        return found


    ## REMOVE ALL BELOW'##########################################################################################################
    # def setAsync(self,enabled):
    #     try:
    #         if(enabled):
    #             self.serial.readyRead.connect(self.serialReceive)
    #         else:
    #             self.serial.readyRead.disconnect(self.serialReceive)
    #     except:
    #         pass


    # def processReplies(self):

    #     text = self.replytext
    #     self.replytext = ""

    #     ################################
    #     def process_cmd(entry):
    #         for i,reply in enumerate(entry["replies"]):
    #             if(entry["convert"]):
    #                 entry["replies"][i] = entry["convert"](reply) #apply conversion
    #         if(entry["callback"]):
    #             if(len(entry["replies"]) == 1):
    #                 entry["callback"](entry["replies"][0])
    #             else:
    #                 entry["callback"](entry["replies"])

    #     ####################################
    #     # Parse
        
    #     split_reply = text.split(">") #replies

    #     n = 0
    #     # For all replies in buffer
    #     for replytext in split_reply:
    #         if replytext=="" or len(replytext) < 3:
    #             continue
    #         if(replytext[0] == "!"):
    #             self.main.serialchooser.serialLog("Log: "+replytext[1::])
    #             continue
    #         reply = replytext.split(":",1)
    #         if(len(reply) != 2):
    #             #print(reply)
    #             continue
    #         cmd_reply = reply[0]
    #         reply_val = reply[1]
            
    #         sendqueue_elem = None
    #         # For all pending commands in queue (Should always be the first!)
    #         for elem in enumerate(self.serialQueue):
    #             try:
    #                 cmdnames = elem[1]["cmds"]
    #                 if(cmd_reply in cmdnames):
    #                     sendqueue_elem = elem[1]
    #                     sendqueue_elem["replies"].append(reply_val)
    #                     sendqueue_elem["cmds"].remove(cmd_reply) # reply found. remove cmd so this entry is not found for additional replies of the same name if slow
    #                     if not (len(sendqueue_elem["replies"]) < sendqueue_elem["len"]):
    #                         # finished with all commands?
    #                         process_cmd(sendqueue_elem)
    #                         del self.serialQueue[elem[0]] # delete only when all replies received and not persistent entry
    #                     break
    #             except Exception as e:
                  
    #                 raise e
                    
    #                 self.main.serialchooser.serialLog("Error while processing reply {}.\nError:{}\n".format(cmd_reply,e))

            
    #         # Persistent callbacks
    #         for elem in self.persistentCallbacks:
    #             cmdnames = elem["cmds"]
    #             if(cmd_reply in cmdnames):
    #                 elem["replies"].append(reply_val)
    #                 process_cmd(elem)
    #                 elem["replies"].clear()

    #         if(sendqueue_elem == None):
    #             # Nothing found. Received a command nobody waits on.
    #             self.main.serialchooser.serialLog(replytext+"\n")

        
    # # Adds command to send and receive queue
    # def addToQueue(self,cmdraw,callback,convert):
    #     if(not cmdraw.endswith(";") and not cmdraw.endswith("\n")):
    #         cmdraw = cmdraw+";"
    #     # try to split command names
    #     cmds = [c for c in re.split(';|\n',cmdraw) if c]
    #     entry = {"callback":callback,"cmdraw":cmdraw,"cmds":cmds,"convert":convert,"replies":[],"len":len(cmds)}

    #     # check if exactly the same request is already present to prevent flooding if serial port is frozen
    #     if entry in self.serialQueue:
    #         return

    #     self.serialQueue.append(entry)

    #     self.serial.write(bytes(cmdraw,"utf-8"))

    # """
    #  Get asynchronous commands and pass the result to the callback. 
    #  Better performance. Recommended
    #  cmds and callbacks can be lists or a single command (without ; or \n)
    #  Usages:
    #  pass multiple commands in a list with a single callback (Will pass a list of replies)
    #  pass a single command and a single callback
    #  pass multiple commands and callbacks in lists
    #  You can also pass an additional conversion function to apply to all replies before sending to callbacks. (int or float for example)
    # """
    # def serialGetAsync(self,cmds,callbacks,convert=None,prefix=None):
    #     print("oldCMD:",cmds)
    #     if(prefix != None):
    #         if(type(cmds) == list):
    #             for i in range(len(cmds)):
    #                 cmds[i]=prefix+"."+cmds[i]
    #         elif (type(cmds) == str):
    #             cmds=prefix+"."+cmds
    #     if(not self.serial.isOpen()):
    #         return False
    #     if(type(cmds) == list and type(callbacks) == list): # Multiple commands and callbacks
    #         for cmd,callback in zip(cmds,callbacks):
    #             self.addToQueue(cmd,callback,convert)
    #     elif(type(cmds) == list): # Multiple commands. One callback
    #         #for cmd in cmds:
    #         cmd = ";".join(cmds)
    #         self.addToQueue(cmd,callbacks,convert)
    #     else: # One command and callback or direct
    #         self.addToQueue(cmds,callbacks,convert)

    # def serialRegisterCallback(self,cmd,callback,convert = None):
    #     self.persistentCallbacks.append({"callback":callback,"cmdraw":cmd,"cmds":[cmd],"convert":convert,"replies":[],"len":1})

    # # get a synchronous reply with timeout. Not recommended
    # def serialGet(self,cmd,timeout=500):
    #     if(not self.serial.isOpen()):
    #         self.main.log("Error: Serial closed")
    #         return None
    #     t=0

    #     self.waitForRead = True
    #     self.serial.write(bytes(cmd,"utf-8"))
    #     t=0
    #     while self.waitForRead:
    #         if(timeout-t < 0):
    #             return None
    #         t+=10
    #         time.sleep(0.01)
    #         QApplication.processEvents()

    #     data = self.serial.readAll()

    #     lastSerial = data.data().decode("utf-8")
    #     reply = lastSerial[1::].split(":",1)
    #     checkcmd = re.split(';|\n',cmd)[0]
    #     if(checkcmd != reply[0]):
    #         print("Error. incorrect reply received " + reply[0] + " expected " + checkcmd)
    #         return None
    #     lastSerial=reply[1]
 
    #     if(lastSerial and lastSerial[-1] == "\n"):
    #         lastSerial=lastSerial[0:-1]
    #     return lastSerial
