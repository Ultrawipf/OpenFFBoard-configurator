import queue,time
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication
from collections import deque
class SerialComms(QObject):
    maxSendBytes = 64 # How many bytes to send before waiting for replies

    def __init__(self,main,serialport):
        QObject.__init__(self)
        self.serial = serialport
        self.main=main
        self.serialQueue = deque()
        self.sendQueue = deque()
        self.serial.readyRead.connect(self.serialReceive)
        self.sentCommandSize=0 # tracks sent bytes so never more than 64 bytes are sent. Includes next command to send
        self.waitForRead = False
        self.serial.aboutToClose.connect(self.reset)
        self.cmdbuf = []
    
    def reset(self):
        self.serialQueue.clear()
        self.sendQueue.clear()
        
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
        def process_cmd(reply,cur_queue): 

            num = cur_queue[3] # commands per callback
            
            if(reply[0] != "!"):            
                if(reply.startswith("Err")):
                    self.main.log(reply)
                    print(reply)
                    reply = None
                    return
                else:
                    if(cur_queue[2]):
                        reply = cur_queue[2](reply) #apply conversion
            else:
                # Not a command. pass to log
                self.main.serialchooser.serialLog(reply+"\n")
                return
            # Wait for more?
            self.cmdbuf.append(reply)
            if(len(self.cmdbuf) < num):
                return

            if(cur_queue[1]):
                if(cur_queue[3] == 1):
                    self.cmdbuf = self.cmdbuf[0]
                cur_queue[1](self.cmdbuf)
                self.cmdbuf = [] # reset

        ####################################
        split_reply = text.split(">")
        n = 0
        self.cmdbuf = []
        cur_queue = self.serialQueue[0]
        for reply in split_reply:
            if reply=="":
                continue
            if(len(self.cmdbuf) == 0):
                cur_queue = self.serialQueue.popleft()
            self.sentCommandSize -= len(cur_queue[0])
            
            process_cmd(reply,cur_queue)
            self.trySend()

        
    # Adds command to send and receive queue
    def addToQueue(self,cmd,callback,convert,num):
        
        if(not cmd.endswith(";") and not cmd.endswith("\n")):
            cmd = cmd+";"
        self.serialQueue.append([cmd,callback,convert,num])
        self.sendQueue.append(cmd)
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
    def serialGetAsync(self,cmds,callbacks,convert=None,num = 1):
        if(not self.serial.isOpen()):
            return False
        if(type(cmds) == list and type(callbacks) == list): # Multiple commands and callbacks
            for cmd,callback in zip(cmds,callbacks):
                self.addToQueue(cmd,callback,convert,1)
        elif(type(cmds) == list): # Multiple commands. One callback
            #for cmd in cmds:
            num = len(cmds)
            cmd = ";".join(cmds)
            self.addToQueue(cmd,callbacks,convert,num)
        else: # One command and callback or direct
            self.addToQueue(cmds,callbacks,convert,num)

            


    # get a synchronous reply with timeout. Not recommended
    def serialGet(self,cmd,timeout=500):
        
        if(not self.serial.isOpen()):
            self.main.log("Error: Serial closed")
            return None
        t=0
        while len(self.serialQueue)>0:
            if(timeout-t < 0):
                print("Timeout")
                return None
            t+=10
            time.sleep(0.01)
            QApplication.processEvents()

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
        lastSerial=lastSerial.replace(">","")
 
        if(lastSerial and lastSerial[-1] == "\n"):
            lastSerial=lastSerial[0:-1]
        
        return lastSerial
