import queue,time
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication
from collections import deque
import re

class SerialComms(QObject):
   
    def __init__(self,main,serialport):
        QObject.__init__(self)
        self.serial = serialport
        self.main=main
        self.serialQueue = []
        self.serial.readyRead.connect(self.serialReceive)
        self.waitForRead = False
        self.serial.aboutToClose.connect(self.reset)
        self.cmdbuf = []
        self.persistentCallbacks = []
    
    def reset(self):
        self.serialQueue.clear()
        self.waitForRead = False
        self.cmdbuf = []
        
    def checkOk(self,reply):
        if(reply == "OK" or reply.find("Err") == -1):
            return
        else:
            self.main.log(reply)

    def serialWrite(self,cmd):
        if(self.serial.isOpen()):
            self.serialGetAsync(cmd,self.checkOk)

    def setAsync(self,enabled):
        try:
            if(enabled):
                self.serial.readyRead.connect(self.serialReceive)
            else:
                self.serial.readyRead.disconnect(self.serialReceive)
        except:
            pass

    def serialReceive(self):
        if(self.waitForRead):
            self.waitForRead=False
            return

        data = self.serial.readAll()
        text = data.data().decode("utf-8")

        ################################
        def process_cmd(entry): 
            for i,reply in enumerate(entry["replies"]):
                if(entry["convert"]):
                    entry["replies"][i] = entry["convert"](reply) #apply conversion
            if(entry["callback"]):
                if(len(entry["replies"]) == 1):
                    entry["callback"](entry["replies"][0])
                else:
                    entry["callback"](entry["replies"])

        ####################################
        # Parse
        
        split_reply = text.split(">") #replies

        n = 0
        # For all replies in buffer
        for replytext in split_reply:
            if replytext=="" or len(replytext) < 3:
                continue
            if(replytext[0] == "!"):
                self.main.serialchooser.serialLog("Log: "+replytext[1::])
                continue
            reply = replytext.split(":",1)
            cmd_reply = reply[0]
            reply_val = reply[1]
            
            sendqueue_elem = None
            # For all pending commands in queue (Should always be the first!)
            for elem in enumerate(self.serialQueue):
                cmdnames = elem[1]["cmds"]
                if(cmd_reply in cmdnames):
                    sendqueue_elem = elem[1]
                    sendqueue_elem["replies"].append(reply_val)
                    sendqueue_elem["cmds"].remove(cmd_reply) # reply found. remove cmd so this entry is not found for additional replies of the same name if slow
                    if not (len(sendqueue_elem["replies"]) < sendqueue_elem["len"]):
                        # finished with all commands?
                        process_cmd(sendqueue_elem)
                        del self.serialQueue[elem[0]] # delete only when all replies received and not persistent entry
                    break
            
            # Persistent callbacks
            for elem in self.persistentCallbacks:
                cmdnames = elem["cmds"]
                if(cmd_reply in cmdnames):
                    elem["replies"].append(reply_val)
                    process_cmd(elem)
                    elem["replies"].clear()

            if(sendqueue_elem == None):
                # Nothing found. Received a command nobody waits on.
                self.main.serialchooser.serialLog(replytext+"\n")

        
    # Adds command to send and receive queue
    def addToQueue(self,cmdraw,callback,convert):
        if(not cmdraw.endswith(";") and not cmdraw.endswith("\n")):
            cmdraw = cmdraw+";"
        # try to split command names
        cmds = [c for c in re.split(';|\n',cmdraw) if c]
        entry = {"callback":callback,"cmdraw":cmdraw,"cmds":cmds,"convert":convert,"replies":[],"len":len(cmds)}

        # check if exactly the same request is already present to prevent flooding if serial port is frozen
        if entry in self.serialQueue:
            return

        self.serialQueue.append(entry)

        self.serial.write(bytes(cmdraw,"utf-8"))

    """
     Get asynchronous commands and pass the result to the callback. 
     Better performance. Recommended
     cmds and callbacks can be lists or a single command (without ; or \n)
     Usages:
     pass multiple commands in a list with a single callback (Will pass a list of replies)
     pass a single command and a single callback
     pass multiple commands and callbacks in lists
     You can also pass an additional conversion function to apply to all replies before sending to callbacks. (int or float for example)
    """
    def serialGetAsync(self,cmds,callbacks,convert=None):
        if(not self.serial.isOpen()):
            return False
        if(type(cmds) == list and type(callbacks) == list): # Multiple commands and callbacks
            for cmd,callback in zip(cmds,callbacks):
                self.addToQueue(cmd,callback,convert)
        elif(type(cmds) == list): # Multiple commands. One callback
            #for cmd in cmds:
            cmd = ";".join(cmds)
            self.addToQueue(cmd,callbacks,convert)
        else: # One command and callback or direct
            self.addToQueue(cmds,callbacks,convert)

    def serialRegisterCallback(self,cmd,callback,convert = None):
        self.persistentCallbacks.append({"callback":callback,"cmdraw":cmd,"cmds":[cmd],"convert":convert,"replies":[],"len":1})

    # get a synchronous reply with timeout. Not recommended
    def serialGet(self,cmd,timeout=500):
        if(not self.serial.isOpen()):
            self.main.log("Error: Serial closed")
            return None
        t=0

        self.waitForRead = True
        self.serial.write(bytes(cmd,"utf-8"))
        t=0
        while self.waitForRead:
            if(timeout-t < 0):
                return None
            t+=10
            time.sleep(0.01)
            QApplication.processEvents()

        data = self.serial.readAll()

        lastSerial = data.data().decode("utf-8")
        reply = lastSerial[1::].split(":",1)
        checkcmd = re.split(';|\n',cmd)[0]
        if(checkcmd != reply[0]):
            print("Error. incorrect reply received " + reply[0] + " expected " + checkcmd)
            return None
        lastSerial=reply[1]
 
        if(lastSerial and lastSerial[-1] == "\n"):
            lastSerial=lastSerial[0:-1]
        return lastSerial
