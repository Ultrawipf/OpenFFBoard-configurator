import sys
import hid
import struct
from dataclasses import dataclass
from PyQt6.QtCore import QThread, pyqtSignal

VID = 0x1209 
PID = 0xFFB0 

@dataclass
class HIDReport:
    report_id: int
    buttons: int
    axis_x: int
    axis_y: int
    axis_z: int
    axis_rx: int
    axis_ry: int
    axis_rz: int
    dial: int
    slider: int

    def is_button_pressed(self, button_index):
        """Helper to check if button N (0-63) is pressed"""
        return (self.buttons >> button_index) & 1
    
class HIDWorker(QThread):
    """
    Dedicated thread for HID reading to avoid blocking the UI.
    """
    # Signal to send HIDReport data
    data_received = pyqtSignal(HIDReport)
    # Signal to notify connection status
    connection_status = pyqtSignal(bool, str)  # connected, message
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.device_joy = None  # Joysttick
        self.device_cmd = None  # Commands
        self.is_connected = False
        
        self.unpack_format = None
        self.axis_size = 0 # 16 or 32
        self.expected_len = 0

    def connect_device(self):
        """Connect to HID device"""
        try:
            # Open hid device
            
            interfaces = hid.enumerate(VID, PID)
            path_joy = None
            path_cmd = None
            
            for intf in interfaces:
                usage_page = intf['usage_page']
                path = intf['path']
                
                # NOTE: Sous Windows usage_page est fiable. 
                # Sous Linux, parfois hidapi retourne 0, on peut se fier à 'interface_number' 
                # (souvent 0=Joy, 1 ou 2=Config)
                
                if usage_page == 0x01: # Generic Desktop -> Joystick
                    print(f" -> Trouvé Joystick (Gaming View) sur {path}")
                    path_joy = path
                
                elif usage_page == 0xFF00: # Vendor Defined -> Config
                    print(f" -> Trouvé Config (Commandes) sur {path}")
                    path_cmd = path
                    
            # --- OUVERTURE DES CONNEXIONS ---
            
            # 1. Connexion Joystick (Lecture seule, non bloquante)
            if path_joy:
                self.device_joy = hid.device()
                self.device_joy.open_path(path_joy)
                self.device_joy.set_nonblocking(1) # Important pour le polling rapide
                print("✅ Connecté au Joystick")


            # 2. Connexion Commandes (Lecture/Ecriture)
            if path_cmd:
                self.device_cmd = hid.device()
                self.device_cmd.open_path(path_cmd)
                # On peut le laisser bloquant ou non selon ta logique d'envoi
                self.device_cmd.set_nonblocking(1) 
                print("✅ Connecté aux Commandes")

            
        except OSError as e:
            print(f"Error opening device: {e}")
            self.is_connected = False
            self.connection_status.emit(False, f"FFBoard Device not found on USB: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.is_connected = False
            self.connection_status.emit(False, f"Unexpected error during connexion: {e}")

        return (self.device_joy is not None) or (self.device_cmd is not None)
    
    def disconnect_device(self):
        """Disconnect from HID device"""
        if self.device_joy:
            try:
                self.device_joy.close()
                self.is_connected = False
                print("Device disconnected")
            except Exception as e:
                print(f"Error disconnecting device: {e}")

    def run(self):
        # Connect to device when thread starts
        if not self.connect_device():
            # If connection fails, don't continue with the thread
            return

        try:

            self.connection_status.emit(True, "Successfull")

            # Read the report from the hid device
            #self.sendCommand(1,0xA01,0,0x00,0) # get power
            
            # On lit jusqu'à 65 bytes
            #data = self.device_cmd.read(65)
            
            #if data:
            #   self.parse_and_print_response(data)
                
            print("   [Thread Joystick] Démarré")
            while self.running and self.device_joy:
                # Lecture brute (taille max 64)
                data = self.device_joy.read(64)
                if data:
                    parsed_report = self.parse_report(data)
                    if parsed_report:
                        self.data_received.emit(parsed_report)
                self.msleep(10) # ~100Hz
                    
        except Exception as e:
            print(f"Error HID: {e}")
            self.connection_status.emit(False, f"Communication error: {e}")
            # In case of error, stop the thread
            self.running = False
        finally:
            self.disconnect_device()
                
    def start_thread(self):
        """Start the thread and set running flag to True"""
        self.running = True
        self.start()
                
    def stop(self):
        """Stop the thread and disconnect device"""
        self.running = False
        self.wait()
        if self.device_joy: self.device_joy.close()
        if self.device_cmd: self.device_cmd.close()
                
    def detect_format(self, data_len):
        """
        Determines the format based on the size of the first received packet.
        """
        # Note : We accept >= because sometimes USB adds padding up to 64 bytes
        if data_len >= 41: 
            # 1B ID + 8B Buttons + 8*4B Axes = 41 bytes min
            print("Detection: Firmware 32-bit (High Precision)")
            self.axis_size = 32
            # '<' little endian, 'B' uchar, 'Q' ulonglong, 'i' int (4 bytes) * 8
            self.unpack_format = '<BQiiiiiiii'
            self.expected_len = 41
            return True
            
        elif data_len >= 25:
            # 1B ID + 8B Buttons + 8*2B Axes = 25 bytes min
            print("Detection: Firmware 16-bit (Standard)")
            self.axis_size = 16
            # '<' little endian, 'B' uchar, 'Q' ulonglong, 'h' short (2 bytes) * 8
            self.unpack_format = '<BQhhhhhhhh'
            self.expected_len = 25
            return True
            
        else:
            print(f"Unknown format or packet too small ({data_len} bytes)")
            return False
        
    def sendCommand(self,type,cls,inst,cmd,data=0,adr=0):
        fmt = '<BBHBIqQ'
        report_id = 0xA1
        buffer = struct.pack(fmt, report_id, type, cls, inst, cmd, data, adr)
        self.device_cmd.write(buffer)
        
    def parse_and_print_response(self, data):
        """
        Décode la réponse brute reçue (liste d'entiers)
        """
        # Conversion list[int] -> bytes
        raw = bytes(data)
        
        # Vérification du Report ID (0xA1 selon ton code)
        if raw[0] == 0xA1:
            try:
                # On découpe selon ton code pywinusb :
                # data[0] = ID
                t = raw[1]
                cls = struct.unpack('<H', raw[2:4])[0]
                instance = raw[4]
                cmd = struct.unpack('<L', raw[5:9])[0]
                val = struct.unpack('<q', raw[9:17])[0]
                addr = struct.unpack('<q', raw[17:25])[0]
                
                print(f"REÇU -> Type: {t}, Class: {hex(cls)}.{instance}, Cmd: {cmd}, Val: {val}, Addr: {addr}")
            except struct.error:
                print("Erreur de décodage paquet")

    def parse_report(self, data):
        """Parse the HID raw data in report

        Args:
            data (byte array): raw data from report
        """
        # 1. Conversion to bytes if we receive a list of integers (common with hidapi)
        if isinstance(data, list):
            data = bytes(data)

        # 2. Size verification
        # Structure: 1B (ID) + 8B (Buttons) + 8 * 2B (Axes) = 25 bytes
        if self.unpack_format is None:
            if not self.detect_format(len(data)):
                return None
        
        # NOTE : Sometimes hidapi returns more data (USB padding to 64 bytes), 
        # so we just check that we have *at least* the required size.
        if len(data) < self.expected_len:
            print(f"Error: Incomplete data (received {len(data)} bytes, expected {self.expected_len})")
            return None

        try:
            # 3. Decoding (Unpack)
          
            # We only take the first 25 bytes even if the buffer is larger
            unpacked = struct.unpack(self.unpack_format, data[:self.expected_len])
            
            # 4. Object creation
            return HIDReport(
                report_id=unpacked[0],
                buttons=unpacked[1],
                axis_x=unpacked[2],
                axis_y=unpacked[3],
                axis_z=unpacked[4],
                axis_rx=unpacked[5],
                axis_ry=unpacked[6],
                axis_rz=unpacked[7],
                dial=unpacked[8],
                slider=unpacked[9]
            )

        except struct.error as e:
            print(f"Error parsing struct: {e}")
            return None
