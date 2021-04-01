# User Interfaces

There are three possible user interfaces to Insteon-MQTT the _command line_, the _WebGUI_, or _MQTT messages_.

## Command Line

To command devices, you can use the command line tool:
  ```
  insteon-mqtt config.yaml on AA.BB.CC
  ```

Run `insteon-mqtt -h` to see all the commands that can be sent and for help with those commands.  For example `insteon-mqtt on -h` will give you help with the `on` command.

Commands entered in the command line will produce nice human readable responses.

## WebGUI
The WebGUI is __only available to those who installed Insteon-MQTT as a HomeAssistant Addon__.  The WebGUI, is accessible from the Add-on page via the __Open Web UI__ button.  Once you click this button you will get a brief notice about how to use the WebGUI.

All of the standard Command Line functions that you see documented for Insteon-MQTT can be used in the WebGUI.

> The prefix `insteon-mqtt config.yaml` will be added to all of your commands, you do not need to type this information.

  - Type `-h` to get a list of commands.
  - For example to join a device named `hallway light` you would type
    `join 'hallway light'` and hit enter.

The WebGUI will provide nice human readable outputs.

## MQTT Messages

Commands can be sent to the command topic for the device.  For example, to turn on a light, use the following mqtt message.

  ```
  Topic: insteon/command/aa.bb.cc
  Payload: { "cmd" : "on" }
  ```

MQTT messages can be sent using the command line application `mosquitto_pub`:
   ```
   mosquitto_pub -t 'insteon/command/AA.BB.CC' -m '{ "cmd" : "on" }'
   ```

Run `mosquitto_pub -h` for help with the command.

> Commands sent via MQTT messages will not produce nice user friendly output.  You will have to monitor your log output to see the result of the command.

> Note the `session` function could be used to get the output.
