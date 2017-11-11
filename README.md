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

- user documentation
- code comments
- unit tests
- custom scene creation
- automatic initial state update (get each device's state on start up)
- automatic download of a devices all link database
- store and manage all link version and update when it changes on the device
- ability to modify the all link database on each device
- automatically link devices to the modem including all groups (like the smoke bridge)
- logging control
- configuration file and database saving location control
- pip packaging
- possible device discovery

## Setup

Create a virtual env with Python 3 (I happen to use miniconda for
this) and install the dependencies from requirements.txt.

Edit the config.yaml file and list the Insteon devices by type and
address.  There is no automatic device discovery.  Devices must be
linked both ways (as a controller and responder) to the PLM modem
(this will not be required in the final version).

Run the run.py script.  Subscribe to the topic's defined in the
config.yaml file and press some buttons to see the Insteon data flow.
To get full scene support, devices must have a local copy of the
database.  Right now that requires a specific command like this to be
sent for each device (this will be automated in the near future):

```
   mosquitto_pub -t 'insteon/set/44.a3.79' -m '{"getdb": 1}'
```

When each device has a local database, it will automatically notify
each device in the scene when it's triggered to update it's state and
send out an MQTT message.