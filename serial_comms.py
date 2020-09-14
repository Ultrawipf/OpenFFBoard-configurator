import queue


class SerialComms:
    def __init__(self,main,serialport):
        self.serial = serialport
        self.main=main
        self.serialQueue = queue.Queue()
        self.sendQueue = queue.Queue()
        self.serial.readyRead.connect(self.serialReceive)
        self.sentCommandSize=0 # tracks sent bytes so never more than 64 bytes are sent
        self.waitForEmptyQueue = False
    def checkOk(self,reply):
        if(reply == "OK" or reply.find("Err") == -1):
            return
        else:
            self.main.log(reply)

    def serialWrite(self,cmd):
        if(self.serial.isOpen()):
            self.serialGetAsync(cmd,self.checkOk,readall=True)
            if(not self.serial.waitForBytesWritten(1000)):
                self.main.log("Error writing "+cmd)

    def setAsync(self,enabled):
        try:
            if(enabled):
                self.serial.readyRead.connect(self.serialReceive)
            else:
                self.serial.readyRead.disconnect(self.serialReceive)
        except:
            pass

    def checkSendQueue(self):
        if(not self.sendQueue.empty()): # remaining commands
            cmd = self.sendQueue.get()
            if(self.sentCommandSize + len(cmd) < 64):
                print("Removing queue")
                self.sentCommandSize += len(cmd)
                self.main.serialchooser.write(bytes(cmd,"utf-8"))
            else:
                # Add to send queue again
                self.sendQueue.put(cmd)

    def serialReceive(self):
        data = self.serial.readAll()
        text = data.data().decode("utf-8")

        # Command replies start with > and end with \n
        if(self.serialQueue.empty()):
            self.main.serialchooser.serialLog(text)
            self.checkSendQueue()
            return
        cur_queue = self.serialQueue.get()
        self.sentCommandSize -= len(cur_queue[0])
        
        def process_cmd(reply,cur_queue): 
            if(reply[0] == ">"):
                if(not cur_queue[3]):
                    reply = reply[1::]
                
                if(reply.startswith("Err")):
                    self.main.log(reply)
                elif(cur_queue[1]):
                    if(cur_queue[2]):
                        reply = cur_queue[2](reply) #apply conversion
                    cur_queue[1](reply)
                
            else:
                # Not a command. pass to log
                self.main.serialchooser.serialLog(reply+"\n")
            self.checkSendQueue()

        if(cur_queue[3]): # read all
            process_cmd(text,cur_queue)
            return
        for reply in text.split(">"):
            if reply=="":
                continue
            
            process_cmd(reply,cur_queue)
            if(not self.serialQueue.empty()):
                cur_queue = self.serialQueue.get()
                self.sentCommandSize -= len(cur_queue[0])
        
    """
     Get asynchronous commands and pass the result to the callback. 
     Better performance.
     cmds and callbacks can be lists or a single command (without ; or \n)
     Pass a conversion function to apply to all replies before passing to callbacks. (int or float for example)
    """
    def serialGetAsync(self,cmds,callbacks,convert=None,readall=False):
        commands=[]
        if(type(cmds) == list and type(callbacks) == list):
            for cmd,callback in zip(cmds,callbacks):
                cmd = cmd+";"
                self.serialQueue.put([cmd,callback,convert,False])
                commands.append(cmd)
        elif(type(cmds) == list):
            for cmd in cmds:
                cmd = cmd+";"
                self.serialQueue.put([cmd,callbacks,convert,readall])
                commands.append(cmd)
        else:
            cmds = cmds+";"
            self.serialQueue.put([cmds,callbacks,convert,readall])
            commands.append(cmds)

        for cmd in commands:
            
            if(self.sentCommandSize + len(cmd) < 64):
                self.sentCommandSize+=len(cmd)
                self.main.serialchooser.write(bytes(cmd,"utf-8"))
            else:
                # Add to send queue
                print("Append queue")
                self.sendQueue.put(cmd)



    # get a synchronous reply with timeout
    def serialGet(self,cmd,timeout=500):
    
        if(not self.serial.isOpen()):
            self.main.log("Error: Serial closed")
            return None
        if not self.serialQueue.empty():
            # do something to wait until queue empty....
            pass
        self.setAsync(False)
        self.main.serialchooser.write(bytes(cmd,"utf-8"))

        if(not self.serial.waitForReadyRead(timeout)):
            self.main.log("Error: Serial timeout")
            self.setAsync(True)
            return None
        
        data = self.serial.readAll()
        self.setAsync(True)
        lastSerial = data.data().decode("utf-8")
        #print(lastSerial)

        lastSerial=lastSerial.replace(">","")
        
        if(lastSerial and lastSerial[-1] == "\n"):
            lastSerial=lastSerial[0:-1]
        
        return lastSerial