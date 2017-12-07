# Insteon PLM <-> MQTT bridge

This is a Python 3 package that communicates with an Insteon PLM modem
(USB and serial) and converts Insteon state changes to MQTT and MQTT
commands to Insteon commands.  It allows an Insteon network to be
integrated into and controlled from anything that can use MQTT.

My initial intent with this package is better integrate Insteon into
Home Assistant and make it easier and more understandable to add new
features and devices.

Version: 0.4.0


# Quickstart

Blah, blah, blah, too much reading, how do I use it?  [Read the quick
start guide](doc/quick_start.md)

# Overview

The bridge runs as a server listening to an MQTT broker and to a
serial/USB/network connection to an Insteon PLM modem.  Devices must
be set up in the input configuration file for the system to understand
what they are and how to interpret messages from them.

# Supported Features

- Command Insteon devices using MQTT messages.  Topics and payloads
  can be customized using Jinja templates.
- Report Insteon device states changes by MQTT messages.  Topics and
  payloads can be customized using Jinja templates.
- Report state changes for any device in an Insteon scene when the
  scene is triggered.
- Supported Insteon devices (future devices will be easy to add, these
  are just the set I own and can easily test).
  - On/off switches (lamp modules, appliance modules, outlets)
  - Dimmer switches (lamp modules, dimmer switches, etc.)
  - Motion sensors
  - Mini-remotes
  - Smoke bridge
- Automatically link new devices to the modem.  The system will
  correctly link all the Insteon groups for a device (like the smoke
  bridge which has 7 groups).
- Add and delete entries from the modem and device all link databases.
- Command line tool for simpler sending of MQTT messages to send to
  the server.

# Detailed Documentation

- Each device supports and publishes a different set of MQTT commands.
  Consult the [device documentation page](doc/devices.md) for details
  on each those commands.


# Future Work

There is still more work to do and here are a some of my plans for
future enhancements:

- Full suite of unit tests.
- More Insteon devices: door sensors, leak sensors, keypads, fanlincs,
  etc.
- Custom scene creation (software based scenes) and triggering.
- PIP packaging and installation.
- YAML input configuration validation.
- Heal network (remove records for missing devices, fix missing links).
- Modem and device scene management.  Define all the links (scenes) in
  a configuration file and have the system push that information to the
  devices.  Eliminates the need to do any manual linking of devices and
  serves as a backup of the Insteon network and scenes.
