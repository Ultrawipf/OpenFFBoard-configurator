### Changes this version:
- Fixed effect monitor windows not opening after reconnect if disconnected while window was open
- Added support for serial FFB mainclass (opens regular FFB mode tabs)
- Added option do disable update notifications (Can be enabled/disabled in release browser and update popups)
  - This resets your profile file because it adds a new global settings section. You can migrate profile settings by copying the "profiles" section from profiles.json.1.old to the new profiles.json