# Insteon PLM <-> MQTT bridge

This is a Python 3 package that communicates with an Insteon PLM modem
(USB and serial) and converts Insteon state changes to MQTT and MQTT
commands to Insteon commands.  It allows an Insteon network to be
integrated into and controlled from anything that can use MQTT.

My initial intent with this package is better integrate Insteon into
Home Assistant and make it easier and more understandable to add new
features and devices.

## Current Status

This is currently under development.  Here's what works so far:

- basic Insteon devices (dimmers, on/off modules, modem, smoke bridge)
- download all link database (scenes) from each device and store locally
- refresh device state on startup and download all link database if changes
  occurred.
- convert Insteon state changes to MQTT
- convert MQTT commands to Insteon commands
- correctly update all devices in a scene (and send MQTT) when the scene is
  triggered by the device.
- send remote commands (get db, refresh state) to devices via MQTT
- correctly handle commands arriving while db is being downloaded

Things remaining to do:

- user documentation (github)
- code comments + sphinx html docs
- unit tests
- more devices: mini-remotes, door sensors, leak sensors, keypads, thermostats,
  fanlinks, motion sensors, etc.
- custom scene creation (PLM modem scenes) and scene triggering
- simulate device scenes via MQTT (clicking dimmer button)
- ability to modify the all link database on each device
- automatically link devices to the modem including all groups (like the
  smoke bridge or thermostat)
- logging control
- configuration file and database saving location control
- pip packaging
- possible device discovery
- MQTT payload templates.
- yaml config validator  (voluptuous like HA?)

## Setup

Create a virtual env with Python 3 (I happen to use miniconda for
this) and install the dependencies from requirements.txt.

Edit the config.yaml file and list the Insteon devices by type and
address.  There is no automatic device discovery.  Devices must be
linked both ways (as a controller and responder) to the PLM modem
(this will not be required in the final version).

Set the startup_refresh input to True in config.yaml and run the
run.py script.  Subscribe to the topic's defined in the config.yaml
file and press some buttons to see the Insteon data flow.  To get full
scene support, devices must have a local copy of the database.  When
startup_refresh is true, it will ping each device in the config file
and download the device's database if there is no local copy or if the
local copy is out of date.  This may take a little while the first
time that it's run.

When each device has a local database, it will automatically notify
each device in the scene when it's triggered to update it's state and
send out an MQTT message.

## Supported Devices

### Dimmers

TODO: setup, MQTT commands

### On/Off Modules

TODO: setup, MQTT commands, motion sensors

### Smoke Bridge

TODO: setup, limitations, linking


## Thanks

Thanks to [Insteon terminal](https://github.com/pfrommerd/insteon-terminal),
without the work that went into that repo, it would have taken me
forever to get this to work.  I learned all of the command protocols
and database managemenet commands from inspecting that code.