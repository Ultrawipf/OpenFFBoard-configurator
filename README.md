# OpenFFBoard-configurator
A simple GUI to configure the [Open FFBoard](https://github.com/Ultrawipf/OpenFFBoard) written in Python 3 with Qt.

This allows complete configuration of all settings in the Open FFBoard firmware at runtime.

Requires the latest firmware version most of the time from a matching branch.


Be very careful when changing motor types, drivers or the power value.

Incorrect settings may cause unintended movements or damage hardware.


On older windows versions CDC drivers may not load automatically.

Then you need to manually install for example the STM VCP driver for the device. (We will provide an installer later)


![FFB Window](screenshots/FFBwheel.png?raw=true)

Dependencies:

PyQt5
pyqtgraph (For TMC graph)
pyusb and libusb-1.0.dll for DFU