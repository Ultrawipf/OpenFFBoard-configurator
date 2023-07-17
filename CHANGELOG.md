### Changes this version:
- Added TMC space vector PWM checkbox

### Changes in 1.13.x:
- Fixed issue in encoder tuning UI
- Added SSI encoder ui
- Added PWM direction checkbox
- When a command callback target causes an error it will remove the callback, print a warning and resume instead of aborting.
  - Prevents issues in case a request is sent during a timeout causing empty encoder config fields in rare cases
- Added percentage to power slider
- Added axis selection for effect monitor (new firmware required)


