# Insteon PLM <-> MQTT bridge

This is a Python 3 package that communicates with an Insteon PLM modem
(USB and serial) or an Insteon Hub and converts Insteon state changes to MQTT and MQTT
commands to Insteon commands.  It allows an Insteon network to be
integrated into and controlled from anything that can use MQTT.

This package works well with HomeAssistant and can be easily [installed as an addon](docs/HA_Addon_Instructions.md) using the HomeAssistant Supervisor.

Version: 1.1.1  ([History](CHANGELOG.md))

### Recent Breaking Changes

- 0.9.1 - A Yaml validation routine was added.  If you have an error in your
  config.yaml file, you will get an error on startup.

# Quickstart

Blah, blah, blah, too much reading, how do I use it?  [Read the quick
start guide](docs/quick_start.md)

Using Home Assistant Supervisor?
[Install Insteon-MQTT as an Add-on](docs/HA_Addon_Instructions.md)

# Documentation

- [Installation Guide](docs/quick_start.md) - Install from the command line
- [Startup Script](docs/auto_start.md) - Running InsteonMQTT on startup.
- [Install as a HomeAssistant Addon](docs/HA_Addon_Instructions.md) - Install in HomeAssistant
  - [Discovery for HomeAssistant](docs/discovery.md) - Automatic entity discovery
  - [Customizing HomeAssistant Entities](docs/discovery_customization_ui.md) - Customizing entities in HomeAssistant
  - [Discovery Overrides](docs/discovery_customization_config.md) - Alter discovery entities using templates and overrides
- [Configuration](docs/configuration.md) - The base configuration requirements
- [Initialize your Devices](docs/initializing.md) - Setting up your Insteon Devices
- [User Interface Options](docs/user_interface.md) - Three available user interfaces.
- [Device Documentation](docs/mqtt.md) - Each device supports and publishes a different set of MQTT commands.
- [Guide to Templating](docs/Templating.md) - A short primer on Jinja templates
- [Scene/Link Management](docs/scenes.md) - Creating links between devices and creating a `scenes.yaml` file
- [Help and Debugging](docs/debugging.md) - Need help?  Look here!

# Overview

The bridge runs as a server listening to an MQTT broker and to a
serial/USB/network connection to an Insteon PLM modem.  Devices must
be set up in the input configuration file for the system to understand
what they are and how to interpret messages from them.

## Supported Devices
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
- Hidden Door sensors
- EZIO4O 4 relay device


## Supported Features

- Command Insteon devices using MQTT messages.  Topics and payloads
  can be customized using Jinja templates.
- Simulate button presses using MQTT messages (device scene triggering).
- Report Insteon device states changes by MQTT messages.  Topics and
  payloads can be customized using Jinja templates.
- Report state changes for any device in an Insteon scene when the
  scene is triggered including normal, fast, and manual modes.
- State changes can be tagged with arbitrary reason strings to allow
  automations to change behavior based on context.
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
- Scene/Link Management
  - Add or delete links on devices from a defined configuration
  - Import scenes defined on the network into a file for backup
- If using HomeAssistant Supervisor, a web based GUI for easy configuration and testing


## Developer Documentations

- [Development Guide](docs/CONTRIBUTING.md)
- [HomeAssistant Supervisor Development](docs/hassio_development.md)
- [Release Delivery Notes](docs/delivery.md)


# Future Work

There is still more work to do and here are a some of my plans for
future enhancements:

- Full suite of unit tests.

# Thanks

Thanks to [Insteon terminal](https://github.com/pfrommerd/insteon-terminal),
without the work that went into that repo, it would have taken me
forever to get this to work.  I learned all of the command protocols
and database managemenet commands from inspecting that code.

# Old Breaking Changes

- 0.8.3 - HomeAssistant version 2021.4.0 now only supports percentages for fan
  speeds.  This means any fan entities in HomeAssistant that were configured
  to use "low", "medium", and "high" for the fan speed will no longer work.
  See [config-example.yaml](https://github.com/TD22057/insteon-mqtt/blob/master/config-example.yaml)
  under the `mqtt -> fan` section for a suggest configuration in
  HomeAssistant.  __Users not using HomeAssistant are unaffected.__
- 0.7.4 - IOLinc, the scene_topic has been elimited, please see the documentation
  for the replaces functionality.
- 0.7.2 - KeypadLinc now supports both dimmer and on/off device types.  This required
  changing the KeypadLinc inputs in the MQTT portion of the config.yaml file.
  See the file in the repository for the new input fields. ([Issue #33][I33]).
