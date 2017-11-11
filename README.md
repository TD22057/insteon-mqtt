# Insteon PLM <-> MQTT bridge

This is a Python 3 package that communicates with an Insteon PLM modem
(USB and serial) and converts Insteon state changes to MQTT and MQTT
commands to Insteon commands.  It allows an Insteon network to be
integrated into and controlled from anything that can use MQTT.

My initial intent with this package is better integrate Insteon into
HOme Assistant.

## Current Status

This is currently under development.  Here's what works so far:

- basic Insteon devices (dimmers, on/off modules, modem, smoke bridge)
- download all link database (scenes) from each device and store locally
- convert Insteon state changes to MQTT
- convert MQTT commands to Insteon commands
- correctly update all devices in a scene (and send MQTT) when the scene is triggered.
- send remote commands (get db, refresh state) to devices via MQTT

Things remaining to do:

- documentation
- unit tests
- automatic initial state update (get each device's state on start up)
- automatic download of a devices all link database
- store and manage all link version and update when it changes on the device
- ability to modify the all link database on each device
- automatically link devices to the modem including all groups (like the smoke bridge)
- logging control
- configuration file and database saving location control
- pip packaging

