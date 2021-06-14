## Defining Entities in HomeAssistant Using Yaml

> This page is only relevant to those who are using HomeAssistant
> __without__ the Discovery Platform.

The following are some example yaml configuration settings that can be used if
you want to manually define your entities in HomeAssistant.  Manually defining
your entities requires an intermediate level of familiarity with
[Yaml](https://www.tutorialspoint.com/yaml/index.htm),
[HomeAssistant](https://www.home-assistant.io/docs/configuration/),
and [Jinja Templates](https://github.com/TD22057/insteon-mqtt/blob/master/docs/Templating.md).
__Beginners are highly encouraged to use the Discovery Platform.__

These are just example configurations. You will at minimum need to edit the
names and addresses to match your devices.  You may also need to make changes
to suit your setup.  For example, if you have changed the template for a topic
you will need to alter how that topic is defined in HomeAssistant.

> Configuration settings and variables for HomeAssistant are defined by
> HomeAssistant.  We do not vigilantly track the changes that are made to
> HomeAssistant, so it is possible that these examples may not be exactly
> corret.

<!-- TOC -->

  - [Modem Scenes](#modem-scenes)
  - [Switches](#switches)
  - [Dimmers](#dimmers)
  - [Generic Battery Sensors](#generic-battery-sensors)
  - [Motion Sensors](#motion-sensors)
  - [Hidden Door Sensors](#hidden-door-sensors)
  - [Leak Sensors](#leak-sensors)
  - [Remotes](#remotes)
  - [SmokeBridge](#smokebridge)
  - [Thermostat](#thermostat)
  - [FanLinc](#fanlinc)
  - [KeypadLincs](#keypadlincs)
  - [IOLincs](#iolincs)
  - [Outlets](#outlets)
  - [EZIO4O](#ezio4o)

<!-- /TOC -->

### Modem Scenes

There is no "state" for modem scenes.  So you only need to define the command
topic.

```yaml
switch:
  - platform: mqtt
    name: Modem Group 10
    command_topic: 'insteon/modem/scene'
    payload_on: '{"state": "on", "group": "10"}'
    payload_off: '{"state": "off", "group": "10"}'
```

### Switches

```yaml
switch:
  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/state'
    command_topic: 'insteon/aa.bb.cc/set'
    json_attributes_topic: 'insteon/aa.bb.cc/state'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: '{{value_json.state}}'
```

### Dimmers

```yaml
light:
  - platform: mqtt
    schema: json
    name: "insteon 1"
    state_topic: "insteon/aa.bb.cc/state"
    command_topic: "insteon/aa.bb.cc/level"
    brightness: true
    json_attributes_topic: "insteon/aa.bb.cc/state"
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
```

### Generic Battery Sensors

Generic Battery Sensors include triggerlinc door and window sensors.  But
could also include other battery devices if no specific support has been
added. Not all battery sensors off all of these entities.  For example the
basic Triggerlinc door sensors do not have heartbeats.

```yaml
binary_sensor:
  - platform: mqtt
    name: Door Sensor
    state_topic: 'insteon/aa.bb.cc/state'
    device_class: 'door'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/state'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: '{{value_json.state}}'

  - platform: mqtt
    name: Door Sensor Battery
    state_topic: 'insteon/aa.bb.cc/battery'
    device_class: 'battery'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/battery'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}}
      }
    value_template: '{{value_json.state}}'

sensor:
  - platform: mqtt
    name: Door Sensor Heartbeat
    state_topic: 'insteon/aa.bb.cc/heartbeat'
    device_class: timestamp
    force_update: true
```

### Motion Sensors

```yaml
binary_sensor:
  - platform: mqtt
    name: Motion Sensor
    state_topic: 'insteon/aa.bb.cc/state'
    device_class: motion
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/state'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: '{{value_json.state}}'

  - platform: mqtt
    name: Motion Sensor Battery
    state_topic: 'insteon/aa.bb.cc/battery'
    device_class: 'battery'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/battery'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}}
      }
    value_template: '{{value_json.state}}'

  - platform: mqtt
    name: Motion Sensor Dusk/Dawn
    state_topic: 'insteon/aa.bb.cc/dawn'
    device_class: light
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/dawn'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}}
      }
    value_template: '{{value_json.state}}'
```

### Hidden Door Sensors

```yaml
binary_sensor:
  - platform: mqtt
    name: Door Sensor
    state_topic: 'insteon/aa.bb.cc/state'
    device_class: 'door'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/state'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: '{{value_json.state}}'

  - platform: mqtt
    name: Door Sensor Battery
    state_topic: 'insteon/aa.bb.cc/battery'
    device_class: 'battery'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/battery'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}}
      }
    value_template: '{{value_json.state}}'

sensor:
  - platform: mqtt
    name: Door Sensor Heartbeat
    state_topic: 'insteon/aa.bb.cc/heartbeat'
    device_class: timestamp
    force_update: true
  - platform: mqtt
    name: Door Sensor Voltage
    state_topic: 'insteon/aa.bb.cc/battery_voltage'
    device_class: 'voltage'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/battery_voltage'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}}
      }
    value_template: '{{value_json.voltage}}'
```

### Leak Sensors

```yaml
binary_sensor:
  - platform: mqtt
    name: Leak Sensor
    state_topic: 'insteon/aa.bb.cc/wet'
    device_class: 'moisture'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/wet'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}}
      }
    value_template: '{{value_json.state}}'

sensor:
  - platform: mqtt
    name: Leak Sensor Heartbeat
    state_topic: 'insteon/aa.bb.cc/heartbeat'
    device_class: timestamp
    force_update: true
```

### Remotes

```yaml
binary_sensor:
  # You will need to repeat this entity entry for as many buttons as you have
  - platform: mqtt
    name: Remote Button 1
    state_topic: 'insteon/aa.bb.cc/state/1'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/state/1'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: '{{value_json.state}}'

  - platform: mqtt
    name: Remote Battery
    state_topic: 'insteon/aa.bb.cc/battery'
    device_class: 'battery'
    force_update: true
    json_attributes_topic: 'insteon/aa.bb.cc/battery'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}}
      }
    value_template: '{{value_json.state}}'
```

### SmokeBridge

```yaml
binary_sensor:
  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/smoke'
    name: Smoke Sensor
    device_class: 'smoke'

  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/battery'
    name: Smoke Detector Battery
    device_class: 'battery'

  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/co'
    name: Gas Sensor
    device_class: 'gas'

  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/error'
    name: Smoke Detector Problem
    device_class: 'problem'
```

### Thermostat

This example assumes the use of Farenheit, to use Celsius, be sure to make the
necessary changes.

```yaml
climate:
  - platform: mqtt
    name: Upstairs Thermostat
    mode_state_topic: "insteon/aa.bb.cc/mode_state"
    current_temperature_topic: "insteon/aa.bb.cc/ambient_temp"
    fan_mode_state_topic: "insteon/aa.bb.cc/fan_state"
    fan_modes: ["auto", "on"]
    action_topic: 'insteon/aa.bb.cc/status_state'
    current_temperature_template: "{{value_json.temp_f}}"
    fan_mode_command_topic: 'insteon/aa.bb.cc/fan_command'
    hold_state_topic: 'insteon/aa.bb.cc/hold_state'
    mode_command_topic: 'insteon/aa.bb.cc/mode_command'
    mode_state_topic: 'insteon/aa.bb.cc/mode_state'
    modes: ["off", "cool", "heat", "auto"]
    precision: 1.0
    temperature_high_command_topic: 'insteon/aa.bb.cc/cool_sp_command'
    temperature_high_state_topic: 'insteon/aa.bb.cc/cool_sp_state'
    temperature_high_state_template: "{{value_json.temp_f}}"
    temperature_low_command_topic: 'insteon/aa.bb.cc/heat_sp_command'
    temperature_low_state_topic: 'insteon/aa.bb.cc/heat_sp_state'
    temperature_low_state_template: "{{value_json.temp_f}}"
    temperature_unit: "F"
```

### FanLinc

The light entity on the fan is a duplicate of the dimmer entry above.

```yaml
fan:
  - platform: mqtt
    name: FanLinc Fan
    command_topic: 'insteon/aa.bb.cc/fan/set'
    state_topic: 'insteon/aa.bb.cc/fan/state'
    percentage_command_topic: 'insteon/aa.bb.cc/fan/speed/set'
    percentage_command_template: >-
      {% if value < 10 %}
        off
      {% elif value < 40 %}
        low
      {% elif value < 75 %}
        medium
      {% else %}
        high
      {% endif %}
    percentage_state_topic: 'insteon/aa.bb.cc/fan/speed/state'
    percentage_value_template: >-
      {% if value == 'low' %}
        33
      {% elif value == 'medium' %}
        67
      {% elif value == 'high' %}
        100
      {% else %}
        0
      {% endif %}
    preset_mode_state_topic: "insteon/aa.bb.cc/fan/speed/state"
    preset_mode_command_topic: "insteon/aa.bb.cc/fan/speed/set"
    preset_modes: ["off", "low", "medium", "high"]
    json_attributes_topic: 'insteon/aa.bb.cc/fan/state'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "reason" : "{{value_json.reason}}"
      }

light:
  - platform: mqtt
    schema: json
    name: "FanLinc Light"
    state_topic: "insteon/aa.bb.cc/state"
    command_topic: "insteon/aa.bb.cc/level"
    brightness: true
    json_attributes_topic: "insteon/aa.bb.cc/state"
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
```

### KeypadLincs
A KeypadLinc is an on/off or dimmer switch (Insteon group 1) plus a
series of scene control buttons which operate on other groups.  The group
1 behavior will depend on whether the device is an on/off or dimmer.  The
4 or 6 other buttons are controlled like switches.

6 button and 8 button keypads have use the following button numbers:
```
   1 on           1       2
 3       4        3       4
 5       6        5       6
   1 off          7       8
```

```yaml
#### Group 1 Entity
# If KPL is a dimmer
light:
  - platform: mqtt
    schema: json
    name: "KPL Dimmer"
    state_topic: "insteon/aa.bb.cc/state/1"
    command_topic: "insteon/aa.bb.cc/set/1"
    brightness: true
    json_attributes_topic: "insteon/aa.bb.cc/state/1"
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }

# If KPL is a switch
switch:
  - platform: mqtt
    name: "KPL Switch"
    state_topic: 'insteon/aa.bb.cc/state/1'
    command_topic: 'insteon/aa.bb.cc/set/1'
    json_attributes_topic: 'insteon/aa.bb.cc/state/1'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: '{{value_json.state}}'

#### Remaining Buttons
# You will need to duplicate this entity for as many buttons as you have
switch:
  - platform: mqtt
    name: "KPL Button 2"
    state_topic: 'insteon/aa.bb.cc/state/2'
    command_topic: 'insteon/aa.bb.cc/set/2'
    json_attributes_topic: 'insteon/aa.bb.cc/state/2'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: '{{value_json.state}}'
```

### IOLincs

The IOLinc is both a switch (momentary or latching on/off) and a sensor
that can be on or off.  If you configure the IOLinc to be momentary, then
the on command will trigger it for the duration that is configured and
the off command is ignored.  If it's configured as a latching switch,
then the on and off commands work like a normal switch.

> NOTE: the on/off payload forces the relay to on or off ignoring any special
requirements associated with the Momentary_A,B,C functions or the
relay_linked flag.

```yaml
switch:
  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/relay'
    command_topic: 'insteon/aa.bb.cc/set'
    name: IOLinc Relay
    json_attributes_topic: 'insteon/aa.bb.cc/state'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }

binary_sensor:
  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/sensor'
    name: IOLinc Sensor
    json_attributes_topic: 'insteon/aa.bb.cc/state'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
```

### Outlets

The non-dimming in wall outlet modules is two independent switches
(top and bottom outlet).  The top outlet is group 1, the bottom
outlet is group 2.

```yaml
switch:
  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/state/1'
    command_topic: 'insteon/aa.bb.cc/set/1'
    name: "Outlet Top"
    json_attributes_topic: 'insteon/aa.bb.cc/state/1'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: "{{value_json.state}}"

  - platform: mqtt
    state_topic: 'insteon/aa.bb.cc/state/2'
    command_topic: 'insteon/aa.bb.cc/set/2'
    name: "Outlet Bottom"
    json_attributes_topic: 'insteon/aa.bb.cc/state/2'
    json_attributes_template: >-
      {
      "timestamp" : {{value_json.timestamp}},
      "mode" : "{{value_json.mode}}",
      "reason" : "{{value_json.reason}}"
      }
    value_template: "{{value_json.state}}"
```

### EZIO4O

```yaml
switch:
  - platform: mqtt
    name: Relay 1
    state_topic: 'insteon/aa.bb.cc/state/1'
    command_topic: 'insteon/aa.bb.cc/set/1'
  - platform: mqtt
    name: Relay 2
    state_topic: 'insteon/aa.bb.cc/state/2'
    command_topic: 'insteon/aa.bb.cc/set/2'
  - platform: mqtt
    name: Relay 3
    state_topic: 'insteon/aa.bb.cc/state/3'
    command_topic: 'insteon/aa.bb.cc/set/3'
  - platform: mqtt
    name: Relay 4
    state_topic: 'insteon/aa.bb.cc/state/4'
    command_topic: 'insteon/aa.bb.cc/set/4'
```
