# OpenFFBoard-configurator [![Build Configurator](https://github.com/Ultrawipf/OpenFFBoard-configurator/actions/workflows/build-pyinstaller.yml/badge.svg)](https://github.com/Ultrawipf/OpenFFBoard-configurator/actions/workflows/build-pyinstaller.yml)
A simple GUI to configure the [Open FFBoard](https://github.com/Ultrawipf/OpenFFBoard) written in Python 3 with PyQt. 

This allows complete configuration of all settings in the Open FFBoard firmware at runtime.

Requires the latest firmware version most of the time from a matching branch.
When errors occur hinting at missing commands make sure your firmware and configurator versions are compatible!


Be very careful when changing motor types, drivers or the power value.

Incorrect settings may cause unintended movements or damage hardware.


On older windows versions (older than Windows 10) CDC drivers may not load automatically.

Then you need to manually install for example the STM VCP driver for the device. (We will provide an installer later)


![FFB Window](screenshots/FFBwheel.png?raw=true)


![Axis Window](screenshots/Axispage.png?raw=true)


![TMC Window](screenshots/TMC.png?raw=true)

Dependencies:

PyQt6
PyQt6-Charts (For TMC graph)
pyusb and libusb-1.0.dll for DFU
intelhex for uploading hex files

Install dependencies with `pip install -r requirements.txt` and run `python main.py` to start the application.

A fully executable windows version can be built using pyinstaller and the `build/build.bat` script.

Additionally an automatic build script will create a build artifact for commits on the master branch.