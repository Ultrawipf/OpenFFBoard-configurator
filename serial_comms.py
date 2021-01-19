import queue,time
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication
from collections import deque
import re

# Regex for splitting a command from a value (power=x) --> =
cmd_reserved_re = '=|\?|!|;|\n'

class SerialComms(QObject):
    maxSendBytes = 64 # How many bytes to send before waiting for replies. Slows down communication a bit

    def __init__(self,main,serialport):
        QObject.__init__(self)
        self.serial = serialport
        self.main=main
        self.serialQueue = []
        self.sendQueue = deque()
        self.serial.readyRead.connect(self.serialReceive)
        self.sentCommandSize=0 # tracks sent bytes so never more than 64 bytes are sent. Includes next command to send
        self.waitForRead = False
        self.serial.aboutToClose.connect(self.reset)
        self.cmdbuf = []
    
    def reset(self):
        self.serialQueue.clear()
        self.sendQueue.clear()
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

    def trySend(self):
        if(len(self.sendQueue) == 0 or not self.serial.isOpen()):
            return
        nextLen = len(self.sendQueue[0])
        
        if(self.sentCommandSize + nextLen < self.maxSendBytes):
            cmd = self.sendQueue.popleft()
            self.sentCommandSize += nextLen
            self.serial.write(bytes(cmd,"utf-8"))
            self.trySend()

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
            # else:
            #     # Not a command. pass to log
            #     self.main.serialchooser.serialLog(reply+"\n")
            #     return
  
            if(entry["callback"]):
                if(len(entry["replies"]) == 1):
                    entry["callback"](entry["replies"][0])
                else:
                    entry["callback"](entry["replies"])

        ####################################
        # Parse
        
        split_reply = re.split(">|!",text) #replies
        
        n = 0
        # For all replies in buffer
        for replytext in split_reply:
            if replytext=="" or len(replytext) < 2:
                continue
            if(replytext[0] == "!" or len(self.serialQueue) == 0):
                self.main.serialchooser.serialLog(text)
                continue
            reply = replytext.split("=",1)
            
            cmd_reply = reply[0]
            reply_val = reply[1]
            sendqueue_elem = None
            # For all pending commands in queue (Should always be the first!)
            for elem in enumerate(self.serialQueue):
                cmdnames = elem[1]["cmds"]
                if(cmd_reply in cmdnames):
                    sendqueue_elem = elem[1]
                    sendqueue_elem["replies"].append(reply_val)
                    if not (len(sendqueue_elem["replies"]) < len(sendqueue_elem["cmds"])):
                        # finished with all commands?
                        self.sentCommandSize -= len(sendqueue_elem["cmdraw"])
                        process_cmd(sendqueue_elem)
                        if not sendqueue_elem["persistent"]:
                            del self.serialQueue[elem[0]] # delete only when all replies received and not persistent entry
                        else:
                            sendqueue_elem["replies"].clear() # only clear replies instead
                        break

            if(sendqueue_elem == None):
                # Nothing found. dump to log
                self.main.serialchooser.serialLog(replytext+"\n")

            self.trySend()

        
    # Adds command to send and receive queue
    def addToQueue(self,cmdraw,callback,convert,persistent=False):
        # num: amount of commands in raw cmd
        
        if(not cmdraw.endswith(";") and not cmdraw.endswith("\n")):
            cmdraw = cmdraw+";"
        # try to split command base names
        cmds = [re.split(cmd_reserved_re,e)[0] for e in re.split(';|\n',cmdraw) if e]
        length = len(cmdraw)
        entry = {"callback":callback,"cmdraw":cmdraw,"cmds":cmds,"convert":convert,"replies":[],"persistent":persistent}
        self.serialQueue.append(entry)
        self.sendQueue.append(cmdraw)
        self.trySend()

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
        reply = lastSerial[1::].split("=",1)
        checkcmd = re.split(cmd_reserved_re,cmd,maxsplit=1)[0]
        if(checkcmd != reply[0]):
            print("Error. incorrect reply received " + reply[0] + " expected " + checkcmd)
            return None
        lastSerial=reply[1]
 
        if(lastSerial and lastSerial[-1] == "\n"):
            lastSerial=lastSerial[0:-1]
        
        return lastSerial
