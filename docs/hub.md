# Insteon Hub as a Modem
The following Hub model numbers are known to work, others may as well.
- 2245-222

The Hub can be used as a modem instead of a PLM device.  However, you must use
either a PLM or a Hub, you cannot use both.

## Benefits

The only real benefit to using a Hub is that it may make it easier for you to
locate the modem more in the center of your house.  It also saves you from
having to purchase a PLM if you already own a Hub.

## Drawbacks

There are no major issues with using a Hub as your modem, but there are a few
downsides:
- Slightly slower response because of how the Hub works approximately 1/4 of a
second.
- You can't use the features of the Hub (the Insteon Mobile app) with
Insteon-Mqtt.  At least currently, any changes made using the Insteon Apps
will not be reflected inside Insteon-Mqtt.
- Similarly if you use any of the direct integrations with the Hub such as
Alexa, Google Home, Logitech,... the states of your devices will not be
properly reflected in Insteon-Mqtt.  However, if these integrations are made
through Home Assistant, everything will work as normal.

## Notes

If you use the hub, you may notice a lot of the following warnings in your log
file.  This is normal and they can be ignored:

*WARNING Protocol: No read handler found for message type*

These occur because the Hub, even when not using the Insteon App, periodically
polls the devices as well as performs other tasks.

## Configuration

Configuring Insteon-Mqtt to use a Hub rather than the PLM is easy.  Simply
add the following lines to your config.yaml file.  In the sample file you will
see that they are near the top.

use_hub: True
hub_ip: <<ip address of Hub>>
hub_user: <<username>>
hub_password: <<password>>

The username and password can be found on a printed label on the underside of
your hub.  These values are unchangable.
