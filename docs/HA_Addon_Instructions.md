# Insteon-MQTT Quick Start for Home Assistant users

## Prerequisites

These instructions assume that you:

- Have a Home Assistant installation with Home Assistant Supervisor up and
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
9. Edit `/config/insteon-mqtt/config.yaml` as appropriate.

   - Set the Insteon port to be the USB port or address of the PLM modem OR
     if using an Insteon Hub set its address, username, and password.
   - Set the modem Insteon hex address (printed on the back of the modem).
   - Edit the Insteon device section and enter the hex addresses of all
     the devices you have.

10. Restart the insteon-mqtt addon to pick up the changes.
11. Join and Pair each device in your network.  This can be accomplished
    using the Web Command Line interface, which is accessible from the Add-on
    page via the __Open Web UI__ button.

    - Type `-h` to get a list of commands.
    - You do not need to type the `insteon-mqtt config.yaml` portion, that will
    be added for you.
    - For example to join a device named `hallway light` you would type
    `join 'hallway light'` and hit enter.  To pair the same device you would
    type `pair 'hallway light'`.
    - Do this for all of your devices.
12. Edit your Home Assistant configuration to add your devices as MQTT devices
    to Home Assistant.  In the __mqtt__ section of the initial config.yaml
    file, there are examples of Home Assistant configurations for each device
    type.
13. See the [command documentation](mqtt.md) for additional commands.

## Backing up your Data

The default settings in the config.yaml file will save all user data to the
`/config/insteon-mqtt` directory.  So you only need to backup and save this
data, you do not need to make a snapshot of the Insteon-MQTT add-on.  This
directory may also contain a log file if you have enabled logging,
be careful, this can get quite large.

## Updating

Check the supervisor page periodically for updates to Insteon-MQTT

## Questions

If you have questions, please look on the
[Discussions](https://github.com/TD22057/insteon-mqtt/discussions) page
to see if it has been asked and answered before.  If not, feel free to ask.

## Issues

If you have found a bug, or wish to request a new feature, please look on the
[Issues](https://github.com/TD22057/insteon-mqtt/issues) page to see if the
issue or feature request has been already identified.  If not, feel free to
add it.
