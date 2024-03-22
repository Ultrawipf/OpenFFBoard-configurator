### Changes this version:
- Disabled tmc autotune button for DC and None motors
- Added Axis position readout 
  - TODO: axis.cpr will be changed to be consistent with axis.pos in firmware and not report TMC encoder cpr anymore -> encoder tuning resolution will display incorrect again and needs fixing
- Added task list window
- Fixed some issues in DFU flashing

### Changes in 1.14.x:
- Added TMC space vector PWM checkbox
- Added option to prefer energy dissipation in motor for TMC instead of brake resistor
- Added speed limiter axis option
- Added basic translation function
- Fixed CS selection in SPI buttons
- Added axis output torque to FX live graph