from PyQt6.QtGui import QTextCursor
from base_ui import WidgetUI,CommunicationHandler
import pydfu
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets  import QFileDialog,QMessageBox,QApplication

class DFUModeUI(WidgetUI, CommunicationHandler):
    selectedFile = None
    dfuDevice = None
    firstFail = True
    mainUI = None
    def __init__(self, main=None,device = None, mainUI = None):
            WidgetUI.__init__(self, main, 'dfu.ui')
            CommunicationHandler.__init__(self)
            self.groupbox_controls.setEnabled(False)
            self.main = main #type: main.MainUi
            self.mainUI = mainUI

            self.pushButton_DFU.clicked.connect(self.dfu)
            self.pushButton_filechooser.clicked.connect(self.fileClicked)
            self.pushButton_fullerase.clicked.connect(self.fullEraseClicked)
            self.pushButton_upload.clicked.connect(self.uploadClicked)

            self.devFound = False
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.initUi)
            self.timer.start(1000)

            self.checkBox_massErase.setEnabled(False) #TODO disable checkbox for now

    def hideEvent(self, a0) -> None:
        if(self.dfuDevice):
            pydfu.exit_dfu()
        return super().hideEvent(a0)


    def initUi(self):
        dfu_devices = pydfu.get_dfu_devices(idVendor=0x0483, idProduct=0xdf11)
        if not dfu_devices:
            # No devices found
            if self.firstFail:
                self.log("Searching devices...\n")
                self.log("Make sure the bootloader is detected and drivers installed. Short boot0 to force the bootloader when connecting\n")
                self.log("No DFU device found.\nRetrying..")
                self.firstFail = False
            else:
                self.log(".")
            # Enable the DFU button if the serial is connected
            if self.mainUI.connected:
                self.pushButton_DFU.setEnabled(True)
            else:
                self.pushButton_DFU.setEnabled(False)
        elif len(dfu_devices) > 1:
            self.log("Found multiple DFU devices:" + str(dfu_devices) + "\n")
            self.log("Please disconnect other DFU devices to avoid mistakes\n")

        else:
            self.timer.stop()
            try:
                pydfu.init()
            except ValueError as e:
                self.log("Found DFU device but could not connect: " + str(e.args[1]))
                self.timer.start()
                return
            self.log("Found DFU device. Please select an option")
            self.dfuDevice = dfu_devices[0]
            self.groupbox_controls.setEnabled(True)
            self.pushButton_filechooser.setEnabled(True)
            self.pushButton_fullerase.setEnabled(True)
            self.pushButton_DFU.setEnabled(False)

    def dfu(self):
        self.sendCommand("sys","dfu")
        self.log("\nEntering DFU...\n")
        self.mainUI.resetPort()


    def fileClicked(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
        dlg.setNameFilters(["Firmware files (*.hex *.dfu)","DFU files (*.dfu)","Intel hex files (*.hex)"])
        if dlg.exec():
            filenames = dlg.selectedFiles()
            self.selectFile(filenames[0])
            self.pushButton_upload.setEnabled(True)
        else:
            self.pushButton_upload.setEnabled(False)

    def selectFile(self,filename):
        self.selectedFile = filename
        self.label_filename.setText(self.selectedFile)
        if(self.selectedFile.endswith("dfu")):
            elements = pydfu.read_dfu_file(self.selectedFile)
        elif(self.selectedFile.endswith("hex")):
            elements = pydfu.read_hex_file(self.selectedFile)
        else:
            self.log("Not a known firmware file\n")
            return

        if not elements:
            self.log("Error parsing file\n")
            return
        size = sum([e["size"] for e in elements])
        self.log("Loaded {} segments with {} bytes\n".format(len(elements), size))
        self.elements = elements

    def uploadClicked(self):

        elements = self.elements
        mass_erase = self.checkBox_massErase.isChecked()
        self.groupbox_controls.setEnabled(False)
        if(mass_erase):
            self.fullErase()
        
        self.log("Uploading {} segments... Do NOT close this window or disconnect until done!\n".format(len(elements)))
        try:
            pydfu.write_elements(elements, mass_erase, progress=self.progress)
            self.log("Uploaded!\n")
        except Exception as e:
            self.log(str(e))
            self.log("USB Exception during flashing... Please reflash firmware!\n")

        pydfu.exit_dfu()
        self.log("Done. Please reset\n")
        self.groupbox_controls.setEnabled(True)
        self.dfuDevice = None

    def fullEraseClicked(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Full chip erase")
        msg.setText("Fully erase the chip?")
        msg.setInformativeText("This erases EVERYTHING.\nFirmware and settings.\nYou may need a programmer or short the boot0 pins to reflash it!")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        ret = msg.exec()
        # Warning displayed. Erase!
        if ret == QMessageBox.StandardButton.Ok:
            self.fullErase()

    def fullErase(self):
        if self.dfuDevice:
            self.log("Full chip erase started...\n")
            try:
                self.progress(0,25,100)
                pydfu.mass_erase()
                self.progress(0,100,100)
                self.log("Chip erased\n")
            except Exception as e:
                self.progress(0,100,100)
                self.log(str(e))
                self.log("USB Exception during erasing... Please reflash firmware!\n")

    def log(self,txt):
        self.textBrowser_dfu.moveCursor(QTextCursor.MoveOperation.End)
        self.textBrowser_dfu.insertPlainText(txt)
        self.textBrowser_dfu.moveCursor(QTextCursor.MoveOperation.End)
        self.update()
        QApplication.processEvents()

    def progress(self,addr, offset, size):
        self.progressBar.setValue(int(offset * 100 / size))
        self.update()
        QApplication.processEvents()