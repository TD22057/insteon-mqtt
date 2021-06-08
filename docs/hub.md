# Insteon Hub as a Modem
The Hub can be used as a modem instead of a PLM device.  However, you
must use either a PLM or a Hub, you cannot use both.

Hubs do not have any technical benefit over a PLM. But it may save you from
having to purchase a PLM if you already own a Hub.

> You can't use the features of the Hub (the Insteon Mobile app) with
> Insteon-Mqtt.  Any changes made using the Insteon Apps
> will not be reflected inside Insteon-Mqtt.

The interfaces available on Insteon Hubs have changed a bit over the years, be
sure to check you model number and follow the instructions for your hub.

<!-- TOC -->

  - [Older Generation Hubs](#older-generation-hubs)
    - [Configuration](#configuration)
  - [Current Generation Hubs](#current-generation-hubs)
    - [Configuration](#configuration-1)
    - [Caveats](#caveats)
    - [Notes](#notes)

<!-- /TOC -->

## Older Generation Hubs
Models:
- 2242-222 (~2012)

These hubs have a port(9761) that allows for direct serial commands.

### Configuration

```yaml
insteon:
  port: "socket://<IP Address>:9761"
  # where <IP Address> is the address of your hub.
  use_hub: False
```

> Be sure `use_hub` is false.

## Current Generation Hubs
Models:
- 2245-222 (~2016)

These hubs only have a http interface.  So all commands have to be issued over
http.

### Configuration

Configuring Insteon-Mqtt to use a Hub rather than the PLM is easy.  Simply
add the following lines to your config.yaml file.  In the sample file you will
see that they are near the top.

```yaml
insteon:
  use_hub: True
  hub_ip: <<ip address of Hub>>
  hub_user: <<username>>
  hub_password: <<password>>
```

The username and password can be found on a printed label on the underside of
your hub.  These values are unchangable.

### Caveats

Because modern hubs only have an http interface there are a few
downsides:
- Slightly slower response (approximately 1/4 of a second) because of how the
Hub works.
- If you use any of the direct integrations with the Hub such as
Alexa, Google Home, Logitech,... the states of your devices will not be
properly reflected in Insteon-Mqtt.  However, if these integrations are made
through Home Assistant, everything will work as normal.

### Notes

You may notice a lot of the following warnings in your log file.  This is
normal and they can be ignored:

`WARNING Protocol: No read handler found for message type`

These occur because the Insteon cloud, even when not using the Insteon App,
periodically polls the devices as well as performs other tasks.
