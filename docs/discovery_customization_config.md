# Discovery Customization in Insteon-MQTT

<!-- TOC -->

- [Discovery Customization in Insteon-MQTT](#discovery-customization-in-insteon-mqtt)
  - [Background](#background)
  - [Defaults](#defaults)
  - [Overrides](#overrides)
    - [Device-level overrides](#device-level-overrides)
      - [Modifying](#modifying)
      - [Hiding](#hiding)
    - [Class-level overrides](#class-level-overrides)
      - [Class-level override example: SwitchLinc Relay as Light](#class-level-override-example-switchlinc-relay-as-light)
      - [Class-level override example: KeypadLinc](#class-level-override-example-keypadlinc)
      - [Class-level override example: Mini Remote Switch](#class-level-override-example-mini-remote-switch)
      - [Class-level override example: multiple classes](#class-level-override-example-multiple-classes)
  - [Entity names for overrides](#entity-names-for-overrides)
    - [Device type 'battery_sensor' entities](#device-type-battery_sensor-entities)
    - [Device type 'dimmer' entities](#device-type-dimmer-entities)
    - [Device type 'ezio4o' entities](#device-type-ezio4o-entities)
    - [Device type 'fan_linc' entities](#device-type-fan_linc-entities)
    - [Device type 'hidden_door' entities](#device-type-hidden_door-entities)
    - [Device type 'io_linc' entities](#device-type-io_linc-entities)
    - [Device type 'keypad_linc' entities](#device-type-keypad_linc-entities)
    - [Device type 'keypad_linc_sw' entities](#device-type-keypad_linc_sw-entities)
    - [Device type 'leak' entities](#device-type-leak-entities)
    - [Device type 'mini_remote1' entities](#device-type-mini_remote1-entities)
    - [Device type 'mini_remote4' entities](#device-type-mini_remote4-entities)
    - [Device type 'mini_remote8' entities](#device-type-mini_remote8-entities)
    - [Device type 'motion' entities](#device-type-motion-entities)
    - [Device type 'smoke_bridge' entities](#device-type-smoke_bridge-entities)
    - [Device type 'switch' entities](#device-type-switch-entities)
    - [Device type 'outlet' entities](#device-type-outlet-entities)

<!-- /TOC -->

## Background

To understand how Home Assistant's MQTT integration discovery works,
read more about the [Home Assistant Discovery
Protocol](https://www.home-assistant.io/docs/mqtt/discovery/).

Insteon-MQTT's implementation of this protocol relies heavily on
[Jinja2
templates](https://github.com/TD22057/insteon-mqtt/blob/master/docs/Templating.md).

## Defaults

The default entities produced by Insteon-MQTT discovery are built from
two templates: one for the device, and one for *each* entity supported
by the device.  The templates are included in the
[`config-base.yaml`](../insteon_mqtt/data/config-base.yaml) file that
is part of the Insteon-MQTT installation.

The template which produces the device information, which is common to all
devices supported by Insteon-MQTT, looks like this:

```yaml
mqtt:
  device_info_template:
    ids: "{{address}}"
    mf: "Insteon"
    mdl: "{%- if model_number != 'Unknown' -%}
            {{model_number}} - {{model_description}}
          {%- elif dev_cat_name != 'Unknown' -%}
            {{dev_cat_name}} - 0x{{'%0x' % sub_cat|int }}
          {%- elif dev_cat == 0 and sub_cat == 0 -%}
            No Info
          {%- else -%}
            0x{{'%0x' % dev_cat|int }} - 0x{{'%0x' % sub_cat|int }}
          {%- endif -%}"
    sw: "0x{{'%0x' % firmware|int }} - {{engine}}"
    name: "{{name_user_case}}"
    via_device: "{{modem_addr}}"

```

This template uses the shortened attribute names listed in the MQTT
Discovery documentation: `ids` instead of `identifiers`, `mf` instead
of `manufacturer`, etc.

The templates which produce the entities for a specific device type
look like this (for a FanLinc):

```yaml
mqtt:
  fan_linc:
    discovery_entities:
      fan:
        component: 'fan'
        config:
          uniq_id: "{{address}}_fan"
          name: "{{name_user_case}} fan"
          device: "{{device_info}}"
          avty_t: "{{availability_topic}}"
          cmd_t: "{{fan_on_off_topic}}"
          stat_t: "{{fan_state_topic}}"
          stat_val_tpl: "{% raw %}{{value_json.state}}{% endraw %}"
          pct_cmd_t: "{{fan_speed_set_topic}}"
          pct_cmd_tpl: "{% raw %}{% if value < 10 %}off{% elif value < 40 %}low{% elif value < 75 %}medium{% else %}high{% endif %}{% endraw %}"
          pct_stat_t: "{{fan_speed_topic}}"
          pct_val_tpl: "{% raw %}{% if value == 'low' %}33{% elif value == 'medium' %}67{% elif value == 'high' %}100{% else %}0{% endif %}{% endraw %}"
          pr_mode_stat_t: "{{fan_speed_topic}}"
          pr_mode_cmd_t: "{{fan_speed_set_topic}}"
          pr_modes: ["off", "low", "medium", "high"]
          json_attr_t: "{{fan_state_topic}}"
          json_attr_tpl: "{%- raw -%}
                          {\"timestamp\": {{value_json.timestamp}}, \"reason\": \"{{value_json.reason}}\"}
                          {%- endraw -%}"
      light:
        component: 'light'
        config:
          uniq_id: "{{address}}_light"
          name: "{{name_user_case}}"
          avty_t: "{{availability_topic}}"
          cmd_t: "{{level_topic}}"
          stat_t: "{{state_topic}}"
          brightness: true
          schema: "json"
          device: "{{device_info}}"
          json_attr_t: "{{state_topic}}"
          json_attr_tpl: "{%- raw -%}
                          {\"timestamp\": {{value_json.timestamp}}, \"mode\": \"{{value_json.mode}}\", \"reason\": \"{{value_json.reason}}\"}
                          {%- endraw -%}"
```

This set of templates produces two entities for each FanLinc device,
one named `fan` and one named `light`. Note that these names are
internal to the Insteon-MQTT configuration only, they are not exposed
to Home Assistant (Home Assistant uses the name from the `name`
attribute in the `config` block).

Each entity provides a `component` attribute which tells Home
Assistant which type of component this entity should be mapped to, and
a `config` block which provides the details of the entity (in the MQTT
Discovery protocol, this `config` block become the payload of the
discovery message sent over MQTT).

As with the `device_info_template`, these `config` blocks use the
shortened attribute names when available: `cmd_t` instead of
`command_topic`, `json_attr_t` instead of `json_attributes_topic`,
etc.

A special attribute in the `config` block is the `device` attribute:
as shown above, its value is "{{device_info}}", which means it will
contain the result of rendering the `device_info_template` for the
device which contains this entity. All of the entities contained by
that device will have the same content in their `device` attributes,
and Home Assistant will use that information to link them with the
device.

## Overrides

There is an override mechanism available, which allows the
configuration in `config.yaml` to add, replace, or remove attributes
at both the device and entity levels; it also permits 'hiding' of
entities and entire devices so that they will not appear in Home
Assistant.

Overrides are specified using a `discovery_overrides` block at the
appropriate level; those blocks look like this:

```yaml
discovery_overrides:
  discoverable: true/false
  device:
    # add an attribute named 'sa'
    sa: "Office"
    # replace the attribute named 'mf'
    mf: "Custom"
    # remove the attribute named 'sw'
    sw: ""
  <entity name>:
    discoverable: true/false
    component: <type>
    config:
      # add an attribute named 'icon'
      icon: "mdi:ceiling-fan"
      # replace the attribute named 'name'
      name: "Office Fan"
      # remove the attribute named 'cmd_t'
      cmd_t: ""
```

When an overrides block is processed, each instruction in it is
applied to the attributes provided by the template used for the
device, or to the attributes left after a previous overrides block was
processed (in cases where multiple overrides blocks are used for the
same device).

The available 'entity names' for each type of device are documented
at the bottom of this page.

### Device-level overrides

#### Modifying

Specifying overrides at the device level looks like this:

```yaml
insteon:
  devices:
    fan_linc:
      - aa.bb.cc: "Office Fan"
        discovery_overrides:
          device:
            sa: "Office"
          fan:
            config:
              name: "Office Fan"
              icon: "mdi:ceiling-fan"
          light:
            config:
              name: "Office Fan Light"
              icon: "mdi:ceiling-fan-light"
```

There are five overrides in this block:

* The `sa` (`suggested_area`) of the entire device is set to
  "Office". If the Home Assistant configuration includes an Area named
  "Office", then this device and its entities will appear in the
  dashboard section for that area.

* The name of the `fan` entity of the device is set to "Office Fan",
  which will be used instead of the default "Office Fan fan".

* The icon for the `fan` entity of the device is set to
  "mdi:ceiling-fan", which will be used instead of the default
  "mdi:fan" icon in the Home Assistant dashboard.

* The name of the `fan` entity of the device is set to "Office Fan Light",
  which will be used instead of the default "Office Fan".

* The icon for the `light` entity of the device is set to
  "mdi:ceiling-fan-light", which will be used instead of the default
  "mdi:lightbulb" icon in the Home Assistant dashboard.

#### Hiding

It is also possible to hide devices or entities from the discovery
system; if this FanLinc should not appear in Home Asssistant at all,
then:

```yaml
insteon:
  devices:
    fan_linc:
      - aa.bb.cc: "Office FanLinc"
        discovery_overrides:
          discoverable: false
```

Note that this only hides the device from Home Assistant; it is still
fully operational in Insteon-MQTT, so it can be controlled and queried
using MQTT messages, and it can participate in scenes defined in
`scenes.yaml`.

If, on the other hand, the device should appear in Home Assistant, but
this particular fan does not have a light, then:

```yaml
insteon:
  devices:
    fan_linc:
      - aa.bb.cc: "Office FanLinc"
        discovery_overrides:
          light:
            discoverable: false
```

This will hide *just* the light from Home Assistant, but not the fan.

### Class-level overrides

When the Insteon-MQTT configuration includes multiple devices which
require the same overrides, or even just a common subset of overrides,
it can be more efficient (and easier to maintain) to create a 'class'
which contains those overrides and gives them a useful name.

This is done by adding a block to the `mqtt` section of `config.yaml`,
and including the necessary `discovery_overrides` content in that
block.

```yaml
mqtt:
  switch_as_light:
    discovery_overrides:
      switch:
        component: "light"
        config:
          brightness: false
          val_tpl: ""
```

This block provides three overrides for an entity named `switch` in
any device that it is applied to:

* The `component` mapping is set to "light", replacing the default of
  "switch".

* The `brightness` attribute is set to "false", so that Home Assistant
  will know that this 'light' can only be set to 'on' or 'off', not to
  a brightness level.

* The `val_tpl` attribute is set to an empty string, so that it will
  be removed from the configuration data sent to Home Assistant
  ('light' entities in Home Assistant do not support the `val_tpl`
  attribute).

Applying this new 'discovery override class' to multiple Insteon
SwitchLinc Relay devices is done this way:

```yaml
insteon:
  devices:
    switch:
      - dd.ee.01: "Office Closet"
        discovery_override_class: "switch_as_light"
      - dd.ee.02: "Attic"
        discovery_override_class: "switch_as_light"
      - dd.ee.03: "Basement"
        discovery_override_class: "switch_as_light"
```

The `discovery_override_class` attribute of the device is used to
indicate the name(s) of classes of discovery override data which
should be applied to this device during MQTT Discovery. The classes
are applied in the order they are specified. Finally, any
`discovery_overrides` specified at the device level are applied.

The result is that all three of these devices are reported to Home
Assistant as 'on-off lights', rather than generic switches.

#### Class-level override example: SwitchLinc Relay as Light

Repeating (and condensing) the example from the last section:

The desired result is for a series of SwitchLinc Relay devices to
appear in Home Assistant as lights, instead of generic switches.

```yaml
insteon:
  devices:
    switch:
      - dd.ee.01: "Office Closet"
        discovery_override_class: "switch_as_light"
      - dd.ee.02: "Attic"
        discovery_override_class: "switch_as_light"
      - dd.ee.03: "Basement"
        discovery_override_class: "switch_as_light"

mqtt:
  switch_as_light:
    discovery_overrides:
      switch:
        component: "light"
        config:
          brightness: false
          val_tpl: ""
```

#### Class-level override example: KeypadLinc

A common situation is that Insteon-MQTT is configured to manage a
KeypadLinc that has a 6-button faceplate, not an 8-button
faceplace. Since the default `discovery_entities` for a KeypadLinc
assume there are 8 buttons (plus a virtual 9th button to be used if
the KeypadLinc has been configured with a 'detached load'), Home
Assistant will show switches for the device that do not actually
exist.

An example `discovery_override_class` overrides block to hide the
unneeded entities could look like this:

```yaml
insteon:
  devices:
    keypad_linc:
      - dd.ee.01: "Office"
        discovery_override_class: "kpl_6_buttons"
    keypad_linc_sw:
      - dd.ee.02: "Garage"
        discovery_override_class: "kpl_6_buttons"

mqtt:
  kpl_6_buttons:
    discovery_overrides:
      button2:
        discoverable: false
      button7:
        discoverable: false
      button8:
        discoverable: false
      button9:
        discoverable: false
```

This overrides block contains four overrides, each of which 'hide' a
specific entity from the default list of entities for a
KeypadLinc. The example shows this being applied to both a
dimmer-style KeypadLinc and a relay-style (on/off) KeypadLinc.

#### Class-level override example: Mini Remote Switch

Insteon produces three types of battery-powered wireless remote
controllers: the Mini Remote Switch, the Mini Remote (4 scene), and
the Mini Remote. They all operate identically and Insteon-MQTT
supports them all equally, but they have different numbers of buttons
(1, 4, and 8, respectively).

When a Mini Remote Switch is configured in `config.yaml`, the result
will be eight 'binary_sensor' entities appearing in Home Assistant
(along with a 'battery' entity used to monitor the battery power
level), but seven of them are not useful.

An example `discovery_override_class` overrides block to hide the
unneeded entities could look like this:

```yaml
insteon:
  devices:
    mini_remote1:
      - dd.ee.01: "Stairs"
        discovery_override_class: "remote_1_button"

mqtt:
  remote_1_button:
    discovery_overrides:
      button2:
        discoverable: false
      button3:
        discoverable: false
      button4:
        discoverable: false
      button5:
        discoverable: false
      button6:
        discoverable: false
      button7:
        discoverable: false
      button8:
        discoverable: false
```

This overrides block contains seven overrides, each of which hides the
corresponding button so that it will not appear in Home Assistant. The
'battery' entity for the device is not affected by these overrides.

#### Class-level override example: multiple classes

Combining some of the examples above, the Insteon network might
include a number of dimmers, FanLincs, KeypadLincs, and Mini Remotes
in a large 'game room'. Some of those devices will require overrides
to change entity names or hide entities that are not usable; all of
them require an override to set the 'suggested area'.

```yaml
insteon:
  devices:
    dimmer:
      - bb.bb.01: "North End Lights"
        discovery_override_class: "game_room"
      - bb.bb.02: "South End Lights"
        discovery_override_class: "game_room"
    fan_linc:
      - cc.cc.01: "North Fan"
        discovery_override_class:
          - "fan_name_icons"
          - "game_room"
      - cc.cc.02: "South Fan"
        discovery_override_class:
          - "fan_name_icons"
          - "game_room"
    keypad_linc:
      - dd.dd.01: "North Fan"
        discovery_override_class:
          - "kpl_6_buttons"
          - "game_room"
      - dd.dd.02: "South Fan"
        discovery_override_class:
          - "kpl_6_buttons"
          - "game_room"
    mini_remote1:
      - ee.ee.01: "North End Drapes"
        discovery_override_class:
          - "remote_1_button"
          - "game_room"
      - ee.ee.02: "South End Drapes"
        discovery_override_class:
          - "remote_1_button"
          - "game_room"

mqtt:
  game_room:
    discovery_overrides:
      device:
        sa: "Game Room"
  fan_name_icons:
    discovery_overrides:
      fan:
        config:
          name: "Office Fan"
          icon: "mdi:ceiling-fan"
      light:
        config:
          name: "Office Fan Light"
          icon: "mdi:ceiling-fan-light"
  kpl_6_buttons:
    discovery_overrides:
      button2:
        discoverable: false
      button7:
        discoverable: false
      button8:
        discoverable: false
      button9:
        discoverable: false
  remote_1_button:
    discovery_overrides:
      button2:
        discoverable: false
      button3:
        discoverable: false
      button4:
        discoverable: false
      button5:
        discoverable: false
      button6:
        discoverable: false
      button7:
        discoverable: false
      button8:
        discoverable: false
```

With all of these overrides in place, this group of eight devices will
appear in the "Game Room" Area in Home Assistant; only the necessary
(and useful) entities will appear, and the FanLinc entities will have
custom names and icons.

## Entity names for overrides

Each section below documents the default entities produced during
MQTT Discovery for each type of device (of group of types) supported
by Insteon-MQTT.

### Device type 'battery_sensor' entities

|Name|Component Type|Purpose|
|---|---|---|
|door|binary_sensor|open/closed sensor|
|battery|binary_sensor|battery good/low|
|heartbeat|sensor|regular update from device to confirm communication|

### Device type 'dimmer' entities

|Name|Component Type|Purpose|
|---|---|---|
|dimmer|light|lever/paddle dimmer control|

### Device type 'ezio4o' entities

|Name|Component Type|Purpose|
|---|---|---|
|relay1|switch|low-voltage relay 1|
|relay2|switch|low-voltage relay 2|
|relay3|switch|low-voltage relay 3|
|relay4|switch|low-voltage relay 4|

### Device type 'fan_linc' entities

|Name|Component Type|Purpose|
|---|---|---|
|fan|fan|multi-speed fan controller|
|light|light|dimmable light controller|

### Device type 'hidden_door' entities

|Name|Component Type|Purpose|
|---|---|---|
|door|binary_sensor|open/closed sensor|
|battery|binary_sensor|battery good/low|
|heartbeat|sensor|regular update from device to confirm communication|
|voltage|sensor|battery voltage|

### Device type 'io_linc' entities

|Name|Component Type|Purpose|
|---|---|---|
|relay|switch|low-voltage relay|
|sensor|binary_sensor|contact closure input|

### Device type 'keypad_linc' entities

Note that Home Assistant control of buttons 2-8 will
only turn the button LEDs on and off; it will not
trigger the responders that have been linked (in a scene)
to the buttons.

|Name|Component Type|Purpose|
|---|---|---|
|button1|light|'On'on 6-button, 'A' on 8-button|
|button2|switch|not usable on 6-button, 'B' on 8-button|
|button3|switch|'A' on 6-button, 'C' on 8-button|
|button4|switch|'B' on 6-button, 'D' on 8-button|
|button5|switch|'C' on 6-button, 'E' on 8-button|
|button6|switch|'D' on 6-button, 'F' on 8-button|
|button7|switch|not usable on 6-button, 'G' on 8-button|
|button8|switch|not usable on 6-button, 'H' on 8-button|
|button9|switch|not currently usable in Insteon-MQTT|

### Device type 'keypad_linc_sw' entities

Note that Home Assistant control of buttons 2-8 will
only turn the button LEDs on and off; it will not
trigger the responders that have been linked (in a scene)
to the buttons.

|Name|Component Type|Purpose|
|---|---|---|
|button1|light (with `brightness` set to "false")|'On'on 6-button, 'A' on 8-button|
|button2|switch|not usable on 6-button, 'B' on 8-button|
|button3|switch|'A' on 6-button, 'C' on 8-button|
|button4|switch|'B' on 6-button, 'D' on 8-button|
|button5|switch|'C' on 6-button, 'E' on 8-button|
|button6|switch|'D' on 6-button, 'F' on 8-button|
|button7|switch|not usable on 6-button, 'G' on 8-button|
|button8|switch|not usable on 6-button, 'H' on 8-button|
|button9|switch|not currently usable in Insteon-MQTT|

### Device type 'leak' entities

|Name|Component Type|Purpose|
|---|---|---|
|wet|binary_sensor|wet/dry sensor|
|heartbeat|sensor|regular update from device to confirm communication|

### Device type 'mini_remote1' entities

|Name|Component Type|Purpose|
|---|---|---|
|button1|binary_sensor|paddle switch|
|button2|binary_sensor|not usable|
|button3|binary_sensor|not usable|
|button4|binary_sensor|not usable|
|button5|binary_sensor|not usable|
|button6|binary_sensor|not usable|
|button7|binary_sensor|not usable|
|button8|binary_sensor|not usable|
|battery|binary_sensor|battery good/low|

### Device type 'mini_remote4' entities

|Name|Component Type|Purpose|
|---|---|---|
|button1|binary_sensor|'a' switch|
|button2|binary_sensor|'b' switch|
|button3|binary_sensor|'c' switch|
|button4|binary_sensor|'d' switch|
|button5|binary_sensor|not usable|
|button6|binary_sensor|not usable|
|button7|binary_sensor|not usable|
|button8|binary_sensor|not usable|
|battery|binary_sensor|battery good/low|

### Device type 'mini_remote8' entities

|Name|Component Type|Purpose|
|---|---|---|
|button1|binary_sensor|'a' switch|
|button2|binary_sensor|'b' switch|
|button3|binary_sensor|'c' switch|
|button4|binary_sensor|'d' switch|
|button5|binary_sensor|'e' switch|
|button6|binary_sensor|'f' switch|
|button7|binary_sensor|'g' switch|
|button8|binary_sensor|'h' switch|
|battery|binary_sensor|battery good/low|

### Device type 'motion' entities

|Name|Component Type|Purpose|
|---|---|---|
|motion|binary_sensor|motion sensor|
|battery|binary_sensor|battery good/low|
|dusk|binary_sensor|dawn/dusk (light level) sensor|

### Device type 'smoke_bridge' entities

|Name|Component Type|Purpose|
|---|---|---|
|smoke|binary_sensor|smoke sensor|
|battery|binary_sensor|battery good/low|
|co|binary_sensor|carbon monoxide sensor|
|error|binary_sensor|operational error|

### Device type 'switch' entities

|Name|Component Type|Purpose|
|---|---|---|
|switch|switch|toggle/paddle switch|

### Device type 'outlet' entities

|Name|Component Type|Purpose|
|---|---|---|
|top|switch|upper receptacle|
|bottom|switch|lower receptacle|
