# The `reason` String
Insteon-MQTT tries to track why a device changed state and reports this as `reason`.  The possible values are:
  - `device` if a button was pressed on the device.
  - `scene` if the device is responding to a scene trigger.
  - `refresh` if the update is from a refresh'.
  - `command` if the device is responding to an on/off command.
  - `an arbitrary string` if one was passed in via the scene or on/off style command inputs.

## Templating
The reason string is a value that can be used in [templating](Templating.md). It is not enabled by default.  You will need to edit your `config.yaml` file if you wish to enable `reason` support.

## Why would one use reason?
It can be useful in automations to pass the reason why a device state was changed so that other automations can see and handle the change appropriately.
