# Configuring Insteon-MQTT

## Basic Configuration - Good for 95% of Users

The following is the bare minimum of changes to the `config.yaml` file that are necessary to get Insteon-MQTT started.

1. __Configure Modem__ Set the Insteon port as `port` under the `insteon` section to be the USB port or address of the PLM modem on your system.  If using an Insteon Hub, see [Hub Instructions](hub.md).

2. __Config Devices__ Edit the `insteon` -> `devices` section and enter the hex addresses of all the devices you have under the appropriate device types.

3. __Configure MQTT Broker__ Under the `mqtt` section, set `broker` to the broker IP or domain name, and the `port` to the proper port.  If you have installed the moquitto broker locally, you may not need to alter anything here.  You can also set the `username` and `password` if necessary.

## Advanced Configuration - Generally not needed by most users

#### User Config Overlay of Base Config File

Starting in version 1.0.0 InsteonMQTT now includes a base configuration file which the user configuration file is overlayed over the top.  You should not directly edit the base configuration file, as it will be overwritten during updates.  If you want to change a default setting, simply define the same key in your user configuration file and set your desired value.

You can view the contents of the base configuration file here:
[config-base.yaml](../insteon_mqtt/data/config-base.yaml)

Settings in your user config file will replace those in the base config file pursuant to the following rules:

1. Any unique key found in user_config will be added to the base_config.
2. Any value in user_config that __is not__ an associative array, will be copied to the same key in base_config.
3. Any value in user_config that __is__ an associative array, will be recursively examined applying these same rules.

So for example, assuming the following `base_config` and `user_config` files:

**base_config:**
```YAML
insteon:
  devices:
    switch: []

mqtt:
  broker: example.com
  switch:
    topic: some-topic
    discovery_entities:
      - component: switch
        config: some-config
  dimmer:
    topic: some-topic2
    discovery_entities:
      - component: dimmer
        config: some-config
```

**user_config:**
```YAML
insteon:
  devices:
    switch:
      - aa.bb.cc: my device

mqtt:
  broker: my.broker.com
  switch:
    topic: new_topic
  dimmer:
```

The resulting config file will be:

```YAML
insteon:
  devices:
    switch:
      - aa.bb.cc: my device

mqtt:
  broker: my.broker.com
  switch:
    topic: new_topic
    discovery_entities:
      - component: switch
        config: some-config
  dimmer:
```

#### `insteon` -> `storage` - device storage folder

The device storage folder contains a json file for each device that is used to cache the various values on the device, most importantly it contains a cache of the device link database. Everything in this folder can be recreated by querying the device. There is no need to backup these files.  Generally, most users should __not__ edit these files.

#### `mqtt` - device templates

Insteon-MQTT uses Jinja2 templates for the greatest interoperability.  Each device category `modem`, `switch`, `dimmer`, ... uses templates for defining the mqtt topic and payload for each message type.  See [Templating](templating.md) for help with Jinja2 templates.

#### Device Specific Configuration Settings
See [Device Specific Configuration Settings](config_extra.md)
