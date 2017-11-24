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

- basic Insteon devices (dimmers, on/off modules, modem, smoke bridge,
  motion sensors)
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
- unit tests
- more devices: mini-remotes, door sensors, leak sensors, keypads, thermostats,
  fanlincs, etc.
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
- heal network command (remove all db records for missing devices)
- remove device command (remove device from all db records)
- add erase_db function to devices and modem.


## Setup

Create a virtual env with Python 3 (I happen to use miniconda for
this) and install the dependencies from requirements.txt.

Edit the config.yaml file and list the Insteon devices you have by
type and address.  There is no automatic device discovery at this
time.  Devices must already be linked both ways (as a controller and
responder) with the PLM modem (this will not be required in the final
version).

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

These examples assume the state reporting topic is 'inteon/state' and
the input command topic is 'insteon/set' (those can be changed in the
configuration file).  Device addresses are AA.BB.CC which are the 6
digit hex device address codes.  Address can be input spaces, commas,
or decimal separators and are case insensitive.

All devices support the following commands:
  - 'refresh' will ping the device, update the device's internal state
    (on level, on/off, etc) and check the all link database for
    changes.
  - 'get_db' will cause the device to re-download it's all link database.

### PLM Modem

Configuration file setup for the modem:

```
    port: "/dev/insteon"
    storage: "/var/lib/insteon-mqtt"
    startup_refresh: True
    address: 44.85.11
```

Input commands can be sent to the modem to download it's all link
database or remove and reload the database for every device.

```
   Topic: insteon/set/AA.BB.CC
   Payload:
      'refresh'
      'reload_all'
      'get_db'
      'set_btn'
```


### Dimmers

Configuration file setup for a dimmer:

```
    - dimmer:
        name: "switch 1"
        address: 48.3d.46
```

State change messages get published whenever the device changes state.

```
   Topic: insteon/state/AA.BB.CC
   Payload: { "level" : LEVEL }
```

Input commands can be sent to the device to turn it on or off, change
the dimmer level, refresh the state, or download it's database

```
   Topic: insteon/set/AA.BB.CC
   Payload:
      'ON' or 'OFF'
      'UP' or 'DOWN'
      { "cmd" : "set", "level" : LEVEL }
      'refresh'
      'get_db'

   Example command line:
      mosquitto_pub -t 'insteon/set/48.b0.ad' -m '{"cmd":"set", "level":128}'
```


### On/Off Modules

Configuration file setup for an on/off module:

```
    - on_off:
        name: "switch 1"
        address: 48.3d.46
```

State change messages get published whenever the device changes state.

```
   Topic: insteon/state/AA.BB.CC
   Payload: 'ON' or 'OFF'
```

Input commands can be sent to the device to turn it on or off, refresh
the state, or download it's database

```
   Topic: insteon/set/AA.BB.CC
   Payload:
      'ON' or 'OFF'
      'refresh'
      'get_db'
```


### Motion Sensors


Configuration file setup for an on/off module:

```
    - motion:
        name: "Front door"
        address: 48.3d.46
```

State change messages get published whenever the device changes state.

```
   Topic: insteon/state/AA.BB.CC
   Payload: 'ON' or 'OFF'
```

Input commands can be sent to the device to refresh the state, or
download it's database These commands only work if the device is awake
(recently triggered or in all link mode) since batter operated devices
do not listen for arbitrary input commands.

```
   Topic: insteon/set/AA.BB.CC
   Payload:
      'refresh'
      'get_db'
```


### Smoke Bridge


Configuration file setup for a smoke bridge module:

```
    - smoke_bridge:
        name: "Smoke"
        address: 48.3d.46
```

State change messages get published whenever the device changes state.
The condition string will be one of: 'smoke', 'CO', 'test', 'clear',
'low battery', 'error', 'heartbeat'.

```
   Topic: insteon/state/AA.BB.CC
   Payload: { "condition" : CONDITION }
```

Input commands can be sent to the device to refresh the state, or
download it's database

```
   Topic: insteon/set/AA.BB.CC
   Payload:
      'refresh'
      'get_db'
```



## Thanks

Thanks to [Insteon terminal](https://github.com/pfrommerd/insteon-terminal),
without the work that went into that repo, it would have taken me
forever to get this to work.  I learned all of the command protocols
and database managemenet commands from inspecting that code.
