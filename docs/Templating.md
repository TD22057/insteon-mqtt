# Templating Overview
Insteon-MQTT makes extensive use of templating using the [Jinja2](https://jinja.palletsprojects.com/en/2.11.x/) templating language.  This makes Insteon-MQTT _very flexible_, however, __templating errors are by far the number one user issue.__ This document is meant to be a simple overview focused exclusively on how templating workins inside Insteon-MQTT with some references to HomeAssistant.  If you are interested in getting a thorough understanding of Jinja, there are many helpful documents online, some are listed at the bottom of this page.

## Why is Templating Needed?
Insteon-MQTT is designed to interact with any home automation system using the MQTT protocol.  In a simple example, when a light is turned on Insteon-MQTT sends a message to the home automation system using the MQTT protocol.  For example, the message may look like:
```
topic: insteon/aa.bb.cc/state
message: on
```

Similarly, the home automation system can turn on a light by sending the following message to Insteon-MQTT:
```
topic: insteon/aa.bb.cc/set
message: on
```

#### Templating is needed because the format of the message may need to be different
Not all home automation systems are going to ingest or publish messages in the same format.  For example, some systems or entities may use json encoded messages such as:
```
topic: insteon/aa.bb.cc/set
message: '{"cmd":"on"}'
```

Templating allows the user to describe the format of the message so that the data can be properly read or written.  It means that Insteon-MQTT can likely support any home automation system.  It also means, users can extend or alter the functionality of Insteon-MQTT to better suit their needs.

## Templating Basic Usage
In its most basic form, the Jinja2 templating language has two components __The Template__ and __The Values__.

#### The Template
A template is a script that when executed, commonly called rendered, will generate a string output.  The following is a basic example:

`This is a template` --> `This is a template`

This template always renders to the same string.  Not very interesting, but still a valid template, and in some cases this is necessary.

#### The Values
The most basic functionality of templating is the ability to use variables.  When rendering a template the variables are converted to their values.  So assuming that the variable `on_str` has the value `on` these templates will render as follows:

`{ "state" : "{{on_str}}" }` --> `{ "state" : "on" }`

`{{on_str}}` --> `on`

Variables are defined in the template using the notation `{{...}}` which is used for expressions.  When the rendering engine encounters `{{on_str}}` above, it checks to see if it has a variable names `on_str`, if it does, it replaced the tag with the value.

The availability of variables is controlled inside Insteon-MQTT.  You sadly can only use variables that have been defined, but the we try to make all logical variables available.  _If there is a variable you would like to use that is not present, please let us know._

If you attempt to use a variable that does not exist you will not get an error, but the value will be an empty string `""`.

#### Values Defined in Insteon-MQTT
Generally, the list of defined values can be found in the comments section in the sample config file.  The list of variables can be slightly different for different types of devices so pay attention.

##### Input Variables in Payloads
When parsing an incomming message payload, such as a message sent to `insteon/aa.bb.cc/set` Insteon-MQTT makes __only two__ variables available:

__value__ - Contains the raw string sent as the payload.

__json__ - Contains the json parsed object of the paylod.  So if the raw payload is `{ "cmd" : "on", "brightness": 255 }` then the template will render as follows:

`{{json.cmd}}` --> `on`

`{{json.brightness}}` --> `255`

## Templating and HomeAssistant

HomeAssistant also uses Jinja2 templating extensively.  HomeAssistant adds an extra layer of useful functions, but generally users do not need more than a basic understanding to achieve desired results.  In many cases, entities can be configured with templates for parsing messages.  HomeAssistant changes too frequently to try to address all of the instances of relevant templating here.  But luckily, the HomeAssistant documentation is well maintained.  See for example the [MQTT Light Entity](https://www.home-assistant.io/integrations/light.mqtt).  Frequently, the relevant configuration settings are names `*_template`.  Some common relevant configuration settings are `json_attributes_template`, `brightness_template`, `command_on_template`, `command_off_template`, and `state_template`.

## Templating Intermediate Usage
Jinja2 exposes a number of [builtin filters](https://jinja.palletsprojects.com/en/2.11.x/templates/#list-of-builtin-filters) that can be used to manipulate variables.  The most common filters you will likely encounter are `lower()` and `upper()` that can be used to convert the case of a variable.  For example if the variable `on_str` has the value `On` this template will produce the following result:

`Lower: {{on_str.lower()}} Upper:{{on_str.upper()}}` --> `Lower:on Upper:ON`

Please see the [Jinja Documentation](https://jinja.palletsprojects.com/en/2.11.x/templates/) for further explanation of filters.

## Templating Advanced Usage
Most advanced usage is beyond what is necessary in Insteon-MQTT with the exception of logical statements.  At times it may be necessary to alter the template depending on the existence of a variable.  Logic statments use the notation `{%...%}`.  The following is an example from the sample config file:

```
{ "cmd" : "{{json.state.lower()}}",
  "level" : {% if json.brightness is defined %}
               {{json.brightness}}
            {% else %}
               255
            {% endif %} }
```

This is used because, in some instances HomeAssistant sends an `On` command without providing any `brightness` data.  So when this template is rendered if the payload was `{ "state" : "ON" }` the rendered output would be:

```
{ "cmd" : "on"
  "level" : 255}
```

Similarly, if the payload was `{ "state" : "ON", "brightness" : 127 }` the rendered output would be:

```
{ "cmd" : "on"
  "level" : 127}
```

Please see the [Jinja Documentation](https://jinja.palletsprojects.com/en/2.11.x/templates/) for further advanced usage.

## Templating Debugging

[Online Jinja Renderer](https://cryptic-cliffs-32040.herokuapp.com/) - This website lets you plug in a template and sample values and then generates the output for you.  This can be helpful for begginners to visualize what is happening or for advanced users to test out complicated templates.

[Online JSON Renderer](https://jsonformatter.curiousconcept.com/) - Useful for testing if the output of your templates produces valid JSON.

### If a Variable always produces an empty string
Variables that do not exist will always render as an empty string.  Double check that you have spelled the variable correctly and that the variable is available for use in the template.

### ERROR MsgTemplate: Invalid JSON message
This error occurs when the template for an input topic such as `/set` or `/command` renders to improper JSON notation.  This message will be accompanied by the rendered output of the template as well as the template string.  Double check that the rendered output matches what it should. Try using the Online JSON Renderer above.

## Further Reading

[Jinja Documentation](https://jinja.palletsprojects.com/en/2.11.x/templates/) - The documentation is very detailed and easy to read with lots of examples.
