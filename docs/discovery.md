# MQTT Discovery Platform

HomeAssistant allows for entities to be defined through an MQTT discovery topic.
This means, that for general installations, a user need only setup InsteonMQTT
following the [Configuration Instructions](https://github.com/TD22057/insteon-mqtt/blob/master/docs/configuration.md)
and HomeAssistant should just work!  No need to add individual entities to the
HomeAssistant configuration.

Read more about the [HomeAssistant Discovery Platform](https://www.home-assistant.io/docs/mqtt/discovery/).

## Customization

Of course, all of us will likely want to tweak or edit the default
configuration and this can be done using [Jinja templates](https://github.com/TD22057/insteon-mqtt/blob/master/docs/Templating.md).

### Default Device Templates

By default,
a device will look to its corresponding subkey in the `mqtt` key.  So for
example, a dimmer device will by default look the the `dimmer` subkey under
the `mqtt` key:

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

### Using a Custom Device Template

Each device can also define a distinct template for its discovery entities.
This is done using [Device Specific Configuration](https://github.com/TD22057/insteon-mqtt/blob/master/docs/config_extra.md).
Specifically, using the `discovery_class` key.  So you can do the following:
```yaml
insteon:
  device:
    dimmer:
      - dd.ee.ff: my_dimmer
        discovery_class: my_discovery_class

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

Each entry `discovery_entities` is an associative array with the __required__
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

> The `config` json template __must generate valid json_.  This is a good json
[validator](https://jsonformatter.curiousconcept.com/).  __Notably__ json strings
cannot contain raw newline characters, they can however be represented by `\n`

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
- `<<topics>>` = (str) topic keys as defined in the config.yaml
file under the _default class_ for this device are available as variables.

> The `<<topics>>` available are __always__ those listed under the default
class for this device.  So for a `dimmer` the topics will be gathered from
the `mqtt->dimmer` key.  Topics listed under a user defined `discovery_class`
will be ignored.

Additional variables may be offered by specific devices classes.  Those
variables are defined in the `config-example.yaml` file under the relevant
`mqtt` device keys.

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
