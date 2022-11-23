### Changes this version:
- Added debug toggle option in help menu
- Read errors/emit signal only once after all tabs are initialized
- Using new odrive error codes

### Changes since v1.9.x:
- Changed units for flux offset to A
- Properly delete ffb rate connections when changing mainclass
- Support for local encoder index
- Fixed range slider not snapping and updating value correctly when dragged by mouse
- Added logger function
- Packing multiple commands into a single string to reduce packet flooding at startup
- Added TMC torque filter option