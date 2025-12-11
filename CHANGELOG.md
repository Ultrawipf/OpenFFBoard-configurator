### Changes this version:
- Fixes analog axis progressbars cutting off text and ADS111x progressbars not populating when set to 4

### Changes in v16.x:
- Added RMD CAN motor tab
- Chip temperature status added
- Save button is disabled during saving to prevent multiple clicks
- Fixed shifter threshold range to allow increased ranges in v1.16 firmware
- Added speed limit to profile
- Removed ODrive error names
- Added remote CAN mainclass page
- Delete callbacks on connection close. Fixes random error messages if a UI element is not properly removed
- Added expo curve tuning UI (If used with v1.16.4 FW)
- Using $XDG_CONFIG_HOME/openffb on linux if no local profile file found
- Improved python 3.13 compatibility
- Fixed analog input range sliders not updating correctly when autotune is toggled after changing channel numbers
- Added MagnTek mode selector. Support for MT6835
- Fixed TMC4671 tab calibration warning popup blocking thread causing timeouts
- Added MT encoder spi speed selector