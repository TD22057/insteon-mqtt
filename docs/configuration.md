# Configuring Insteon-MQTT

## Basic Configuration - Good for 95% of Users

The following is the bare minimum of changes to the `config.yaml` file that are necessary to get Insteon-MQTT started.

1. __Configure Modem__ Set the Insteon port as `port` under the `insteon` section to be the USB port or address of the PLM modem on your system.  If using an Insteon Hub, see [Hub Instructions](hub.md).

2. __Config Devices__ Edit the `insteon` -> `devices` section and enter the hex addresses of all the devices you have under the appropriate device types.

3. __Configure MQTT Broker__ Under the `mqtt` section, set `broker` to the broker IP or domain name, and the `port` to the proper port.  If you have installed the moquitto broker locally, you may not need to alter anything here.  You can also set the `username` and `password` if necessary.

## Advanced Configuration - Generally not needed by most users

#### `insteon` -> `storage` - device storage folder

The device storage folder contains a json file for each device that is used to cache the various values on the device, most importantly it contains a cache of the device link database. Everything in this folder can be recreated by querying the device. There is no need to backup these files.  Generally, most users should __not__ edit these files.

#### `mqtt` - device templates

Insteon-MQTT uses Jinja2 templates for the greatest interoperability.  Each device category `modem`, `modem`, `switch`, `dimmer`, ... uses templates for defining the mqtt topic and payload for each message type.  See [Templating](templating.md) for help with Jinja2 templates.

#### Device Specific Configuration Settings
See [Device Specific Configuration Settings](config_extra.md)
