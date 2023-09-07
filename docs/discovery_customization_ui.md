# Discovery Customization in Home Assistant

<!-- TOC -->

- [Discovery Customization in Home Assistant](#discovery-customization-in-home-assistant)
  - [Access to configuration](#access-to-configuration)
    - [Altering devices](#altering-devices)
    - [Altering entities](#altering-entities)
    - [Disabling entities](#disabling-entities)
    - [Deleting devices](#deleting-devices)
  - [Entity names](#entity-names)
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

## Access to configuration

All configuration of the devices and entities discovered from
Insteon-MQTT is done in the MQTT integration. To access the
integration in the Home Assistant UI:

1. Click the 'Configuration' menu item in the sidebar.

1. Click 'Devices and Services' in the Configuration pane.

1. If the 'Integrations' item in the top menu bar is not highlighted,
click it to access the installed integrations.

1. Locate the MQTT integration (which may require scrolling if there
are a large number of integrations installed).

1. In the MQTT integration panel there will be two links: one for
devices, and one for entities. Each of these links will lead to the
respective section of the Configuration pane, with the list filtered
to show only the items provided by the MQTT integration.

### Altering devices

In the device list, find the one you wish to alter and click on it. A
new pane will appear with the details of the device.

Click the pencil icon next to the device name; in the dialog that
appears, the name of the device and its Area can be set or
modified. Make any changes necessary, then click the 'Update' link in
the bottom-right corner of the dialog.

To return to the device list, click the left arrow in the top menu bar.

### Altering entities

In the entity list, find the one you wish to alter and click on it. In
the dialog that appears, the name of the entity, the icon displayed
for the entity, and the 'Entity ID' can be set or modified. If the
entity should be listed in a different Area from its containing
device, click the 'Advanced settings' section to open it, and set the
desired Area in the 'Set entity area only' field.

Make any changes necessary, then click the 'Update' link in the
bottom-right corner of the dialog.

To return to the entity list, click the left arrow in the top menu bar.

### Disabling entities

In some cases the entity list for a device discovered from
Insteon-MQTT may contain entities which are not applicable to your
situation. For example the defeult entity list for a KeypadLinc
includes 9 buttons, but if the installed KeypadLinc has a 6-button
faceplate, there will be three extra entities listed for it.

A similar situation may occur for a Mini Remote Switch or a Mini
Remote (4 Scene), the entity list will contain 8 buttons by default.

In the entity list, find the one you wish to disable and click on
it. In the dialog that appears, click the 'Enable entity' slider to
turn it off. Click the 'Update' link in the bottom-right corner of the
dialog.

This process can be reversed to re-enable a disabled entity, although
Home Assistant will need to be restarted to complete the process (and
the MQTT integration will display a reminder).

To return to the entity list, click the left arrow in the top menu bar.

### Deleting devices

If you remove a device from your insteon network, or in some cases
change how it is defined, you will end up with a 'stale' device in
Home Assistant.  To remove an abandoned device, make sure you remove
it from the `devices` section of the Insteon-MQTT `config.yaml` file,
then restart Insteon-MQTT. After it has restarted, restart Home
Assistant.

In the device list, find the one you wish to delete and click on it. A
new pane will appear with the details of the device.

In the device settings pane, click the Delete button. A dialog will
appear to confirm the deletion request; once the device has been
deleted, Home Assistant will display 'Device / service not found.'
with a 'GO BACK' link. Click that link to return to the device list.

## Entity names

Each section below documents the entities produced during MQTT
Discovery for each type of device (of group of types) supported by
Insteon-MQTT. In the tables below, 'NAME' is substituted with the
name specified in `config.yaml` for the device, after conversion
to Home Assistant's internal name format (all lowercase, spaces
replaced by underscores, etc).

As an example, a FanLinc device named "Game Room" in `config.yaml`
will produce two entities: 'fan.game_room_fan' and 'light.game_room'.

### Device type 'battery_sensor' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_door|open/closed sensor||
|binary_sensor.NAME_battery|battery good/low|
|sensor.NAME_heartbeat|regular update from device to confirm communication|

### Device type 'dimmer' entities

|Name|Purpose|
|---|---|
|light.NAME|lever/paddle dimmer control|

### Device type 'ezio4o' entities

|Name|Purpose|
|---|---|
|switch.NAME_relay_1|low-voltage relay 1|
|switch.NAME_relay_2|low-voltage relay 2|
|switch.NAME_relay_3|low-voltage relay 3|
|switch.NAME_relay_4|low-voltage relay 4|

### Device type 'fan_linc' entities

|Name|Purpose|
|---|---|
|fan.NAME_fan|multi-speed fan controller|
|light.NAME|dimmable light controller|

### Device type 'hidden_door' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_door|open/closed sensor|
|binary_sensor.NAME_battery|battery good/low|
|sensor.NAME_heartbeat|regular update from device to confirm communication|
|sensor.NAME_voltage|battery voltage|

### Device type 'io_linc' entities

|Name|Purpose|
|---|---|
|switch.NAME_relay|low-voltage relay|
|binary_sensor.NAME_sensor|contact closure input|

### Device type 'keypad_linc' entities

Note that Home Assistant control of buttons 2-8 will
only turn the button LEDs on and off; it will not
trigger the responders that have been linked (in a scene)
to the buttons.

|Name|Purpose|
|---|---|
|light.NAME_btn_1|'On'on 6-button, 'A' on 8-button|
|switch.NAME_btn_2|not usable on 6-button, 'B' on 8-button|
|switch.NAME_btn_3|'A' on 6-button, 'C' on 8-button|
|switch.NAME_btn_4|'B' on 6-button, 'D' on 8-button|
|switch.NAME_btn_5|'C' on 6-button, 'E' on 8-button|
|switch.NAME_btn_6|'D' on 6-button, 'F' on 8-button|
|switch.NAME_btn_7|not usable on 6-button, 'G' on 8-button|
|switch.NAME_btn_8|not usable on 6-button, 'H' on 8-button|
|switch.NAME_btn_9|not currently usable in Insteon-MQTT|

### Device type 'keypad_linc_sw' entities

Note that Home Assistant control of buttons 2-8 will
only turn the button LEDs on and off; it will not
trigger the responders that have been linked (in a scene)
to the buttons.

|Name|Purpose|
|---|---|
|light.NAME_btn_1|'On'on 6-button, 'A' on 8-button|
|switch.NAME_btn_2|not usable on 6-button, 'B' on 8-button|
|switch.NAME_btn_3|'A' on 6-button, 'C' on 8-button|
|switch.NAME_btn_4|'B' on 6-button, 'D' on 8-button|
|switch.NAME_btn_5|'C' on 6-button, 'E' on 8-button|
|switch.NAME_btn_6|'D' on 6-button, 'F' on 8-button|
|switch.NAME_btn_7|not usable on 6-button, 'G' on 8-button|
|switch.NAME_btn_8|not usable on 6-button, 'H' on 8-button|
|switch.NAME_btn_9|not currently usable in Insteon-MQTT|

### Device type 'leak' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_leak|wet/dry sensor|
|sensor.NAME_heartbeat|regular update from device to confirm communication|

### Device type 'mini_remote1' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_btn_1|paddle switch|
|binary_sensor.NAME_btn_2|not usable|
|binary_sensor.NAME_btn_3|not usable|
|binary_sensor.NAME_btn_4|not usable|
|binary_sensor.NAME_btn_5|not usable|
|binary_sensor.NAME_btn_6|not usable|
|binary_sensor.NAME_btn_7|not usable|
|binary_sensor.NAME_btn_8|not usable|
|binary_sensor.NAME_battery|battery good/low|

### Device type 'mini_remote4' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_btn_1|'a' switch|
|binary_sensor.NAME_btn_2|'b' switch|
|binary_sensor.NAME_btn_3|'c' switch|
|binary_sensor.NAME_btn_4|'d' switch|
|binary_sensor.NAME_btn_5|not usable|
|binary_sensor.NAME_btn_6|not usable|
|binary_sensor.NAME_btn_7|not usable|
|binary_sensor.NAME_btn_8|not usable|
|binary_sensor.NAME_battery|battery good/low|

### Device type 'mini_remote8' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_btn_1|'a' switch|
|binary_sensor.NAME_btn_2|'b' switch|
|binary_sensor.NAME_btn_3|'c' switch|
|binary_sensor.NAME_btn_4|'d' switch|
|binary_sensor.NAME_btn_5|'e' switch|
|binary_sensor.NAME_btn_6|'f' switch|
|binary_sensor.NAME_btn_7|'g' switch|
|binary_sensor.NAME_btn_8|'h' switch|
|binary_sensor.NAME_battery|battery good/low|

### Device type 'motion' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_motion|motion sensor|
|binary_sensor.NAME_battery|battery good/low|
|binary_sensor.NAME_dusk|dawn/dusk (light level) sensor|

### Device type 'smoke_bridge' entities

|Name|Purpose|
|---|---|
|binary_sensor.NAME_smoke|smoke sensor|
|binary_sensor.NAME_battery|battery good/low|
|binary_sensor.NAME_co|carbon monoxide sensor|
|binary_sensor.NAME_error|operational error|

### Device type 'switch' entities

|Name|Purpose|
|---|---|
|switch.NAME|toggle/paddle switch|

### Device type 'outlet' entities

|Name|Purpose|
|---|---|
|switch.NAME_top|upper receptacle|
|switch.NAME_bottom|lower receptacle|
