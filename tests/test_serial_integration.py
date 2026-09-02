"""End to end test of the receive path over a real tty. POSIX only."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import PyQt6.QtSerialPort
from PyQt6.QtCore import QIODevice, QTimer, QEventLoop
from PyQt6.QtWidgets import QApplication

import serial_comms

app = QApplication.instance() or QApplication(sys.argv)


class FakeMain:
    def log(self, *args):
        pass


@unittest.skipUnless(hasattr(os, "openpty"), "needs a POSIX pty")
class TestSerialOverPty(unittest.TestCase):
    def setUp(self):
        serial_comms.SerialComms.callbackDict.clear()
        self.master, slave = os.openpty()
        name = os.ttyname(slave)
        os.close(slave)

        self.port = PyQt6.QtSerialPort.QSerialPort()
        self.port.setPortName(name)
        self.port.setBaudRate(115200)
        self.assertTrue(self.port.open(QIODevice.OpenModeFlag.ReadWrite), self.port.errorString())
        self.port.clear(PyQt6.QtSerialPort.QSerialPort.Direction.AllDirections)
        self.comms = serial_comms.SerialComms(FakeMain(), self.port)

    def tearDown(self):
        self.port.close()
        os.close(self.master)

    def pump(self, ms=300):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def test_burst_is_fully_delivered(self):
        got = []
        serial_comms.SerialComms.registerCallback(
            handler="t", cls="main", cmd="id", callback=got.append, delete=False, typechar="?")

        os.write(self.master, b"sys.0.swver?|1.17.0]\n")  # leftover tail from a previous session
        for i in range(300):
            os.write(self.master, ("[main.0.id?|%d]\n" % i).encode())
        os.write(self.master, "[sys.0.temp?|41.2 °C]\n".encode())
        self.pump()

        self.assertEqual(got, [str(i) for i in range(300)])

    def test_modal_dialog_does_not_lose_replies(self):
        """Opening a nested event loop from a callback must not drop pending replies."""
        got = []
        opened = []

        def blocking(reply):
            opened.append(reply)
            loop = QEventLoop()
            QTimer.singleShot(200, loop.quit)
            loop.exec()

        serial_comms.SerialComms.registerCallback(
            handler="t", cls="sys", cmd="swver", callback=blocking, delete=True, typechar="?")
        serial_comms.SerialComms.registerCallback(
            handler="t", cls="main", cmd="id", callback=got.append, delete=False, typechar="?")

        os.write(self.master, b"[sys.0.swver?|1.17.0]\n")
        for i in range(50):
            os.write(self.master, ("[main.0.id?|%d]\n" % i).encode())
        self.pump(600)

        self.assertEqual(opened, ["1.17.0"])
        self.assertEqual(got, [str(i) for i in range(50)])


if __name__ == "__main__":
    unittest.main()
