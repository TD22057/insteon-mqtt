# MQTT Discovery Platform

Home Assistant's MQTT Integration supports device discovery, a
mechanism that allows services like Insteon-MQTT to *push* information
about the devices they support into Home Assistant. In many cases, a
user of Insteon-MQTT will only need to follow the basic [Configuration
Instructions](configuration.md), and then use the brief instructions
below to enable the discovery mechanism.

With those configurations in place, all of the devices known to Insteon-MQTT
will automatically appear in Home Assistant, using a default configuration
for each device. If desired, each device's configuration can be customized,
either in Home Assistant or in the Insteon-MQTT configuration files.

<!-- TOC -->

- [MQTT Discovery Platform](#mqtt-discovery-platform)
  - [Enabling the discovery platform](#enabling-the-discovery-platform)
    - [Insteon-MQTT 1.0.0 and later](#insteon-mqtt-100-and-later)
    - [Insteon-MQTT 0.8.3 or earlier](#insteon-mqtt-083-or-earlier)
  - [Customization](#customization)
  - [Writing your own templates](#writing-your-own-templates)
    - [Default Device Templates](#default-device-templates)
    - [Using a Custom Device Template](#using-a-custom-device-template)
    - [Writing a `discovery_entities` Template](#writing-a-discovery_entities-template)
      - [JSON Dangers](#json-dangers)
      - [Passing Jinja Templates as Values](#passing-jinja-templates-as-values)
      - [Example `discovery_entities`](#example-discovery_entities)

<!-- /TOC -->

## Enabling the discovery platform

### Insteon-MQTT 1.0.0 and later

If your Insteon-MQTT configuration was built using version 1.0.0 (or
any later version), enabling the disovery platform requires a single
configuration setting in your `config.yaml` file:


```YAML
mqtt:
  enable_discovery: true
```

Enabling the platform, then restarting Insteon-MQTT, will result in
the __default__ device and entity templates (which are included in the
[config-base.yaml](../insteon_mqtt/data/config-base.yaml) file that 
is part of the Insteon-MQTT installation)
being used to *push* those devices and entities to Home Assistant.

### Insteon-MQTT 0.8.3 or earlier

If your Insteon-MQTT configuration was built using any version before
1.0.0, you will need to read the [Migrating to
Discovery](migrating.md) page for instructions on how to incorporate
the necessary changes into your `config.yaml` file, and into your Home
Assistant configurations.

## Customization

If the default devices and entities created by Insteon-MQTT do not
suit your needs, there are two methods available for customization.

One option is to edit the devices and entities in the Home Assistant
UI, and a guide for doing that is in the [Discovery Customization in
Home Assistant](discovery_customization_ui.md) page.

The other option is to use 'overrides' in the Insteon-MQTT
configuration itself, so that the customized devices and entities are
sent to Home Assistant directly. A guide for using the 'overrides'
feature is in the [Discovery Customization in
Insteon-MQTT](discovery_customization_config.md) page.

## Writing your own templates

### Default Device Templates

Discovery Device Templates are contained in your `yaml` config
file. They are defined using the `discovery_entities` key. By default,
a device will look to its corresponding subkey under the `mqtt` key.
So for example, a dimmer device will by default look to the `dimmer`
subkey under the `mqtt` key:

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

If you review the contents of the base configuration file, under the
`mqtt` section, you will see many examples of the `discovery_entities`
setting. [config-base.yaml](../insteon_mqtt/data/config-base.yaml)

### Using a Custom Device Template

Each device can also define a distinct template for its discovery
entities.  This is done using [Device Specific
Configuration](config_extra.md).  Specifically, using the
`discovery_class` key.  So you can do the following:

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

This class can be reused by any number of devices.  Any device that
uses the entry `discovery_class: my_discovery_class` will look to this
class.

### Writing a `discovery_entities` Template
The `discovery_entities` key must contain an associative array.  Each
array entry will generate an entity in Home Assistant.  Some devices
may only have one entity, other devices may have multiple entities.

Each entry in `discovery_entities` has a name; this name is used
__only__ inside the Insteon-MQTT configuration system, it is not
communicated to Home Assistant.

Each entry in `discovery_entities` is an associative array with the
__required__ keys `component` and `config`.

- `component` - (str) One of the supported Home Assistant MQTT components,
eg. `binary_sensor`, `light`, `switch` [See here for a full list](https://www.home-assistant.io/docs/mqtt/discovery/)

- `config` - (associative array) The array is rendered into a __JSON__
string that is acceptable to Home Assistant.  The contents of what is
required in this JSON string are defined by the [Home Assistant
Discovery
Platform](https://www.home-assistant.io/docs/mqtt/discovery/).

  -  Each entry in this array is processed as a Jinja2 template, which
means that variable substitution and template logic can be used.

> The `config` array __must include__ an entry for `unique_id`
or `uniq_id` containing a unique id for this entity.  It is __strongly
recommended__ that you use the the device address as part of this
unique id.  The recommended format is `{{address}}_suffix` where the
suffix is something that plainly describes the nature of this entity.
Devices with only a single entity do not need a suffix, but it is
still good practice to use one.  The unique id is used internally by
HomeAssistant and is not otherwise visible to the user.

The `config` array has a number of variables available to it.  For
all devices this includes at minimum the following, devices may also
add additional variables unique to these devices:

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

- `device` = (str) a string which should bring in the standard device
  information; the recommended value is
  "{{device_info}}". Documentation of the `device_info` value can be
  found [here](discovery_customization_config.md#defaults).

- `availability_topic` = (str) the _availabiltiy_topic_ string as defined in
  the config.yaml file under the _mqtt_ key.

- `<<topics>>` = (str) topic keys as defined in the config.yaml
file under the _default class_ for this device are available as variables.

> The `<<topics>>` available are __always__ those listed under the
default class for this device.  So for a `dimmer` the topics will be
gathered from the `mqtt->dimmer` key.  Topics listed under a
user-defined `discovery_class` will be ignored.

Additional variables may be offered by specific device classes.
Those variables are defined in the [config-base.yaml](../insteon_mqtt/data/config-base.yaml) 
file under the relevant `mqtt` device keys.

#### JSON Dangers

> The entries in the `config` array __must generate valid JSON__. This is a
good JSON [validator](https://jsonformatter.curiousconcept.com/).

__Notable Gotchas__

1. __Newline Characters__ - JSON strings cannot contain raw newline
characters, they can however be represented by `\n`. Keep in mind that
the config template is first ingested from YAML.  You can read about
[how yaml handles whitespace](https://yaml-multiline.info/).  Second,
the config array entries are rendered through Jinja2.  You can read
about [how jinja handles
whitespace](https://tedboy.github.io/jinja2/templ6.html).

1. __Single Quotes__ - JSON requires doubles quotes, you __cannot__
use single quotes to define a string.  You can escape double quotes
with `\"`

#### Passing Jinja Templates as Values
Home Assistant uses Jinja2 templates as well, and in a number of cases
entities have configuration settings that contain a template.  If you
attempt to enter a template as a value, it will be rendered by
Insteon-MQTT, which in this case would likely result in an empty
value.

To pass an unrendered template on to Home Assistant __you must escape
the template__.  The template can be escaped using the `{% raw %}
{{escaped_stuff}} {% endraw %}` format.  For example:

```yaml
mqtt:
  climate:
    discovery_entities:
      sensor:
        component: "climate"
        config:
          .... # other settings
          temp_lo_stat_tpl: "{% raw %}{{value_json.temp_f}}{% endraw %}"
```

#### Example `discovery_entities`

```yaml
mqtt:
  # Other keys omitted
  dimmer:
    # Other keys omitted
    discovery_entities:
      light:
        component: 'light'
        config:
          uniq_id: "{{address}}_light"
          name: "{{name_user_case}}"
          cmd_t: "{{level_topic}}"
          stat_t: "{{state_topic}}"
          brightness: true
          schema: "json"
          device: "{{device_info}}"
```
