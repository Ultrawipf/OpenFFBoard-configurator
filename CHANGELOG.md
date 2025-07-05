### Changes this version:
- Added expo curve tuning UI (If used with v1.16.4 FW)
- Using $XDG_CONFIG_HOME/openffb on linux if no local profile file found
- Improved python 3.13 compatibility

### Changes in v16.x:
- Added RMD CAN motor tab
- Chip temperature status added
- Save button is disabled during saving to prevent multiple clicks
- Fixed shifter threshold range to allow increased ranges in v1.16 firmware
- Added speed limit to profile
- Removed ODrive error names
- Added remote CAN mainclass page
- Delete callbacks on connection close. Fixes random error messages if a UI element is not properly removed