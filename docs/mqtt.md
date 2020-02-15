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
   - [IOLinc](#iolinc)
   - [KeypadLinc](#keypadlinc)
   - [Leak Sensors](#leak-sensors)
   - [Motion Sensors](#motion-sensors)
   - [Outlets](#outlets)
   - [Remotes](#remote-controls)
   - [Smoke Bridge](#smoke-bridge)
   - [Switches](#switches)


## Required Device Initialization

When adding a new device or after performing a factory reset on a device it
is necessary to perform a three step process to setup the device to work
properly with insteon-mqtt.  The steps are 1) Join, 2) Pair, and 3) Sync
(only if you have scenes defined for this device in a scenes.yaml file).  
The Join and Pair commands can be re-run at anytime without harm.  You can also
run sync in dry-run mode at any time to see what changes would be made.

From the command line these actions can be performed as follows:

```
insteon-mqtt config.yaml join aa.bb.cc
insteon-mqtt config.yaml pair aa.bb.cc
insteon-mqtt config.yaml sync aa.bb.cc
```

These commands can also be performed using the mqtt interface by publishing
the following separate commands to the command topic (discussed below):

   ```
   { "cmd" : "join"}
   { "cmd" : "pair"}
   { "cmd" : "sync"}
   ```

See the following discussion of management commands for a more detailed
explanation of these actions.

---

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

### Join a New Device to the Network

Supported: devices

New devices<sup>1</sup> will refuse to communicate with the modem until the
device has been specifically told to respond to the modem.  This can be done by
running the 'join' command on the device

The command payload is:

   ```
   { "cmd" : "join"}
   ```

This command can also be run from the command line:

   ```
   insteon-mqtt config.yaml join aa.bb.cc
   ```

<sup>1</sup> Specifically devices that have version I2CS of the engine, which
have been available since March 2012, and are the only devices sold as new
since about 2015.  Older I1 and I2 devices do not require this step, however
they will not be adversely affected by this command.


### Pair a Device to the Modem

Supported: devices

This performs the default initialization of the device and in particular tells
the device that it should inform the modem whenever its state changes. This
includes devices that have multiple states to track such as KeypadLincs.

The command payload is:

   ```
   { "cmd" : "pair"}
   ```

This command can also be run from the command line:

   ```
   insteon-mqtt config.yaml pair aa.bb.cc
   ```


### Sync Device Links

Supported: modem, device

This function will alter the device's link database to match the scenes
defined in the scenes.yaml file.  This includes adding new links as well as
deleting un-defined links.  Details can be found in [Scene Management](scenes.md)

The command payload is below.  Setting the dry_run flag to true will cause the
changes to be made to the device, the default false will only report what would
happen:

  ```
  { "cmd" : "sync", ["dry_run" : true/false]}
  ```

  This command can also be run from the command line:

   ```
   insteon-mqtt config.yaml sync aa.bb.cc
   ```

### Sync All Device Links

Supported: modem

This function will perform the sync command on all devices.

The command payload is as follows.  Setting the dry_run flag to true will cause
the changes to be made to the device, the default false will only report what
would happen:

  ```
  { "cmd" : "sync_all", ["dry_run" : true/false]}
  ```

 This command can also be run from the command line:

  ```
  insteon-mqtt config.yaml sync-all
  ```

### Import Device Links

Supported: modem, device

The 'import-scenes' function will take the links defined on each device and
parse them into a scene which can be saved to the scenes.yaml file.  Please
read the in [Scene Management](scenes.md)

The command payload is below.  Setting the dry_run flag to true will cause the
changes to be made to the file, the default false will only report what would
happen:

  ```
  { "cmd" : "import_scenes", ["dry_run" : true/false]}
  ```

  This command can also be run from the command line:

   ```
   insteon-mqtt config.yaml import-scenes aa.bb.cc
   ```

### Sync All Device Links

Supported: modem

This function will perform the import-scenes command on all devices.

The command payload is as follows.  Setting the dry_run flag to true will cause
the changes to be made to the file, the default false will only report what
would happen:

  ```
  { "cmd" : "import_scenes_all", ["dry_run" : true/false]}
  ```

 This command can also be run from the command line:

  ```
  insteon-mqtt config.yaml import-scenes-all
  ```

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

If this is sent to the modem, it will trigger an all link database
download.  If it's sent to a device, the device state (on/off, dimmer
level, etc) will be updated and the database will be downloaded if
it's out of date.  The model information of the device will also be
queried if it is not known. Setting the force flag to true will download
the database even if it's not out of date and will recheck the model
information even if known.  The command payload is:


   ```
   { "cmd" : "refresh", ["force" : true/false] }
   ```

If the device reports a state change because of the refresh command the
reason string will be set to "refresh".

### Refresh all devices

Supported: modem

The modem will send a refresh command to each device that it knows
about (i.e. devices defined in the config file).  The command payload
is:

   ```
   { "cmd" : "refresh_all", ["force" : true/false] }
   ```


### Get device model information

Supported: device

Will send a command to the device to get the device category, sub-category,
and firmware version.  This information may be used to determine what
features are available on the device:

  ```
  { "cmd" : "get_model" }
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

Supported: devices

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

   - backlight: integer in the range 0x00-0xff which changes the LED backlight
     level on the device.
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
     commands.  If a bit is 0, hten the button only sends off commands.
   - nontoggle_bits: 8 bit integer flags - 1 per button.  If a bit is 1, then
     that button is a non-toggle button and will only send a signal per the
     signal_bits input.  If a bit is 0, then that button is a toggle button
     and will alternate on an doff signals

IOLinc supports the flags:

   - mode: "latching" / "momentary-a" / "momentary-b" / "momentary-c" to
     change the relay mode (see the IOLinc user's guide for details)
   - trigger_reverse: 0/1 reverses the trigger command state
   - relay_linked: 0/1 links the relay to the sensor value



### Print the current all link database.

Supported: modem, devices

This command is mainly used from the command line tool and allows printing of
the current all link database for a device.

   ```
   { "cmd": "print_db" }
   ```


### Scene triggering.

Supported: modem, devices

This command triggers scenes from the modem or device.  For the modem, this
triggers virtual modem scenes (i.e. any group number where the modem is the
controller).  For devices, the group is the button number and this will
simulate pressing the button on the device.  Note that devices do not work
properly with the off command - they will emit the off scene message but not
actually turn off themselves so insteon-mqtt will send an off command to the
device once the scene messages are done.  The reason field is optional and
will be passed through to the output state change payload.

   ```
   { "cmd": "scene", "group" : group, "is_on" : 0/1, ["reason" : "..."] }
   ```

   Supported: modem

   The modem also allows the triggering of scenes from a name defined in a
   [Scene Management](scenes.md) file as well. To access a scene by its name
   simply drop the group attribute and add the name attribute such as.

   ```
   { "cmd": "scene", "name" : "test_scene", "is_on" : 0/1, ["reason" : "..."] }
   ```


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
   - 'reason' is the reason for the change.  'device' if a button was pressed
     on the device.  'scene' if the device is responding to a scene trigger.
     'refresh' if the update is from a refresh'.  'command' if the device is
     responding to an on/off command.  Or an arbitrary string if one was
     passed in via the scene or on/off style command inputs.

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
   - 'reason' is the reason for the change.  'device' if a button was pressed
     on the device.  'scene' if the device is responding to a scene trigger.
     'refresh' if the update is from a refresh'.  'command' if the device is
     responding to an on/off command.  Or an arbitrary string if one was
     passed in via the scene or on/off style command inputs.

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
   - 'reason' is the reason for the change.  'device' if a button was pressed
     on the device.  'scene' if the device is responding to a scene trigger.
     'refresh' if the update is from a refresh'.  'command' if the device is
     responding to an on/off command.  Or an arbitrary string if one was
     passed in via the scene or on/off style command inputs.

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

Here is a sample configuration that accepts and publishes messages
matching the Home Assistant MQTT fan configuration.

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
input confi file which controls the behavior of the group 1 switch.  The
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
   - 'mode' is the on/off mode: 'normal', 'fast', or instant'
   - 'fast' is 1 if the mode is fast, 0 otherwise
   - 'instant' is 1 if the mode is instant, 0 otherwise
   - 'reason' is the reason for the change.  'device' if a button was pressed
     on the device.  'scene' if the device is responding to a scene trigger.
     'refresh' if the update is from a refresh'.  'command' if the device is
     responding to an on/off command.  Or an arbitrary string if one was
     passed in via the scene or on/off style command inputs.

Manual state output is invoked when a button on the device is held down.
Manual mode flags are UP or DOWN (when the on or off button is pressed and
held), and STOP (when the button is released.  Manual template variables are
name, address, and:

   - 'manual_str' = 'up'/'off'/'down'
   - 'manual' = 1/0/-1
   - 'manual_openhab' = 2/1/0
   - 'reason' (see above)

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
     level_topic: 'insteon/{{address}}/level/1'
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

A sample battery sensor topic and payload configuration is:

   ```
   battery_sensor:
     # Trigger events
     state_topic: 'insteon/{{address}}/state'
     state_payload: '{{on_str.upper()}}'

     # Low battery warning
     low_battery_topic: 'insteon/{{address}}/battery'
     low_battery_payload: '{{is_low_str.upper()}}'
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
     heartbeat_topic: 'insteon/{{address}}/heartbeat'
     heartbeat_payload: '{{heartbeat_time}}'
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
   - 'reason' is the reason for the change.  'device' if a button was pressed
     on the device.  'scene' if the device is responding to a scene trigger.
     'refresh' if the update is from a refresh'.  'command' if the device is
     responding to an on/off command.  Or an arbitrary string if one was
     passed in via the scene or on/off style command inputs.

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
