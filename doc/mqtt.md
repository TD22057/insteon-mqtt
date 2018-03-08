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

   - [Switches](#switches)
   - [Dimmers](#dimmers)
   - [FanLinc](#fanlinc)
   - [KeypadLinc](#keypadlinc)
   - [IOLinc](#iolinc)
   - [Battery Sensors](#battery-sensors)
   - [Motion Sensors](#motion-sensors)
   - [Leak Sensors](#leak-sensors)
   - [Remotes](#remote-controls)
   - [Smoke Bridge](#smoke-bridge)


## Required links (scenes)

These commands assume that the devices have been linked correctly to the
modem in order for the commands to work.  To use a new device, see the
linking command - that can be used to pair the device with the modem (in both
directions) for group 1 which is required to allow the device to accept any
commands from the modem and report basic state changes.

More complicated devices need more links than that to fully work.  FanLInc,
KeypadLinc, IOLinc, multi-button remotes, battery sensors, and the Smoke
bridge all require link to be created from the device to the modem for every
group/button and/or message that the device publishes.  Multi-button devices
also require that the modem have a link to the device for each button in
order to allow scene simulation.  The pair command can be used to
automatically configure these links and should used whenever adding a new
device.

---

## Management commands

Management commands can be sent by using the command line tool
"insteon-mqtt" or by publishing a MQTT message to the command topic
(cmd_topic in the config file).  Management commands may be supported
by the modem, by the devices, or by both.  For examples of the command
style, see [command line module source code](../insteon_mqtt/cmd_line).

All management commands use a payload that is JSON dictionary.  If the
documentation below, if a key/value pair is enclosed in square
brackets [], then it's optional.  If a value can be one of many like
true or false, then the possible values are separated by a slash /.

The MQTT topic to publish management commands to is (aa.bb.cc is the
device address or nice name from the config.yaml file):

   ```
   insteon/command/aa.bb.cc
   ```


### Activate all linking mode

Supported: modem, devices

This turns on all linking mode and is the same as pressing the set
button for 3 sec on the modem or device.  The default group is 1.

This can be used to connect new devices to the modem.  Run 'linking modem',
'linking aa.bb.cc' to control the device from the modem and 'linking
aa.bb.cc', 'linking modem' so the modem will get broadcast messages from the
device.  For more complicated devices, then run a 'pair device' command to
configure the other links that the device needs.

The command payload is:

   ```
   { "cmd" : "linking", ["group" : group] }
   ```

Once you run the linking command, you should also run 'refresh' on the device
to update it's local database.  The modem will automatically update, but the
devices don't send a message when the linking is complete so there is no way
to know when to update the database.

For example, to add a new Insteon device, edit the config.yaml file to
identify the device and address and restart insteon-mqtt.  Then link it with
the modem both directions and run the pair command to add any other
(non-group 1 links):

   ```
   insteon-mqtt config.yaml linking modem
   insteon-mqtt config.yaml linking keypad1
      [device will double beep]
   insteon-mqtt config.yaml linking keypad1
   insteon-mqtt config.yaml linking modem
      [device will double beep]
   insteon-mqtt config.yaml pair keypad1
   ```


### Refresh the device state and download it's all link database

Supported: modem, devices

If this is sent to the modem, it will trigger an all link database
download.  If it's sent to a device, the device state (on/off, dimmer
level, etc) will be updated and the database will be downloaded if
it's out of date.  Setting the force flag to true will download the
database even if it's not out of date.  The command payload is:


   ```
   { "cmd" : "refresh", ["force" : true/false] }
   ```


### Refresh all devices

Supported: modem

The modem will send a refresh command to each device that it knows
about (i.e. devices defined in the config file).  The command payload
is:

   ```
   { "cmd" : "refresh_all", ["force" : true/false] }
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
the next click of the button will send out an ON command (and vice versa).
Button is an integer in the range [1,8].  In the 6 button version, buttons
1,2 and 7,8 are not commandable and can only be toggled by sending on/off
commands.

   ```
   { "cmd": "set_button_led", "button" : button, "is_on" : true/false }
   ```

### Get and set operating flags.

Supported: devices

This command gets and sets various Insteon device flags.  The set of
supported flags depends on the device type.  The command line tool accepts an
arbitrary list of "key=value" strings which get sent to the device for
validation.  For example, to change the backlight level of a switch:

   ```
   insteon-mqtt config.yaml set-flags aa.bb.cc backlight=0x11
   ```

The MQTT format of the command is:

   ```
   { "cmd" : "set_flags", "KEY" : "VALUE", ... }
   ```

Switch, KeypadLinc, and Dimmer all support the flags:

   - backlight: integer in the range 0x11-0xff which changes the LED backlight
     level on the device.

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
device once the scene messages are done.

   ```
   { "cmd": "scene", "group" : group, "is_on" : 0/1 }
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

Input state change messages have the following variables defined which
can be used in the templates:

   - 'value' is the message payload (string)
   - 'json' is the message payload converted to JSON format if the
     conversion succeeds.  Values inside the JSON payload can be
     accessed using the form 'json.ATTR'.  See the Jinja2 docs for
     more details.

The input state change payload template must convert the input message
into the format.  The optional instant key defaults to 0 (normal
ramping behavior) but can be set to 1 to perform an instant state
change.

   ```
   { "cmd" : "on"/"off", ["instant" : 0/1] }
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
format (LEVEL must be in the range 0->255).  The optional instant key
defaults to 0 (normal ramping behavior) but can be set to 1 to perform an
instant state change.

   ```
   { "cmd" : "on"/"off", "level" : LEVEL, ["instant" : 0/1] }
   ```

Here is a sample configuration that accepts and publishes messages
using a JSON format that contains the level using the tag
"brightness".

   ```
   switch:
      # Output state change:
      state_topic: 'insteon/{{address}}/state'
      state_payload: '{ "state" : "{{on_str}}", "brightness" : {{level}} }'

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
      fan_state_payload: '{{on_str}}"

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

The KeypadLinc is a wall mounted dimmer control and scene controller.
Basically it combines a dimmer switch and remote control.  The dimmer portion
of the KeypadLinc uses the dimmer settings (see above).  The other buttons
are treated as switches (see the switch documentation above) but have no load
connected to them.  KeypadLincs are usually configured as 6 button or 8
button devices with the following button number layouts:

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

A sample remote control topic and payload configuration is:

   ```
   keypad_linc:
      # Output state change:
      btn_state_topic: 'insteon/{{address}}/state/{{button}}'
      btn_state_payload: '{{on_str.upper()}}'

      # Input state change.  For any button besides 1, this just
      # updates the LED state.
      btn_on_off_topic: 'insteon/{{address}}/set/{{button}}'
      btn_on_off_payload: '{ "cmd" : "{{json.state}}" }'

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

The battery powered sensor sends motion events on the "state' configuration
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
   - 'is_dawn_str' is "on" for dawn", "off" for dusk
   - 'is_dusk' is 1 for dusk, 0 for dawn
   - 'is_dusk_str' is "on" for dusk", "off" for dawn
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

Leak sensors do not accept any input commands.  The low battery
messages are inherited from the battery sensor inputs.  The leak
sensor adds another possible state change for wet/dry events.

The wet/dry change defines the following variables for templates:

   - 'is_wet' is 0 for dry, 1 for wet
   - 'is_wet_str' is 'on' for wet, 'off' for dry
   - 'is_dry' is 0 for wet, 1 for dry
   - 'is_dry_str' is 'on' for dry, 'off' for wet
   - 'state' is 'wet' or 'dry'

A sample leak sensor topic and payload configuration is:

   ```
   leak:
     wet_dry_topic: 'insteon/{{address}}/leak'
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

A sample remote control topic and payload configuration is:

   ```
   remote:
     state_topic: 'insteon/{{address}}/state/{{button}}'
     state_payload: '{{on_str.upper()}}'
   ```

---

## Smoke Bridge

A smoke bridge device does not accept any input commands.  Internally,
they send updates for a number of groups depending on the type of
alert and a single clear group to say everything is ok.  The system
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
