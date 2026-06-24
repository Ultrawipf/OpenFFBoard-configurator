### v1.17.1
- Update check fails more gracefully at startup with no network


### v1.17.0
- Fixes analog axis progressbars cutting off text and ADS111x progressbars not populating when set to 4
- Fixed task list sorting and command ID
- Faster startup in some cases
- Added signature check indicator

### v1.16.8
- Fixed TMC4671 tab calibration warning popup blocking thread causing timeouts
- Added MT encoder spi speed selector

### v1.16.7
- Added MagnTek mode selector. Support for MT6835

### v1.16.6
- Fixed analog input range sliders not updating correctly when autotune is toggled after changing channel numbers

### v1.16.5
- Added expo curve tuning UI (If used with v1.16.4 FW)
- Using $XDG_CONFIG_HOME/openffb on linux if no local profile file found
- Improved python 3.13 compatibility

### v1.16.3
- Added remote CAN mainclass page

### v1.16.2
- Added speed limit to profile
- Removed ODrive error names

### v1.16.1
- Fixed shifter threshold range to allow increased ranges in v1.16 firmware

### v1.16.0
- Added RMD CAN motor tab
- Chip temperature status added
- Save button is disabled during saving to prevent multiple clicks

### v1.15.2
- Added TMC debug openloop test mode
- Improved stability
- Improved language selector
- Added BISS-C direction selection
- Fixed local ABN encoder index checkbox

### v1.15.0
- Added permanent inertia and friction effect sliders
- Added position save toggle for ODrive

### v1.14.3
- Disabled tmc autotune button for DC and None motors
- Added Axis position readout 
  - TODO: axis.cpr will be changed to be consistent with axis.pos in firmware and not report TMC encoder cpr anymore -> encoder tuning resolution will display incorrect again and needs fixing
- Added task list window
- Fixed some issues in DFU flashing

### v1.14.1
- Added basic translation function
- Fixed CS selection in SPI buttons
- Added axis output torque to FX live graph

### v1.14.0
- Added TMC space vector PWM checkbox
- Added option to prefer energy dissipation in motor for TMC instead of brake resistor
- Added speed limiter axis option

### v1.13.3
- Added percentage to power slider
- Added axis selection for effect monitor (new firmware required)

### v1.13.1
- Added PWM direction checkbox
- When a command callback target causes an error it will remove the callback, print a warning and resume instead of aborting.
  - Prevents issues in case a request is sent during a timeout causing empty encoder config fields in rare cases

### v1.13.0
- Fixed issue in encoder tuning UI
- Added SSI encoder ui

### v1.12.0
- Added support for Simplemotion V2 (Ioni/Argon motor drivers)

### v1.11.1
- Added an emergency stop indication to the bottom ffb rate status bar (Error/Stop symbol + Text)
- Fixed a possible crash when changing certain effect gains in newer Qt6 versions

### v1.11.0
- Fixed effect monitor windows not opening after reconnect if disconnected while window was open
- Added support for serial FFB mainclass (opens regular FFB mode tabs)
- Added option do disable update notifications (Can be enabled/disabled in release browser and update popups)
  - This resets your profile file because it adds a new global settings section. You can migrate profile settings by copying the "profiles" section from profiles.json.1.old to the new profiles.json

### v1.10.2
- Added debug toggle option in help menu
- Read errors/emit signal only once after all tabs are initialized
- Using new odrive error codes

### v1.10.1
- Changed units for flux offset to A
- Properly delete ffb rate connections when changing mainclass

### v1.10.0
- Support for local encoder index
- Fixed range slider not snapping and updating value correctly when dragged by mouse
- Added logger function
- Packing multiple commands into a single string to reduce packet flooding at startup
- Added TMC torque filter option

### v1.9.x
- Added analog filter option
- Added ADS111X source dialog
- Added manual range tuning option for local analog and ADS111X
- Automatically connects at startup if one supported FFBoard device is found
- Many small fixes for stability
- Added update browser (Help->updates)
- Added automatic update notifications for firmware and GUI if detected
- Redesigned UI layout
- Added effect monitoring windows
- Added advanced effect tuning window
- Added encoder filter tuning window
- Added basic profile management system
- Added encoder gear reduction option (For belt/gear driven wheels if there is a reduction between the wheel and encoder. Prescales all internal positions)
- Added constant force rate readout
- Fixed serial port not writing pending data on reset/reboot/mainclass change


# Persistent changelog
Append changes at the top. 
The first section is used in release comments