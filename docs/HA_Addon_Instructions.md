# Quick Start for Home Assistant users

## Prerequisites

These instructions assume that you:

- Have a Home Assistant installation with Home Assistant __Supervisor__ up and
  running.  Installing using the instructions in the Home Assistant
  [Getting Started Guide](https://www.home-assistant.io/getting-started/)
  or the slightly more advanced
  [Recommened Installation Methods](https://www.home-assistant.io/docs/installation/#recommended)
  will work.  The advanced
  [Home Assistant Supervised](https://github.com/home-assistant/supervised-installer)
  installation should also work as well.

- Have a working MQTT broker up and running.
  [Mosquitto](https://mosquitto.org/) is good choice, and there is [an add-on
  for Home Assistant](https://www.home-assistant.io/addons/mosquitto/) that
  makes installation simple.

- Have an Insteon PLM modem (serial or USB) or an Insteon HUB on a fixed IP
  address.

## Installation

1. Navigate in Home Assistant frontend to __Supervisor -> Add-on Store__
2. Select the menu in the top right and click __Repositories__
3. Paste the following URL into the __Add Repository__ field:
   `https://github.com/TD22057/insteon-mqtt`
4. Click __ADD__
5. Scroll to find the __Insteon MQTT Repository__
6. Click on the __Insteon MQTT__ Add on
7. Click __Install__
8. Click __Start__ to start the Add-on, this will create your initial config
   files.
9. Edit `/addon_configs/83fc19e1_insteon-mqtt/config.yaml` using the VSCode or
   SSH Addon as appropriate (see [Where Are My Files](#where-are-my-files)).
   See [configuration](configuration.md) for detailed instructions.
10. Enable the [Discovery Platform](discovery.md)

> Alternatively, if you choose to define your entities in Home Assistant
> manually instead of using the Discovery Platform, see [Home Assistant yaml
  config](HA_yaml_config.md)

11. Restart the insteon-mqtt addon to pick up the changes to the `config.yaml` file.
12. If you navigate in Home Assistant to __Configuration -> Integrations -> MQTT__ you should see your devices and entities.
13. Initialize your devices as discussed in [initializing](initializing.md).
14. See the [device documentation](mqtt.md) for additional commands.

## Where Are My Files

The Insteon-MQTT config files, device database, and log file are stored in
the addon's own configuration directory.  The same directory has a different
path depending on where you are looking from:

| Where you are looking from      | Path                                     |
|---------------------------------|------------------------------------------|
| VSCode Addon or SSH Addon       | `/addon_configs/83fc19e1_insteon-mqtt/`  |
| Inside the Insteon-MQTT addon   | `/config/`                               |

Paths written in your `config.yaml` file (such as `storage`, `scenes`, or the
log `file`) are read by the Insteon-MQTT addon, so they should use the
`/config/` form, e.g. `/config/scenes.yaml`.

> __Note:__ The `/config/` directory inside the Insteon-MQTT addon is __not__
> the Home Assistant `/config` directory (where `configuration.yaml` lives).

### Older Installations

Prior versions of the addon stored files in the Home Assistant config
directory at `/config/insteon-mqtt/` (`/homeassistant/insteon-mqtt/` within
the VSCode or SSH Addon).  On upgrade, these files are automatically moved to
the new location and a `CONFIG-MOVED.txt` file is left behind in the old
directory.  Once Insteon-MQTT is running correctly, the old directory can be
deleted.

## Backing up your Data

The default settings in the config.yaml file will save all user data to the
addon's config directory described above.  This directory is backed up when
you make a snapshot of the Insteon-MQTT add-on.  This directory may also
contain a log file if you have enabled logging, be careful, this can get
quite large.

## Updating

Check the supervisor page periodically for updates to Insteon-MQTT

## Additional Resources

- [User Interfaces](user_interface.md) for information on how to interact with Insteon-MQTT

- [Debugging](debugging.md) for information on how to diagnose problems.

- [Device documentation](mqtt.md) for information on
  device configuration and available MQTT commands and options.
