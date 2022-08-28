### Changes since v1.8:

- Added analog filter option
- Added ADS111X source dialog
- Added manual range tuning option for local analog and ADS111X
- Automatically connects at startup if one supported FFBoard device is found
- Many small fixes for stability

#### Updater:
- Added update browser (Help->updates)
- Added automatic update notifications for firmware and GUI if detected
  
#### Redesign:
- Redesigned UI layout
- Added effect monitoring windows
- Added advanced effect tuning window
- Added encoder filter tuning window
- Added basic profile management system
- Added encoder gear reduction option (For belt/gear driven wheels if there is a reduction between the wheel and encoder. Prescales all internal positions)
- Added constant force rate readout

### Fixed since 1.8.6:
- Fixed serial port not writing pending data on reset/reboot/mainclass change