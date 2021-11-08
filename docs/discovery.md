# MQTT Discovery Platform

HomeAssistant allows for InsteonMQTT to define entities using a discovery
protocol. This means, that for general installations, a user need only setup
InsteonMQTT following the
[Configuration Instructions](https://github.com/TD22057/insteon-mqtt/blob/master/docs/configuration.md)
and then follow the brief enabling instructions below to get Insteon working
in HomeAssistant.

<!-- TOC -->

- [MQTT Discovery Platform](#mqtt-discovery-platform)
  - [Enabling the Discovery Platform](#enabling-the-discovery-platform)
  - [Customization](#customization)
    - [Altering entities in HomeAssistant](#altering-entities-in-homeassistant)
    - [Disabling Entities in HomeAssistant](#disabling-entities-in-homeassistant)
    - [Deleting Entities in HomeAssistant](#deleting-entities-in-homeassistant)
  - [Writing your own templates](#writing-your-own-templates)
    - [Default Device Templates](#default-device-templates)
    - [Using a Custom Device Template](#using-a-custom-device-template)
    - [Writing a `discovery_entities` Template](#writing-a-discovery_entities-template)
      - [JSON Dangers](#json-dangers)
      - [Passing Jinja Templates as Values](#passing-jinja-templates-as-values)
      - [Example `discovery_entities` templates](#example-discovery_entities-templates)
    - [The Special `device_info_template` Variable](#the-special-device_info_template-variable)
  - [Sample Templates for Custom Discovery Classes](#sample-templates-for-custom-discovery-classes)
    - [Single Button Remote](#single-button-remote)
    - [Six Button Keypadlinc](#six-button-keypadlinc)
    - [Setting Switches as Lights](#setting-switches-as-lights)

<!-- /TOC -->

## Enabling the Discovery Platform

Enabling the discovery platform for new installations is very easy.  All you
need to do is set the following configuration setting:
to true:

```YAML
mqtt:
  enable_discovery: true
```

The base configuration file that ships inside InsteonMQTT contains the initial templates for all Insteon devices.

> __If you installed InsteonMQTT starting with version 0.8.3 or earlier__, you will
need to read the [Migrating to Discovery](migrating.md) page for instructions on how to
incorporate the changes to the `config.yaml` file into your configuration.

## Customization

If the default entities defined by InsteonMQTT do not suit your needs, you may
be able to alter the entities within HomeAssistant.

### Altering entities in HomeAssistant

To do this, go to
`Configuration -> Integrations` find the MQTT integration and click on the
entities link.

This page will contain a list of all of the defined entities. Find the one you
wish to alter and click on it.  This settings page allows you to change the
name (only used in the UI) of the entity, the icon used in the UI, and the
entity ID that is used when referencing the entity in automations and in the
frontend.  Under advanced settings, you can also change the area of the Device.
Click update to save your changes.

### Disabling Entities in HomeAssistant

It may also be the case that InsteonMQTT has defined a number of entities that
you do not need.  For example, your keypadlinc may only have 6 buttons but 9
are defined.

To remove the extra buttons, go to
`Configuration -> Integrations` find the MQTT integration and click on the
entities link.  This page will contain a list of all of the defined entities.
Find the one you wish to disable and click on it.

To remove the extra buttons, simply toggle tne `enable entity` setting.  The
device will now no longer be listed in the UI, and will not show up in the
logbook or history.

### Deleting Entities in HomeAssistant

If you remove a device from your insteon network, or in some cases change how
it is defined, you will end up with old entities in HomeAssistant.  To remove
an abandoned entity, make sure you remove it from the `devices` section of the
InsteonMQTT `yaml` config file.  Then restart InsteonMQTT.  You then need to
restart HomeAssistant.

Then go to, `Configuration -> Integrations` find the MQTT integration and
click on the entities link.  This page will contain a list of all of the
defined entities. Find the one you wish to delete and click on it.  Abandoned
devices are easy to find because of the red icon on the right side.

Inside, the settings page, click the Delete button.  If the delete button is
disabled, then you have not 1) removed the device from your InsteonMQTT config,
2) restarted InsteonMQTT, OR 3) restared HomeAssistant.

## Writing your own templates

To understand how HomeAssistant discovery works, read more about the
[HomeAssistant Discovery Protocol](https://www.home-assistant.io/docs/mqtt/discovery/).

Tweaking, editing, or adding to the default
configuration and can be done using [Jinja templates](https://github.com/TD22057/insteon-mqtt/blob/master/docs/Templating.md).

### Default Device Templates

Discovery Device Templates are contained in your `yaml` config file. They are
defined using the `discovery_entities` key. By
default, a device will look to its corresponding subkey under the `mqtt` key.
So for example, a dimmer device will by default look to the `dimmer` subkey
under the `mqtt` key:

```YAML
insteon:
  device:
    dimmer:
      - aa.bb.cc: my_dimmer

mqtt:
  dimmer:
    discovery_entities:
      # This is where device aa.bb.cc will look to find its template by
      # default
```

If you review the contents of the base configuration file, under the `mqtt` section, you will see many examples of the `discovery_entities` setting. [config-base.yaml](https://github.com/TD22057/insteon-mqtt/blob/master/insteon_mqtt/data/config-base.yaml)

### Using a Custom Device Template

Each device can also define a distinct template for its discovery entities.
This is done using [Device Specific Configuration](https://github.com/TD22057/insteon-mqtt/blob/master/docs/config_extra.md).
Specifically, using the `discovery_class` key.  So you can do the following:
```yaml
insteon:
  device:
    dimmer:
      - dd.ee.ff: my_dimmer
        discovery_class: my_discovery_class  # < Note the lack of hyphen

mqtt:
  my_discovery_class:  # < Note the class name
    discovery_entities:
      # This is where device dd.ee.ff will look to find its template by
      # default
```

This class can be reused by any number of devices.  Any device that uses the
entry `discovery_class: my_discovery_class` will look to this class.

### Writing a `discovery_entities` Template
The `discovery_entities` key should contain a list.  Each list entry will
generate an entity in HomeAssistant.  Some devices may only have one entity,
other devices may have multiple entities.

Each entry in `discovery_entities` is an associative array with the __required__
keys `component` and `config`.
- `component` - (String) One of the supported HomeAssistant MQTT components,
eg. `binary_sensor`, `light`, `switch`
- `config` - (jinja template) The template must produce a __json__ string that is
acceptable to HomeAssistant.  The contents of what is required in this json
string are defined by the
[HomeAssistant Discovery Platform](https://www.home-assistant.io/docs/mqtt/discovery/).

> The `config` json template __must include__ an entry for `unique_id` or
`uniq_id` containing a unique id for this entity.  It is __strongly
recommended__ that you use the the device address as part of this unique id.
The recommended format is `{{address}}_suffix` where the suffix is something
that plainly describes the nature of this enity.  Devices with only a single
entity do not need a suffix, but it is still good practice to use one.

The `config` template has a number of variables available to it.  For all
devices this includes at minimum the following, devices may also add
additional variables unique to these devices:

- `name` = (str) device name in lower case
- `address` = (str) hexadecimal address of device as a string
- `name_user_case` = (str) device name in the case entered by
the user
- `engine` = (str) device engine version (e.g. i1, i2, i2cs).  Will return
`Unknown` if unknown.
- `model_number` = (str) device model number (e.g. 2476D).  Will return
`Unknown` if unknown.
- `model_description` = (str) description (e.g. SwitchLinc Dimmer) Will return
`Unknown` if unknown.
- `firmware` = (int) device firmware version. Will return 0 by default
- `dev_cat` = (int) device category.  Will return 0 by default
- `dev_cat_name` = (str) device category name Will return `Unknown` if unknown.
- `sub_cat` = (int) device sub-category.  Will return 0 by default
- `modem_addr` = (str) hexadecimal address of modem as a string
- `device_info_template` = (jinja template) a template defined in
config.yaml.  _See below_
- `availability_topic` = The _availabiltiy_topic_ string as defied in the config.yaml file under the _mqtt_ key.
- `<<topics>>` = (str) topic keys as defined in the config.yaml
file under the _default class_ for this device are available as variables.

> The `<<topics>>` available are __always__ those listed under the default
class for this device.  So for a `dimmer` the topics will be gathered from
the `mqtt->dimmer` key.  Topics listed under a user defined `discovery_class`
will be ignored.

Additional variables may be offered by specific devices classes.  Those
variables are defined in the `config-example.yaml` file under the relevant
`mqtt` device keys.

#### JSON Dangers

> The `config` json template __must generate valid json__.  This is a good json
[validator](https://jsonformatter.curiousconcept.com/).

__Notable Gotchas__

1. __Newline Characters__ - JSON strings cannot contain raw newline characters,
they can however be represented by `\n`. Keep in mind that the config template
is first injested from yaml.  You can read about
[how yaml handles whitespace](https://yaml-multiline.info/).  Second, the
config template is rendered through Jinja.  You can read about
[how jinja handles whitespace](https://tedboy.github.io/jinja2/templ6.html).
2. __Trailing Commas__ - JSON cannot include trailing commas.  The last item
in a list or the last key:value pair in an object __cannot__ be followed by a
comma.
3. __Single Quotes__ - JSON requires doubles quotes, you __cannot__ use single
quotes to define a string.  You can escape double quotes with `\"`

#### Passing Jinja Templates as Values
HomeAssistant uses jinja templates as well, and in a number of cases entities
have configuration settings that contain a template.  If you attempt to enter a
template as a value, it will be rendered by InsteonMQTT, which in this case
would likely result with an empty value.

To pass an unrendered template on to HomeAssistant __you must escape the
template__.  The template can be escaped using the `{% raw %} {{escaped_stuff}} {% endraw %}`
format.  For example:

```yaml
mqtt:
  climate:
    discovery_entities:
      - component: "climate"
        config: |-
          {
          .... # other settings
          "temp_lo_stat_tpl": "{% raw %}{{value_json.temp_f}}{% endraw %}",
          }
```

#### Example `discovery_entities` templates

```yaml
mqtt:
  # Other keys ommitted
  dimmer:
    # Other keys omitted
    discovery_entities:
      - component: 'light'
        config: |-
          {
            "uniq_id": "{{address}}_light",
            "name": "{{name_user_case}}",
            "cmd_t": "{{level_topic}}",
            "stat_t": "{{state_topic}}",
            "brightness": true,
            "schema": "json",
            "device": {{device_info_template}}
          }
```

### The Special `device_info_template` Variable
Inside HomeAssistant each entity config can contain a description about the
device that the entity is contained in.  This is mostly a cosmetic feature
that provides some level of topology to HomeAssistant and can allow you to
see all of the entities on a single device.

This device description configuration is likely going to use an identical
template from one device to the next.  To make things easier, the subkey
`device_info_template` can be defined under the `mqtt` key.  The contents
of this key should be a template that when rendered produces the device_info
relevant to the majority of your devices.  This template can then be inserted
into any of the `discovery_entities` by using the `device_info_template`
variable.

You can view the default template in [config-base.yaml](https://github.com/TD22057/insteon-mqtt/blob/master/insteon_mqtt/data/config-base.yaml)

For example, the following a complex template that produces a nice device
info:
```YAML
mqtt:
  # Other keys omitted
  device_info_template: |-
    {
      "ids": "{{address}}",
      "mf": "Insteon",
      "mdl": "{%- if model_number != 'Unknown' -%}
                {{model_number}} - {{model_description}}
              {%- elif dev_cat_name != 'Unknown' -%}
                {{dev_cat_name}} - 0x{{'%0x' % sub_cat|int }}
              {%- elif dev_cat == 0 and sub_cat == 0 -%}
                No Info
              {%- else -%}
                0x{{'%0x' % dev_cat|int }} - 0x{{'%0x' % sub_cat|int }}
              {%- endif -%}",
      "sw": "0x{{'%0x' % firmware|int }} - {{engine}}",
      "name": "{{name_user_case}}",
      "via_device": "{{modem_addr}}"
    }
```

This when used in a `discovery_entities` template described above will render
as:

```JSON
{
  "uniq_id": "4f.23.38_light",
  "name": "my dimmer",
  "cmd_t": "insteon/4f.23.38/level",
  "stat_t": "insteon/4f.23.38/state",
  "brightness": true,
  "schema": "json",
  "device": {
    "ids": "4f.23.38",
    "mf": "Insteon",
    "mdl": "2477D - SwitchLinc Dimmer (Dual-Band)",
    "sw": "0x45 - i2cs",
    "name": "my dimmer",
    "via_device": "41.ee.e6"
  }
}
```

## Sample Templates for Custom Discovery Classes

### Single Button Remote

The default remote configuration exposes entities for all eight
buttons.  However, if you have a single button remote, you likely
only want to see an entity for that single button.  The following
sample configuration settings will enable that:

```yaml
insteon:
  device:
    mini_remote1::
      - dd.ee.ff: my_remote
        discovery_class: remote_1  # < note no dash at start of line

mqtt:
  remote_1:  # < Note the class name
    discovery_entities:
      - component: 'binary_sensor'
        config: |-
          {
            "uniq_id": "{{address}}_btn",
            "name": "{{name_user_case}} btn",
            "stat_t": "{{state_topic_1}}",
            "device": {{device_info_template}}
          }
      - component: 'binary_sensor'
        config: |-
          {
            "uniq_id": "{{address}}_battery",
            "name": "{{name_user_case}} battery",
            "stat_t": "{{low_battery_topic}}",
            "device_class": "battery",
            "device": {{device_info_template}}
          }
      - component: 'sensor'
        config: |-
          {
            "uniq_id": "{{address}}_heartbeat",
            "name": "{{name_user_case}} heartbeat",
            "stat_t": "{{heartbeat_topic}}",
            "device_class": "timestamp",
            "device": {{device_info_template}}
          }
```

### Six Button Keypadlinc

The default Keypad_linc configuration exposes entities for all eight
buttons.  However, if you have a six button keypad_linc, you likely
only want to see entities for those six buttons.  The following
sample configuration settings will enable that:

```yaml
insteon:
  device:
    keypad_linc::
      - 11.22.33: my_6_button_kpl
        discovery_class: kpl_6  # < note no dash at start of line

mqtt:
  kpl_6:  # < Note the class name
  discovery_entities:
    - component: 'light'
      config: |-
        {
          "uniq_id": "{{address}}_1",
          "name": "{{name_user_case}} btn 1",
          "device": {{device_info_template}},
          "brightness": {{is_dimmable|lower()}},
          "cmd_t": "{%- if is_dimmable -%}
                      {{dimmer_level_topic}}
                    {%- else -%}
                      {{btn_on_off_topic_1}}
                    {%- endif -%}",
          "schema": "json",
          "stat_t": "{%- if is_dimmable -%}
                      {{dimmer_state_topic}}
                    {%- else -%}
                      {{btn_state_topic_1}}
                    {%- endif -%}"
        }
    - component: 'switch'  # No button 2 on 6 button devices
      config: |-
        {
          "uniq_id": "{{address}}_3",
          "name": "{{name_user_case}} btn 3",
          "device": {{device_info_template}},
          "cmd_t": "{{btn_on_off_topic_3}}",
          "stat_t": "{{btn_on_off_topic_3}}",
        }
    - component: 'switch'
      config: |-
        {
          "uniq_id": "{{address}}_4",
          "name": "{{name_user_case}} btn 4",
          "device": {{device_info_template}},
          "cmd_t": "{{btn_on_off_topic_4}}",
          "stat_t": "{{btn_on_off_topic_4}}",
        }
    - component: 'switch'
      config: |-
        {
          "uniq_id": "{{address}}_5",
          "name": "{{name_user_case}} btn 5",
          "device": {{device_info_template}},
          "cmd_t": "{{btn_on_off_topic_5}}",
          "stat_t": "{{btn_on_off_topic_5}}",
        }
    - component: 'switch'
      config: |-
        {
          "uniq_id": "{{address}}_6",
          "name": "{{name_user_case}} btn 6",
          "device": {{device_info_template}},
          "cmd_t": "{{btn_on_off_topic_6}}",
          "stat_t": "{{btn_on_off_topic_6}}",
        }
      # No buttons 7-9 on 6 button devices
```

### Setting Switches as Lights

Switchlincs are by default defined as `switch` components in HomeAssistant.
However, you may prefer to define them as `light` components without the
dimming feature. This has a few benefits, 1) the component classification may
better match the actual use, 2) you get the nice lightbulb icon automatically,
3) when the entities are linked to devices such as Google Home or Amazon Alexa
HomeAssistant, they will appear within these platforms as lights.

To do this, define a new custom `discovery_class` as follows:

```yaml
mqtt:
  switch_as_light:
  # Maps a switch to a light, which is nicer in HA for actual lights
  discovery_entities:
    - component: "light"
      config: >-
        {
          "uniq_id": "{{address}}_light",
          "name": "{{name_user_case|title}}",
          "cmd_t": "{{on_off_topic}}",
          "stat_t": "{{state_topic}}",
          "brightness": false,
          "schema": "json",
          "device": {{device_info_template}}
        }
```

Then for each device just add the discovery class:

```yaml
devices:
  switch:
    - aa.bb.cc: My Light
      discovery_class: switch_as_light
