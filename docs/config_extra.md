# Additional Device Specific Configuration Settings
These settings can be set using the following format:
```yaml
insteon:
  devices:
    switch:
      - aa.bb.cc: lamp1
        extra_config: 1
      - 11.22.33: lamp2
```
In this case, `lamp1` would have the value of 1 set for the `extra_config` setting.  This setting __only__ affects `lamp1` and will not affect `lamp2`.

> Device names __must be defined__ to use a device specific configuration.

> Note the indentation and __the lack of a dash__ on the line specifying the device specific configuration entry.

## Settings for Specific Device Types
Some device types have additional settings.

> No such settings yet.

## Settings

### `discovery_class` - Discovery Template Class
This key can be used to define a custom discovery template for this device.
The value of this setting should be a subkey under the `mqtt` key in the yaml
config file.  This subkey must contain a `discovery_entities` list of each of
the discovery entities.  For more details and examples see
[Discovery](discovery.md).

### `discovery_override_class` - Discovery Override Class
Details of this setting can be found in [Discovery Customization in
Insteon-MQTT](discovery_customizaton_config.md).

### `discoverable` - Discovery Control
Details of this setting can be found in [Discovery Customization in
Insteon-MQTT](discovery_customizaton_config.md).

## Advanced Settings
These settings can be used with all device types, but should be considered advanced.  These settings may cause undesirable effects.

### `min_hops` - Minimum Hops
If a specific device frequently takes between 5-15 seconds to respond to a command.  Try setting the `min_hops` for that device to 1.  Restart InsteonMQTT and test out the device.  If there continues to be a delay, `min_hops` can be increased to 2 or 3.  Ideally, you want __the lowest value for `min_hops` that removes the delay.__

For example, the configuration of a device in `config.yaml` could look like:
```yaml
insteon:
  devices:
    switch:
      - aa.bb.cc: lamp1
        min_hops: 1
      - 11.22.33: lamp2
```
In this case, all messages sent to `lamp1` would have a minimum of 1 hops set.  While `lamp2` would continue to use the calculated smart-hops value.

> Setting `min_hops` likely will __not help__ a device that frequently fails to respond to commands at all.

#### Detailed Minimum Hops Explanation
Each message sent _to_ a device has a hops value (between 0 and 3) that defines the number of times the message will be rebroadcast to the network.  InsteonMQTT calculates the optimum hop count by monitoring the number of hops it takes for messages _from_ the device to reach the Modem.

However, in some cases, the hops distance is asymetric in that the amount of hops necessary to _send_ to the device is more than the amount of hops to _receive_ messages from the device.  When this happens, messages sent to this device frequently have to be resent, which may result in a delay of 5-15 seconds for the device to respond.

Setting the `min_hops` value will ensure that InsteonMQTT never uses less than the amount of hops defined when sending a message and should remove the delay in the device response to a command.

>__Be warned__ that setting `min_hops` when it is not needed or setting a value higher than is needed, may cause issues on your Insteon network.  This is because a message may be rebroadcast more than necessary causing delays and congestion, which can cause other devices to fail to respond or can cause corrupted messages.
