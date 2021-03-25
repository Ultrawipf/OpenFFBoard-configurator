from base_ui import WidgetUI
import pydfu
import threading
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets  import QFileDialog,QMessageBox,QApplication

class DFUModeUI(WidgetUI):
    selectedFile = None
    dfuDevice = None
    def __init__(self, main=None,device = None):
            WidgetUI.__init__(self, main,'dfu.ui')
            self.groupbox_controls.setEnabled(False)
            self.main = main #type: main.MainUi

            self.pushButton_filechooser.clicked.connect(self.fileClicked)
            self.pushButton_fullerase.clicked.connect(self.fullEraseClicked)
            self.pushButton_upload.clicked.connect(self.uploadClicked)

            self.devFound = False
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.initUi)
            self.timer.start(1000)

            self.checkBox_massErase.setEnabled(False) #TODO disable checkbox for now


    def initUi(self):
        self.log("Searching devices...")
        dfu_devices = pydfu.get_dfu_devices(idVendor=0x0483, idProduct=0xdf11)
        if not dfu_devices:
            # No devices found
            self.log("No DFU device found. Retrying")

        elif len(dfu_devices) > 1:
            self.log("Found multiple DFU devices:" + str(dfu_devices))
            self.log("Please disconnect other DFU devices to avoid mistakes")

        else:
            self.timer.stop()
            pydfu.init()
            self.log("Found DFU device. Please select an option")
            self.dfuDevice = dfu_devices[0]
            self.groupbox_controls.setEnabled(True)
            self.pushButton_filechooser.setEnabled(True)
            self.pushButton_fullerase.setEnabled(True)

    def fileClicked(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFile)
        dlg.setNameFilters(["DFU files (*.dfu)"])
        if dlg.exec_():
            filenames = dlg.selectedFiles()
            self.selectFile(filenames[0])
            self.pushButton_upload.setEnabled(True)
        else:
            self.pushButton_upload.setEnabled(False)

    def selectFile(self,filename):
        self.selectedFile = filename
        self.label_filename.setText(self.selectedFile)

    def uploadClicked(self):
        elements = pydfu.read_dfu_file(self.selectedFile)
        if not elements:
            self.log("Error parsing DFU file")
            return
        mass_erase = self.checkBox_massErase.isChecked()
        self.groupbox_controls.setEnabled(False)
        if(mass_erase):
            self.fullErase()
        
        self.log("Uploading... Do NOT close this window or disconnect!")
        try:
            pydfu.write_elements(elements, mass_erase, progress=self.progress)
            self.log("Uploaded!")
        except Exception as e:
            self.log(str(e))
            self.log("USB Exception during flashing... Please reflash firmware!")

        pydfu.exit_dfu()
        self.log("Please reset")
        self.groupbox_controls.setEnabled(True)

    def fullEraseClicked(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Full chip erase")
        msg.setText("Fully erase the chip?")
        msg.setInformativeText("This erases EVERYTHING.\nFirmware and settings.\nYou may need a programmer or short the boot0 pins to reflash it!")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        ret = msg.exec()
        # Warning displayed. Erase!
        if ret == QMessageBox.Ok:
            self.fullErase()
        

    def fullErase(self):
        if self.dfuDevice:
            self.log("Full chip erase started...")
            try:
                pydfu.mass_erase()
                self.log("Chip erased")
            except Exception as e:
                self.log(str(e))
                self.log("USB Exception during erasing... Please reflash firmware!")
            

    def log(self,txt):
        self.textBrowser_dfu.append(txt)
        self.update()
        QApplication.processEvents()

    def progress(self,addr, offset, size):
        self.progressBar.setValue(offset * 100 / size)
        self.update()
        QApplication.processEvents()