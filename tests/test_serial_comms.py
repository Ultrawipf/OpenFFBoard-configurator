"""Regression tests for the serial receive path. Run with: python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import PyQt6.QtSerialPort
from PyQt6.QtCore import QByteArray, QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

import serial_comms

app = QApplication.instance() or QApplication(sys.argv)


class FakePort(PyQt6.QtSerialPort.QSerialPort):
    """QSerialPort whose readAll() returns whatever the test fed in."""

    def __init__(self):
        super().__init__()
        self._data = QByteArray()

    def feed(self, data):
        self._data = QByteArray(data)

    def readAll(self):
        data = self._data
        self._data = QByteArray()
        return data


class FakeMain:
    def log(self, *args):
        pass


class SerialCommsTestCase(unittest.TestCase):
    def setUp(self):
        serial_comms.SerialComms.callbackDict.clear()
        self.port = FakePort()
        self.comms = serial_comms.SerialComms(FakeMain(), self.port)
        self.comms.send_buffer = []
        self.raw = []
        self.comms.rawReply.connect(self.raw.append)

    def receive(self, data):
        self.port.feed(data)
        self.comms.serialReceive()

    def register(self, name, sink, cls="main", cmd="id", **kwargs):
        kwargs.setdefault("delete", True)
        kwargs.setdefault("typechar", "?")
        serial_comms.SerialComms.registerCallback(
            handler=name, cls=cls, cmd=cmd, callback=sink, **kwargs)


class TestCallbackDispatch(SerialCommsTestCase):
    def test_all_matching_oneshot_callbacks_run(self):
        """Removing an expired callback must not skip the next one."""
        called = []
        for name in ("timeout_check_cb", "get_main_classes", "id_cb", "fourth"):
            self.register(name, (lambda n: lambda r: called.append(n))(name))

        self.receive(b"[main.0.id?|0]\n")

        self.assertEqual(called, ["timeout_check_cb", "get_main_classes", "id_cb", "fourth"])
        self.assertEqual(serial_comms.SerialComms.callbackDict["main"], [])

    def test_persistent_callbacks_are_kept(self):
        called = []
        self.register("oneshot", lambda r: called.append("oneshot"), delete=True)
        self.register("keep", lambda r: called.append("keep"), delete=False)

        self.receive(b"[main.0.id?|0]\n")
        self.receive(b"[main.0.id?|1]\n")

        self.assertEqual(called, ["oneshot", "keep", "keep"])

    def test_conversion_does_not_leak_to_next_callback(self):
        got = []
        self.register("converted", got.append, conversion=int)
        self.register("raw", got.append)

        self.receive(b"[main.0.id?|7]\n")

        self.assertEqual(got, [7, "7"])

    def test_nested_event_loop_does_not_double_call(self):
        """A callback that opens a modal dialog must not make others run twice."""
        called = []

        def blocking(reply):
            called.append("blocking")
            loop = QEventLoop()
            QTimer.singleShot(10, loop.quit)
            loop.exec()

        self.register("blocking", blocking)
        self.register("second", lambda r: called.append("second"))

        self.receive(b"[main.0.id?|0]\n")

        self.assertEqual(called, ["blocking", "second"])

    def test_failing_callback_is_removed(self):
        def broken(reply):
            raise RuntimeError("widget deleted")

        called = []
        self.register("broken", broken, delete=False)
        self.register("second", lambda r: called.append("second"))

        self.receive(b"[main.0.id?|0]\n")

        self.assertEqual(called, ["second"])
        self.assertEqual(serial_comms.SerialComms.callbackDict["main"], [])


class TestParser(SerialCommsTestCase):
    def collect(self):
        got = []
        self.register("sink", got.append, delete=False)
        return got

    def test_plain_frames(self):
        got = self.collect()
        self.receive(b"[main.0.id?|1]\n[main.0.id?|2]\n")
        self.assertEqual(got, ["1", "2"])

    def test_frame_split_across_reads(self):
        got = self.collect()
        self.receive(b"[main.0.i")
        self.receive(b"d?|1]\n")
        self.assertEqual(got, ["1"])

    def test_truncated_frame_before_first_start_marker(self):
        """A stray ']' must not wedge the parser forever."""
        got = self.collect()
        self.receive(b"sys.0.swver?|1.17.0]\n")
        self.receive(b"[main.0.id?|1]\n")
        self.receive(b"[main.0.id?|2]\n")
        self.assertEqual(got, ["1", "2"])
        self.assertNotIn("]", self.comms.replytext)

    def test_noise_between_frames(self):
        got = self.collect()
        self.receive(b"[main.0.id?|1]\ndebug: booting\n[main.0.id?|2]\n")
        self.assertEqual(got, ["1", "2"])

    def test_multibyte_split_across_reads(self):
        """A read boundary inside a UTF-8 sequence must not drop the chunk."""
        got = self.collect()
        frame = "[main.0.id?|1]\n[sys.0.temp?|41.2 °C]\n[main.0.id?|2]\n".encode()
        cut = frame.index(b"\xc2") + 1
        self.receive(frame[:cut])
        self.receive(frame[cut:])
        self.assertEqual(got, ["1", "2"])

    def test_invalid_byte_does_not_drop_chunk(self):
        got = self.collect()
        self.receive(b"[main.0.id?|1]\n\xff\xfe[main.0.id?|2]\n")
        self.assertEqual(got, ["1", "2"])

    def test_buffer_is_capped(self):
        self.receive(b"[" + b"x" * (serial_comms.SerialComms.MAX_REPLY_BUFFER + 1))
        self.assertEqual(self.comms.replytext, "")

    def test_unmatched_frame_is_emitted_raw(self):
        self.receive(b"[not a command]\n")
        self.assertEqual(self.raw, ["not a command"])
        self.assertEqual(self.comms.replytext, "")


class TestReset(SerialCommsTestCase):
    def test_reset_clears_receive_and_send_buffers(self):
        self.comms.replytext = "[partial"
        self.comms.send_buffer = ["main.0.id?;"]

        self.comms.reset()

        self.assertEqual(self.comms.replytext, "")
        self.assertEqual(self.comms.send_buffer, [])

    def test_decoder_state_is_dropped(self):
        got = []
        self.register("sink", got.append, delete=False)
        self.receive("[sys.0.temp?|°".encode()[:-1])
        self.comms.reset()
        self.receive(b"[main.0.id?|1]\n")
        self.assertEqual(got, ["1"])


if __name__ == "__main__":
    unittest.main()
