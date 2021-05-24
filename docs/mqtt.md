# Overview

The system is designed to accept several types of MQTT commands as
inputs and publish several types of MQTT packets as outputs.  Inputs
can be management commands or state changes.  Outputs will be state
change notifications.

Management commands are commands that manage the state of the system
like modifying the all link database on a device and in general, won't
be needed that often.  Management commands have a fixed MQTT topic
(set in configuration file input cmd_topic) and fixed JSON payload
format.

State changes can be inputs to the devices in the network (e.g. turn
a light off, set a dimmer to 50%) or outputs from the system as
notifications (e.g. motion sensor triggered, light is now at 50%).
State change command and notification topics and payloads are totally
configurable.  Each device type in the configuration file has a topic
and payload template that allows you to customize how state changes
are input and output from the system.

## Addressing

The Insteon six digit hex code address of a device is it's identifier.
An optional name (set in the config file) can also be used.  MQTT
topics are case sensitive so all Insteon hex addresses must be entered
in lower case format (e.g. "a1.b2.c3", not "A1.B2.B3").  The modem can
be identified by it's address or the string "modem".

   - [Battery Sensors](#battery-sensors)
   - [Dimmers](#dimmers)
   - [FanLinc](#fanlinc)
   - [Hidden Door Sensors](#hidden-door-sensors)
   - [IOLinc](#iolinc)
   - [KeypadLinc](#keypadlinc)
   - [Leak Sensors](#leak-sensors)
   - [Motion Sensors](#motion-sensors)
   - [Outlets](#outlets)
   - [Remotes](#remote-controls)
   - [Smoke Bridge](#smoke-bridge)
   - [Switches](#switches)
   - [Thermostat](#thermostat)

## Required Device Initialization
> See [device initialization](initialization.md) for a discussion about the steps required when setting up a new or factory reset device.

## Management commands

Management commands can be sent by using the command line tool
"insteon-mqtt" or by publishing a MQTT message to the command topic
(cmd_topic in the config file).  Management commands may be supported
by the modem, by the devices, or by both.  For examples of the command
style, see [command line module source code](../insteon_mqtt/cmd_line).

All management commands use a payload that is a JSON dictionary.  In the
documentation below, if a key/value pair is enclosed in square
brackets [], then it's optional.  If a value can be one of many like
true or false, then the possible values are separated by a slash /.

The MQTT topic to publish management commands to is (aa.bb.cc is the
example device address):

   ```
   insteon/command/aa.bb.cc
   ```

Alternatively you can use the nice names from the config.yaml file too:

   ```
   insteon/command/NICE NAME
   ```

### Print the Version of Insteon-MQTT

Supported: modem

If requesting help or submitting a bug, you can use this command to get the
version of Insteon-MQTT that you are running:

  The default topic location is:

  `insteon/command/modem`

  ```
  { "cmd" : "version"}
  ```

This command can also be run from the command line:

  ```
  insteon-mqtt -v
  ```

### Join a New Device to the Network

Supported: devices

See [initialization](initializing.md) for a discussion of `join`.

### Join all devices

Supported: modem

See [initialization](initializing.md) for a discussion of `join-all`.

### Pair a Device to the Modem

Supported: devices

See [initialization](initializing.md) for a discussion of `pair`.

### Pair all devices

Supported: modem

See [initialization](initializing.md) for a discussion of `pair-all`.

### Sync Device Links

Supported: modem, device

See [scenes](scenes.md) for a detailed description of `sync`.

### Sync All Device Links

Supported: modem

See [scenes](scenes.md) for a detailed description of `sync_all`.

### Import Device Links

Supported: modem, device

See [scenes](scenes.md) for a detailed description of `import_scenes`.

### Import All Device Links

Supported: modem

See [scenes](scenes.md) for a detailed description of `import_scenes_all`.

### Activate all linking mode

Supported: modem, devices

This turns on all linking mode and is the same as pressing the set
button for 3 sec on the modem or device.  The default group is 1.

This command is not normally needed by most users.  However, if you are
experiencing difficulty with the 'join' or 'pair' commands, this command can be
used to solve those issues.

For example, this can be used in place of the 'join' command.  To do this
use the linking command in place of physically pressing the set button on the
device.  So first run 'linking modem', then second run 'linking aa.bb.cc' to
setup a link to control the device from the modem.

Similarly, this can also be used in place of the 'pair' command. To do this
first run 'linking aa.bb.cc', then run 'linking modem' to make the device a
controller of the modem so the modem will get state change messages from the
device.  For more complicated devices, you can also link the other groups on
the device as well.

The command payload is:

   ```
   { "cmd" : "linking", ["group" : group] }
   ```

Once you run the linking command, you should also run 'refresh' on the device
to update it's local database.  The modem will automatically update, but the
devices don't send a message when the linking is complete so there is no way
to know when to update the database.


### Refresh the device state and download it's all link database

Supported: modem, devices

See [initialization](initializing.md) for a discussion of `refresh`.

### Refresh all devices

Supported: modem

See [initialization](initializing.md) for a discussion of `refresh-all`.


### Get device model information

Supported: device

Will send a command to the device to get the device category, sub-category,
and firmware version.  This information may be used to determine what
features are available on the device:

  ```
  { "cmd" : "get_model" }
  ```


### Get device engine information

Supported: device

The engine version can be i1, i2, or i2cs.  The engine version defines what
type of messages can be used with a device and the type of all link database
used by a device.

New Insteon devices purchased after 2018 are almost certainly all i2cs devices.
By default, we assume a device is i2cs.

If you have an older device that is not responding the the refresh command try
running get_engine and then try running refresh again.  This only needs to be
run once on any device.  The resulting information will be saved in the device
data.

  ```
  { "cmd" : "get_engine" }
  ```

### Get all device engines

Supported: modem

This will cause a get_engine command to be sent to each device (i.e. devices
defined in the config file).  The command payload is:

  ```
  { "cmd" : "get_engine_all"}
  ```

### Add the device as a controller of another device.

Supported: modem, devices

This commands modifies the all link database on the device to add it as a
controller of another device.  If the two-way flag is set (true is the
default), it will also modify the other device database to have an entry as
the responder of the first device.  There is a group input (1-255) of the
Insteon group number to use for the each end.  The controller group is the
button being pressed.  The responder group is the button that should respond.
The command payload is:

   ```
   { "cmd" : "db_add_ctrl_of", "local_group" : ctrl_group,
     remote_addr" : aa.bb.cc, "remote_group" : resp_group,
     ["two_way" : true/false], [refresh" : true/false],
     ["local_data" : [D1,D2,D3]], ["remote_data" : [D1, D2,D3]] } }
   ```

### Add the device as a responder of another device.

Supported: modem, devices

This commands modifies the all link database on the device to add it as a
responder of another device.  If the two-way flag is set (true is the
default), it will also modify the other device database to have an entry as
the controller of the first device.  There is a group input (1-255) of the
Insteon group number to use for the each end.  The controller group is the
button being pressed.  The responder group is the button that should respond.
The command payload is:

   ```
   { "cmd" : "db_add_resp_of", "local_group" : resp_group,
     remote_addr" : aa.bb.cc, "remote_group" : ctrl_group,
     ["two_way" : true/false], [refresh" : true/false],
     ["local_data" : [D1,D2,D3]], ["remote_data" : [D1, D2,D3]] } }
   ```


### Delete the device as a controller of another device.

Supported: modem, devices

This commands modifies the all link database on the device to remove
it as a controller of another device.  If the two-way flag is set
(true is the default), it will also modify the other device database
to remove the entry as the responder of the first device.  The group
is an integer (1-255) of the Insteon group number to use for the link.
The command payload is:

   ```
   { "cmd" : "db_del_ctrl_of", "addr" : aa.bb.cc, "group" : group,
     ["two_way" : true/false], [refresh" : true/false] }
   ```


### Delete the device as a responder of another device.

Supported: modem, devices

This commands modifies the all link database on the device to remove
it as a responder of another device.  If the two-way flag is set (true
is the default), it will also modify the other device database to
remove the entry as the controller of the first device.  The group is
an integer (1-255) of the Insteon group number to use for the link.
The command payload is:

   ```
   { "cmd" : "db_del_resp_of", "addr" : aa.bb.cc, "group" : group,
     ["two_way" : true/false], [refresh" : true/false] }
   ```

### Change KeypadLinc button LED state.

Supported: KeypadLinc

This command turns the LED on a KeypadLinc button on or off.  This also
toggles the internal state of the button.  So if a button LED is turned off,
the next click of the button will send out an ON command (and vice verse).
Button is an integer in the range [1,8].  In the 6 button version, buttons
1,2 and 7,8 are not commandable and can only be toggled by sending on/off
commands.

   ```
   { "cmd": "set_button_led", "group" : button, "is_on" : true/false }
   ```

### Get and set operating flags.

Supported: devices, modem (get_flags only)

To request the current flag settings on a device:

  ```
  insteon-mqtt config.yaml get-flags aa.bb.cc
  ```

The MQTT format of the command is:

  ```
  { "cmd" : "get_flags"}
  ```

This command gets and sets various Insteon device flags.  The set of
supported flags depends on the device type.  The command line tool accepts an
arbitrary list of "key=value" strings which get sent to the device for
validation.  For example, to change the back light level of a switch:

   ```
   insteon-mqtt config.yaml set-flags aa.bb.cc backlight=0x11
   ```

The MQTT format of the command is:

   ```
   { "cmd" : "set_flags", "KEY" : "VALUE", ... }
   ```

Switch, KeypadLinc, and Dimmer all support the flags:

   - backlight: changes the LED backlight level on the device.  Insteon
     documentation defines the range from 0x11 - 0x7F, however, levels below
     0x11 appear to work on some devices, and levels above 0x7F may also work.
     Switches and dimmers go as low as 0x04 and KeypadLincs go all the way
     down to 0x01. Setting to 0x00 will turn off the backlight, any other
     value will turn on the backlight.
   - on_level: integer in the range 0x00-0xff which sets the on level that will
     be used when the button is pressed.
   - load_attached: 0/1 to attach or detach the load from the group 1 button.
   - follow_mask: 8 bit integer flags - 1 per button.  Requires a group=N
     input as well.  This sets the follow mask for the input group.  When
     that button is pressed, any button with the bit set in this mask will be
     changed to match the state of the button.  This is used for the 6 button
     device to have the groups (1,2) and (7,8) stay in sync.
   - off_mask: 8 bit integer flags - 1 per button.  Requires a group=N input
     as well.  This sets the off mask for the input group.  When that button
     is pressed, all the buttons with the bits set in this mask will turn
     off.  This is used to implement radio buttons.
   - signal_bits: 8 bit integer flags - 1 per button.  Only used for
     non-toggle buttons.  If a bit is 1, then the button only sends on
     commands.  If a bit is 0, then the button only sends off commands.
   - nontoggle_bits: 8 bit integer flags - 1 per button.  If a bit is 1, then
     that button is a non-toggle button and will only send a signal per the
     signal_bits input.  If a bit is 0, then that button is a toggle button
     and will alternate on an doff signals

  KeypadLinc and Dimmer support the flags:

   - ramp_rate: float in the range of 0.5 to 540 seconds which sets the default ramp
     rate that will be used when the button is pressed
   - resume_dim: bool indicating if the device's on level should be determined from
     the configured on_level flag, or based on the last on level (currently this will
     only effect manually pressing the button and not commands send through insteon-mqtt)

IOLinc supports the flags:

   - mode: "latching" / "momentary-a" / "momentary-b" / "momentary-c" to
     change the relay mode (see the IOLinc user's guide for details)
   - trigger_reverse: 0/1 reverses the trigger command state
   - relay_linked: 0/1 links the relay to the sensor value
   - momentary_secs: .1-6300 the number of seconds the relay stays closed in
          momentary mode.  There is finer resolution at the low end. Higher
          values will be rounded to the next valid value. Setting this to 0
          will cause the IOLinc to change to latching mode. Setting this to
          a non-zero value will cause the IOLinc to change to momentary mode.

Motion Sensors support the flags:

   - led_on: 0/1 - Should led on the device flash on motion?

   - night_only: 0/1 - Should motion only be reported at night?

   - on_only: 0/1 - Should only on motions be reported with no off messages?

   - timeout: seconds between state updates (30 second increments, 2842
     models allow between 30 seconds to 4 hours, the 2844 models allow
     between 30 seconds and 40 minutes).

   - light_sensitivity: 1-255:  Amount of darkness required for night
     to be triggered.  Affects night_only mode as well as the dawn/dusk
     reporting

### Print the current all link database.

Supported: modem, devices

This command is mainly used from the command line tool and allows printing of
the current all link database for a device.

   ```
   { "cmd": "print_db" }
   ```


### Scene triggering.

Supported: devices

This command triggers scenes from a device, as though the button on the
device has been pressed.  The group is the button number and this will
simulate pressing the button on the device.  This will cause all linked
responders to react to the ON/OFF command. The reason field is optional and
will be passed through to the output state change payload, see [reason](reason.md).

Args:
- group = Will default to 1 and can generally be omitted for most devices.
- is_on = True or False.  This defines whether linked devices are sent an
on or an off command.  The target device will treat off as level = 0x00 and
on as the level defined on the device on_level unless level is passed.
- level = If present, the target device will change to this on_level
- reason = Will be passed through to the output state, defaults to 'device' See [reason](reason.md)

   ```
   { "cmd": "scene", "group" : group, "is_on" : 0/1, ["level": 0-255],
   ["reason" : "..."] }
   ```

Supported: modem

For the modem, this triggers virtual modem scenes (i.e. any group number
where the modem is the controller).  The modem also allows the triggering
of scenes from a name defined in a [Scene Management](scenes.md) file as
well. To access a scene by its name simply drop the group attribute and add
the name attribute such as.

Args:
- Same as the device args, but modem does __not__ support the level command

```
{ "cmd": "scene", "name" : "test_scene", "is_on" : 0/1, ["reason" : "..."] }
```


### Mark a battery device as awake.

Supported: battery devices only

Please see [Battery Devices](battery_devices.md) for information about the `awake` command.

### Force a Battery Voltage Check

Supported: Remote and Motion only

The next time the device is awake, this will send a request for the battery
voltage.  If it is low, it will trigger an event on the low_voltage topic.

  ```
  { "cmd": "get_battery_voltage" }
    ```


### Set the Low Battery Voltage

Supported: Motion only

Sets the value at which the battery in the device will be determined to be
low.  Only used on devices that support battery voltage checks and have
removable batteries.  Which is currently only the Motion sensor.  The default
low battery voltage for the motion sensor is 7.0.  The normal low voltage
message would have been sent on group 3 when this voltage is reached anyways.

This is useful for those of us using Li-Ion batteries in the motion sensors
which have an initial voltage of 7.8 at best, and a low voltage well below
that of a normal alkaline battery.  When using these batteries, the low
voltage message on group 3 is likely never sent, because the battery is always
below the expected value

  ```
  { "cmd": "set_low_battery_voltage", "voltage": 7.0 }
    ```

### Send a raw insteon command.

Supported: devices

Send a raw insteon command to devices. Any changes as a result of this
command won't be kept in sync automatically, so use this at your risk.
This command is intended to help developing and debugging insteon-mqtt,
and is as low level as it gets. It supports standard and extended direct
messages.

#### Standard Direct message payload

A standard message requires the cmd1 and cmd2 attributes - allowed values are
`0x00` (0) -> `0xFF` (255).

   ```
   { "cmd": "raw_command", "cmd1": 31, "cmd2": 0 }
   ```

#### Extended Direct message payload

To send an extended message, simply provide the data property (a list of numbers).
It's value will be right padded with 0s and trimmed to 14 digits, then converted
to bytes. The allowed values cmd1, cmd2, and elements within the data array are
`0x00` (0) -> `0xFF` (255). The payload also allows specifying the crc type, with
the allowed values of `D14`, `CRC`. If the type is not supplied the data array
will be sent as is without calculating a CRC.

   ```
   { "cmd": "raw_command", "cmd1": 32, "cmd2": 4, data: [], crc_type: "D14" }
   ```

#### Insteon command tables

You can find insteon command tables online; however, they are usually out
dated. Most modern devices (since ~2012) run the i2cs engine, which is an
extension on the i2 engine and updated certain commands to require the 
D14 crc. If you try commands from an old command table and recieve a
response that indicates an invalid checksum for a standard command, you
can try it as an extended command with the D14 checksum.

---

# State change commands

State change commands can be sent by using the command line tool
"insteon-mqtt" or by publishing a MQTT message to the specific command
topic for a device as set in the configuration file.  Devices will
publish state changes using the state topic set in the configuration
file and using the format as defined by the payload templates.

The templates are defined using the Jinja2 package.  Each define (and
command) defines a set of variables that are available for you to use
in the templates.  So there are no real pre-defined topics and
payloads - they are all customizable.

The sample configuration file provided is designed to work with Home
Assistant and contains templates and examples for using it with that
system.  In the future, other example configurations may also be
provided (feel free to send me any).

MQTT topic templates have the following template variables available
for use.  These variables are also available for the payload
templates.

   - 'address' is the Insteon hex code address (a1.b2.c3).
   - 'name' is the name set in the config file or address if none was set.

The input state change payload template must convert the inbound
payload into the format that the device expects.

---

## Switches

On/off switches will publish their on/off state on the state topic
whenever the device state changes.  Switches have only two states: on
and off.

Output state change messages have the following variables defined
which can be used in the templates:

   - 'on' is 1 if the device is on and 0 if the device is off.
   - 'on_str' is "on" if the device is on and "off" if the device is off.
   - 'mode' is the on/off mode: 'normal', 'fast', or instant'
   - 'fast' is 1 if the mode is fast, 0 otherwise
   - 'instant' is 1 if the mode is instant, 0 otherwise
   - 'reason' is the reason for the change.  See [reason](reason.md)

Manual state output is invoked when a button on the device is held down.
Manual mode flags are UP or DOWN (when the on or off button is pressed and
held), and STOP (when the button is released.  Manual template variables are
name, address, and:

   - 'manual_str' = 'up'/'off'/'down'
   - 'manual' = 1/0/-1
   - 'manual_openhab' = 2/1/0

Input state change messages have the following variables defined which
can be used in the templates:

   - 'value' is the message payload (string)
   - 'json' is the message payload converted to JSON format if the
     conversion succeeds.  Values inside the JSON payload can be
     accessed using the form 'json.ATTR'.  See the Jinja2 docs for
     more details.

The input state change payload template must convert the input message into
the format.  The optional mode flag can be used to send a 'normal'
(default)', 'fast', or 'instant' command to the device.

   ```
   { "cmd" : "on"/"off", ["mode" : 'normal'/'fast'/'instant'] }
   ```

The input command can be either a direct on/off command which will just
change the load connected to the switch (using the on_off inputs) or a scene
on/off command which simulates pressing the button on the switch (using the
scene inputs).

Here is a sample configuration that accepts and publishes messages
using upper case ON an OFF payloads.

   ```
   switch:
     # Output state change:
     state_topic: 'insteon/{{address}}/state'
     state_payload: '{{on_str}}'

     manual_state_topic: 'insteon/{{address}}/manual_state'
     manual_state_payload: '{{manual_str.upper()}}'

     # Direct change only changes the load:
     on_off_topic: 'insteon/{{address}}/set'
     on_off_payload: '{ "cmd" : "{{value.lower()}}" }'

     # Scene change simulates clicking the switch:
     scene_topic: 'insteon/{{address}}/scene'
     scene_payload: '{ "cmd" : "{{value.lower()}}" }'
   ```

When the switch changes state a message like `ON` or `OFF` is
published to the topic `insteon/a1.b1.c1/state`.  To command the
switch to turn on, send a message to `insteon/a1.b1.c1/set` with the
payload `ON`.

---

## Dimmers

Dimmers are the same as switches but have an addition field "level"
which sets the dimming level using the range 0->255 (0 is the same as
off and 255 is 100% on).  They will publish their on/off state on the
state topic whenever the device state changes.

Output state change messages have the following variables defined
which can be used in the templates:

   - 'on' is 1 if the device is on and 0 if the device is off.
   - 'on_str' is "on" if the device is on and "off" if the device is off.
   - 'level_255' is the dimmer level in the range 0->255.
   - 'level_100' is the dimmer level in the range 0->100.
   - 'mode' is the on/off mode: 'normal', 'fast', or instant'
   - 'fast' is 1 if the mode is fast, 0 otherwise
   - 'instant' is 1 if the mode is instant, 0 otherwise
   - 'reason' is the reason for the change.  See [reason](reason.md)

Manual state output is invoked when a button on the device is held down.
Manual mode flags are UP or DOWN (when the on or off button is pressed and
held), and STOP (when the button is released.  Manual template variables are
name, address, and:

   - 'manual_str' = 'up'/'off'/'down'
   - 'manual' = 1/0/-1
   - 'manual_openhab' = 2/1/0

Input state change messages have the following variables defined which
can be used in the templates:

   - 'value' is the message payload (string)
   - 'json' is the message payload converted to JSON format if the
     conversion succeeds.  Values inside the JSON payload can be
     accessed using the form 'json.ATTR'.  See the Jinja2 docs for
     more details.

The input state change has two inputs.  One is the same as the switch input
system and only accepts on and off states in either direct or scene mode.
The second is similar but also accepts the level argument to set the dimmer
level.  The dimmer payload template must convert the input message into the
format (LEVEL must be in the range 0->255).  The optional mode flag can be
used to send a 'normal' (default)', 'fast', or 'instant' command to the
device.

   ```
   { "cmd" : "on"/"off", "level" : LEVEL, ["mode" : 'normal'/'fast'/'instant'] }
   ```

Here is a sample configuration that accepts and publishes messages
using a JSON format that contains the level using the tag
"brightness".

   ```
   dimmer:
     # Output state change:
     state_topic: 'insteon/{{address}}/state'
     state_payload: '{ "state" : "{{on_str}}", "brightness" : {{level_255}} }'

     manual_state_topic: 'insteon/{{address}}/manual_state'
     manual_state_payload: '{{manual_str.upper()}}'

     # Input state change for the load:
     on_off_topic: 'insteon/{{address}}/set'
     on_off_payload: '{ "cmd" : "{{json.state}}" }'

     # Scene change simulates clicking the switch:
     scene_topic: 'insteon/{{address}}/scene'
     scene_payload: '{ "cmd" : "{{value.lower()}}" }'

     # Dimming control:
     level_topic: 'insteon/{{address}}/level'
     level_payload: >
        { "cmd" : "{{json.state}}",
          "level" : {{json.brightness}} }

   ```

To change the level of the dimmer with this configuration, publish a
message like this to the level topic for the device:

   ```
   { "state" : "on", "brightness" : 175 }
   ```

---

## FanLinc

A FanLinc device is an Insteon device for controlling a ceiling fan
and light.  The light portion of the FanLinc uses the dimmer settings
(see above).  The fan controller uses a four speed setting system
(off, low, medium, and high).

The fan portion of the device can be turned on and off (where on means
use the last speed setting that was chosen) or set to a specific
level.

Output state change messages have the following variables defined
which can be used in the templates:

   - 'on' is 1 if the device is on and 0 if the device is off.
   - 'on_str' is "on" if the device is on and "off" if the device is off.
   - 'level' is the integer speed level 0-3 for off (0), low (1), medium (2),
      and high (3)
   - 'level_str' is the speed level 'off', 'low', 'medium', or 'high'.
   - 'reason' is the reason for the change.  See [reason](reason.md)

Input state change messages have the following variables defined which
can be used in the templates:

   - 'value' is the message payload (string)
   - 'json' is the message payload converted to JSON format if the
     conversion succeeds.  Values inside the JSON payload can be
     accessed using the form 'json.ATTR'.  See the Jinja2 docs for
     more details.

The input state change has two inputs.  One is the same as the switch
input system and only accepts on and off states.  The second is
similar but also accepts the level argument to set the fan speed.  The
speed payload template must convert the input message into the format
(SPEED must be one of the valid level integers or strings).

   ```
   { "cmd" : "on"/"off" }
   { "cmd" : SPEED }
   ```

Here is a sample configuration.  HomeAssistant starting in version 2021.4.0
dropped support for the off/low/medium/high fan speeds.  See
[config-example.yaml](https://github.com/TD22057/insteon-mqtt/blob/master/config-example.yaml)
in the mqtt -> fan section for an example HomeAssistant config that works
with InsteonMQTT.

   ```
   fan_linc:
     # Output state change:
     fan_state_topic: 'insteon/{{address}}/fan/state'
     fan_state_payload: '{{on_str}}'

     # Input on/off change (payload should be 'ON' or 'OFF')
     fan_on_off_topic: 'insteon/{{address}}/fan/set'
     fan_on_off_payload: '{ "cmd" : "{{value.lower}}" }'

     # Output speed state change.
     fan_speed_topic: 'insteon/{{address}}/fan/speed/state'
     fan_speed_payload: '{{level_str}}'

     # Input fan speed change (payload should be 'off', 'low', 'medium',
     # or 'high'.
     fan_speed_set_topic: 'insteon/{{address}}/fan/speed/set'
     fan_speed_set_payload: '{ "cmd" : "{{value.lower}}" }'
   ```


---

## KeypadLinc

The KeypadLinc is a wall mounted on/off or dimmer control and scene
controller.  Basically it combines a on/off or dimmer switch and remote
control.  Dimmers and on/off devices are listed under separate entries in the
input config file which controls the behavior of the group 1 switch.  The
other buttons are treated as on/off switches (see the switch documentation
above) but have no load connected to them.  KeypadLincs are usually
configured as 6 button or 8 button devices with the following button number
layouts:

```
   6 button         8 button
   ---------        --------
     1 on           1      2
   3       4        3      4
   5       6        5      6
     1 off          7      8
```

The button change defines the following variables for templates:

   - 'button' is 1...n for the button number.
   - 'on' is 1 if the button is on, 0 if it's off.
   - 'on_str' is 'on' if the button is on, 'off' if it's off.
   - 'mode' is the on/off mode: 'normal', 'fast', instant', or 'ramp'
   - 'fast' is 1 if the mode is fast, 0 otherwise
   - 'instant' is 1 if the mode is instant, 0 otherwise
   - 'transition' is the ramp rate in seconds.
   - 'reason' is the reason for the change.  See [reason](reason.md)

The optional transition flag can be used to specify a ramp rate.  If 'ramp'
mode is specified but no transition value, a ramp rate of 2 seconds is used.
If a transition value is specified but no mode, 'ramp' mode is implied.
Ramp mode is only supported on 2334-222 and 2334-232 devices at this time.

   ```
   { "cmd" : "on"/"off", "level" : LEVEL, ["mode" : 'normal'/'fast'/'instant'/'ramp'], "transition" : RATE }
   ```

Note: RATE is specified as a number of seconds and is rounded down to the
nearest supported Half Rate.  Note that not all devices support ramp rates
and that specifying one will limit the precision of LEVEL.
See http://www.madreporite.com/insteon/ramprate.htm for more details on the
"Light ON at Ramp Rate" and "Light OFF at Ramp Rate" commands.

Manual state output is invoked when a button on the device is held down.
Manual mode flags are UP or DOWN (when the on or off button is pressed and
held), and STOP (when the button is released.  Manual template variables are
name, address, and:

   - 'manual_str' = 'up'/'off'/'down'
   - 'manual' = 1/0/-1
   - 'manual_openhab' = 2/1/0
   - 'reason' See [reason](reason.md)

A sample remote control topic and payload configuration is:

   ```
   keypad_linc:
     # Output on/off state change:
     btn_state_topic: 'insteon/{{address}}/state/{{button}}'
     btn_state_payload: '{{on_str.upper()}}'

     # Output dimmer state changes.
     dimmer_state_topic: 'insteon/{{address}}/state/1'
     state_payload: '{ "state" : "{{on_str}}", "brightness" : {{level_255}} }'

     manual_state_topic: 'insteon/{{address}}/manual_state/{{button}}'
     manual_state_payload: '{{manual_str.upper()}}'

     # Input on/off state change.  For any button besides 1, this just
     # updates the LED state.
     btn_on_off_topic: 'insteon/{{address}}/set/{{button}}'
     btn_on_off_payload: '{ "cmd" : "{{json.state}}" }'

     # Input dimmer control
     level_topic: 'insteon/{{address}}/set/1'
     level_payload: >
        { "cmd" : "{{json.state}}",
          "level" : {{json.brightness}} }

     # Scene input - simulates clicking the button.
     btn_scene_topic: 'insteon/{{address}}/scene/{{button}}'
     btn_scene_payload: '{ "cmd" : "{{value.lower()}}" }'
   ```

---


## Battery Sensors

Battery powered sensors (which include door sensors, hidden door
sensors, and window sensors) do not accept any input commands.
Internally, they will send state changes on the Insteon groups 1 for
motion and 3 for low battery.  Each of these messages only has two
states, on or off.

The battery powered sensor sends motion events on the "state" configuration
topic which defines the following variables defined which can be used
in the templates:

   - 'on' is 1 if the device is on and 0 if the device is off.
   - 'on_str' is "on" if the device is on and "off" if the device is off.

The low battery condition defines the following variables for
templates:

   - 'is_low' is 1 for a low battery, 0 for normal.
   - 'is_low_str' is 'on' for a low battery, 'off' for normal.

Some battery sensors also issues a heartbeat every 24 hours that can be used
to confirm that they are still working.  Presently, only the Leak sensor is
known to use heartbeat messages. The following variables can be used for
templates:

   - "is_heartbeat" is 1 whenever a heartbeat occurs
   - "is_heartbeat_str" is "on" whenever a heartbeat occurs
   - "heartbeat_time" is the Unix timestamp of when the heartbeat occurred

The Battery Sensor class is also the base for other battery devices that
have additional features, namely Motion Sensors, Leak Sensors, and Remotes.

A sample battery sensor topic and payload configuration is:

   ```
   battery_sensor:
     # Trigger events
     state_topic: 'insteon/{{address}}/state'
     state_payload: '{{on_str.upper()}}'

     # Low battery warning
     low_battery_topic: 'insteon/{{address}}/battery'
     low_battery_payload: '{{is_low_str.upper()}}'

     # Heartbeats
     heartbeat_topic: 'insteon/{{address}}/heartbeat'
     heartbeat_payload: '{{heartbeat_time}}'
   ```

---

## Motion Sensors

Motion sensors do not accept any input commands.  The motion
triggering and low battery are inherited from the battery sensor
inputs.  The motion sensors adds another possible state change for
dawn/dusk (Insteon group 2)

The dawn/dusk change defines the following variables for templates:

   - 'is_dawn' is 1 for dawn, 0 for dusk
   - 'is_dawn_str' is "on" for dawn, "off" for dusk
   - 'is_dusk' is 1 for dusk, 0 for dawn
   - 'is_dusk_str' is "on" for dusk, "off" for dawn
   - 'state' is "dawn" or "dusk"

A sample motion sensor topic and payload configuration is:

   ```
   motion:
     # Light level events
     dawn_dusk_topic: 'insteon/{{address}}/dawn'
     dawn_dusk_payload: '{{is_dawn_str.upper()}}'
   ```

---

## Hidden Door Sensors

Hidden Door sensors do not accept any input commands in their normal "off"
state.  If you press and hold the link button for about 3 seconds it will
beep and its small LED will blink.  It will be awake for about the next 4
minutes where you can download the db and or configure the units many
options.  All configuration option offered by this device are available for
configuration here.  The open/closed (one group) and low battery are
inherited from the battery sensor inputs.  The hidden door sensor adds
another possible state change the 2 groups configuration where it will report
open as ON on group 0x01 and closed as ON on group 0x02.  The raw Insteon
reported battery voltage level is reported over MQTT.

Note: The Insteon Dev notes provide 4 points for correlation of this raw
battery level to actual battery voltages.

   61=~1.75V
   54=~1.6V
   51=~1.5V
   40=~1.25V (default low battery mark)

The following variable is available for templating:

   'batt_volt' is the raw Insteon voltage level

A sample hidden door sensor topic and payload configuration is:

   ```
   hidden_door:
     battery_voltage_topic: 'insteon/{{address}}/battery_voltage'
     battery_voltage_payload: '{"voltage" : {{batt_volt}}}'
   ```

To set configuration option on the device, first press and hold the device link
button until it beeps and the LED starts flashing.  Next tell insteon-mqtt the
device is awake with:

   ```
   { "cmd" : "awake" }
   ```

This will tell insteon-mqtt to send commands right away rather than queuing
until the deice is awake.

View Current configuration in log:

   ```
   { "cmd" : "get_flags" }
   ```

This configuration can be changed with the following command:

   ```
   { "cmd" : "set_flags", "key" : value }

   ```

An example to turn on two groups:

   ```
   { "cmd" : "set_flags", "two_groups" : 1 }'
   ```

Configuration is available for the following options:

The following key/value pairs are available:

   - cleanup_report = 1/0: tell the device whether or not to send cleanup
   reports

   - led_disable = 1/0: disables small led on back of device to blink on
   state change

   - link_to_all = 1/0: links to 0xFF group (all available groups)

   - two_groups = 1/0: Report open/close on group 1 or report open on group 1
   and closed on 2

   - prog_lock = 1/0: prevents device from being programmed by local button
   presses

   - repeat_closed = 1/0: Repeat open command every 5 mins for 50 mins

   - repeat_open = 1/0: Repeat open command every 5 mins for 50 mins

   - stay_awake = 1/0: keeps device awake - but uses a lot of battery

Beyond these flags there are two additional settings:

   - Low Battery threshold.  This is the raw Insteon voltage level that where
   the device will trigger a group 0x03 low battery warning. Example to set to
   64 below:

   ```
   { "cmd" : "set_low_battery_voltage", "voltage" : 64 }
   ```

   - Heart Beat Interval.  The sensor will send a heartbeat to prove that it is
   functional at a configurable interval.  The more frequent it wakes up to
   this group 0x04 message the faster the battery will deplete.
   The time between heartbeats sent is 5 minutes x this setting.  So setting
   this value to 24 would be 24 x 5 mins = 120 mins.  this can be set from
   0 -> 255.  Setting to 0 = 24 hours or 1440 minutes.  Example: to set to 10
   minutes below:

   ```
   { "cmd" : "set_heart_beat_interval", "interval" : 2 }
   ```


---

## Leak Sensors

Leak sensors do not accept any input commands. The leak
sensor has state change for wet/dry events and also for heartbeat every 24
hours. The leak sensors does not report low battery condition like other
battery operated devices.

The wet/dry change defines the following variables for templates:

   - 'is_wet' is 0 for dry, 1 for wet
   - 'is_wet_str' is 'on' for wet, 'off' for dry
   - 'is_dry' is 0 for wet, 1 for dry
   - 'is_dry_str' is 'on' for dry, 'off' for wet
   - 'state' is 'wet' or 'dry'

A sample leak sensor topic and payload configuration is:

   ```
   leak:
     wet_dry_topic: 'insteon/{{address}}/wet'
     wet_dry_payload: '{{state.upper()}}'
   ```

---

## Remote Controls

Remote controls are battery powered scene controllers.  They do not
accept any input commands.  The low battery messages are inherited
from the battery sensor inputs.  The remote adds another state change
for button on and off events.  Buttons on the remote alternate sending
on and off commands each time they are pressed.

The button change defines the following variables for templates:

   - 'button' is 1...n for the button number.
   - 'on' is 1 if the button is on, 0 if it's off.
   - 'on_str' is 'on' if the button is on, 'off' if it's off.
   - 'mode' is the on/off mode: 'normal', 'fast', or instant'
   - 'fast' is 1 if the mode is fast, 0 otherwise
   - 'instant' is 1 if the mode is instant, 0 otherwise

Manual state output is invoked when a button on the device is held down.
Manual mode flags are UP or DOWN (when the on or off button is pressed and
held), and STOP (when the button is released.  Manual template variables are
name, address, and:

   - 'manual_str' = 'up'/'off'/'down'
   - 'manual' = 1/0/-1
   - 'manual_openhab' = 2/1/0

A sample remote control topic and payload configuration is:

   ```
   remote:
     state_topic: 'insteon/{{address}}/state/{{button}}'
     state_payload: '{{on_str.upper()}}'

     manual_state_topic: 'insteon/{{address}}/manual_state/{{button}}'
     manual_state_payload: '{{manual_str.upper()}}'
   ```

---

## Smoke Bridge

A smoke bridge device does not accept any input commands.  Internally,
they send updates for a number of groups depending on the type of
alert and a single clear group to say everything is OK.  The system
will translate those into one of four output MQTT messages (smoke
detected, CO warning, low battery, and a general error).  When the
clear message is received internally, an off state is sent to each of
the four topics.

The smoke bridge defines the following template variables for all of
the alerts:

   - 'on' is 1 if the alert is active, 0 if it's not
   - 'on_str' is 'on' if the alert is active, 'off' if it's not

A sample smoke bridge topic and payload configuration is:

   ```
   smoke_bridge:
     smoke_topic: 'insteon/{{address}}/smoke'
     smoke_payload: '{{on_str.upper()}}'

     co_topic: 'insteon/{{address}}/co'
     co_payload: '{{on_str.upper()}}'

     battery_topic: 'insteon/{{address}}/battery'
     battery_payload: '{{on_str.upper()}}'

     error_topic: 'insteon/{{address}}/error'
     error_payload: '{{on_str.upper()}}'
   ```

---

## Outlets

On/off outlets will publish their on/off state on the state topic whenever
the device state changes.  Outlets have only two states: on and off and use
group 1 for the top outlet and group 2 for the bottom outlet.

Output state change messages have the following variables defined
which can be used in the templates:

   - 'on' is 1 if the device is on and 0 if the device is off.
   - 'on_str' is "on" if the device is on and "off" if the device is off.
   - 'button' is 1 or 2 for the button number.
   - 'mode' is the on/off mode: 'normal', 'fast', or instant'
   - 'fast' is 1 if the mode is fast, 0 otherwise
   - 'instant' is 1 if the mode is instant, 0 otherwise
   - 'reason' is the reason for the change.  See [reason](reason.md)

Input state change messages have the following variables defined which
can be used in the templates:

   - 'value' is the message payload (string)
   - 'json' is the message payload converted to JSON format if the
     conversion succeeds.  Values inside the JSON payload can be
     accessed using the form 'json.ATTR'.  See the Jinja2 docs for
     more details.

The input state change payload template must convert the input message into
the format.  The optional mode flag can be used to send a 'normal'
(default)', 'fast', or 'instant' command to the device.

   ```
   { "cmd" : "on"/"off", "group" : group, ["mode" : 'normal'/'fast'/'instant'] }
   ```

The input command can be either a direct on/off command which will just
change the load connected to the switch (using the on_off inputs) or a scene
on/off command which simulates pressing the button on the switch (using the
scene inputs).

Here is a sample configuration that accepts and publishes messages
using upper case ON an OFF payloads.

   ```
   outlet:
      # Output state change:
      state_topic: 'insteon/{{address}}/state/{{button}}'
      state_payload: '{{on_str}}'

      # Direct change only changes the load:
      on_off_topic: 'insteon/{{address}}/set/{{button}}'
      on_off_payload: '{ "cmd" : "{{value.lower()}}" }'

      # Scene change simulates clicking the switch:
      scene_topic: 'insteon/{{address}}/scene/{{button}}'
      scene_payload: '{ "cmd" : "{{value.lower()}}" }'
   ```

When the outlet changes state a message like `ON` or `OFF` is published to
the topic `insteon/a1.b1.c1/state/1`.  To command the switch to turn on, send
a message to `insteon/a1.b1.c1/set/1` with the payload `ON`.

---

## Thermostat

The thermostat has a lot of available states and commands.

Output state change topic and payload.  Available variables for templating in
all cases are:
   address = 'aa.bb.cc'
   name = 'device name'

### State Topics

The following is an example configuration:

   temp_c = temperature in celsius
   temp_f = temperature in farenheit

  ```
  ambient_temp_topic: 'insteon/{{address}}/ambient_temp'
  ambient_temp_payload: ''{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}''
  cool_sp_state_topic: 'insteon/{{address}}/cool_sp_state'
  cool_sp_state_payload: ''{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}''
  heat_sp_state_topic: 'insteon/{{address}}/heat_sp_state'
  heat_sp_state_payload: ''{"temp_f" : {{temp_f}}, "temp_c" : {{temp_c}}}''
  ```

   fan_mode = "ON", "AUTO"
   is_fan_on = 0/1

  ```
  fan_state_topic: 'insteon/{{address}}/fan_state'
  fan_state_payload: '{{fan_mode}}'
  ```

   mode = 'OFF', 'AUTO', 'HEAT', 'COOL', 'PROGRAM'

  ```
  mode_state_topic: 'insteon/{{address}}/mode_state'
  mode_state_payload: '{{mode}}'
  ```
   humid = humidity percentage

  ```
  humid_state_topic: 'insteon/{{address}}/humid_state'
  humid_state_payload: ''{{humid}}''
  ```

   status = "OFF", "HEATING", "COOLING"
   is_heating = 0/1
   is_cooling = 0/1

  ```
  status_state_topic: 'insteon/{{address}}/status_state'
  status_state_payload: ''{{status}}''
  ```

 Caution, there is no push update for the hold or energy state.  ie, if
 you press hold on the physical device, you will not get any notice of
 this unless you run get_status().  There is also no way to programatically
 change the hold state or energy state

   hold_str = 'OFF', 'TEMP'
   is_hold = 0/1

  ```
  hold_state_topic: 'insteon/{{address}}/hold_state'
  hold_state_payload: '{{hold_str}}'
  ```
   energy_str = 'OFF', 'ON'
   is_energy = 0/1

  ```
  energy_state_topic: 'insteon/{{address}}/energ_state'
  energy_state_payload: '{{energy_str}}'
  ```

### Command Topics

Available variables for templating all of these commands are:
   address = 'aa.bb.cc'
   name = 'device name'
   value = the input payload
   json = the input payload converted to json.  Use json.VAR to extract
          a variable from a json payload.


Mode state command.  The output of passing the payload through the template
must match the following:

 ```
 { "cmd" : "auto"/"off"/"heat"/"cool","program" }
 ```

Sample configuration:

  ```
  mode_command_topic: 'insteon/{{address}}/mode_command'
  mode_command_payload: '{ "cmd" : "{{value.lower()}}" }'
  ```

Fan state command.  The output of passing the payload through the template must
match the following:

  ```
  { "cmd" : "auto"/"on" }
  ```

Sample configuration:

  ```
  fan_command_topic: 'insteon/{{address}}/fan_command'
  fan_command_payload: '{ "cmd" : "{{value.lower()}}" }'
  ```

Temp setpoint commands. The payloads should be in the form of

  ```
  {temp_c: float, temp_f: float}
  ```

Only one unit needs to be present.  If temp_f is present it will be used
regardless

Sample Configuration:

  ```
  heat_sp_command_topic: 'insteon/{{address}}/heat_sp_command'
  heat_sp_payload: '{ "temp_f" : {{value}} }'
  cool_sp_command_topic: 'insteon/{{address}}/cool_sp_command'
  cool_sp_payload: '{ "temp_f" : {{value}} }'
  ```

### Polling

If the 'pair' command has been run correctly, the thermostat should push
ambient temp, setpoint temps, humdity, and status message automatically.
However if you want, you can poll the device for the status of these values
as well by running 'get_status'.  This command will also get the units (C or F)
specified on the device, which is necessary for properly decoding some of the
temp messages from the device.  This command is also run as part of a 'refresh'.
So if you are seeing strange temperatures, try running this command or 'refresh'

Topic:
  ```
  insteon/command/aa.bb.cc
  ```

Payload:
  ```
  { "cmd" : "get_status"}
  ```
---

## IOLinc

The IOLinc is both a switch (momentary or latching on/off) and a sensor
that can be on or off.  There is a state topic which returns the state of both
objects, as well as individual relay and sensor topics that only return the
state of those objects.

The set-flags command line command can be used to change the mode settings.

There is also a set topic similar to other devices.  This obviously can only
be used to set the state of the relay.  However it may not work as you expect:

- In Latching mode, the set function works like any other switch. Turning the
relay on and off accordingly.
- If you configure the IOLinc to be momentary, then the ON command will trigger
the relay to turn on for the duration that is configured then off.  An OFF the
command will only cause the relay to turn off, it it is still on because the
momentary duration has not fully elapsed yet.
- The on/off payload forces the relay to on or off IGNORING any special
requirements associated with the Momentary_A,B,C functions or the
relay_linked flag.

If you want a command that respects the Momentary_A,B,C requirements, you want
to create a modem scene and to issue the commands to that scene.  See
[Scene triggering](#scene triggering) for a description for how to issue
commands to a scene.  And see [Scene Management](scenes.md) for a description
of how to make a scene and the scenes.yaml file for examples of an IOLinc
scene.

In Home Assistant use MQTT switch with a configuration like:
  switch:
    - platform: mqtt
      state_topic: 'insteon/aa.bb.cc/relay'
      command_topic: 'insteon/aa.bb.cc/set'
  binary_sensor:
    - platform: mqtt
      state_topic: 'insteon/aa.bb.cc/sensor'

Alternatively, to use a modem scene to control the IOLinc
  switch:
    - platform: mqtt
      state_topic: 'insteon/aa.bb.cc/relay'
      command_topic: "insteon/command/modem"
      payload_off: '{ "cmd": "scene", "name" : "<<NAME>>", "is_on" : 0}'
      payload_on: '{ "cmd": "scene", "name" : "<<NAME>>", "is_on" : 1}'

State Topic:
  ```
  'insteon/{{address}}/state'
  ```

State Topic Payload:
  ```
  '{ "sensor" : "{{sensor_on_str.lower()}}"", relay" : {{relay_on_str.lower()}} }'
  ```

Relay State Topic:
  ```
  'insteon/{{address}}/relay'
  ```

Payload:
  ```
  '{{relay_on_str.lower()}}'
  ```

Sensor State Topic:
  ```
  'insteon/{{address}}/sensor'
  ```

Payload:
  ```
  '{{sensor_on_str.lower()}}'
  ```

Set Command Topic:
  ```
  'insteon/{{address}}/set'
  ```

Payload:
  ```
  '{ "cmd" : "{{value.lower()}}" }'
  ```

---
