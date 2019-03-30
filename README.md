# Insteon PLM <-> MQTT bridge

This is a Python 3 package that communicates with an Insteon PLM modem
(USB and serial) and converts Insteon state changes to MQTT and MQTT
commands to Insteon commands.  It allows an Insteon network to be
integrated into and controlled from anything that can use MQTT.

My initial intent with this package is better integrate Insteon into
Home Assistant and make it easier and more understandable to add new
features and devices.

Version: 0.6.8  ([History](HISTORY.md))

### Breaking changes from last version:

- KeypadLinc now supports both dimmer and on/off device types.  This required
  changing the KeypadLinc inputs in the MQTT portion of the config.yaml file.
  See the file in the repository for the new input fields. ([Issue #33][I33]).


# Quickstart

Blah, blah, blah, too much reading, how do I use it?  [Read the quick
start guide](docs/quick_start.md)

Using hassio? [Read the hass.io quick start guide](docs/hassio_quick_start.md)


# Overview

The bridge runs as a server listening to an MQTT broker and to a
serial/USB/network connection to an Insteon PLM modem.  Devices must
be set up in the input configuration file for the system to understand
what they are and how to interpret messages from them.


# Supported Features

- Command Insteon devices using MQTT messages.  Topics and payloads
  can be customized using Jinja templates.
- Simulate button presses using MQTT messages (device scene triggering).
- Report Insteon device states changes by MQTT messages.  Topics and
  payloads can be customized using Jinja templates.
- Report state changes for any device in an Insteon scene when the
  scene is triggered.
- Currently supported Insteon devices
  - On/off switches (lamp modules, appliance modules, etc.)
  - Dimmer switches (lamp modules, dimmer switches, etc.)
  - On/off outlets
  - FanLinc dimmer and fan controller
  - KeypadLinc on/off and dimmer and scene controller
  - IOLinc relay and sensor module
  - Mini-remotes (4 and 8 button battery powered scene controllers)
  - Battery powered sensors (door, hidden door, window, etc.)
  - Leak sensors
  - Motion sensors
  - Smoke bridge
  - Thermostats
- Automatically link new devices to the modem.  The system will
  correctly link all the Insteon groups for a device (like the smoke
  bridge which has 7 groups).
- Link devices to the modem and each other via MQTT commands or the
  command line tool.
- Add and delete entries from the modem and device all link databases.
- Command line tool for simpler sending of MQTT messages to send to
  the server.
- Automatically attempt to download the all link database from battery
  powered devices when a message is seen from them (i.e. trip a motion
  sensor or push a remote button to get it to download the database).
- Trigger modem virtual scenes
- Automatic inbound message de-duplication.


# Detailed Documentation

- Each device supports and publishes a different set of MQTT commands.
  Consult the [device documentation page](docs/mqtt.md) for details
  on each those commands.

- [Full system install and automatically starting the server](docs/auto_start.md) on startup.

- [Development Guide](docs/CONTRIBUTING.md)


# Future Work

There is still more work to do and here are a some of my plans for
future enhancements:

- Full suite of unit tests.
- YAML input configuration validation.
- Heal network (remove records for missing devices, fix missing links).
- Modem and device scene management.  Define all the links (scenes) in
  a configuration file and have the system push that information to the
  devices.  Eliminates the need to do any manual linking of devices and
  serves as a backup of the Insteon network and scenes.


# Thanks

Thanks to [Insteon terminal](https://github.com/pfrommerd/insteon-terminal),
without the work that went into that repo, it would have taken me
forever to get this to work.  I learned all of the command protocols
and database managemenet commands from inspecting that code.
